import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from ..duckdb_handler import DuckDBHandler
from ..historical.alpaca_data_fetcher import get_alpaca_data

logger = logging.getLogger(__name__)

class UpdateFrequency(Enum):
    REAL_TIME = "real_time"  # Every minute
    FREQUENT = "frequent"     # Every 5 minutes
    REGULAR = "regular"       # Every 15 minutes
    HOURLY = "hourly"        # Every hour
    DAILY = "daily"          # Once per day

@dataclass
class UpdateConfig:
    """Configuration for data updates"""
    # Update frequencies for different timeframes
    timeframe_frequencies: Dict[str, UpdateFrequency] = None
    
    # Batch settings
    batch_size: int = 10  # Number of symbols to update in parallel
    
    # Timing settings
    market_open: str = "09:30"  # Eastern Time
    market_close: str = "16:00"  # Eastern Time
    extended_hours: bool = True  # Include pre/post market
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    
    # Cache settings
    cache_duration: int = 300  # seconds
    
    def __post_init__(self):
        if self.timeframe_frequencies is None:
            self.timeframe_frequencies = {
                "1m": UpdateFrequency.REAL_TIME,
                "5m": UpdateFrequency.FREQUENT,
                "15m": UpdateFrequency.REGULAR,
                "1h": UpdateFrequency.HOURLY,
                "4h": UpdateFrequency.HOURLY,
                "1d": UpdateFrequency.DAILY
            }

@dataclass
class UpdateTask:
    """Represents a data update task"""
    symbol: str
    timeframe: str
    last_update: Optional[datetime]
    next_update: datetime
    priority: int  # Lower number = higher priority
    retry_count: int = 0

