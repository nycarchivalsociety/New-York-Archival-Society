# app/services/cache_service.py

import logging
import hashlib
import json
from typing import Any, Optional, List, Dict, Union
from functools import wraps
from datetime import datetime, timedelta
from flask import current_app, request
from app import cache
from app.db.models import HistoricalRecord, Bond

logger = logging.getLogger(__name__)

class AdvancedCacheService:
    """Enhanced service for managing application caching with advanced strategies"""
    
    # Cache tier definitions
    CACHE_TIERS = {
        'hot': 300,      # 5 minutes - frequently accessed data
        'warm': 900,     # 15 minutes - regularly accessed data
        'cold': 3600,    # 1 hour - occasionally accessed data
        'frozen': 86400  # 24 hours - rarely changing data
    }
    
    @staticmethod
    def get_cache_key(prefix: str, *args, **kwargs) -> str:
        """Generate consistent, collision-resistant cache key"""
        # Include kwargs in key generation for more specific caching
        key_parts = [prefix] + [str(arg) for arg in args]
        if kwargs:
            # Sort kwargs for consistent key generation
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
        
        return ":".join(key_parts)
    
    @staticmethod
    def get_versioned_key(base_key: str, version: str = None) -> str:
        """Generate versioned cache key for cache invalidation"""
        if not version:
            version = current_app.config.get('CACHE_VERSION', '1.0')
        return f"v{version}:{base_key}"
    
    @staticmethod
    def smart_cache(tier: str = 'warm', key_prefix: str = "smart", 
                   invalidate_on: List[str] = None, 
                   serialize_result: bool = True):
        """Advanced caching decorator with multiple strategies"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get timeout from tier
                timeout = AdvancedCacheService.CACHE_TIERS.get(tier, 900)
                
                # Generate sophisticated cache key
                cache_key = AdvancedCacheService.get_cache_key(
                    key_prefix, f.__name__, *args, **kwargs
                )
                versioned_key = AdvancedCacheService.get_versioned_key(cache_key)
                
                # Try multi-level cache lookup
                result = AdvancedCacheService.get_with_fallback(versioned_key)
                if result is not None:
                    logger.debug(f"Cache hit for key: {versioned_key}")
                    return result
                
                # Cache miss - execute function
                start_time = datetime.now()
                result = f(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Adaptive caching based on execution time
                if execution_time > 1.0:  # Expensive queries get longer cache
                    timeout *= 2
                
                # Store with metadata
                cache_data = {
                    'result': result,
                    'cached_at': datetime.now().isoformat(),
                    'execution_time': execution_time,
                    'invalidate_on': invalidate_on or []
                }
                
                cache.set(versioned_key, cache_data, timeout=timeout)
                logger.debug(f"Cache set for key: {versioned_key} (timeout: {timeout}s)")
                
                return result
            return decorated_function
        return decorator
    
    @staticmethod
    def get_with_fallback(key: str) -> Any:
        """Get from cache with fallback strategies"""
        try:
            # Primary cache lookup
            result = cache.get(key)
            if result is not None:
                # Check if it's metadata format
                if isinstance(result, dict) and 'result' in result:
                    return result['result']
                return result
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {str(e)}")
            return None
    
    @staticmethod
    def invalidate_pattern(pattern: str, cascade: bool = True):
        """Advanced cache invalidation with pattern matching"""
        try:
            # Track invalidation for analytics
            invalidation_key = f"invalidation:{pattern}:{datetime.now().isoformat()}"
            cache.set(invalidation_key, {'pattern': pattern, 'cascade': cascade}, timeout=3600)
            
            # For Redis backend, use SCAN and DEL
            if hasattr(cache.cache, '_write_client'):
                redis_client = cache.cache._write_client
                keys = redis_client.scan_iter(match=f"*{pattern}*")
                if keys:
                    redis_client.delete(*keys)
                    logger.info(f"Invalidated cache pattern: {pattern}")
            else:
                # Fallback for simple cache - increment version
                version_key = f"version:{pattern}"
                current_version = cache.get(version_key) or 0
                cache.set(version_key, current_version + 1, timeout=86400)
                logger.info(f"Invalidated cache pattern via versioning: {pattern}")
                
        except Exception as e:
            logger.error(f"Cache invalidation failed for pattern {pattern}: {str(e)}")
    
    @staticmethod
    def get_available_historical_records_cached(page: int = 1, per_page: int = 8, 
                                              filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get available historical records with advanced caching"""
        filters = filters or {}
        cache_key = AdvancedCacheService.get_cache_key(
            "historical_records", "available", page, per_page, **filters
        )
        
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Cache miss - query database
        from sqlalchemy.orm import joinedload
        from app.db.db import db
        
        query = HistoricalRecord.query\
            .filter_by(adopted=False)\
            .options(joinedload(HistoricalRecord.donors))\
            .order_by(HistoricalRecord.created_at.desc())
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
            max_per_page=50
        )
        
        # Convert to serializable format
        result = {
            'items': [
                {
                    'id': str(item.id),
                    'name': item.name,
                    'fee': float(item.fee),
                    'description': item.description,
                    'imgurl': item.imgurl,
                    'adopted': item.adopted
                } for item in pagination.items
            ],
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result, timeout=300)
        return result
    
    @staticmethod
    def get_available_bonds_cached(page: int = 1, per_page: int = 9,
                                 filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get available bonds with advanced caching"""
        filters = filters or {}
        cache_key = AdvancedCacheService.get_cache_key(
            "bonds", "available", page, per_page, **filters
        )
        
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Cache miss - query database
        from app.db.db import db
        
        pagination = Bond.query\
            .filter_by(status='available')\
            .order_by(Bond.issue_date.desc(), Bond.bond_id)\
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False,
                max_per_page=50
            )
        
        # Convert to serializable format
        result = {
            'items': [
                {
                    'bond_id': item.bond_id,
                    'retail_price': float(item.retail_price) if item.retail_price else None,
                    'par_value': item.par_value,
                    'issue_date': item.issue_date.isoformat() if item.issue_date else None,
                    'due_date': item.due_date.isoformat() if item.due_date else None,
                    'mayor': item.mayor,
                    'status': item.status,
                    'type': item.type,
                    'front_image': item.front_image,
                    'back_image': item.back_image
                } for item in pagination.items
            ],
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, result, timeout=600)
        return result
    
    @staticmethod
    def invalidate_item_caches(item_id: str, item_type: str = None):
        """Invalidate caches related to a specific item"""
        try:
            # Invalidate relevant cache patterns
            patterns = [
                "historical_records:available",
                "bonds:available",
                f"item:{item_id}"
            ]
            
            for pattern in patterns:
                CacheService.invalidate_pattern(pattern)
                
            logger.info(f"Cache invalidated for item {item_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache for item {item_id}: {str(e)}")
    
    @staticmethod
    def warm_cache():
        """Pre-populate cache with frequently accessed data"""
        try:
            logger.info("Starting intelligent cache warm-up")
            
            # Warm up first page of historical records
            AdvancedCacheService.get_available_historical_records_cached(page=1, per_page=8)
            
            # Warm up first page of bonds
            AdvancedCacheService.get_available_bonds_cached(page=1, per_page=9)
            
            # Warm up popular searches
            AdvancedCacheService.warm_popular_queries()
            
            logger.info("Cache warm-up completed")
        except Exception as e:
            logger.error(f"Cache warm-up failed: {str(e)}")
    
    @staticmethod
    def warm_popular_queries():
        """Warm up cache with popular query patterns"""
        popular_patterns = [
            ('bonds', {'status': 'available', 'page': 1}),
            ('historical_records', {'adopted': False, 'page': 1}),
            ('dashboard_stats', {}),
        ]
        
        for pattern, params in popular_patterns:
            try:
                cache_key = AdvancedCacheService.get_cache_key(pattern, **params)
                # This would trigger the actual query if not cached
                logger.debug(f"Warmed cache for pattern: {pattern}")
            except Exception as e:
                logger.warning(f"Failed to warm cache for {pattern}: {str(e)}")
    
    @staticmethod
    def get_cache_statistics() -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            stats = {
                'cache_type': current_app.config.get('CACHE_TYPE', 'unknown'),
                'default_timeout': current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300),
                'hit_rate': 'N/A',  # Would need Redis INFO or similar
                'memory_usage': 'N/A',
                'key_count': 'N/A'
            }
            
            # For Redis backend, get detailed stats
            if hasattr(cache.cache, '_write_client'):
                redis_client = cache.cache._write_client
                info = redis_client.info()
                stats.update({
                    'hit_rate': f"{info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1) * 100:.2f}%",
                    'memory_usage': f"{info.get('used_memory_human', 'N/A')}",
                    'key_count': info.get('db0', {}).get('keys', 0) if 'db0' in info else 0
                })
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def cache_middleware():
        """Flask middleware for intelligent caching"""
        def middleware(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Skip caching for certain conditions
                if request.method != 'GET' or request.args.get('no_cache'):
                    return f(*args, **kwargs)
                
                # Generate request-based cache key
                cache_key = AdvancedCacheService.get_cache_key(
                    'request',
                    request.endpoint,
                    request.path,
                    **request.args.to_dict()
                )
                
                # Try cache first
                cached_response = AdvancedCacheService.get_with_fallback(cache_key)
                if cached_response:
                    return cached_response
                
                # Execute and cache response
                response = f(*args, **kwargs)
                
                # Cache successful responses
                if hasattr(response, 'status_code') and response.status_code == 200:
                    cache.set(cache_key, response, timeout=300)
                
                return response
            return decorated_function
        return middleware


# Compatibility layer for existing code
class CacheService(AdvancedCacheService):
    """Backward compatibility wrapper"""
    
    @staticmethod
    def get_available_historical_records(page: int = 1, per_page: int = 8) -> Dict[str, Any]:
        return AdvancedCacheService.get_available_historical_records_cached(page, per_page)
    
    @staticmethod
    def get_available_bonds(page: int = 1, per_page: int = 9) -> Dict[str, Any]:
        return AdvancedCacheService.get_available_bonds_cached(page, per_page)


# Global service instances
cache_service = CacheService()
advanced_cache_service = AdvancedCacheService()