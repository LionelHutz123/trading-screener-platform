import sqlite3
import pandas as pd
import json
from typing import Optional, Dict, Any, Iterator
import logging
from pathlib import Path
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class SQLDatabaseHandler:
    """Handler for SQLite database operations"""
    
    def __init__(self, db_path: str = "financial_data.db"):
        self.db_path = db_path
        self.logger = logger
        self.conn = None
        self._verify_db_file()
        self.connect()
        self._ensure_tables_exist()
        
    def connect(self):
        """Establish connection to the database"""
        self.logger.debug(f"Establishing database connection")
        self.conn = sqlite3.connect(self.db_path)
        self.logger.debug("Database connection established")

    def _verify_db_file(self):
        """Check if database file exists and is accessible"""
        if self.db_path == ':memory:':
            return
            
        if not self.db_path.endswith('.db'):
            raise ValueError("Database path must end with .db extension")
        
        try:
            open(self.db_path, 'a').close()
        except IOError as e:
            raise PermissionError(f"Cannot access database file: {self.db_path}") from e

    def _ensure_tables_exist(self):
        """Create tables if they don't exist"""
        try:
            # Create price bars table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS price_bars (
                    timestamp DATETIME NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    timeframe VARCHAR(5) NOT NULL,
                    open FLOAT NOT NULL,
                    high FLOAT NOT NULL,
                    low FLOAT NOT NULL,
                    close FLOAT NOT NULL,
                    volume INTEGER NOT NULL,
                    PRIMARY KEY (timestamp, symbol, timeframe)
                )
            """)
            
            # Create optimization runs table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name VARCHAR(255) NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    timeframe VARCHAR(5) NOT NULL,
                    parameters JSON NOT NULL,
                    metrics JSON NOT NULL,
                    equity_curve BLOB,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create parameter sets table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS parameter_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name VARCHAR(255) NOT NULL,
                    parameters JSON NOT NULL,
                    performance_score FLOAT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(strategy_name, parameters)
                )
            """)
            
            # Create indices for faster querying
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON price_bars(symbol, timeframe)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON price_bars(timestamp)")
            
            self.conn.commit()
            self.logger.debug("Database tables and indices created/verified")
        except Exception as e:
            self.logger.error(f"Failed to create/verify tables: {str(e)}")
            raise

    def store_bars(self, symbol: str, timeframe: str, bars: pd.DataFrame, upsert: bool = True):
        """Store price bars in database"""
        if bars.empty:
            self.logger.warning(f"No data to store for {symbol} {timeframe}")
            return

        try:
            # Ensure column names are lowercase
            bars = bars.copy()
            bars.columns = bars.columns.str.lower()
            
            # Set timestamp as index if it's a column
            if 'timestamp' in bars.columns:
                bars = bars.set_index('timestamp')
            
            # Add symbol and timeframe if not present
            if 'symbol' not in bars.columns:
                bars['symbol'] = symbol
            if 'timeframe' not in bars.columns:
                bars['timeframe'] = timeframe

            # Use pandas to_sql with appropriate parameters
            bars.to_sql(
                'price_bars',
                self.conn,
                if_exists='replace' if upsert else 'fail',
                index=True,
                index_label='timestamp'
            )
            
            self.conn.commit()
            self.logger.info(f"Successfully stored {len(bars)} rows for {symbol} {timeframe}")
        except Exception as e:
            self.logger.error(f"Failed to store data for {symbol} {timeframe}: {str(e)}")
            raise

    def get_bars(self, symbol: str, timeframe: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> pd.DataFrame:
        """Get price bars from database"""
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

        query += " ORDER BY timestamp ASC"

        try:
            df = pd.read_sql_query(
                query,
                self.conn,
                params=tuple(params),
                parse_dates=['timestamp']
            )
            return df.set_index('timestamp')
        except Exception as e:
            self.logger.error(f"Error getting bars: {str(e)}")
            raise

    def get_bars_chunked(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        chunk_size: int = 1000
    ) -> Iterator[pd.DataFrame]:
        """Get price bars in chunks to handle large datasets"""
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

        query += " ORDER BY timestamp ASC"

        offset = 0
        while True:
            chunk_query = f"{query} LIMIT {chunk_size} OFFSET {offset}"
            df = pd.read_sql_query(
                chunk_query,
                self.conn,
                params=tuple(params),
                parse_dates=['timestamp']
            )
            if df.empty:
                break
            yield df.set_index('timestamp')
            offset += chunk_size

    def store_optimization_result(self, 
                                strategy_name: str,
                                symbol: str,
                                timeframe: str,
                                parameters: Dict[str, Any],
                                metrics: Dict[str, float],
                                equity_curve: Optional[np.ndarray] = None):
        """Store optimization run results"""
        try:
            # Convert numpy array to bytes for storage
            equity_bytes = None
            if equity_curve is not None:
                equity_bytes = equity_curve.tobytes()
            
            self.conn.execute("""
                INSERT INTO optimization_runs 
                (strategy_name, symbol, timeframe, parameters, metrics, equity_curve)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                strategy_name,
                symbol,
                timeframe,
                json.dumps(parameters),
                json.dumps(metrics),
                equity_bytes
            ))
            
            # Update parameter sets if performance improved
            score = metrics.get('sharpe_ratio', 0)
            self.conn.execute("""
                INSERT INTO parameter_sets 
                (strategy_name, parameters, performance_score)
                VALUES (?, ?, ?)
                ON CONFLICT(strategy_name, parameters) 
                DO UPDATE SET 
                    performance_score = CASE 
                        WHEN excluded.performance_score > performance_score 
                        THEN excluded.performance_score 
                        ELSE performance_score 
                    END
            """, (
                strategy_name,
                json.dumps(parameters),
                score
            ))
            
            self.conn.commit()
            self.logger.info(f"Stored optimization result for {strategy_name} {symbol} {timeframe}")
            
        except Exception as e:
            self.logger.error(f"Error storing optimization result: {str(e)}")
            raise

    def get_best_parameters(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get best performing parameters for a strategy"""
        try:
            cursor = self.conn.execute("""
                SELECT parameters, performance_score
                FROM parameter_sets
                WHERE strategy_name = ? AND is_active = 1
                ORDER BY performance_score DESC
                LIMIT 1
            """, (strategy_name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'parameters': json.loads(row[0]),
                    'score': row[1]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting best parameters: {str(e)}")
            raise

    def get_optimization_history(self, 
                               strategy_name: str,
                               symbol: Optional[str] = None,
                               limit: Optional[int] = None) -> pd.DataFrame:
        """Get optimization run history"""
        query = """
            SELECT 
                id, strategy_name, symbol, timeframe, 
                parameters, metrics, created_at
            FROM optimization_runs
            WHERE strategy_name = ?
        """
        params = [strategy_name]
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
            
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        try:
            df = pd.read_sql_query(
                query,
                self.conn,
                params=tuple(params),
                parse_dates=['created_at']
            )
            
            # Parse JSON columns
            df['parameters'] = df['parameters'].apply(json.loads)
            df['metrics'] = df['metrics'].apply(json.loads)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting optimization history: {str(e)}")
            raise

    def get_row_count(self, symbol: str, timeframe: str) -> int:
        """Get number of rows for a symbol and timeframe"""
        try:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM price_bars WHERE symbol = ? AND timeframe = ?",
                (symbol, timeframe)
            )
            return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    def clear_table(self, table_name: str):
        """Delete all records from a table"""
        try:
            self.conn.execute(f"DELETE FROM {table_name}")
            self.conn.commit()
            self.logger.info(f"Cleared all records from {table_name}")
        except Exception as e:
            self.logger.error(f"Error clearing table {table_name}: {str(e)}")
            raise

    def get_available_symbols(self) -> list[str]:
        """Get list of available symbols in the database"""
        cursor = self.conn.execute("SELECT DISTINCT symbol FROM price_bars")
        return [row[0] for row in cursor.fetchall()]

    def get_available_timeframes(self, symbol: str) -> list[str]:
        """Get list of available timeframes for a symbol"""
        cursor = self.conn.execute(
            "SELECT DISTINCT timeframe FROM price_bars WHERE symbol = ?",
            (symbol,)
        )
        return [row[0] for row in cursor.fetchall()]

    def is_connected(self) -> bool:
        """Check if database connection is active"""
        try:
            self.conn.execute("SELECT 1")
            return True
        except:
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information"""
        return {
            'connected': self.is_connected(),
            'database': self.db_path,
            'type': 'SQLite3'
        }

    def __del__(self):
        """Close database connection on object destruction"""
        if self.conn:
            self.conn.close() 