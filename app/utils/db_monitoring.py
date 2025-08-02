# app/utils/db_monitoring.py

"""
Database performance monitoring and analysis tools
Provides real-time insights into query performance, connection usage, and optimization opportunities
"""

import logging
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass, asdict
from contextlib import contextmanager

import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
from flask import current_app, g, request

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Data class for storing query performance metrics"""
    query_hash: str
    sql_text: str
    execution_time: float
    timestamp: datetime
    parameters: Dict[str, Any]
    stack_trace: Optional[str] = None
    row_count: Optional[int] = None
    connection_id: Optional[str] = None


@dataclass
class ConnectionMetrics:
    """Data class for storing connection pool metrics"""
    pool_size: int
    checked_out: int
    overflow: int
    checked_in: int
    timestamp: datetime


class DatabaseMonitor:
    """
    Comprehensive database performance monitoring system
    """
    
    def __init__(self, max_slow_queries: int = 1000):
        self.slow_queries = deque(maxlen=max_slow_queries)
        self.query_stats = defaultdict(list)
        self.connection_stats = deque(maxlen=100)
        self.slow_query_threshold = 1.0  # seconds
        self.enabled = True
        self._lock = threading.Lock()
    
    def enable(self):
        """Enable monitoring"""
        self.enabled = True
        logger.info("Database monitoring enabled")
    
    def disable(self):
        """Disable monitoring"""
        self.enabled = False
        logger.info("Database monitoring disabled")
    
    def record_query(self, metrics: QueryMetrics):
        """Record query execution metrics"""
        if not self.enabled:
            return
        
        with self._lock:
            # Record slow queries
            if metrics.execution_time > self.slow_query_threshold:
                self.slow_queries.append(metrics)
                logger.warning(
                    f"Slow query detected: {metrics.execution_time:.3f}s - "
                    f"{metrics.sql_text[:100]}..."
                )
            
            # Aggregate statistics by query hash
            self.query_stats[metrics.query_hash].append(metrics)
            
            # Keep only recent stats (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.query_stats[metrics.query_hash] = [
                m for m in self.query_stats[metrics.query_hash]
                if m.timestamp > cutoff_time
            ]
    
    def record_connection_stats(self, metrics: ConnectionMetrics):
        """Record connection pool metrics"""
        if not self.enabled:
            return
        
        with self._lock:
            self.connection_stats.append(metrics)
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent slow queries"""
        with self._lock:
            recent_slow = sorted(
                self.slow_queries,
                key=lambda x: x.execution_time,
                reverse=True
            )[:limit]
            
            return [asdict(query) for query in recent_slow]
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get aggregated query statistics"""
        with self._lock:
            stats = {}
            
            for query_hash, metrics_list in self.query_stats.items():
                if not metrics_list:
                    continue
                
                execution_times = [m.execution_time for m in metrics_list]
                
                stats[query_hash] = {
                    'sql_sample': metrics_list[0].sql_text[:200] + "...",
                    'call_count': len(metrics_list),
                    'total_time': sum(execution_times),
                    'average_time': sum(execution_times) / len(execution_times),
                    'min_time': min(execution_times),
                    'max_time': max(execution_times),
                    'last_executed': max(m.timestamp for m in metrics_list).isoformat()
                }
            
            # Sort by total time descending
            sorted_stats = dict(
                sorted(stats.items(), key=lambda x: x[1]['total_time'], reverse=True)
            )
            
            return sorted_stats
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            if not self.connection_stats:
                return {'error': 'No connection statistics available'}
            
            recent_stats = list(self.connection_stats)[-10:]  # Last 10 measurements
            
            return {
                'current': asdict(recent_stats[-1]) if recent_stats else None,
                'average_pool_size': sum(s.pool_size for s in recent_stats) / len(recent_stats),
                'average_checked_out': sum(s.checked_out for s in recent_stats) / len(recent_stats),
                'max_checked_out': max(s.checked_out for s in recent_stats),
                'pool_utilization_percent': (
                    max(s.checked_out for s in recent_stats) / 
                    max(s.pool_size for s in recent_stats) * 100
                ) if recent_stats else 0,
                'history': [asdict(stat) for stat in recent_stats]
            }
    
    def analyze_performance_issues(self) -> Dict[str, Any]:
        """Analyze performance issues and provide recommendations"""
        issues = []
        recommendations = []
        
        # Analyze slow queries
        slow_queries = self.get_slow_queries(5)
        if slow_queries:
            issues.append(f"Found {len(self.slow_queries)} slow queries")
            recommendations.append("Review slow queries and add appropriate indexes")
        
        # Analyze connection pool usage
        conn_stats = self.get_connection_statistics()
        if conn_stats.get('pool_utilization_percent', 0) > 80:
            issues.append("High connection pool utilization")
            recommendations.append("Consider increasing pool size or optimizing connection usage")
        
        # Analyze query patterns
        query_stats = self.get_query_statistics()
        frequent_queries = [
            q for q in query_stats.values() 
            if q['call_count'] > 100 and q['average_time'] > 0.1
        ]
        
        if frequent_queries:
            issues.append(f"Found {len(frequent_queries)} frequently called slow queries")
            recommendations.append("Consider caching or optimizing frequently called queries")
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.now().isoformat()
        }


# Global monitor instance
db_monitor = DatabaseMonitor()


def setup_sqlalchemy_monitoring(engine: Engine):
    """
    Set up SQLAlchemy event listeners for monitoring
    """
    
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time"""
        context._query_start_time = time.perf_counter()
        context._query_statement = statement
        context._query_parameters = parameters
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query completion and metrics"""
        if not hasattr(context, '_query_start_time'):
            return
        
        execution_time = time.perf_counter() - context._query_start_time
        
        # Create query hash for grouping
        query_hash = str(hash(statement.strip()))
        
        # Get stack trace for slow queries
        stack_trace = None
        if execution_time > db_monitor.slow_query_threshold:
            import traceback
            stack_trace = ''.join(traceback.format_stack()[-5:])  # Last 5 frames
        
        metrics = QueryMetrics(
            query_hash=query_hash,
            sql_text=statement,
            execution_time=execution_time,
            timestamp=datetime.now(),
            parameters=parameters or {},
            stack_trace=stack_trace,
            row_count=cursor.rowcount if hasattr(cursor, 'rowcount') else None,
            connection_id=str(id(conn))
        )
        
        db_monitor.record_query(metrics)
    
    @event.listens_for(Pool, "connect")
    def pool_connect(dbapi_conn, connection_record):
        """Record pool connection events"""
        logger.debug(f"New database connection established: {id(dbapi_conn)}")
    
    @event.listens_for(Pool, "checkout")
    def pool_checkout(dbapi_conn, connection_record, connection_proxy):
        """Record pool checkout events"""
        if hasattr(connection_proxy.pool, 'size'):
            metrics = ConnectionMetrics(
                pool_size=connection_proxy.pool.size(),
                checked_out=connection_proxy.pool.checkedout(),
                overflow=connection_proxy.pool.overflow(),
                checked_in=connection_proxy.pool.checkedin(),
                timestamp=datetime.now()
            )
            db_monitor.record_connection_stats(metrics)


def query_performance_monitor(threshold_seconds: float = 1.0):
    """
    Decorator for monitoring specific function query performance
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                execution_time = time.perf_counter() - start_time
                
                if execution_time > threshold_seconds:
                    logger.warning(
                        f"Function {f.__name__} executed slowly: {execution_time:.3f}s "
                        f"(threshold: {threshold_seconds}s)"
                    )
                
                # Store in Flask g for request context
                if hasattr(g, 'function_performance'):
                    g.function_performance[f.__name__] = execution_time
                else:
                    g.function_performance = {f.__name__: execution_time}
        
        return wrapper
    return decorator


