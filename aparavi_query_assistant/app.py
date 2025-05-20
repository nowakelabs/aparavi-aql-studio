#!/usr/bin/env python3
"""
Aparavi Query Assistant

A modular web application that translates natural language questions into
AQL queries with visualization recommendations.

This is the main entry point for the application.
"""

import sys
import os
import atexit
import signal
import logging
from modules.core.app import create_app
import config
from modules.db.database import CredentialStore

# Import query logger to initialize it
import modules.utils.query_logger

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check for command-line arguments to use in-memory database
in_memory = '--in-memory' in sys.argv or os.environ.get('USE_IN_MEMORY_DB') == '1'

# Handle Flask debug mode reloading - use in-memory only when we're the reloader process
# This avoids database locking issues while still using file database in production
if config.DEBUG and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    logger.info("Flask reloader process detected - using in-memory database to avoid file locking")
    in_memory = True

db_path = None

if '--alternate-db' in sys.argv:
    # Use an alternate database path for testing
    idx = sys.argv.index('--alternate-db')
    if len(sys.argv) > idx + 1:
        db_path = sys.argv[idx + 1]

# Initialize database connection
db_store = CredentialStore(config, db_path=db_path, in_memory=in_memory)

# Function to discover Ollama instances
def discover_ollama_instance():
    """
    Check for Ollama availability at different locations.
    This helps automatically find Ollama in both Docker Compose and local environments.
    """
    import requests
    import time
    
    # Potential Ollama locations to check
    ollama_hosts = [
        {"url": "http://aparavi-ollama:11434", "name": "aparavi-ollama (Docker Compose)"},
        {"url": "http://localhost:11434", "name": "localhost"}
    ]
    
    # Check for environment variable override for Ollama host
    if os.environ.get('OLLAMA_HOST'):
        env_host = os.environ.get('OLLAMA_HOST')
        logger.info(f"Using Ollama host from environment variable: {env_host}")
        # Add it as the first host to check
        ollama_hosts.insert(0, {"url": env_host, "name": "environment variable"})
    
    # Check for environment variable override for Ollama model
    if os.environ.get('OLLAMA_MODEL'):
        model = os.environ.get('OLLAMA_MODEL')
        logger.info(f"Using Ollama model from environment variable: {model}")
        config.OLLAMA_MODEL = model
        # Also store this in the database for use in the UI
        db_store.store_setting('ollama_model', model)
    
    # Try to get stored URL from database first
    stored_url = db_store.get_setting('ollama_base_url')
    if stored_url:
        logger.info(f"Using Ollama URL from database: {stored_url}")
        # Update config with stored URL
        config.OLLAMA_BASE_URL = stored_url
        return stored_url
    
    # Check each potential location
    for host in ollama_hosts:
        logger.info(f"Checking for Ollama at {host['name']} ({host['url']})")
        try:
            # Set a short timeout to not hang startup for too long
            response = requests.get(f"{host['url']}/api/tags", timeout=2)
            
            if response.status_code == 200:
                logger.info(f"✓ Ollama discovered at {host['name']}")
                
                # Update config with discovered URL
                config.OLLAMA_BASE_URL = host['url']
                
                # Store this URL in settings for future use
                db_store.store_setting('ollama_base_url', host['url'])
                
                return host['url']
        except Exception as e:
            logger.info(f"✗ Could not connect to Ollama at {host['name']}: {str(e)}")
    
    # No instance found, use default
    logger.info("No Ollama instance found, using default URL")
    return config.OLLAMA_BASE_URL

# Attempt to discover Ollama instance
ollama_url = discover_ollama_instance()
logger.info(f"Using Ollama URL: {ollama_url}")

# Define cleanup function
def cleanup_database():
    logger.info("Shutting down and cleaning up database connection...")
    if db_store:
        db_store.close()
    logger.info("Cleanup complete")

# Register cleanup on exit
atexit.register(cleanup_database)

# Register signal handlers for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}. Shutting down...")
    sys.exit(0)  # This will trigger the atexit handlers

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Create the Flask application
app = create_app(db_store=db_store)

if __name__ == '__main__':
    print("Aparavi Query Assistant")
    print("-----------------------")
    print(f"Starting the server on http://{config.HOST}:{config.PORT}")
    print("Press Ctrl+C to quit")
    
    try:
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    except Exception as e:
        logger.error(f"Error running application: {e}")
    finally:
        cleanup_database()