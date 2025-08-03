#!/usr/bin/env python3
"""
Security Monitoring and Alerting System for HutzTrades
Monitors for attacks, suspicious activity, and security incidents
"""

import os
import json
import time
import smtplib
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from pathlib import Path

class SecurityMonitor:
    def __init__(self):
        self.config = {
            # Alert thresholds
            'failed_requests_threshold': 50,      # Failed requests per hour
            'blocked_ips_threshold': 10,          # Blocked IPs per hour
            'suspicious_patterns_threshold': 20,   # Suspicious patterns per hour
            'error_rate_threshold': 0.05,         # 5% error rate
            
            # Monitoring windows
            'monitor_window': 3600,               # 1 hour in seconds
            'alert_cooldown': 1800,               # 30 minutes between alerts
            
            # Email settings (configure via environment variables)
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'email_user': os.getenv('ALERT_EMAIL_USER'),
            'email_password': os.getenv('ALERT_EMAIL_PASSWORD'),
            'alert_recipients': os.getenv('ALERT_RECIPIENTS', '').split(','),
            
            # Webhook settings
            'webhook_url': os.getenv('SECURITY_WEBHOOK_URL'),
            'slack_webhook': os.getenv('SLACK_WEBHOOK_URL')
        }
        
        # Monitoring data
        self.events = defaultdict(deque)
        self.alerts_sent = defaultdict(float)
        self.metrics = {
            'total_requests': 0,
            'failed_requests': 0,
            'blocked_ips': set(),
            'suspicious_events': 0,
            'last_alert': None
        }
        
        # Setup logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "security_monitor.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def record_event(self, event_type: str, details: Dict):
        """Record a security event"""
        now = time.time()
        event = {
            'timestamp': now,
            'type': event_type,
            'details': details
        }
        
        self.events[event_type].append(event)
        
        # Clean old events (keep last hour)
        while (self.events[event_type] and 
               now - self.events[event_type][0]['timestamp'] > self.config['monitor_window']):
            self.events[event_type].popleft()
        
        # Update metrics
        self.update_metrics(event_type, details)
        
        # Check for alert conditions
        self.check_alert_conditions()

    def update_metrics(self, event_type: str, details: Dict):
        """Update security metrics"""
        if event_type == 'request':
            self.metrics['total_requests'] += 1
        elif event_type == 'failed_request':
            self.metrics['failed_requests'] += 1
        elif event_type == 'ip_blocked':
            self.metrics['blocked_ips'].add(details.get('ip'))
        elif event_type == 'suspicious_activity':
            self.metrics['suspicious_events'] += 1

    def get_recent_events(self, event_type: str, minutes: int = 60) -> List[Dict]:
        """Get recent events of a specific type"""
        cutoff_time = time.time() - (minutes * 60)
        return [
            event for event in self.events[event_type]
            if event['timestamp'] > cutoff_time
        ]

    def calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        if self.metrics['total_requests'] == 0:
            return 0.0
        return self.metrics['failed_requests'] / self.metrics['total_requests']

    def check_alert_conditions(self):
        """Check if any alert conditions are met"""
        now = time.time()
        
        # Check failed requests
        recent_failures = len(self.get_recent_events('failed_request', 60))
        if recent_failures >= self.config['failed_requests_threshold']:
            self.send_alert(
                'high_failure_rate',
                f"High failure rate detected: {recent_failures} failed requests in the last hour",
                {'failed_requests': recent_failures}
            )
        
        # Check blocked IPs
        recent_blocks = len(self.get_recent_events('ip_blocked', 60))
        if recent_blocks >= self.config['blocked_ips_threshold']:
            self.send_alert(
                'high_block_rate',
                f"High IP blocking rate: {recent_blocks} IPs blocked in the last hour",
                {'blocked_ips': recent_blocks}
            )
        
        # Check suspicious activity
        recent_suspicious = len(self.get_recent_events('suspicious_activity', 60))
        if recent_suspicious >= self.config['suspicious_patterns_threshold']:
            self.send_alert(
                'high_suspicious_activity',
                f"High suspicious activity: {recent_suspicious} events in the last hour",
                {'suspicious_events': recent_suspicious}
            )
        
        # Check error rate
        error_rate = self.calculate_error_rate()
        if error_rate >= self.config['error_rate_threshold']:
            self.send_alert(
                'high_error_rate',
                f"High error rate detected: {error_rate:.2%}",
                {'error_rate': error_rate}
            )

    def send_alert(self, alert_type: str, message: str, details: Dict):
        """Send security alert"""
        now = time.time()
        
        # Check alert cooldown
        last_alert = self.alerts_sent.get(alert_type, 0)
        if now - last_alert < self.config['alert_cooldown']:
            return
        
        self.alerts_sent[alert_type] = now
        self.metrics['last_alert'] = now
        
        alert_data = {
            'type': alert_type,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'severity': self.get_alert_severity(alert_type)
        }
        
        # Log alert
        self.logger.warning(f"SECURITY ALERT [{alert_type}]: {message}")
        
        # Save alert to file
        self.save_alert(alert_data)
        
        # Send notifications
        self.send_email_alert(alert_data)
        self.send_webhook_alert(alert_data)

    def get_alert_severity(self, alert_type: str) -> str:
        """Determine alert severity level"""
        high_severity = [
            'high_failure_rate',
            'ddos_attack',
            'security_breach',
            'multiple_attack_vectors'
        ]
        
        medium_severity = [
            'high_block_rate',
            'high_suspicious_activity',
            'high_error_rate'
        ]
        
        if alert_type in high_severity:
            return 'HIGH'
        elif alert_type in medium_severity:
            return 'MEDIUM'
        else:
            return 'LOW'

    def send_email_alert(self, alert_data: Dict):
        """Send email alert if configured"""
        if not (self.config['email_user'] and self.config['email_password'] and 
                self.config['alert_recipients']):
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email_user']
            msg['To'] = ', '.join(self.config['alert_recipients'])
            msg['Subject'] = f"🚨 HutzTrades Security Alert - {alert_data['type']}"
            
            body = f"""
Security Alert Detected

Type: {alert_data['type']}
Severity: {alert_data['severity']}
Message: {alert_data['message']}
Timestamp: {alert_data['timestamp']}

Details:
{json.dumps(alert_data['details'], indent=2)}

---
HutzTrades Security Monitoring System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['email_user'], self.config['email_password'])
            
            text = msg.as_string()
            server.sendmail(self.config['email_user'], self.config['alert_recipients'], text)
            server.quit()
            
            self.logger.info(f"Email alert sent for {alert_data['type']}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {str(e)}")

    def send_webhook_alert(self, alert_data: Dict):
        """Send webhook alert if configured"""
        if not self.config['webhook_url']:
            return
        
        try:
            import requests
            
            payload = {
                'text': f"🚨 Security Alert: {alert_data['message']}",
                'alert_type': alert_data['type'],
                'severity': alert_data['severity'],
                'timestamp': alert_data['timestamp'],
                'details': alert_data['details']
            }
            
            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Webhook alert sent for {alert_data['type']}")
            else:
                self.logger.error(f"Webhook alert failed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {str(e)}")

    def save_alert(self, alert_data: Dict):
        """Save alert to file"""
        try:
            alerts_file = Path("logs/security_alerts.json")
            
            # Load existing alerts
            alerts = []
            if alerts_file.exists():
                with open(alerts_file, 'r') as f:
                    alerts = json.load(f)
            
            # Add new alert
            alerts.append(alert_data)
            
            # Keep only last 1000 alerts
            if len(alerts) > 1000:
                alerts = alerts[-1000:]
            
            # Save back to file
            with open(alerts_file, 'w') as f:
                json.dump(alerts, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save alert: {str(e)}")

    def generate_security_report(self) -> Dict:
        """Generate comprehensive security report"""
        now = time.time()
        
        # Get metrics for last hour
        recent_requests = len(self.get_recent_events('request', 60))
        recent_failures = len(self.get_recent_events('failed_request', 60))
        recent_blocks = len(self.get_recent_events('ip_blocked', 60))
        recent_suspicious = len(self.get_recent_events('suspicious_activity', 60))
        
        # Calculate rates
        failure_rate = (recent_failures / recent_requests) if recent_requests > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_period': '1 hour',
            'metrics': {
                'total_requests': recent_requests,
                'failed_requests': recent_failures,
                'failure_rate': failure_rate,
                'blocked_ips': recent_blocks,
                'suspicious_events': recent_suspicious
            },
            'alert_status': {
                'last_alert': self.metrics.get('last_alert'),
                'alerts_today': len([
                    alert for alert in self.get_recent_events('alert', 1440)  # 24 hours
                ])
            },
            'top_threats': self.get_top_threats(),
            'recommendations': self.get_security_recommendations()
        }
        
        return report

    def get_top_threats(self) -> List[Dict]:
        """Get top security threats from recent events"""
        threats = []
        
        # Analyze recent suspicious events
        suspicious_events = self.get_recent_events('suspicious_activity', 60)
        
        # Group by IP and pattern
        threat_summary = defaultdict(lambda: {'count': 0, 'patterns': set()})
        
        for event in suspicious_events:
            ip = event['details'].get('ip', 'unknown')
            patterns = event['details'].get('patterns', [])
            
            threat_summary[ip]['count'] += 1
            threat_summary[ip]['patterns'].update(patterns)
        
        # Convert to list and sort by severity
        for ip, data in threat_summary.items():
            threats.append({
                'ip': ip,
                'event_count': data['count'],
                'attack_patterns': list(data['patterns']),
                'threat_level': 'HIGH' if data['count'] > 10 else 'MEDIUM' if data['count'] > 5 else 'LOW'
            })
        
        return sorted(threats, key=lambda x: x['event_count'], reverse=True)[:10]

    def get_security_recommendations(self) -> List[str]:
        """Get security recommendations based on recent activity"""
        recommendations = []
        
        recent_blocks = len(self.get_recent_events('ip_blocked', 60))
        recent_suspicious = len(self.get_recent_events('suspicious_activity', 60))
        error_rate = self.calculate_error_rate()
        
        if recent_blocks > 5:
            recommendations.append("Consider implementing geographical IP blocking")
        
        if recent_suspicious > 10:
            recommendations.append("Review and tighten suspicious pattern detection rules")
        
        if error_rate > 0.03:
            recommendations.append("Investigate high error rate - possible system issues")
        
        if not recommendations:
            recommendations.append("Security posture is good - continue monitoring")
        
        return recommendations

# Global security monitor instance
security_monitor = SecurityMonitor()

def monitor_request(ip: str, user_agent: str, path: str, status_code: int):
    """Monitor an incoming request"""
    security_monitor.record_event('request', {
        'ip': ip,
        'user_agent': user_agent,
        'path': path,
        'status_code': status_code
    })
    
    if status_code >= 400:
        security_monitor.record_event('failed_request', {
            'ip': ip,
            'user_agent': user_agent,
            'path': path,
            'status_code': status_code
        })

def monitor_blocked_ip(ip: str, reason: str):
    """Monitor IP blocking event"""
    security_monitor.record_event('ip_blocked', {
        'ip': ip,
        'reason': reason
    })

def monitor_suspicious_activity(ip: str, patterns: List[str], details: Dict):
    """Monitor suspicious activity"""
    security_monitor.record_event('suspicious_activity', {
        'ip': ip,
        'patterns': patterns,
        'details': details
    })

if __name__ == "__main__":
    # Generate and display security report
    report = security_monitor.generate_security_report()
    print("HutzTrades Security Report")
    print("=" * 50)
    print(json.dumps(report, indent=2))