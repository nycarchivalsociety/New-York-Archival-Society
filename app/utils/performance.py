# app/utils/performance.py

import time
import logging
from functools import wraps
from flask import request, g
from typing import Callable, Any

logger = logging.getLogger(__name__)

def monitor_performance(threshold_ms: float = 1000.0):
    """
    Decorator to monitor function performance and log slow operations
    
    Args:
        threshold_ms: Log warning if function takes longer than this (milliseconds)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000
                
                # Log performance metrics
                if execution_time_ms > threshold_ms:
                    logger.warning(
                        f"Slow operation detected: {f.__name__} took {execution_time_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(f"{f.__name__} executed in {execution_time_ms:.2f}ms")
                
                # Store in Flask g for request-level metrics
                if hasattr(g, 'performance_metrics'):
                    g.performance_metrics[f.__name__] = execution_time_ms
                else:
                    g.performance_metrics = {f.__name__: execution_time_ms}
        
        return decorated_function
    return decorator

def track_db_queries():
    """
    Context manager to track database query count and time
    """
    class QueryTracker:
        def __init__(self):
            self.query_count = 0
            self.total_time = 0
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            # In a real implementation, you'd hook into SQLAlchemy events
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.start_time:
                self.total_time = time.time() - self.start_time
                
                if self.query_count > 10:
                    logger.warning(
                        f"High query count detected: {self.query_count} queries "
                        f"in {self.total_time * 1000:.2f}ms"
                    )
    
    return QueryTracker()

def log_request_metrics():
    """Log performance metrics for the current request"""
    if hasattr(g, 'performance_metrics'):
        total_time = sum(g.performance_metrics.values())
        metrics_str = ", ".join([
            f"{func}: {time_ms:.2f}ms" 
            for func, time_ms in g.performance_metrics.items()
        ])
        
        logger.info(
            f"Request {request.method} {request.path} - "
            f"Total function time: {total_time:.2f}ms - "
            f"Breakdown: {metrics_str}"
        )

def measure_memory_usage():
    """
    Decorator to measure memory usage of a function
    Note: Requires psutil package for accurate memory monitoring
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Any:
            try:
                import psutil
                import os
                
                process = psutil.Process(os.getpid())
                mem_before = process.memory_info().rss / 1024 / 1024  # MB
                
                result = f(*args, **kwargs)
                
                mem_after = process.memory_info().rss / 1024 / 1024  # MB
                mem_diff = mem_after - mem_before
                
                if mem_diff > 10:  # Log if memory usage increased by more than 10MB
                    logger.warning(
                        f"High memory usage in {f.__name__}: "
                        f"{mem_diff:.2f}MB increase (before: {mem_before:.2f}MB, after: {mem_after:.2f}MB)"
                    )
                
                return result
                
            except ImportError:
                logger.debug("psutil not available for memory monitoring")
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator

class PerformanceMiddleware:
    """
    WSGI middleware for request-level performance monitoring
    """
    
    def __init__(self, app, threshold_ms: float = 2000.0):
        self.app = app
        self.threshold_ms = threshold_ms
    
    def __call__(self, environ, start_response):
        start_time = time.time()
        
        def new_start_response(status, response_headers, exc_info=None):
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Log slow requests
            if duration_ms > self.threshold_ms:
                path_info = environ.get('PATH_INFO', '')
                method = environ.get('REQUEST_METHOD', '')
                remote_addr = environ.get('REMOTE_ADDR', '')
                
                logger.warning(
                    f"Slow request: {method} {path_info} from {remote_addr} "
                    f"took {duration_ms:.2f}ms (threshold: {self.threshold_ms}ms)"
                )
            
            return start_response(status, response_headers, exc_info)
        
        return self.app(environ, new_start_response)