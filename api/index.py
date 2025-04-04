# api/index.py

import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging1
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# Load environment variables
env_path = ROOT_DIR / '.env'
dev_env_path = ROOT_DIR / '.env.development'

if env_path.exists():
    logger.info(f"Loading .env from: {env_path}")
    load_dotenv(env_path)
elif dev_env_path.exists():
    logger.info(f"Loading .env.development from: {dev_env_path}")
    load_dotenv(dev_env_path)
else:
    logger.warning(f"No environment files found in {ROOT_DIR}")

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
