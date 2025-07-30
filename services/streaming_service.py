import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
from pathlib import Path

from core.data_engine.duckdb_handler import DuckDBHandler
from core.data_engine.streaming.alpaca_stream_handler import AlpacaStreamHandler, StreamConfig
from core.data_engine.streaming.data_update_scheduler import DataUpdateScheduler, UpdateConfig
from core.signal_processor.real_time_processor import RealTimeSignalProcessor, ProcessorConfig, TradingSignal
from core.alerts.alert_manager import AlertManager, AlertConfig, AlertType

logger = logging.getLogger(__name__)

class StreamingService:
    """Unified service for real-time data streaming and signal processing"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logger
        self.is_running = False
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize database
        self.db_handler = DuckDBHandler(self.config.get('database_path', 'trading_data.duckdb'))
        
        # Initialize components
        self._initialize_components()
        
        # Service tasks
        self.tasks = []
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            'database_path': 'trading_data.duckdb',
            'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
            'timeframes': ['1m', '5m', '15m', '1h', '4h'],
            'alpaca': {
                'api_key': '',
                'secret_key': '',
                'base_url': 'https://data.alpaca.markets',
                'data_feed': 'sip'
            },
            'alerts': {
                'smtp_host': '',
                'smtp_port': 587,
                'smtp_username': '',
                'smtp_password': '',
                'email_from': 'alerts@tradingscreener.com'
            }
        }
    
    def _initialize_components(self):
        """Initialize all service components"""
        # Stream handler configuration
        stream_config = StreamConfig(
            api_key=self.config['alpaca']['api_key'],
            secret_key=self.config['alpaca']['secret_key'],
            base_url=self.config['alpaca']['base_url'],
            data_feed=self.config['alpaca']['data_feed']
        )
        
        # Initialize components
        self.stream_handler = AlpacaStreamHandler(stream_config, self.db_handler)
        self.update_scheduler = DataUpdateScheduler(self.db_handler)
        self.signal_processor = RealTimeSignalProcessor(self.db_handler)
        
        # Alert manager configuration
        alert_config = AlertConfig(
            smtp_host=self.config['alerts'].get('smtp_host', ''),
            smtp_port=self.config['alerts'].get('smtp_port', 587),
            smtp_username=self.config['alerts'].get('smtp_username', ''),
            smtp_password=self.config['alerts'].get('smtp_password', ''),
            email_from=self.config['alerts'].get('email_from', '')
        )
        self.alert_manager = AlertManager(alert_config)
        
        # Set up callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Set up callbacks between components"""
        # Signal processor callback for new signals
        async def on_new_signal(signal: TradingSignal):
            await self.alert_manager.create_signal_alert(signal)
        
        self.signal_processor.register_callback(on_new_signal)
        
        # Stream handler callback for real-time analysis
        from core.data_engine.streaming.alpaca_stream_handler import StreamDataType
        
        async def on_new_bar(market_data):
            # Trigger immediate analysis for critical symbols
            if market_data.symbol in ['AAPL', 'TSLA', 'SPY']:
                await self.signal_processor.process_symbol(
                    market_data.symbol,
                    '1m'  # Process 1-minute bars in real-time
                )
        
        self.stream_handler.register_callback(StreamDataType.BAR, on_new_bar)
    
    async def start(self):
        """Start the streaming service"""
        try:
            self.is_running = True
            self.logger.info("Starting streaming service...")
            
            # Get symbols and timeframes from config
            symbols = self.config.get('symbols', [])
            timeframes = self.config.get('timeframes', [])
            
            # Start alert manager
            alert_task = asyncio.create_task(self.alert_manager.start())
            self.tasks.append(alert_task)
            
            # Start signal processor
            processor_task = asyncio.create_task(self.signal_processor.start())
            self.tasks.append(processor_task)
            
            # Start update scheduler
            scheduler_task = asyncio.create_task(
                self.update_scheduler.start(symbols, timeframes)
            )
            self.tasks.append(scheduler_task)
            
            # Start stream handler
            stream_task = asyncio.create_task(
                self.stream_handler.start(symbols)
            )
            self.tasks.append(stream_task)
            
            # Create system startup alert
            await self.alert_manager.create_system_alert(
                "Streaming Service Started",
                f"Service started with {len(symbols)} symbols and {len(timeframes)} timeframes"
            )
            
            self.logger.info("Streaming service started successfully")
            
            # Wait for tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"Error starting streaming service: {str(e)}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the streaming service"""
        self.logger.info("Stopping streaming service...")
        self.is_running = False
        
        # Create system shutdown alert
        try:
            await self.alert_manager.create_system_alert(
                "Streaming Service Stopping",
                "Service is shutting down"
            )
        except:
            pass
        
        # Stop components in reverse order
        await self.stream_handler.stop()
        await self.update_scheduler.stop()
        await self.signal_processor.stop()
        await self.alert_manager.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Close database
        self.db_handler.close()
        
        self.logger.info("Streaming service stopped")
    
    async def add_symbols(self, symbols: List[str]):
        """Add new symbols to monitoring"""
        # Add to stream handler
        await self.stream_handler.subscribe_symbols(symbols)
        
        # Add to update scheduler
        self.update_scheduler.add_symbols(symbols, self.config.get('timeframes', []))
        
        # Create alert
        await self.alert_manager.create_system_alert(
            "Symbols Added",
            f"Added {len(symbols)} symbols: {', '.join(symbols)}"
        )
    
    async def remove_symbols(self, symbols: List[str]):
        """Remove symbols from monitoring"""
        # Remove from stream handler
        await self.stream_handler.unsubscribe_symbols(symbols)
        
        # Remove from update scheduler
        self.update_scheduler.remove_symbols(symbols)
        
        # Create alert
        await self.alert_manager.create_system_alert(
            "Symbols Removed",
            f"Removed {len(symbols)} symbols: {', '.join(symbols)}"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'is_running': self.is_running,
            'components': {
                'stream_handler': {
                    'subscribed_symbols': len(self.stream_handler.subscribed_symbols),
                    'is_running': self.stream_handler.is_running
                },
                'update_scheduler': {
                    'status': self.update_scheduler.get_status()
                },
                'signal_processor': {
                    'active_signals': len(self.signal_processor.active_signals),
                    'stats': self.signal_processor.get_statistics()
                },
                'alert_manager': {
                    'stats': self.alert_manager.get_statistics()
                }
            }
        }
    
    def get_active_signals(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active trading signals"""
        signals = self.signal_processor.get_active_signals(symbol)
        return [signal.to_dict() for signal in signals]
    
    async def test_alert_system(self):
        """Test the alert system"""
        await self.alert_manager.create_system_alert(
            "Alert System Test",
            "This is a test alert to verify the notification system is working",
            priority=self.signal_processor.SignalPriority.HIGH
        )

async def main():
    """Main entry point for streaming service"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config_path = "config/streaming_config.json"
    
    # Create and start service
    service = StreamingService(config_path)
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main())