@contextmanager
def query_analysis_context(operation_name: str):
    """
    Context manager for analyzing queries within a specific operation
    """
    start_time = time.perf_counter()
    initial_query_count = len(db_monitor.slow_queries)
    
    logger.info(f"Starting query analysis for operation: {operation_name}")
    
    try:
        yield
    finally:
        end_time = time.perf_counter()
        final_query_count = len(db_monitor.slow_queries)
        
        new_slow_queries = final_query_count - initial_query_count
        total_time = end_time - start_time
        
        logger.info(
            f"Operation '{operation_name}' completed in {total_time:.3f}s "
            f"with {new_slow_queries} new slow queries"
        )


class QueryAnalyzer:
    """
    Advanced query analysis and optimization suggestions
    """
    
    @staticmethod
    def analyze_query_patterns() -> Dict[str, Any]:
        """Analyze query patterns for optimization opportunities"""
        query_stats = db_monitor.get_query_statistics()
        
        patterns = {
            'n_plus_one_candidates': [],
            'missing_index_candidates': [],
            'inefficient_joins': [],
            'large_result_sets': []
        }
        
        for query_hash, stats in query_stats.items():
            sql_text = stats['sql_sample'].lower()
            
            # Detect potential N+1 queries
            if (stats['call_count'] > 50 and 
                'select' in sql_text and 
                'where' in sql_text and 
                stats['average_time'] > 0.05):
                patterns['n_plus_one_candidates'].append({
                    'query_hash': query_hash,
                    'call_count': stats['call_count'],
                    'average_time': stats['average_time'],
                    'sql_sample': stats['sql_sample'][:100]
                })
            
            # Detect missing index candidates
            if (stats['average_time'] > 0.5 and 
                ('where' in sql_text or 'order by' in sql_text) and
                'index' not in sql_text):
                patterns['missing_index_candidates'].append({
                    'query_hash': query_hash,
                    'average_time': stats['average_time'],
                    'sql_sample': stats['sql_sample'][:100]
                })
            
            # Detect inefficient joins
            if (stats['average_time'] > 1.0 and 
                'join' in sql_text and 
                stats['call_count'] > 10):
                patterns['inefficient_joins'].append({
                    'query_hash': query_hash,
                    'average_time': stats['average_time'],
                    'call_count': stats['call_count'],
                    'sql_sample': stats['sql_sample'][:100]
                })
        
        return patterns
    
    @staticmethod
    def generate_optimization_report() -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        patterns = QueryAnalyzer.analyze_query_patterns()
        performance_issues = db_monitor.analyze_performance_issues()
        
        recommendations = []
        
        # N+1 query recommendations
        if patterns['n_plus_one_candidates']:
            recommendations.append({
                'type': 'N+1 Query Optimization',
                'priority': 'HIGH',
                'description': 'Use eager loading or batch queries to reduce database round trips',
                'affected_queries': len(patterns['n_plus_one_candidates']),
                'potential_improvement': 'Up to 90% query reduction'
            })
        
        # Index recommendations
        if patterns['missing_index_candidates']:
            recommendations.append({
                'type': 'Missing Indexes',
                'priority': 'HIGH',
                'description': 'Add database indexes for frequently filtered/sorted columns',
                'affected_queries': len(patterns['missing_index_candidates']),
                'potential_improvement': 'Up to 10x query speed improvement'
            })
        
        # Join optimization recommendations
        if patterns['inefficient_joins']:
            recommendations.append({
                'type': 'Join Optimization',
                'priority': 'MEDIUM',
                'description': 'Optimize table joins and consider denormalization for frequently accessed data',
                'affected_queries': len(patterns['inefficient_joins']),
                'potential_improvement': 'Up to 5x query speed improvement'
            })
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'query_patterns': patterns,
            'performance_issues': performance_issues,
            'recommendations': recommendations,
            'summary': {
                'total_slow_queries': len(db_monitor.slow_queries),
                'total_query_types': len(db_monitor.query_stats),
                'monitoring_period_hours': 24,
                'optimization_opportunities': len(recommendations)
            }
        }


