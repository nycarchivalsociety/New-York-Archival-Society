# api/index.py

import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Get project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# Load environment variables from .env file
env_path = ROOT_DIR / '.env'

if env_path.exists():
    logger.info(f"Loading .env from: {env_path}")
    load_dotenv(env_path)
    
    # Verify critical environment variables are loaded
    required_vars = ['DATABASE_URI']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Please ensure your .env file is properly configured.")
    else:
        logger.info("Environment configuration loaded successfully")
        
        # Log Flask configuration for debugging
        flask_env = os.environ.get('FLASK_ENV', 'not set')
        flask_debug = os.environ.get('FLASK_DEBUG', 'not set')
        logger.info(f"Flask Environment: {flask_env}")
        logger.info(f"Flask Debug Mode: {flask_debug}")
else:
    logger.warning(f"No .env file found at {env_path}")
    logger.info("Using system environment variables only")

from app import create_app
from app.services.cache_service import cache_service

# Create app with appropriate configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

# Serverless optimizations for Vercel
def optimize_for_serverless():
    """Optimize application for serverless environment"""
    if config_name == 'production':
        try:
            # Warm up critical caches
            with app.app_context():
                cache_service.warm_cache()
                
            # Preload essential modules
            import app.db.models
            import app.services.paypal_service
            import app.services.transaction_service
            
            logger.info("Serverless optimization completed")
        except Exception as e:
            logger.warning(f"Serverless optimization failed: {str(e)}")

# Global error handler for better performance
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler to prevent cold start issues"""
    logger.error(f"Unhandled exception: {str(e)}")
    return {"error": "Internal server error"}, 500

# Export app for WSGI servers 
#trigger
application = app

if __name__ == '__main__':
    # Development server
    # Production mode should NEVER run in debug mode for performance and security
    if config_name == 'production':
        debug_mode = False  # Force debug OFF in production
        logger.info("Production mode: Debug disabled for optimal performance")
        optimize_for_serverless()  # Run optimization in production mode
    else:
        debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 'yes', 'on']
    
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
