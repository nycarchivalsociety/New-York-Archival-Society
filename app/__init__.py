from flask import Flask
from flask_migrate import Migrate
from flask_caching import Cache
import os
import logging
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
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'new_york_archival_society'
        },
        
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
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///dev.db'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')
    
    # Production-optimized database settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        # Larger pool for production workloads
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 50)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 25)),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 60)),
        
        # Production-specific optimizations
        'connect_args': {
            **Config.SQLALCHEMY_ENGINE_OPTIONS['connect_args'],
            'sslmode': 'require',  # Force SSL in production
            'tcp_keepalives_idle': '600',
            'tcp_keepalives_interval': '30',
            'tcp_keepalives_count': '3'
        }
    }
    
    # Enhanced cache configuration for production
    # Use Redis if available, otherwise fall back to simple cache
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 900  # 15 minutes
    CACHE_KEY_PREFIX = 'nyas:'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

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

    # Register error handlers
    _register_error_handlers(app)
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if app.config.get('SESSION_COOKIE_SECURE'):
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