# Flask integration
def init_db_monitoring(app):
    """Initialize database monitoring for Flask app"""
    
    @app.before_request
    def before_request():
        """Set up request-level monitoring"""
        g.request_start_time = time.perf_counter()
        g.function_performance = {}
    
    @app.after_request
    def after_request(response):
        """Log request performance metrics"""
        if hasattr(g, 'request_start_time'):
            request_time = time.perf_counter() - g.request_start_time
            
            if request_time > 2.0:  # Log slow requests
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {request_time:.3f}s"
                )
            
            # Log function performance if available
            if hasattr(g, 'function_performance'):
                total_function_time = sum(g.function_performance.values())
                if total_function_time > 1.0:
                    logger.info(
                        f"Request function breakdown: {g.function_performance}"
                    )
        
        return response
    
    # Set up SQLAlchemy monitoring
    if hasattr(app, 'extensions') and 'sqlalchemy' in app.extensions:
        engine = app.extensions['sqlalchemy'].db.engine
        setup_sqlalchemy_monitoring(engine)
    
    logger.info("Database monitoring initialized")


# Export main components
__all__ = [
    'DatabaseMonitor',
    'QueryMetrics',
    'ConnectionMetrics',
    'QueryAnalyzer',
    'db_monitor',
    'setup_sqlalchemy_monitoring',
    'query_performance_monitor',
    'query_analysis_context',
    'init_db_monitoring'
]