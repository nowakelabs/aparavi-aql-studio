#!/usr/bin/env python3
"""
Core application module for the Aparavi Query Assistant

This module is responsible for creating and configuring the Flask application.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, session

# Import other modules from the package
from modules.core.api import AparaviAPI
from modules.llm.base import get_llm_provider
from modules.core.callbacks import register_callbacks

def create_app(db_store=None):
    """Create and configure the Flask application
    
    Args:
        db_store: Optional database connection for credentials and caching
        
    Returns:
        Flask application instance
    """
    # Import modules here to avoid circular imports
    from modules.db.database import CredentialStore
    app = Flask(
        __name__, 
        template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates'),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static')
    )
    
    # Import config module here to avoid circular imports
    import config
    
    # Configure Flask app
    app.secret_key = config.SECRET_KEY
    app.config.from_object(config)
    
    # Use the provided database connection, or None - avoid creating a new one
    # to prevent database lock conflicts
    
    # Configure logging
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize API client with default settings
    aparavi_api = AparaviAPI(
        server=config.DEFAULT_APARAVI_SERVER,
        endpoint=config.DEFAULT_API_ENDPOINT,
        username=config.DEFAULT_USERNAME,
        password=config.DEFAULT_PASSWORD,
        db_store=db_store
    )
    
    # Check for stored server settings in database and update the API client if available
    try:
        stored_server = db_store.get_setting('aparavi_server')
        if stored_server:
            aparavi_api.set_server(stored_server)
            logging.info(f"Using stored server address: {stored_server}")
            
        stored_endpoint = db_store.get_setting('api_endpoint')
        if stored_endpoint:
            aparavi_api.set_endpoint(stored_endpoint)
            logging.info(f"Using stored API endpoint: {stored_endpoint}")
            
        # Check for stored credentials
        stored_username = db_store.get_credential('aparavi', 'username')
        stored_password = db_store.get_credential('aparavi', 'password')
        if stored_username and stored_password:
            aparavi_api.update_credentials(
                server=aparavi_api.server,  # Keep the server we just set
                endpoint=aparavi_api.endpoint,  # Keep the endpoint we just set
                username=stored_username,
                password=stored_password
            )
    except Exception as e:
        logging.warning(f"Error loading Aparavi server settings from database: {e}")
    
    # Check for stored API keys in database and update config if needed
    try:
        # Check for stored Ollama settings
        stored_ollama_base_url = db_store.get_setting('ollama_base_url')
        if stored_ollama_base_url:
            config.OLLAMA_BASE_URL = stored_ollama_base_url
            
        stored_ollama_model = db_store.get_setting('ollama_model')
        if stored_ollama_model:
            config.OLLAMA_MODEL = stored_ollama_model
    except Exception as e:
        logging.warning(f"Error retrieving credentials from database: {e}")
    
    # Initialize LLM provider
    try:
        llm_provider = get_llm_provider(config.DEFAULT_LLM_PROVIDER, config, db_store)
        if llm_provider is None:
            logging.warning("No LLM provider available - application will run with limited functionality")
            # Create a flag to indicate LLM is not available
            app.config['LLM_AVAILABLE'] = False
        else:
            app.config['LLM_AVAILABLE'] = True
    except Exception as e:
        logging.error(f"Error initializing LLM provider: {e}")
        llm_provider = None
        app.config['LLM_AVAILABLE'] = False
    
    # Register application context objects
    @app.context_processor
    def inject_global_vars():
        return {
            'app_name': 'AQL Studio',
            'llm_provider': config.DEFAULT_LLM_PROVIDER.capitalize()
        }
    
    # Import and register routes
    from modules.core.routes import configure_routes
    configure_routes(app, aparavi_api, llm_provider, config)
    
    # Register callback functions
    register_callbacks(app)
    
    return app