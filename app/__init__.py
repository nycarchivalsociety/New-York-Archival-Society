from flask import Flask, request
from flask_migrate import Migrate
from flask_caching import Cache
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from app.db.db import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize extensions
cache = Cache()

# Removed Vercel-incompatible monitoring modules

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Optimized Database configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Connection Pool Optimization
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 20)),  # Increased from 10
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 15)),  # Increased from 5
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 45)),  # Increased from 30
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),  # Increased from 1800
        'pool_pre_ping': True,
        
        # Connection Management  
        'pool_reset_on_return': 'commit',  # Reset connections properly
        
        # Query Optimization
        'echo': os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true',
        'echo_pool': os.environ.get('SQLALCHEMY_ECHO_POOL', 'false').lower() == 'true',
        
        # Performance Settings
        'execution_options': {
            'isolation_level': 'READ_COMMITTED',
            'autocommit': False
        }
    }
    
    # Cache configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    # PayPal configuration
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
    PAYPAL_CLIENT_SECRET_KEY = os.environ.get('PAYPAL_CLIENT_SECRET_KEY')
    PAYPAL_API_BASE_URL = os.environ.get('PAYPAL_API_BASE_URL')
    
    # Email configuration
    EMAILJS_SERVICE_ID = os.environ.get('EMAILJS_SERVICE_ID')
    EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL = os.environ.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL')
    EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM = os.environ.get('EMAILJS_TEMPLATE_ID_FOR_CONTACT')
    EMAILJS_API_ID = os.environ.get('EMAILJS_API_ID')
    RECIPIENT_EMAILS = os.environ.get('RECIPIENT_EMAILS')
    
    # Security headers
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 'yes', 'on']
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')
    
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URI environment variable is required")

class ProductionConfig(Config):
    """Production configuration optimized for speed and performance"""
    # Force debug mode OFF in production regardless of environment variable
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')
    
    # Production-optimized database settings for maximum speed
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        # Aggressive connection pooling for high performance
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 100)),  # Larger pool
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 50)),  # Higher overflow
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),  # Faster timeout
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),
        'pool_pre_ping': False,  # Disable for speed (assume healthy connections)
        
        # Production-specific performance optimizations
        'connect_args': {
            'sslmode': 'require',  # Force SSL in production
            'connect_timeout': 5,  # Fast connection timeout
            'application_name': 'new_york_archival_society'
        },
        
        # Disable query logging in production for performance
        'echo': False,
        'echo_pool': False,
        
        # Optimized execution options for production
        'execution_options': {
            'isolation_level': 'READ_COMMITTED',
            'autocommit': False,
            'compiled_cache': {},  # Enable SQL compilation cache
        }
    }
    
    # High-performance cache configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'redis')  # Prefer Redis over simple
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 1800  # 30 minutes (longer caching)
    CACHE_KEY_PREFIX = 'nyas:prod:'
    
    # Production security and performance headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    SESSION_COOKIE_SECURE = True  # Force HTTPS cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # Stricter security
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minute sessions
    
    # Disable CSRF for API endpoints in production (if using API tokens)
    # WTF_CSRF_ENABLED can be overridden per route
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Template optimizations
    TEMPLATES_AUTO_RELOAD = False  # Disable auto-reload for speed
    EXPLAIN_TEMPLATE_LOADING = False  # Disable template debugging
    
    # JSON optimizations
    JSON_SORT_KEYS = False  # Don't sort JSON keys (faster)
    JSONIFY_PRETTYPRINT_REGULAR = False  # Compact JSON in production
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific logging configuration
        import logging
        import os
        from logging.handlers import RotatingFileHandler
        
        # Reduce logging level for performance
        if not app.debug:
            # Only log warnings and errors in production
            app.logger.setLevel(logging.WARNING)
            
            # Configure efficient file logging
            if os.environ.get('LOG_TO_FILE', 'false').lower() == 'true':
                file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                file_handler.setLevel(logging.WARNING)
                app.logger.addHandler(file_handler)

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory pattern with enhanced configuration"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Validate critical configuration
    _validate_configuration(app)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize cache with fallback to simple cache if Redis fails
    try:
        cache.init_app(app)
    except Exception as e:
        logger.warning(f"Failed to initialize cache with {app.config.get('CACHE_TYPE', 'unknown')} backend: {e}")
        # Force fallback to simple cache
        app.config['CACHE_TYPE'] = 'simple'
        cache.init_app(app)
        logger.info("Initialized cache with simple backend as fallback")

    # Import models within app context
    with app.app_context():
        from app.db import models

    # Register blueprints
    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Register context processor to make EmailJS configuration available to all templates
    @app.context_processor
    def inject_emailjs_config():
        """Make EmailJS configuration available to all templates"""
        return {
            'EMAILJS_SERVICE_ID': app.config.get('EMAILJS_SERVICE_ID', ''),
            'EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL': app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL', ''),
            'EMAILJS_API_ID': app.config.get('EMAILJS_API_ID', ''),
            'RECIPIENT_EMAILS': app.config.get('RECIPIENT_EMAILS', ''),
            'PAYPAL_CLIENT_ID': app.config.get('PAYPAL_CLIENT_ID', '')
        }

    # Register error handlers
    _register_error_handlers(app)
    
    # Security headers with production-specific optimizations
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Production-specific headers for performance and security
        if config_name == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            # Cache static assets aggressively in production
            if request.endpoint and request.endpoint.startswith('static'):
                response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
                response.headers['Expires'] = (datetime.utcnow() + timedelta(days=365)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        elif app.config.get('SESSION_COOKIE_SECURE'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
        return response
    
    logger.info(f"Application created successfully with config: {config_name}")
    return app

def _validate_configuration(app: Flask) -> None:
    """Validate critical application configuration"""
    required_config = ['SQLALCHEMY_DATABASE_URI']
    
    if app.config.get('FLASK_ENV') == 'production':
        required_config.extend([
            'SECRET_KEY',
            'PAYPAL_CLIENT_ID',
            'PAYPAL_CLIENT_SECRET_KEY',
            'PAYPAL_API_BASE_URL'
        ])
    
    missing_config = []
    for key in required_config:
        if not app.config.get(key):
            missing_config.append(key)
    
    if missing_config:
        logger.error(f"Missing required configuration: {', '.join(missing_config)}")
        raise ValueError(f"Missing required configuration: {', '.join(missing_config)}")

def _register_error_handlers(app: Flask) -> None:
    """Register centralized error handlers"""
    from flask import jsonify, render_template, request
    
    @app.errorhandler(400)
    def bad_request_error(error):
        if request.is_json:
            return jsonify({'error': 'Bad request'}), 400
        return render_template('Error_Pages/404_not_found.html'), 400
    
    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json:
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('Error_Pages/404_not_found.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f'Internal server error: {str(error)}')
        if request.is_json:
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('Error_Pages/404_not_found.html'), 500