class DataUpdateScheduler:
    """Manages scheduled updates of market data"""
    
    def __init__(self, db_handler: DuckDBHandler, config: UpdateConfig = None):
        self.db_handler = db_handler
        self.config = config or UpdateConfig()
        self.logger = logger
        
        # Task management
        self.update_queue: List[UpdateTask] = []
        self.active_tasks: Set[str] = set()
        self.last_update_times: Dict[str, datetime] = {}
        
        # State
        self.is_running = False
        self.update_task = None
        self.monitor_task = None
        
        # Statistics
        self.stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_cycle_time": None
        }
        
        # Load state from disk if exists
        self._load_state()
    
    async def start(self, symbols: List[str], timeframes: List[str]):
        """Start the update scheduler"""
        try:
            self.is_running = True
            
            # Initialize update tasks
            self._initialize_tasks(symbols, timeframes)
            
            # Start update loop
            self.update_task = asyncio.create_task(self._update_loop())
            
            # Start monitor loop
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            
            self.logger.info(f"Started update scheduler for {len(symbols)} symbols and {len(timeframes)} timeframes")
            
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {str(e)}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the update scheduler"""
        self.is_running = False
        
        # Cancel tasks
        if self.update_task:
            self.update_task.cancel()
        if self.monitor_task:
            self.monitor_task.cancel()
        
        # Save state
        self._save_state()
        
        self.logger.info("Update scheduler stopped")
    
    def _initialize_tasks(self, symbols: List[str], timeframes: List[str]):
        """Initialize update tasks for all symbol/timeframe combinations"""
        current_time = datetime.now(timezone.utc)
        
        for symbol in symbols:
            for timeframe in timeframes:
                # Get last update time from database
                last_update = self._get_last_update_time(symbol, timeframe)
                
                # Calculate next update time
                frequency = self.config.timeframe_frequencies.get(timeframe, UpdateFrequency.REGULAR)
                next_update = self._calculate_next_update(last_update, frequency)
                
                # Determine priority based on timeframe
                priority = self._get_priority(timeframe)
                
                # Create task
                task = UpdateTask(
                    symbol=symbol,
                    timeframe=timeframe,
                    last_update=last_update,
                    next_update=next_update,
                    priority=priority
                )
                
                self.update_queue.append(task)
        
        # Sort queue by next update time and priority
        self._sort_queue()
    
    async def _update_loop(self):
        """Main update loop"""
        while self.is_running:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check if market is open (if relevant)
                if not self._is_update_time(current_time):
                    await asyncio.sleep(60)  # Check every minute
                    continue
                
                # Get tasks due for update
                due_tasks = self._get_due_tasks(current_time)
                
                if due_tasks:
                    # Process in batches
                    for i in range(0, len(due_tasks), self.config.batch_size):
                        batch = due_tasks[i:i + self.config.batch_size]
                        await self._process_batch(batch)
                    
                    self.stats["last_cycle_time"] = datetime.now(timezone.utc)
                
                # Short sleep to prevent tight loop
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in update loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _monitor_loop(self):
        """Monitor scheduler health and log statistics"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Log every 5 minutes
                
                self.logger.info(f"Scheduler stats: {json.dumps(self.stats, default=str)}")
                self.logger.info(f"Queue size: {len(self.update_queue)}, Active tasks: {len(self.active_tasks)}")
                
                # Check for stuck tasks
                self._check_stuck_tasks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {str(e)}")
    
    async def _process_batch(self, tasks: List[UpdateTask]):
        """Process a batch of update tasks"""
        # Create coroutines for all tasks
        coroutines = [self._update_data(task) for task in tasks]
        
        # Run in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Process results
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to update {task.symbol} {task.timeframe}: {str(result)}")
                self._handle_failed_task(task)
            else:
                self._handle_successful_task(task)
    
    async def _update_data(self, task: UpdateTask):
        """Update data for a specific task"""
        task_key = f"{task.symbol}_{task.timeframe}"
        
        try:
            # Mark as active
            self.active_tasks.add(task_key)
            
            # Determine update range
            start_date, end_date = self._get_update_range(task)
            
            self.logger.info(f"Updating {task.symbol} {task.timeframe} from {start_date} to {end_date}")
            
            # Fetch new data
            result = await asyncio.to_thread(
                get_alpaca_data,
                symbols=[task.symbol],
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                timeframes=[task.timeframe],
                use_database=True,
                save_to_csv=False
            )
            
            # Update statistics
            if result and task.symbol in result and task.timeframe in result[task.symbol]:
                data = result[task.symbol][task.timeframe]
                if data is not None and not data.empty:
                    self.stats["successful_updates"] += 1
                    self.last_update_times[task_key] = datetime.now(timezone.utc)
                    return True
            
            raise ValueError("No data returned")
            
        except Exception as e:
            self.stats["failed_updates"] += 1
            raise e
        finally:
            self.stats["total_updates"] += 1
            self.active_tasks.discard(task_key)
    
    def _get_update_range(self, task: UpdateTask) -> tuple[datetime, datetime]:
        """Determine the date range for update"""
        end_date = datetime.now(timezone.utc)
        
        if task.last_update:
            # Update from last data point
            start_date = task.last_update - timedelta(hours=1)  # Small overlap
        else:
            # Initial load - get appropriate history based on timeframe
            if task.timeframe in ['1m', '5m', '15m']:
                start_date = end_date - timedelta(days=7)
            elif task.timeframe in ['1h', '4h']:
                start_date = end_date - timedelta(days=30)
            else:  # Daily
                start_date = end_date - timedelta(days=365)
        
        return start_date, end_date
    
    def _handle_successful_task(self, task: UpdateTask):
        """Handle successful task completion"""
        task.last_update = datetime.now(timezone.utc)
        task.retry_count = 0
        
        # Calculate next update
        frequency = self.config.timeframe_frequencies.get(task.timeframe, UpdateFrequency.REGULAR)
        task.next_update = self._calculate_next_update(task.last_update, frequency)
        
        # Re-sort queue
        self._sort_queue()
    
    def _handle_failed_task(self, task: UpdateTask):
        """Handle failed task"""
        task.retry_count += 1
        
        if task.retry_count < self.config.max_retries:
            # Schedule retry
            task.next_update = datetime.now(timezone.utc) + timedelta(
                seconds=self.config.retry_delay * task.retry_count
            )
        else:
            # Max retries reached, schedule for next regular update
            self.logger.error(f"Max retries reached for {task.symbol} {task.timeframe}")
            frequency = self.config.timeframe_frequencies.get(task.timeframe, UpdateFrequency.REGULAR)
            task.next_update = self._calculate_next_update(datetime.now(timezone.utc), frequency)
            task.retry_count = 0
        
        # Re-sort queue
        self._sort_queue()
    
    def _calculate_next_update(self, last_update: Optional[datetime], frequency: UpdateFrequency) -> datetime:
        """Calculate next update time based on frequency"""
        base_time = last_update or datetime.now(timezone.utc)
        
        if frequency == UpdateFrequency.REAL_TIME:
            return base_time + timedelta(minutes=1)
        elif frequency == UpdateFrequency.FREQUENT:
            return base_time + timedelta(minutes=5)
        elif frequency == UpdateFrequency.REGULAR:
            return base_time + timedelta(minutes=15)
        elif frequency == UpdateFrequency.HOURLY:
            return base_time + timedelta(hours=1)
        elif frequency == UpdateFrequency.DAILY:
            # Update at market open
            next_day = base_time + timedelta(days=1)
            return next_day.replace(hour=14, minute=30, second=0)  # 9:30 AM ET in UTC
        
        return base_time + timedelta(minutes=15)  # Default
    
    def _get_priority(self, timeframe: str) -> int:
        """Get priority based on timeframe"""
        priority_map = {
            "1m": 1,
            "5m": 2,
            "15m": 3,
            "1h": 4,
            "4h": 5,
            "1d": 6
        }
        return priority_map.get(timeframe, 10)
    
    def _is_update_time(self, current_time: datetime) -> bool:
        """Check if updates should run at current time"""
        # Convert to Eastern Time for market hours check
        # For now, always return True if extended hours are enabled
        if self.config.extended_hours:
            return True
        
        # Otherwise check market hours
        # This is simplified - you'd want proper timezone handling
        hour = current_time.hour
        return 13 <= hour <= 21  # Roughly 9 AM - 5 PM ET in UTC
    
    def _get_due_tasks(self, current_time: datetime) -> List[UpdateTask]:
        """Get tasks that are due for update"""
        due_tasks = []
        
        for task in self.update_queue:
            if task.next_update <= current_time:
                task_key = f"{task.symbol}_{task.timeframe}"
                if task_key not in self.active_tasks:
                    due_tasks.append(task)
            else:
                # Queue is sorted, so we can break early
                break
        
        return due_tasks
    
    def _sort_queue(self):
        """Sort update queue by next update time and priority"""
        self.update_queue.sort(key=lambda t: (t.next_update, t.priority))
    
    def _check_stuck_tasks(self):
        """Check for tasks that have been active too long"""
        current_time = datetime.now(timezone.utc)
        stuck_threshold = timedelta(minutes=10)
        
        for task_key in list(self.active_tasks):
            if task_key in self.last_update_times:
                if current_time - self.last_update_times[task_key] > stuck_threshold:
                    self.logger.warning(f"Task {task_key} appears stuck, removing from active tasks")
                    self.active_tasks.discard(task_key)
    
    def _get_last_update_time(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """Get last update time from database"""
        try:
            # Query database for most recent data point
            data = self.db_handler.get_bars(
                symbol, 
                timeframe, 
                limit=1,
                order='DESC'
            )
            
            if not data.empty:
                return pd.Timestamp(data.index[-1], tz='UTC')
            
        except Exception as e:
            self.logger.error(f"Error getting last update time: {str(e)}")
        
        return None
    
    def _save_state(self):
        """Save scheduler state to disk"""
        try:
            state = {
                "last_update_times": {k: v.isoformat() for k, v in self.last_update_times.items()},
                "stats": self.stats
            }
            
            state_file = Path("data/scheduler_state.json")
            state_file.parent.mkdir(exist_ok=True)
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
    
    def _load_state(self):
        """Load scheduler state from disk"""
        try:
            state_file = Path("data/scheduler_state.json")
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                # Restore last update times
                for key, value in state.get("last_update_times", {}).items():
                    self.last_update_times[key] = datetime.fromisoformat(value)
                
                # Restore stats
                self.stats.update(state.get("stats", {}))
                
                self.logger.info("Loaded scheduler state from disk")
                
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
    
    def add_symbols(self, symbols: List[str], timeframes: List[str]):
        """Add new symbols to the update schedule"""
        self._initialize_tasks(symbols, timeframes)
        self._sort_queue()
        self.logger.info(f"Added {len(symbols)} symbols to update schedule")
    
    def remove_symbols(self, symbols: List[str]):
        """Remove symbols from the update schedule"""
        symbols_set = set(symbols)
        self.update_queue = [t for t in self.update_queue if t.symbol not in symbols_set]
        self.logger.info(f"Removed {len(symbols)} symbols from update schedule")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "queue_size": len(self.update_queue),
            "active_tasks": len(self.active_tasks),
            "stats": self.stats,
            "next_updates": [
                {
                    "symbol": t.symbol,
                    "timeframe": t.timeframe,
                    "next_update": t.next_update.isoformat(),
                    "retry_count": t.retry_count
                }
                for t in self.update_queue[:10]  # First 10 tasks
            ]
        }