import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from collections import deque
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..signal_processor.real_time_processor import TradingSignal, SignalPriority

logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    SMS = "sms"
    TELEGRAM = "telegram"
    DISCORD = "discord"

class AlertType(Enum):
    SIGNAL_CREATED = "signal_created"
    SIGNAL_TRIGGERED = "signal_triggered"
    SIGNAL_EXECUTED = "signal_executed"
    SIGNAL_EXPIRED = "signal_expired"
    MARKET_ALERT = "market_alert"
    SYSTEM_ALERT = "system_alert"

@dataclass
class AlertConfig:
    """Configuration for alert manager"""
    # Email settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    
    # Webhook settings
    webhook_urls: Dict[str, str] = field(default_factory=dict)  # channel -> url
    webhook_timeout: int = 10  # seconds
    
    # Filtering settings
    min_priority: SignalPriority = SignalPriority.MEDIUM
    enabled_channels: List[NotificationChannel] = field(
        default_factory=lambda: [NotificationChannel.EMAIL, NotificationChannel.WEBSOCKET]
    )
    
    # Rate limiting
    max_alerts_per_minute: int = 10
    max_alerts_per_symbol: int = 5
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    
    # Queue settings
    max_queue_size: int = 1000
    batch_size: int = 10
    processing_interval: int = 5  # seconds

