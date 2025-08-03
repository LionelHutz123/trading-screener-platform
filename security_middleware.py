#!/usr/bin/env python3
"""
Security Middleware for HutzTrades API
Implements rate limiting, request validation, and DDoS protection
"""

import time
import hashlib
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import ipaddress

class SecurityMiddleware:
    def __init__(self):
        # Rate limiting storage
        self.rate_limits = defaultdict(deque)
        self.blocked_ips = defaultdict(float)
        
        # Security configuration
        self.config = {
            # Rate limiting
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'requests_per_day': 10000,
            
            # DDoS protection
            'burst_threshold': 20,  # requests in 10 seconds
            'burst_window': 10,
            'block_duration': 300,  # 5 minutes
            
            # Request validation
            'max_request_size': 1024 * 1024,  # 1MB
            'allowed_user_agents': [
                'Mozilla', 'Chrome', 'Safari', 'Firefox', 'Edge',
                'HutzTrades-Client', 'PostmanRuntime', 'curl'
            ],
            
            # Geoblocking (optional)
            'blocked_countries': [],  # Add country codes if needed
            'whitelist_ips': [
                '127.0.0.1',
                '::1'
            ]
        }
        
        # Logging setup
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers"""
        # Check for forwarded headers (from CDN/proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to client IP
        return request.client.host if request.client else '127.0.0.1'

    def is_ip_whitelisted(self, ip: str) -> bool:
        """Check if IP is in whitelist"""
        return ip in self.config['whitelist_ips']

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is temporarily blocked"""
        if ip in self.blocked_ips:
            block_time = self.blocked_ips[ip]
            if time.time() - block_time < self.config['block_duration']:
                return True
            else:
                # Unblock expired IPs
                del self.blocked_ips[ip]
        return False

    def block_ip(self, ip: str, reason: str = "Rate limit exceeded"):
        """Block an IP address"""
        self.blocked_ips[ip] = time.time()
        self.logger.warning(f"Blocked IP {ip}: {reason}")

    def check_rate_limit(self, ip: str) -> Dict[str, any]:
        """Check if IP exceeds rate limits"""
        now = time.time()
        
        # Clean old entries
        while self.rate_limits[ip] and now - self.rate_limits[ip][0] > 3600:
            self.rate_limits[ip].popleft()
        
        # Get current counts
        minute_count = sum(1 for t in self.rate_limits[ip] if now - t < 60)
        hour_count = len(self.rate_limits[ip])
        
        # Check burst protection (20 requests in 10 seconds)
        burst_count = sum(1 for t in self.rate_limits[ip] if now - t < self.config['burst_window'])
        
        if burst_count >= self.config['burst_threshold']:
            self.block_ip(ip, f"Burst protection: {burst_count} requests in {self.config['burst_window']}s")
            return {
                'allowed': False,
                'reason': 'burst_protection',
                'retry_after': self.config['block_duration']
            }
        
        # Check minute limit
        if minute_count >= self.config['requests_per_minute']:
            return {
                'allowed': False,
                'reason': 'minute_limit_exceeded',
                'retry_after': 60
            }
        
        # Check hour limit
        if hour_count >= self.config['requests_per_hour']:
            return {
                'allowed': False,
                'reason': 'hour_limit_exceeded',
                'retry_after': 3600
            }
        
        # Record this request
        self.rate_limits[ip].append(now)
        
        return {
            'allowed': True,
            'remaining_minute': self.config['requests_per_minute'] - minute_count - 1,
            'remaining_hour': self.config['requests_per_hour'] - hour_count - 1
        }

    def validate_user_agent(self, user_agent: str) -> bool:
        """Validate user agent string"""
        if not user_agent:
            return False
        
        # Check for allowed user agents
        return any(agent in user_agent for agent in self.config['allowed_user_agents'])

    def validate_request_size(self, request: Request) -> bool:
        """Validate request size"""
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                return size <= self.config['max_request_size']
            except ValueError:
                return False
        return True

    def detect_suspicious_patterns(self, request: Request) -> List[str]:
        """Detect suspicious request patterns"""
        suspicious = []
        
        # Check for common attack patterns in URL
        url_path = str(request.url.path).lower()
        attack_patterns = [
            'wp-admin', 'phpmyadmin', 'admin', '.env', '.git',
            'config', 'database', 'backup', 'sql', 'shell',
            '<script>', 'javascript:', 'eval(', 'union select'
        ]
        
        for pattern in attack_patterns:
            if pattern in url_path:
                suspicious.append(f"suspicious_url_pattern: {pattern}")
        
        # Check for SQL injection attempts
        query_string = str(request.url.query).lower()
        sql_patterns = ['union', 'select', 'drop', 'insert', 'delete', 'update', '--', ';']
        for pattern in sql_patterns:
            if pattern in query_string:
                suspicious.append(f"potential_sql_injection: {pattern}")
        
        # Check headers for attacks
        user_agent = request.headers.get('user-agent', '').lower()
        malicious_agents = ['nikto', 'sqlmap', 'nmap', 'dirbuster', 'burp']
        for agent in malicious_agents:
            if agent in user_agent:
                suspicious.append(f"malicious_user_agent: {agent}")
        
        return suspicious

    async def security_check(self, request: Request) -> Optional[JSONResponse]:
        """Main security check function"""
        client_ip = self.get_client_ip(request)
        
        # Skip checks for whitelisted IPs
        if self.is_ip_whitelisted(client_ip):
            return None
        
        # Check if IP is blocked
        if self.is_ip_blocked(client_ip):
            self.logger.warning(f"Blocked IP attempted access: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "IP temporarily blocked",
                    "code": "IP_BLOCKED",
                    "retry_after": self.config['block_duration']
                }
            )
        
        # Rate limiting check
        rate_check = self.check_rate_limit(client_ip)
        if not rate_check['allowed']:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "reason": rate_check['reason'],
                    "retry_after": rate_check['retry_after']
                },
                headers={
                    "Retry-After": str(rate_check['retry_after']),
                    "X-RateLimit-Limit": str(self.config['requests_per_minute']),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # User agent validation
        user_agent = request.headers.get('user-agent', '')
        if not self.validate_user_agent(user_agent):
            self.logger.warning(f"Invalid user agent from {client_ip}: {user_agent}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid user agent",
                    "code": "INVALID_USER_AGENT"
                }
            )
        
        # Request size validation
        if not self.validate_request_size(request):
            self.logger.warning(f"Request too large from {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "Request too large",
                    "code": "REQUEST_TOO_LARGE"
                }
            )
        
        # Detect suspicious patterns
        suspicious = self.detect_suspicious_patterns(request)
        if suspicious:
            self.logger.warning(f"Suspicious request from {client_ip}: {suspicious}")
            # Block IP for repeated suspicious activity
            if len(suspicious) > 2:
                self.block_ip(client_ip, f"Multiple suspicious patterns: {suspicious}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Suspicious activity detected",
                        "code": "SUSPICIOUS_ACTIVITY"
                    }
                )
        
        # Add rate limit headers to response
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(self.config['requests_per_minute']),
            "X-RateLimit-Remaining": str(rate_check.get('remaining_minute', 0)),
            "X-RateLimit-Reset": str(int(time.time()) + 60)
        }
        
        return None

# Global security middleware instance
security_middleware = SecurityMiddleware()

def rate_limit(requests_per_minute: int = 60):
    """Decorator for rate limiting specific endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Override default rate limit for this endpoint
            original_limit = security_middleware.config['requests_per_minute']
            security_middleware.config['requests_per_minute'] = requests_per_minute
            
            # Perform security check
            security_response = await security_middleware.security_check(request)
            if security_response:
                return security_response
            
            # Restore original limit
            security_middleware.config['requests_per_minute'] = original_limit
            
            # Call the original function
            result = await func(request, *args, **kwargs)
            
            # Add rate limit headers if response is JSONResponse
            if hasattr(request.state, 'rate_limit_headers') and hasattr(result, 'headers'):
                result.headers.update(request.state.rate_limit_headers)
            
            return result
        return wrapper
    return decorator