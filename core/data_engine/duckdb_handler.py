import duckdb
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Iterator
import logging
from pathlib import Path
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class DuckDBHandler:
    """High-performance database handler using DuckDB for trading data"""
    
    def __init__(self, db_path: str = "trading_data.duckdb"):
        self.db_path = db_path
        self.logger = logger
        self.conn = None
        self._verify_db_file()
        self.connect()
        self._ensure_tables_exist()
        
    def connect(self):
        """Establish connection to DuckDB database"""
        self.logger.debug(f"Establishing DuckDB connection to {self.db_path}")
        self.conn = duckdb.connect(self.db_path)
        # Enable parallel processing
        self.conn.execute("SET enable_progress_bar=true")
        self.conn.execute("SET threads=4")
        self.logger.debug("DuckDB connection established")

    def _verify_db_file(self):
        """Check if database file exists and is accessible"""
        if self.db_path == ':memory:':
            return
            
        if not self.db_path.endswith('.duckdb'):
            raise ValueError("Database path must end with .duckdb extension")
        
        try:
            # Create directory if it doesn't exist
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        except IOError as e:
            raise PermissionError(f"Cannot access database directory: {self.db_path}") from e

    def _ensure_tables_exist(self):
        """Create tables if they don't exist"""
        try:
            # Create price bars table with optimized schema
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS price_bars (
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    timeframe VARCHAR(5) NOT NULL,
                    open DOUBLE NOT NULL,
                    high DOUBLE NOT NULL,
                    low DOUBLE NOT NULL,
                    close DOUBLE NOT NULL,
                    volume BIGINT NOT NULL,
                    PRIMARY KEY (timestamp, symbol, timeframe)
                )
            """)
            
            # Create indicators table for computed technical indicators
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    timeframe VARCHAR(5) NOT NULL,
                    indicator_name VARCHAR(50) NOT NULL,
                    value DOUBLE NOT NULL,
                    PRIMARY KEY (timestamp, symbol, timeframe, indicator_name)
                )
            """)
            
            # Create pattern matches table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_matches (
                    id BIGINT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    timeframe VARCHAR(5) NOT NULL,
                    pattern_type VARCHAR(50) NOT NULL,
                    entry_price DOUBLE NOT NULL,
                    stop_loss DOUBLE,
                    take_profit DOUBLE,
                    confidence DOUBLE NOT NULL,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create backtest results table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id BIGINT PRIMARY KEY,
                    strategy_name VARCHAR(100) NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    timeframe VARCHAR(5) NOT NULL,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    total_trades INTEGER NOT NULL,
                    winning_trades INTEGER NOT NULL,
                    losing_trades INTEGER NOT NULL,
                    win_rate DOUBLE NOT NULL,
                    avg_return DOUBLE NOT NULL,
                    total_return DOUBLE NOT NULL,
                    max_drawdown DOUBLE NOT NULL,
                    sharpe_ratio DOUBLE,
                    parameters JSON,
                    equity_curve JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indices for faster querying
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_price_bars_symbol_timeframe ON price_bars(symbol, timeframe)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_price_bars_timestamp ON price_bars(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_symbol_timeframe ON indicators(symbol, timeframe)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern_matches_symbol_timeframe ON pattern_matches(symbol, timeframe)")
            
            self.conn.commit()
            self.logger.debug("DuckDB tables and indices created/verified")
        except Exception as e:
            self.logger.error(f"Failed to create/verify tables: {str(e)}")
            raise

    def store_bars(self, symbol: str, timeframe: str, bars: pd.DataFrame, upsert: bool = True):
        """Store price bars in database with high performance"""
        if bars.empty:
            self.logger.warning(f"No data to store for {symbol} {timeframe}")
            return
            
        try:
            # Ensure timestamp is in UTC
            if 'timestamp' in bars.columns:
                bars = bars.copy()
                bars['timestamp'] = pd.to_datetime(bars['timestamp']).dt.tz_localize('UTC')
            else:
                bars = bars.copy()
                bars['timestamp'] = pd.to_datetime(bars.index).tz_localize('UTC')
            
            # Add symbol and timeframe columns
            bars['symbol'] = symbol
            bars['timeframe'] = timeframe
            
            # Select and rename columns to match schema
            columns_map = {
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }
            
            # Handle case-insensitive column names
            available_columns = {col.lower(): col for col in bars.columns}
            selected_columns = ['timestamp', 'symbol', 'timeframe']
            
            for target_col, source_col in columns_map.items():
                if source_col in available_columns:
                    selected_columns.append(available_columns[source_col])
                else:
                    self.logger.warning(f"Column {source_col} not found in data for {symbol} {timeframe}")
            
            bars_to_store = bars[selected_columns].copy()
            
            # Convert DataFrame to list of tuples for insertion
            data_to_insert = []
            for _, row in bars_to_store.iterrows():
                # Handle case-insensitive column names
                open_col = 'open' if 'open' in row else 'Open'
                high_col = 'high' if 'high' in row else 'High'
                low_col = 'low' if 'low' in row else 'Low'
                close_col = 'close' if 'close' in row else 'Close'
                volume_col = 'volume' if 'volume' in row else 'Volume'
                
                data_to_insert.append((
                    row['timestamp'],
                    row['symbol'],
                    row['timeframe'],
                    row[open_col],
                    row[high_col],
                    row[low_col],
                    row[close_col],
                    row[volume_col]
                ))
            
            # Use executemany for batch insertion
            if upsert:
                # Use DuckDB's efficient upsert
                self.conn.executemany("""
                    INSERT INTO price_bars (timestamp, symbol, timeframe, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (timestamp, symbol, timeframe) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """, data_to_insert)
            else:
                # Simple insert
                self.conn.executemany("""
                    INSERT INTO price_bars (timestamp, symbol, timeframe, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, data_to_insert)
            
            self.conn.commit()
            self.logger.info(f"Stored {len(bars_to_store)} bars for {symbol} {timeframe}")
            
        except Exception as e:
            self.logger.error(f"Failed to store bars for {symbol} {timeframe}: {str(e)}")
            raise

    def get_bars(self, symbol: str, timeframe: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> pd.DataFrame:
        """Retrieve price bars with optional date filtering"""
        try:
            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM price_bars 
                WHERE symbol = ? AND timeframe = ?
            """
            params = [symbol, timeframe]
            
            if start:
                query += " AND timestamp >= ?"
                params.append(start)
            if end:
                query += " AND timestamp <= ?"
                params.append(end)
                
            query += " ORDER BY timestamp"
            
            result = self.conn.execute(query, params).df()
            
            if not result.empty:
                result.set_index('timestamp', inplace=True)
                result.index = pd.to_datetime(result.index)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve bars for {symbol} {timeframe}: {str(e)}")
            return pd.DataFrame()

    def store_indicator(self, symbol: str, timeframe: str, indicator_name: str, values: pd.Series):
        """Store computed indicator values"""
        try:
            # Prepare data for insertion
            indicator_data = pd.DataFrame({
                'timestamp': values.index,
                'symbol': symbol,
                'timeframe': timeframe,
                'indicator_name': indicator_name,
                'value': values.values
            })
            
            # Remove any NaN values
            indicator_data = indicator_data.dropna()
            
            if indicator_data.empty:
                return
                
            # Upsert indicator values
            self.conn.execute("""
                INSERT INTO indicators (timestamp, symbol, timeframe, indicator_name, value)
                SELECT timestamp, symbol, timeframe, indicator_name, value
                FROM indicator_data
                ON CONFLICT (timestamp, symbol, timeframe, indicator_name) DO UPDATE SET
                    value = EXCLUDED.value
            """, {"indicator_data": indicator_data})
            
            self.conn.commit()
            self.logger.debug(f"Stored {len(indicator_data)} {indicator_name} values for {symbol} {timeframe}")
            
        except Exception as e:
            self.logger.error(f"Failed to store indicator {indicator_name} for {symbol} {timeframe}: {str(e)}")
            raise

    def get_indicator(self, symbol: str, timeframe: str, indicator_name: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> pd.Series:
        """Retrieve indicator values"""
        try:
            query = """
                SELECT timestamp, value
                FROM indicators 
                WHERE symbol = ? AND timeframe = ? AND indicator_name = ?
            """
            params = [symbol, timeframe, indicator_name]
            
            if start:
                query += " AND timestamp >= ?"
                params.append(start)
            if end:
                query += " AND timestamp <= ?"
                params.append(end)
                
            query += " ORDER BY timestamp"
            
            result = self.conn.execute(query, params).df()
            
            if not result.empty:
                result.set_index('timestamp', inplace=True)
                return result['value']
            
            return pd.Series(dtype=float)
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve indicator {indicator_name} for {symbol} {timeframe}: {str(e)}")
            return pd.Series(dtype=float)

    def store_pattern_match(self, pattern_match: Dict[str, Any]):
        """Store pattern match result"""
        try:
            self.conn.execute("""
                INSERT INTO pattern_matches 
                (timestamp, symbol, timeframe, pattern_type, entry_price, stop_loss, take_profit, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern_match['timestamp'],
                pattern_match['symbol'],
                pattern_match['timeframe'],
                pattern_match['pattern_type'],
                pattern_match['entry_price'],
                pattern_match.get('stop_loss'),
                pattern_match.get('take_profit'),
                pattern_match['confidence'],
                json.dumps(pattern_match.get('metadata', {}))
            ))
            
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store pattern match: {str(e)}")
            raise

    def store_backtest_result(self, backtest_result: Dict[str, Any]):
        """Store backtest result"""
        try:
            self.conn.execute("""
                INSERT INTO backtest_results 
                (strategy_name, symbol, timeframe, start_date, end_date, total_trades, 
                 winning_trades, losing_trades, win_rate, avg_return, total_return, 
                 max_drawdown, sharpe_ratio, parameters, equity_curve)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                backtest_result['strategy_name'],
                backtest_result['symbol'],
                backtest_result['timeframe'],
                backtest_result['start_date'],
                backtest_result['end_date'],
                backtest_result['total_trades'],
                backtest_result['winning_trades'],
                backtest_result['losing_trades'],
                backtest_result['win_rate'],
                backtest_result['avg_return'],
                backtest_result['total_return'],
                backtest_result['max_drawdown'],
                backtest_result.get('sharpe_ratio'),
                json.dumps(backtest_result.get('parameters', {})),
                json.dumps(backtest_result.get('equity_curve', []))
            ))
            
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store backtest result: {str(e)}")
            raise

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        try:
            result = self.conn.execute("SELECT DISTINCT symbol FROM price_bars ORDER BY symbol").df()
            return result['symbol'].tolist()
        except Exception as e:
            self.logger.error(f"Failed to get available symbols: {str(e)}")
            return []

    def get_available_timeframes(self, symbol: str) -> List[str]:
        """Get list of available timeframes for a symbol"""
        try:
            result = self.conn.execute(
                "SELECT DISTINCT timeframe FROM price_bars WHERE symbol = ? ORDER BY timeframe",
                [symbol]
            ).df()
            return result['timeframe'].tolist()
        except Exception as e:
            self.logger.error(f"Failed to get available timeframes for {symbol}: {str(e)}")
            return []

    def get_row_count(self, symbol: str, timeframe: str) -> int:
        """Get number of rows for a symbol/timeframe combination"""
        try:
            result = self.conn.execute(
                "SELECT COUNT(*) as count FROM price_bars WHERE symbol = ? AND timeframe = ?",
                [symbol, timeframe]
            ).df()
            return result['count'].iloc[0]
        except Exception as e:
            self.logger.error(f"Failed to get row count for {symbol} {timeframe}: {str(e)}")
            return 0

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.debug("DuckDB connection closed")

    def __del__(self):
        """Destructor to ensure connection is closed"""
        self.close() 