@dataclass
class Alert:
    """Represents an alert"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alert_type: AlertType = AlertType.SIGNAL_CREATED
    priority: SignalPriority = SignalPriority.MEDIUM
    
    # Alert content
    title: str = ""
    message: str = ""
    symbol: Optional[str] = None
    signal_id: Optional[str] = None
    
    # Delivery settings
    channels: List[NotificationChannel] = field(default_factory=list)
    recipients: Dict[str, List[str]] = field(default_factory=dict)  # channel -> recipients
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Delivery status
    delivered_channels: List[NotificationChannel] = field(default_factory=list)
    failed_channels: List[NotificationChannel] = field(default_factory=list)
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "alert_type": self.alert_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "symbol": self.symbol,
            "signal_id": self.signal_id,
            "channels": [c.value for c in self.channels],
            "recipients": self.recipients,
            "metadata": self.metadata,
            "delivered_channels": [c.value for c in self.delivered_channels],
            "failed_channels": [c.value for c in self.failed_channels],
            "retry_count": self.retry_count
        }

class AlertManager:
    """Manages alert queue and notifications"""
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.logger = logger
        
        # Alert queue
        self.alert_queue: deque = deque(maxlen=config.max_queue_size)
        self.processing_queue: List[Alert] = []
        
        # Rate limiting
        self.rate_limiter: Dict[str, deque] = {}  # key -> timestamps
        
        # WebSocket connections (for real-time updates)
        self.websocket_connections: List[Any] = []
        
        # Processing state
        self.is_running = False
        self.processing_task = None
        
        # Statistics
        self.stats = {
            "total_alerts": 0,
            "delivered_alerts": 0,
            "failed_alerts": 0,
            "alerts_by_type": {t.value: 0 for t in AlertType},
            "alerts_by_channel": {c.value: 0 for c in NotificationChannel}
        }
        
        # HTTP session for webhooks
        self.http_session = None
    
    async def start(self):
        """Start the alert manager"""
        try:
            self.is_running = True
            
            # Create HTTP session
            self.http_session = aiohttp.ClientSession()
            
            # Start processing loop
            self.processing_task = asyncio.create_task(self._processing_loop())
            
            self.logger.info("Alert manager started")
            
        except Exception as e:
            self.logger.error(f"Error starting alert manager: {str(e)}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the alert manager"""
        self.is_running = False
        
        # Cancel tasks
        if self.processing_task:
            self.processing_task.cancel()
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
        
        # Process remaining alerts
        await self._process_remaining_alerts()
        
        self.logger.info("Alert manager stopped")
    
    async def create_signal_alert(self, signal: TradingSignal, alert_type: AlertType = AlertType.SIGNAL_CREATED):
        """Create an alert from a trading signal"""
        # Check if alert should be created based on priority
        if signal.priority.value > self.config.min_priority.value:
            return
        
        # Create alert
        alert = Alert(
            alert_type=alert_type,
            priority=signal.priority,
            title=f"{signal.priority.name} {signal.signal_type.upper()} Signal: {signal.symbol}",
            message=self._format_signal_message(signal),
            symbol=signal.symbol,
            signal_id=signal.id,
            channels=self.config.enabled_channels.copy(),
            metadata={
                "signal": signal.to_dict(),
                "timeframe": signal.timeframe,
                "pattern_type": signal.pattern_type
            }
        )
        
        # Set recipients based on configuration
        alert.recipients = self._get_recipients(alert)
        
        # Add to queue
        await self.add_alert(alert)
    
    async def create_market_alert(self, title: str, message: str, 
                                 symbol: Optional[str] = None,
                                 priority: SignalPriority = SignalPriority.MEDIUM):
        """Create a market alert"""
        alert = Alert(
            alert_type=AlertType.MARKET_ALERT,
            priority=priority,
            title=title,
            message=message,
            symbol=symbol,
            channels=self.config.enabled_channels.copy()
        )
        
        alert.recipients = self._get_recipients(alert)
        await self.add_alert(alert)
    
    async def create_system_alert(self, title: str, message: str,
                                 priority: SignalPriority = SignalPriority.LOW):
        """Create a system alert"""
        alert = Alert(
            alert_type=AlertType.SYSTEM_ALERT,
            priority=priority,
            title=title,
            message=message,
            channels=[NotificationChannel.EMAIL]  # System alerts via email only
        )
        
        alert.recipients = self._get_recipients(alert)
        await self.add_alert(alert)
    
    async def add_alert(self, alert: Alert):
        """Add alert to queue"""
        try:
            # Check rate limits
            if not self._check_rate_limit(alert):
                self.logger.warning(f"Rate limit exceeded for alert: {alert.title}")
                return
            
            # Add to queue
            self.alert_queue.append(alert)
            
            # Update statistics
            self.stats["total_alerts"] += 1
            self.stats["alerts_by_type"][alert.alert_type.value] += 1
            
            self.logger.debug(f"Alert added to queue: {alert.title}")
            
        except Exception as e:
            self.logger.error(f"Error adding alert: {str(e)}")
    
    async def _processing_loop(self):
        """Process alerts from queue"""
        while self.is_running:
            try:
                # Move alerts from queue to processing
                batch_size = min(self.config.batch_size, len(self.alert_queue))
                
                if batch_size > 0:
                    for _ in range(batch_size):
                        if self.alert_queue:
                            alert = self.alert_queue.popleft()
                            self.processing_queue.append(alert)
                    
                    # Process batch
                    await self._process_batch()
                
                # Sleep before next cycle
                await asyncio.sleep(self.config.processing_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _process_batch(self):
        """Process a batch of alerts"""
        tasks = []
        
        for alert in self.processing_queue:
            tasks.append(self._deliver_alert(alert))
        
        # Process alerts concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        retry_alerts = []
        
        for alert, result in zip(self.processing_queue, results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to deliver alert {alert.id}: {str(result)}")
                
                # Check if should retry
                if alert.retry_count < self.config.max_retries:
                    alert.retry_count += 1
                    retry_alerts.append(alert)
                else:
                    self.stats["failed_alerts"] += 1
            else:
                self.stats["delivered_alerts"] += 1
        
        # Clear processing queue
        self.processing_queue.clear()
        
        # Re-queue alerts for retry
        for alert in retry_alerts:
            await asyncio.sleep(self.config.retry_delay)
            self.alert_queue.append(alert)
    
    async def _deliver_alert(self, alert: Alert):
        """Deliver alert through all configured channels"""
        delivery_tasks = []
        
        for channel in alert.channels:
            if channel in alert.delivered_channels:
                continue  # Already delivered
            
            if channel == NotificationChannel.EMAIL:
                delivery_tasks.append(self._send_email(alert))
            elif channel == NotificationChannel.WEBHOOK:
                delivery_tasks.append(self._send_webhook(alert))
            elif channel == NotificationChannel.WEBSOCKET:
                delivery_tasks.append(self._send_websocket(alert))
            elif channel == NotificationChannel.TELEGRAM:
                delivery_tasks.append(self._send_telegram(alert))
            elif channel == NotificationChannel.DISCORD:
                delivery_tasks.append(self._send_discord(alert))
        
        # Execute delivery tasks
        results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
        
        # Update delivery status
        for channel, result in zip(alert.channels, results):
            if isinstance(result, Exception):
                alert.failed_channels.append(channel)
                self.logger.error(f"Failed to deliver alert via {channel.value}: {str(result)}")
            else:
                alert.delivered_channels.append(channel)
                self.stats["alerts_by_channel"][channel.value] += 1
        
        # Check if all channels failed
        if len(alert.failed_channels) == len(alert.channels):
            raise Exception("All delivery channels failed")
    
    async def _send_email(self, alert: Alert):
        """Send email notification"""
        try:
            recipients = alert.recipients.get(NotificationChannel.EMAIL.value, [])
            if not recipients or not self.config.smtp_host:
                return
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = alert.title
            msg['From'] = self.config.email_from
            msg['To'] = ', '.join(recipients)
            
            # Create HTML content
            html_content = self._format_email_html(alert)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
            
            self.logger.debug(f"Email sent for alert {alert.id}")
            
        except Exception as e:
            self.logger.error(f"Email delivery failed: {str(e)}")
            raise
    
    async def _send_webhook(self, alert: Alert):
        """Send webhook notification"""
        try:
            webhook_url = self.config.webhook_urls.get('default')
            if not webhook_url:
                return
            
            payload = {
                "alert_id": alert.id,
                "timestamp": alert.timestamp.isoformat(),
                "type": alert.alert_type.value,
                "priority": alert.priority.value,
                "title": alert.title,
                "message": alert.message,
                "symbol": alert.symbol,
                "signal_id": alert.signal_id,
                "metadata": alert.metadata
            }
            
            async with self.http_session.post(
                webhook_url,
                json=payload,
                timeout=self.config.webhook_timeout
            ) as response:
                if response.status != 200:
                    raise Exception(f"Webhook returned status {response.status}")
            
            self.logger.debug(f"Webhook sent for alert {alert.id}")
            
        except Exception as e:
            self.logger.error(f"Webhook delivery failed: {str(e)}")
            raise
    
    async def _send_websocket(self, alert: Alert):
        """Send websocket notification"""
        try:
            # Send to all connected WebSocket clients
            if self.websocket_connections:
                message = json.dumps(alert.to_dict())
                
                # Send to all connections
                disconnected = []
                for ws in self.websocket_connections:
                    try:
                        await ws.send_json(alert.to_dict())
                    except Exception:
                        disconnected.append(ws)
                
                # Remove disconnected clients
                for ws in disconnected:
                    self.websocket_connections.remove(ws)
            
            self.logger.debug(f"WebSocket notification sent for alert {alert.id}")
            
        except Exception as e:
            self.logger.error(f"WebSocket delivery failed: {str(e)}")
            raise
    
    async def _send_telegram(self, alert: Alert):
        """Send Telegram notification"""
        # Placeholder - implement Telegram bot integration
        self.logger.debug("Telegram notification not implemented")
    
    async def _send_discord(self, alert: Alert):
        """Send Discord notification"""
        # Placeholder - implement Discord webhook integration
        self.logger.debug("Discord notification not implemented")
    
    def _format_signal_message(self, signal: TradingSignal) -> str:
        """Format signal into alert message"""
        risk_reward = (signal.take_profit - signal.entry_price) / (signal.entry_price - signal.stop_loss)
        
        message = f"""
Symbol: {signal.symbol}
Timeframe: {signal.timeframe}
Pattern: {signal.pattern_type}
Signal Type: {signal.signal_type.upper()}

Entry Price: ${signal.entry_price:.2f}
Stop Loss: ${signal.stop_loss:.2f} ({((signal.entry_price - signal.stop_loss) / signal.entry_price * 100):.1f}%)
Take Profit: ${signal.take_profit:.2f} ({((signal.take_profit - signal.entry_price) / signal.entry_price * 100):.1f}%)

Risk/Reward: 1:{risk_reward:.1f}
Confidence: {signal.confidence:.0%}
Contributing Signals: {', '.join(signal.contributing_signals)}

Valid Until: {signal.valid_until.strftime('%Y-%m-%d %H:%M UTC') if signal.valid_until else 'N/A'}
"""
        return message.strip()
    
    def _format_email_html(self, alert: Alert) -> str:
        """Format alert as HTML for email"""
        style = """
        <style>
            body { font-family: Arial, sans-serif; }
            .alert-container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .alert-header { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .alert-title { font-size: 20px; font-weight: bold; margin: 0; }
            .alert-content { padding: 15px; }
            .signal-details { background-color: #e9ecef; padding: 15px; border-radius: 5px; }
            .priority-critical { color: #dc3545; }
            .priority-high { color: #fd7e14; }
            .priority-medium { color: #ffc107; }
            .priority-low { color: #28a745; }
        </style>
        """
        
        priority_class = f"priority-{alert.priority.name.lower()}"
        
        html = f"""
        <html>
        <head>{style}</head>
        <body>
            <div class="alert-container">
                <div class="alert-header">
                    <h2 class="alert-title {priority_class}">{alert.title}</h2>
                </div>
                <div class="alert-content">
                    <pre>{alert.message}</pre>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _get_recipients(self, alert: Alert) -> Dict[str, List[str]]:
        """Get recipients for alert based on configuration"""
        # This would be loaded from configuration/database
        # For now, return default recipients
        return {
            NotificationChannel.EMAIL.value: ["trader@example.com"],
            NotificationChannel.WEBHOOK.value: ["default"]
        }
    
    def _check_rate_limit(self, alert: Alert) -> bool:
        """Check if alert passes rate limiting"""
        current_time = datetime.now(timezone.utc)
        
        # Global rate limit
        global_key = "global"
        if global_key not in self.rate_limiter:
            self.rate_limiter[global_key] = deque(maxlen=self.config.max_alerts_per_minute)
        
        # Remove old timestamps
        cutoff_time = current_time.timestamp() - 60
        while (self.rate_limiter[global_key] and 
               self.rate_limiter[global_key][0] < cutoff_time):
            self.rate_limiter[global_key].popleft()
        
        # Check global limit
        if len(self.rate_limiter[global_key]) >= self.config.max_alerts_per_minute:
            return False
        
        # Per-symbol rate limit
        if alert.symbol:
            symbol_key = f"symbol_{alert.symbol}"
            if symbol_key not in self.rate_limiter:
                self.rate_limiter[symbol_key] = deque(maxlen=self.config.max_alerts_per_symbol)
            
            # Check symbol limit
            if len(self.rate_limiter[symbol_key]) >= self.config.max_alerts_per_symbol:
                return False
            
            self.rate_limiter[symbol_key].append(current_time.timestamp())
        
        # Add to global rate limiter
        self.rate_limiter[global_key].append(current_time.timestamp())
        
        return True
    
    async def _process_remaining_alerts(self):
        """Process any remaining alerts before shutdown"""
        try:
            while self.alert_queue or self.processing_queue:
                if self.alert_queue:
                    alert = self.alert_queue.popleft()
                    await self._deliver_alert(alert)
                
                if self.processing_queue:
                    await self._process_batch()
                    
        except Exception as e:
            self.logger.error(f"Error processing remaining alerts: {str(e)}")
    
    def add_websocket_connection(self, websocket):
        """Add a WebSocket connection for real-time updates"""
        self.websocket_connections.append(websocket)
    
    def remove_websocket_connection(self, websocket):
        """Remove a WebSocket connection"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert manager statistics"""
        return {
            **self.stats,
            "queue_size": len(self.alert_queue),
            "processing_size": len(self.processing_queue),
            "active_websockets": len(self.websocket_connections)
        }