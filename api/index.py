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
else:
    logger.warning(f"No .env file found at {env_path}")
    logger.info("Using system environment variables only")

from app import create_app
from app.services.cache_service import cache_service

# Create app with appropriate configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

# Warm up cache on startup in production
if config_name == 'production':
    with app.app_context():
        try:
            cache_service.warm_cache()
        except Exception as e:
            logger.warning(f"Cache warm-up failed: {str(e)}")

# Export app for WSGI servers
application = app

if __name__ == '__main__':
    # Development server
    debug_mode = config_name == 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
