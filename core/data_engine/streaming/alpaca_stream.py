import websockets
import json
import asyncio
import logging
import base64
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from .real_time_processor import RealTimeProcessor
from ..historical.sql_database import SQLDatabaseHandler

@dataclass
class AlpacaStreamConfig:
    api_key: str
    secret_key: str
    paper_trading: bool = True
    
    @property
    def trading_ws_url(self) -> str:
        """Get WebSocket URL for trading updates"""
        return "wss://paper-api.alpaca.markets/stream" if self.paper_trading else "wss://api.alpaca.markets/stream"
    
    @property
    def data_ws_url(self) -> str:
        """Get WebSocket URL for market data"""
        return "wss://stream.data.alpaca.markets/v2/iex" if self.paper_trading else "wss://stream.data.alpaca.markets/v2/sip"

class AlpacaStreamClient:
    """Client for streaming real-time data from Alpaca"""
    
    def __init__(self, config: AlpacaStreamConfig, db_handler: Optional[SQLDatabaseHandler] = None):
        self.config = config
        self.trading_ws = None
        self.data_ws = None
        self.subscribed_streams: Dict[str, List[str]] = {"trading": [], "data": []}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Initialize database handler and real-time processor
        self.db_handler = db_handler or SQLDatabaseHandler()
        self.processor = RealTimeProcessor(self.db_handler)
        
    async def connect(self):
        """Establish WebSocket connections and authenticate"""
        try:
            # Connect to trading WebSocket
            self.trading_ws = await websockets.connect(self.config.trading_ws_url)
            await self._authenticate_trading()
            
            # Connect to data WebSocket
            self.data_ws = await websockets.connect(self.config.data_ws_url)
            await self._authenticate_data()
            
            self.running = True
            self.logger.info("Successfully connected to Alpaca WebSockets")
        except Exception as e:
            self.logger.error(f"Failed to connect: {str(e)}")
            raise
            
    async def _authenticate_trading(self):
        """Authenticate with Alpaca trading API"""
        auth_msg = {
            "action": "auth",
            "key": self.config.api_key,
            "secret": self.config.secret_key
        }
        
        self.logger.debug("Sending auth message to trading API")
        await self.trading_ws.send(json.dumps(auth_msg))
        
        response = await self.trading_ws.recv()
        auth_response = json.loads(response)
        self.logger.debug(f"Received auth response from trading API: {auth_response}")
        
        if (auth_response.get("stream") == "authorization" and 
            auth_response.get("data", {}).get("status") == "authorized"):
            self.logger.info("Successfully authenticated with Alpaca trading API")
        else:
            raise Exception(f"Failed to authenticate with Alpaca trading API: {auth_response}")
            
    async def _authenticate_data(self):
        """Authenticate with Alpaca data API"""
        # Wait for initial connection message
        response = await self.data_ws.recv()
        connection_response = json.loads(response)
        self.logger.debug(f"Received connection response from data API: {connection_response}")
        
        if not (isinstance(connection_response, list) and 
                connection_response[0].get("T") == "success" and 
                connection_response[0].get("msg") == "connected"):
            raise Exception(f"Failed to connect to data API: {connection_response}")
        
        # Send authentication message
        auth_msg = {
            "action": "auth",
            "key": self.config.api_key,
            "secret": self.config.secret_key
        }
        
        self.logger.debug(f"Sending auth message to data API: {auth_msg}")
        await self.data_ws.send(json.dumps(auth_msg))
        
        # Wait for authentication response
        response = await self.data_ws.recv()
        auth_response = json.loads(response)
        self.logger.debug(f"Received auth response from data API: {auth_response}")
        
        if isinstance(auth_response, list):
            msg = auth_response[0]
            if msg.get("T") == "success" and msg.get("msg") == "authenticated":
                self.logger.info("Successfully authenticated with Alpaca data API")
                return
        raise Exception(f"Failed to authenticate with Alpaca data API: {auth_response}")
            
    async def subscribe(self, streams: List[str]):
        """Subscribe to specified data streams"""
        trading_streams = [s for s in streams if s == "trade_updates"]
        data_streams = [s for s in streams if s != "trade_updates"]
        
        if trading_streams and self.trading_ws:
            await self._subscribe_trading(trading_streams)
            
        if data_streams and self.data_ws:
            await self._subscribe_data(data_streams)
            
    async def _subscribe_trading(self, streams: List[str]):
        """Subscribe to trading streams"""
        subscribe_msg = {
            "action": "listen",
            "data": {
                "streams": streams
            }
        }
        
        self.logger.debug(f"Sending subscribe message to trading API: {subscribe_msg}")
        await self.trading_ws.send(json.dumps(subscribe_msg))
        
        response = await self.trading_ws.recv()
        listen_response = json.loads(response)
        self.logger.debug(f"Received subscribe response from trading API: {listen_response}")
        
        if listen_response.get("stream") == "listening":
            self.subscribed_streams["trading"] = streams
            self.logger.info(f"Successfully subscribed to trading streams: {streams}")
        else:
            raise Exception(f"Failed to subscribe to trading streams: {listen_response}")
            
    async def _subscribe_data(self, streams: List[str]):
        """Subscribe to market data streams"""
        # Categorize streams
        trades = [s.replace("T.", "") for s in streams if s.startswith("T.")]
        quotes = [s.replace("Q.", "") for s in streams if s.startswith("Q.")]
        bars = [s.replace("AM.", "") for s in streams if s.startswith("AM.")]
        
        subscribe_msg = {
            "action": "subscribe",
            "trades": trades,
            "quotes": quotes,
            "bars": bars
        }
        
        self.logger.debug(f"Sending subscribe message to data API: {subscribe_msg}")
        await self.data_ws.send(json.dumps(subscribe_msg))
        
        # Wait for subscription response
        response = await self.data_ws.recv()
        subscription_response = json.loads(response)
        self.logger.debug(f"Received response from data API: {subscription_response}")
        
        if isinstance(subscription_response, list):
            msg = subscription_response[0]
            if msg.get("T") == "subscription":
                self.subscribed_streams["data"] = streams
                self.logger.info(f"Successfully subscribed to market data streams: {streams}")
                return
                
        raise Exception(f"Failed to subscribe to market data streams: {subscription_response}")
            
    def on_trade_update(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for trade updates"""
        if "trade_updates" not in self.callbacks:
            self.callbacks["trade_updates"] = []
        self.callbacks["trade_updates"].append(callback)
        
    async def _process_message(self, message: Dict[str, Any], source: str):
        """Process incoming WebSocket messages"""
        try:
            if source == "trading":
                stream = message.get("stream")
                if stream and stream in self.callbacks:
                    for callback in self.callbacks[stream]:
                        try:
                            await callback(message["data"])
                        except Exception as e:
                            self.logger.error(f"Error in callback for stream {stream}: {str(e)}")
            else:  # data stream
                if isinstance(message, list):
                    for msg in message:
                        await self._process_data_message(msg)
                else:
                    await self._process_data_message(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            
    async def _process_data_message(self, msg: Dict):
        """Process a single data message"""
        try:
            msg_type = msg.get("T")
            
            # Process message based on type
            if msg_type == "t":  # Trade
                await self.processor.process_trade(msg)
            elif msg_type == "b":  # Bar
                await self.processor.process_bar(msg)
                
            # Call registered callbacks
            if msg_type in self.callbacks:
                for callback in self.callbacks[msg_type]:
                    try:
                        await callback(msg)
                    except Exception as e:
                        self.logger.error(f"Error in callback for message type {msg_type}: {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"Error processing data message: {str(e)}")
            
    def get_latest_signals(self, symbol: Optional[str] = None) -> Dict:
        """Get latest signals from the processor"""
        return self.processor.get_latest_signals(symbol)
            
    async def start_streaming(self):
        """Start processing WebSocket messages"""
        if not (self.trading_ws or self.data_ws):
            raise Exception("WebSocket not connected")
            
        self.logger.info("Starting message processing loop")
        try:
            while self.running:
                # Create tasks for both WebSocket connections
                tasks = []
                if self.trading_ws:
                    tasks.append(asyncio.create_task(self._process_trading_messages()))
                if self.data_ws:
                    tasks.append(asyncio.create_task(self._process_data_messages()))
                    
                # Wait for any task to complete (or fail)
                await asyncio.gather(*tasks)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
            await self.reconnect()
        except Exception as e:
            self.logger.error(f"Error in message processing: {str(e)}")
            raise
            
    async def _process_trading_messages(self):
        """Process messages from trading WebSocket"""
        while self.running:
            try:
                message = await self.trading_ws.recv()
                await self._process_message(json.loads(message), "trading")
            except Exception as e:
                self.logger.error(f"Error processing trading message: {str(e)}")
            
    async def _process_data_messages(self):
        """Process messages from data WebSocket"""
        while self.running:
            try:
                message = await self.data_ws.recv()
                await self._process_message(json.loads(message), "data")
            except Exception as e:
                self.logger.error(f"Error processing data message: {str(e)}")
            
    async def reconnect(self):
        """Reconnect to WebSocket and resubscribe to streams"""
        self.logger.info("Attempting to reconnect...")
        await self.connect()
        if self.subscribed_streams["trading"]:
            await self._subscribe_trading(self.subscribed_streams["trading"])
        if self.subscribed_streams["data"]:
            await self._subscribe_data(self.subscribed_streams["data"])
            
    async def stop(self):
        """Stop streaming and close connections"""
        self.running = False
        if self.trading_ws:
            await self.trading_ws.close()
        if self.data_ws:
            await self.data_ws.close()
        self.logger.info("WebSocket connections closed") 