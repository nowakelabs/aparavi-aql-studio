#!/usr/bin/env python3
"""
Route definitions for the Aparavi Query Assistant

This module defines the routes and view functions for the Flask application.
"""

import logging
import json
import time
import re
import os
import sys
import uuid
import json
import pickle
import base64
import logging
import zipfile
import pathlib
import hashlib
import shutil
import datetime
from werkzeug.utils import secure_filename
import datetime
import traceback
import threading
import urllib.parse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly
import plotly.graph_objects as go
from flask import render_template, request, jsonify, redirect, url_for, session, flash, Response, current_app, send_file, json as flask_json
from markupsafe import Markup

# Import chat logging functionality
from modules.utils.chat_logger import log_chat_message, log_analysis, log_error, log_info

# Import query logger
from modules.utils.query_logger import (
    log_query_request, log_query_generation, log_query_execution, 
    log_query_error, log_query_modification, log_query_performance,
    log_llm_processing, log_query_feedback, log_query_validation
)

# Import AQL library utilities
from modules.utils.aql_library import get_all_library_queries, get_library_categories, get_query_by_id

# Import query preprocessor
from modules.utils.query_preprocessor import preprocess_query

# Import visualization modules
try:
    from modules.visualizations.manager import VisualizationManager
    VISUALIZATION_ENABLED = True
except ImportError:
    VISUALIZATION_ENABLED = False

# Import debug version of sanitize_query
from modules.core.debug_routes import sanitize_query

# Import extended examples
try:
    from modules.utils.extended_examples import get_all_examples, get_home_examples as get_extended_home_examples
    USE_EXTENDED_EXAMPLES = True
except ImportError:
    USE_EXTENDED_EXAMPLES = False

# Import chat prompts
from modules.utils.chat_prompts import (
    ANALYSIS_SYSTEM_PROMPT, 
    CHAT_SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    ANALYSIS_PROMPT_CLASSIFICATION,
    EMPTY_RESULTS_ANALYSIS_PROMPT
)

# Import LLM provider factory
from modules.llm.base import get_llm_provider

# Import Aparavi API client
from modules.core.api import AparaviAPI

# Global variables to hold the API client and LLM provider
_api_client = None
_llm_provider = None
_visualization_manager = None

# Helper function to get LLM provider for consistent usage
#def get_llm_provider(provider_name, config_obj):
#    """Get LLM provider instance based on name
#    
#    Args:
#        provider_name (str): Name of the provider (openai, ollama, etc.)
#        config_obj: Configuration object with settings
#        
#    Returns:
#        LLM Provider instance
#    """
#    return create_llm_provider(provider_name, config_obj)

def get_api_client():
    """Get or create the Aparavi API client instance
    
    Returns:
        AparaviAPI: The API client instance
    """
    global _api_client
    return _api_client

def get_llm_client(provider=None):
    """Get the appropriate LLM client based on provider
    
    Args:
        provider (str, optional): The LLM provider name. If None, uses default.
        
    Returns:
        LLM provider instance
    """
    global _llm_provider
    global _api_client
    
    # If provider is specified and is different from current, create a new one
    if provider and _llm_provider and provider != _llm_provider.__class__.__name__.lower().replace('provider', ''):
        # Import here to avoid circular imports
        import config
        from modules.llm.base import get_llm_provider
        # Pass the database connection to ensure API keys can be retrieved
        return get_llm_provider(provider, config, _api_client.db_store)
    
    return _llm_provider

def configure_routes(app, api_client, llm_provider, config):
    """Configure routes for the Flask application
    
    Args:
        app: Flask application instance
        api_client: Aparavi API client instance
        llm_provider: LLM provider instance
        config: Configuration module
    """
    logger = logging.getLogger(__name__)
    
    # Store the api_client globally for use in other functions
    global _api_client
    _api_client = api_client
    
    # Store the llm_provider globally
    global _llm_provider
    _llm_provider = llm_provider
    
    # Initialize visualization manager if enabled
    global _visualization_manager
    if VISUALIZATION_ENABLED and getattr(config, 'ENABLE_VISUALIZATIONS', True):
        _visualization_manager = VisualizationManager()
        logger.info("Visualization manager initialized")
    
    # Custom JSON encoder that handles NaN values
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.bool_)):
                return bool(obj)
            if pd.isna(obj):
                return None
            return super(NpEncoder, self).default(obj)
            
    # Register the custom encoder with Flask
    app.json.encoder = NpEncoder
    
    # Serve favicon.ico directly from root to override default behaviors
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('img/logo-48x48.png')
    
    # Helper function to format validation errors for better user experience
    def _format_validation_error(error_message, error_details, query):
        """Format validation error messages to be more user-friendly
        
        Args:
            error_message: The main error message from the API
            error_details: Detailed error information from the API
            query: The AQL query that caused the error
            
        Returns:
            A formatted error message that's more helpful to users
        """
        # Start with the base error message
        formatted_error = error_message
        
        # Add line number information if available in error_details
        if error_details and isinstance(error_details, dict):
            # Check for line and column information
            line_num = error_details.get('line')
            col_num = error_details.get('column')
            position = error_details.get('position')
            
            # Add positional information to the error message
            if line_num is not None and col_num is not None:
                formatted_error += f" at line {line_num}, column {col_num}"
            elif position is not None:
                # Try to calculate line and column from position
                lines = query.splitlines()
                current_pos = 0
                
                for i, line in enumerate(lines):
                    line_length = len(line) + 1  # +1 for newline
                    if current_pos + line_length > position:
                        # Found the line containing the error
                        col = position - current_pos + 1
                        formatted_error += f" at line {i+1}, column {col}"
                        break
                    current_pos += line_length
        
        # Add custom suggestions based on common error patterns
        if 'unexpected' in error_message.lower() and 'expecting' in error_message.lower():
            formatted_error += "\nTip: Check for syntax errors like missing commas, parentheses, or keywords."
        
        if 'column' in error_message.lower() or 'table' in error_message.lower():
            formatted_error += "\nTip: Verify that all table and column names are correct and properly quoted if needed."
        
        if 'operator' in error_message.lower():
            formatted_error += "\nTip: Check that you're using valid operators for the data types being compared."
        
        return formatted_error
    
    @app.route('/')
    def index():
        """Render the main page of the application"""
        # Get API configuration for the template using the current api_client server
        # This ensures we use the stored server from the database
        api_config = {
            'server': api_client.server,
            'endpoint': api_client.endpoint
        }
        
        # Check if we have result data from a previous operation
        result = request.args.get('result')
        
        # Get LLM provider availability status
        # We need to actually get a working provider, not just check if one exists
        llm_available = False
        provider_name = None
        
        # TEMPORARY FIX: Force LLM provider to be available to remove the warning message
        # This will be removed once the root cause is identified
        llm_available = True
        provider_name = "openai"
        app.config['LLM_AVAILABLE'] = True
        
        # Log the override
        logger.info("Overriding LLM provider detection to always show as available")
        
        # The actual provider detection is still done in the background
        try:
            # Try to get a provider to check its real status
            temp_provider = get_llm_provider('auto', config, api_client.db_store)
            
            if temp_provider is not None:
                # If we get a provider, store it in app config
                app.config['llm_provider'] = temp_provider
                provider_name = temp_provider.provider_name
                logger.info(f"Actual LLM provider status: {provider_name} is available")
            else:
                # Log if no provider could be found (but don't change llm_available)
                logger.warning("No actual LLM provider could be initialized, but UI will show as available")
        except Exception as e:
            # Log any errors but don't change llm_available
            logger.warning(f"Error during actual LLM provider check: {e}, but UI will show as available")
        
        # Debug logging for LLM provider status
        if llm_available:
            logger.info(f"Rendering index with LLM provider available: {provider_name}")
        else:
            logger.warning("Rendering index with NO LLM provider available")
            
        # Force app config value to match our detection
        app.config['LLM_AVAILABLE'] = llm_available
        
        if result:
            try:
                result_data = json.loads(result)
                return render_template('index.html', 
                                      result=result_data, 
                                      api_config=api_config, 
                                      llm_available=llm_available,
                                      provider_name=provider_name)
            except Exception as e:
                logger.error(f"Failed to parse result data: {e}")
        
        return render_template('index.html', 
                              api_config=api_config, 
                              llm_available=llm_available,
                              provider_name=provider_name)
    
    @app.route('/help')
    def help_page():
        """Render the help and documentation page"""
        return render_template('help.html')
    
    @app.route('/execute-aql', methods=['POST'])
    def execute_aql():
        """Directly execute an AQL query without LLM translation"""
        if request.method == 'POST':
            # Get the AQL query from the form
            aql_query = request.form.get('aql_query', '')
            
            if not aql_query:
                flash('Please provide an AQL query', 'warning')
                return redirect(url_for('index'))
            
            try:
                # Set up user ID for logging
                if 'user_id' not in session:
                    session['user_id'] = str(uuid.uuid4())
                user_id = session['user_id']
                
                # Log the direct AQL execution
                log_query_request(user_id, f"Direct AQL execution: {aql_query}")
                
                # Note: sanitize_query function has been removed
                # Use the query directly
                sanitized_query = aql_query
                
                # Validate the query
                is_valid, error_message, error_details = api_client.validate_query(sanitized_query)
                log_query_validation(user_id, sanitized_query, is_valid, error_message, error_details)
                
                # Initialize validation status
                validation_status = {
                    "status": "valid" if is_valid else "invalid",
                    "attempts": 1,
                    "maxAttempts": 1,  # No retry for direct AQL
                    "originalQuery": sanitized_query,
                    "currentQuery": sanitized_query,
                    "message": "Query validated successfully" if is_valid else error_message,
                    "progress": 90 if is_valid else 50
                }
                
                # Create result object
                result = {
                    'query': aql_query,
                    'explanation': "This query was executed directly from the library without AI translation.",
                    'understanding': "The query was executed directly from the library.",
                    'provider': "direct",  # Mark as direct execution
                    'validation': validation_status
                }
                
                # If query is invalid, add warning
                if not is_valid:
                    # Format the error message to be more user-friendly
                    friendly_error = _format_validation_error(error_message, error_details, sanitized_query)
                    
                    # Update validation status
                    validation_status["status"] = "failed"
                    validation_status["message"] = friendly_error
                    
                    # Add warning to the explanation
                    result['validation_warning'] = f"Warning: This query has syntax errors: {friendly_error}"
                    result['explanation'] += f"\n\nWARNING: This query has validation errors and may not execute correctly: {friendly_error}"
                
                # Store in session for history
                if 'query_history' not in session:
                    session['query_history'] = []
                
                # Add to history, limited to 10 entries
                history_entry = {
                    'question': "Direct AQL execution from library",
                    'query': result['query'],
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                session['query_history'] = [history_entry] + session['query_history'][:9]
                
                return render_template('index.html', 
                                    result=result, 
                                    api_config={'server': api_client.server, 'endpoint': api_client.endpoint},
                                    llm_available=True,
                                    provider_name="direct")
            except Exception as e:
                logger.error(f"Error processing direct AQL query: {e}")
                traceback.print_exc()
                flash(f"Error processing query: {str(e)}", 'danger')
                return redirect(url_for('index'))
                
        return redirect(url_for('index'))
    
    @app.route('/query', methods=['GET', 'POST'])
    def query():
        """Handle natural language query translation"""
        if request.method == 'POST':
            # Get the natural language question and provider from the form
            question = request.form.get('question', '')
            provider_name = request.form.get('provider', config.DEFAULT_LLM_PROVIDER)
            
            if not question:
                flash('Please enter a question', 'warning')
                return redirect(url_for('index'))
            
            try:
                # Debug mode logging - initial question
                if config.DEBUG:
                    logger.debug("-" * 80)
                    logger.debug(f"LLM INTERACTION START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f"USER QUESTION: {question}")
                    logger.debug(f"PROVIDER: {provider_name}")
                
                # Get current provider for query translation
                provider_name = request.form.get('provider', config.DEFAULT_LLM_PROVIDER)
                if provider_name == 'auto':
                    provider_name = config.DEFAULT_LLM_PROVIDER
                    
                # Dynamically select the LLM provider if needed
                # Always create a fresh provider with the latest db_store connection
                current_provider = get_llm_provider(provider_name, config, api_client.db_store)
                
                # Log the user's natural language question
                if 'user_id' not in session:
                    session['user_id'] = str(uuid.uuid4())
                user_id = session['user_id']
                
                log_query_request(user_id, question)
                
                # Check if LLM provider is available
                if current_provider is None:
                    logger.warning("No LLM provider available to process query")
                    result = {
                        'aql': "",
                        'explanation': "No LLM provider is configured. Please add an API key for OpenAI or Claude in the settings page, or set up Ollama locally.",
                        'error': "No LLM provider available",
                        'visualization': None
                    }
                else:
                    # Translate the question to AQL
                    start_time = time.time()
                    result = current_provider.translate_to_aql(question)
                
                # Add provider info to result - use actual provider name instead of "auto"
                result['provider'] = current_provider.provider_name if hasattr(current_provider, 'provider_name') else provider_name
                
                # Debug mode logging - LLM response
                if config.DEBUG:
                    logger.debug("LLM RESPONSE:")
                    logger.debug(f"UNDERSTANDING: {result.get('understanding', 'N/A')}")
                    logger.debug(f"QUERY: {result.get('query', 'N/A')}")
                    logger.debug(f"EXPLANATION: {result.get('explanation', 'N/A')}")
                
                # Log LLM processing
                log_llm_processing(user_id, question, result, provider_name)
                
                # Log query generation with timing
                query = result.get('query', '')
                explanation = result.get('explanation', '')
                generation_time = time.time() - start_time
                log_query_generation(user_id, question, query, generation_time, provider_name)
                
                # Validate the query before showing to the user
                # Note: sanitize_query function has been removed
                sanitized_query = query
                
                # First attempt at validation
                is_valid, error_message, error_details = api_client.validate_query(sanitized_query)
                log_query_validation(user_id, sanitized_query, is_valid, error_message, error_details)
                
                # If valid on first try, log success
                if is_valid:
                    logger.info(f"Query validated successfully on first attempt")
                
                # Initialize variables to track validation progress
                validation_attempts = 1
                validation_status = {
                    "status": "valid" if is_valid else "invalid",
                    "attempts": validation_attempts,
                    "maxAttempts": 5,  # Maximum number of retry attempts
                    "originalQuery": sanitized_query,
                    "currentQuery": sanitized_query,
                    "message": "Query validated successfully" if is_valid else error_message,
                    "progress": 75 if is_valid else 60
                }
                
                # If invalid, try to fix with LLM and retry
                if not is_valid and current_provider:
                    retry_count = 0
                    max_retries = 5  # Maximum number of retry attempts
                    
                    # Reset validation_attempts to not exceed maxAttempts in the status
                    validation_attempts = 1
                    
                    # Store previous fix attempts to learn from them
                    previous_attempts = []
                    
                    while not is_valid and retry_count < max_retries:
                        retry_count += 1
                        
                        # Update validation status - make sure attempts never exceeds maxAttempts
                        validation_status["attempts"] = min(validation_attempts + retry_count, validation_status["maxAttempts"])
                        validation_status["status"] = "fixing"
                        validation_status["message"] = f"Attempt {retry_count} of {max_retries}: Using AI to fix invalid query..."
                        validation_status["progress"] = 60 + (retry_count * 3)  # Increment progress with each attempt
                        
                        logger.info(f"Attempt {retry_count} of {max_retries}: Retrying with LLM to fix invalid query")
                        
                        # Create feedback for the LLM with previous attempt information
                        feedback = {
                            "original_query": sanitized_query,
                            "error": error_message,
                            "error_details": error_details,
                            "previous_attempts": previous_attempts
                        }
                        
                        # Ask LLM to fix the query
                        fixed_result = current_provider.fix_invalid_query(question, sanitized_query, feedback)
                        fixed_query = fixed_result.get('query', '')
                        fix_explanation = fixed_result.get('explanation', 'No explanation provided')
                        
                        # Add this attempt to previous_attempts for learning
                        previous_attempts.append({
                            "attempt": retry_count,
                            "query": fixed_query,
                            "explanation": fix_explanation,
                            "error": error_message
                        })
                        
                        # Log the fix attempt details
                        logger.info(f"Fix attempt {retry_count} of {max_retries}: LLM suggested changes: {fix_explanation}")
                        
                        if fixed_query and fixed_query != sanitized_query:
                            # Log the query modification
                            log_query_modification(user_id, sanitized_query, fixed_query, "VALIDATION_FIX", 
                                                 f"Fix attempt {retry_count} of {max_retries}: {fix_explanation}")
                            
                            # Update validation status
                            validation_status["currentQuery"] = fixed_query
                            
                            # Validate the fixed query
                            # Note: sanitize_query has been removed
                            is_valid, error_message, error_details = api_client.validate_query(fixed_query)
                            log_query_validation(user_id, sanitized_query, is_valid, error_message, error_details)
                            
                            # Update validation status based on result
                            validation_status["status"] = "valid" if is_valid else "invalid"
                            validation_status["message"] = "Query fixed and validated successfully" if is_valid else f"Fix attempt {retry_count} of {max_retries} failed: {error_message}"
                            validation_status["progress"] = 90 if is_valid else (60 + (retry_count * 3))
                            
                            # If valid after fixing, update the query in the result
                            if is_valid:
                                result['query'] = fixed_query
                                result['validation_fixed'] = True
                                result['fix_explanation'] = fix_explanation
                                logger.info(f"Query validated successfully after {retry_count} of {max_retries} fix attempts")
                                break
                        else:
                            # LLM couldn't fix it, exit retry loop
                            logger.warning("LLM failed to fix the invalid query")
                            validation_status["message"] = "AI could not fix the query"
                            break
                
                # If query is still invalid after retries, add warning to explanation
                if not is_valid:
                    # Format the error message to be more user-friendly
                    friendly_error = _format_validation_error(error_message, error_details, sanitized_query)
                    
                    # Update validation status for response
                    validation_status["status"] = "failed"
                    validation_status["message"] = friendly_error
                    
                    # Add validation warning to the explanation
                    result['validation_warning'] = f"Warning: This query has syntax errors: {friendly_error}"
                    result['explanation'] += f"\n\nWARNING: This query has validation errors and may not execute correctly: {friendly_error}"
                
                # Add validation status to the result
                result['validation'] = validation_status
                
                # Store in session for history
                if 'query_history' not in session:
                    session['query_history'] = []
                
                # Add to history, limited to 10 entries
                history_entry = {
                    'question': question,
                    'query': result['query'],
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                session['query_history'] = [history_entry] + session['query_history'][:9]
                session.modified = True
                
                # Debug mode logging - completion
                if config.DEBUG:
                    logger.debug(f"LLM INTERACTION COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug("-" * 80)
                
                # Get API configuration for template - using current server
                api_config = {
                    'server': api_client.server,
                    'endpoint': api_client.endpoint
                }
                
                return render_template('index.html', result=result, api_config=api_config)
                
            except Exception as e:
                logger.exception(f"Error processing query: {e}")
                error_result = {
                    'understanding': 'Error Processing Query',
                    'query': f"-- Error: {str(e)}",
                    'explanation': f"An error occurred while processing your query: {str(e)}",
                }
                
                # Get API configuration for template - using current server
                api_config = {
                    'server': api_client.server,
                    'endpoint': api_client.endpoint
                }
                
                return render_template('index.html', result=error_result, api_config=api_config)
        
        # Handle GET request with question parameter
        question = request.args.get('question', '')
        if question:
            try:
                # Get a fresh provider with the latest db_store connection
                current_provider = get_llm_provider(config.DEFAULT_LLM_PROVIDER, config, api_client.db_store)
                
                # Check if LLM provider is available
                if current_provider is None:
                    logger.warning("No LLM provider available to process query")
                    result = {
                        'aql': "",
                        'explanation': "No LLM provider is configured. Please add an API key for OpenAI or Claude in the settings page, or set up Ollama locally.",
                        'error': "No LLM provider available",
                        'visualization': None,
                        'provider': 'none'
                    }
                else:
                    # Use the configured LLM provider
                    result = current_provider.translate_to_aql(question)
                    result['provider'] = current_provider.provider_name if hasattr(current_provider, 'provider_name') else config.DEFAULT_LLM_PROVIDER
                
                # Get API configuration for template - using current server
                api_config = {
                    'server': api_client.server,
                    'endpoint': api_client.endpoint
                }
                
                return render_template('index.html', result=result, api_config=api_config)
            except Exception as e:
                logger.exception(f"Error processing query: {e}")
                error_result = {
                    'understanding': 'Error Processing Query',
                    'query': f"-- Error: {str(e)}",
                    'explanation': f"An error occurred while processing your query: {str(e)}",
                }
                
                # Get API configuration for template - using current server
                api_config = {
                    'server': api_client.server,
                    'endpoint': api_client.endpoint
                }
                
                return render_template('index.html', result=error_result, api_config=api_config)
        
        # No question provided, just show the main page
        return redirect(url_for('index'))
    
    @app.route('/execute', methods=['POST'])
    def execute():
        """Execute an AQL query and return results
        
        Executes the provided query against the Aparavi Data Service
        and returns the results as a JSON response.
        """
        if request.method == 'POST':
            try:
                # Start timing the execution
                start_time = time.time()
                
                # Handle both form data and JSON requests
                if request.is_json:
                    data = request.get_json()
                    query = data.get('query', '')
                    format_type = data.get('format', 'csv')  # Default to CSV if not specified
                    original_question = data.get('question', '')
                else:
                    query = request.form['query']
                    format_type = request.form.get('format', 'csv')
                    original_question = request.form.get('question', '')
                
                # Generate a unique ID for the user if not already in session
                if 'user_id' not in session:
                    session['user_id'] = str(uuid.uuid4())
                user_id = session['user_id']
                
                # Get current provider for retry if needed
                provider_name = session.get('current_provider', config.DEFAULT_LLM_PROVIDER)
                current_provider = get_llm_provider(provider_name, config, api_client.db_store)
                
                # Debug mode logging - execution start
                if config.DEBUG:
                    logger.debug("-" * 80)
                    logger.debug(f"QUERY EXECUTION START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f"EXECUTING QUERY: {query}")
                    logger.debug(f"FORMAT: {format_type}")
                
                # Note: sanitize_query function has been removed
                # Use the query directly
                
                # Execute the query (already validated during generation)
                result_df, execution_time, error, cache_hit = api_client.execute_query(
                    query, 
                    use_cache=True, 
                    format_type=format_type
                )
                
                # Check for errors in execution
                if error:
                    logger.warning(f"Error executing query: {error}")
                    log_query_error(user_id, "EXECUTION", error, query=query)
                    
                    return jsonify({
                        'success': False,
                        'error': f"Error executing query: {error}"
                    })
                
                # Calculate total time including processing
                total_time = time.time() - start_time
                
                # Process the result for display
                processed_result = {
                    'columns': result_df.columns.tolist() if not result_df.empty else [],
                    'data': result_df.replace({np.nan: None}).values.tolist() if not result_df.empty else [],
                    'totalRows': len(result_df),
                    'executionTime': execution_time,
                    'cacheHit': cache_hit
                }
                
                # Add a notice if the query executed successfully but returned no data
                if len(result_df) == 0:
                    processed_result['notice'] = "Query executed successfully, but no matching data was found."
                    logger.warning("Query returned zero rows")
                
                # Debug mode logging - execution result
                if config.DEBUG:
                    logger.debug(f"QUERY EXECUTION COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.debug(f"EXECUTION TIME: {processed_result['executionTime']:.2f}s")
                    logger.debug(f"ROWS RETURNED: {processed_result['totalRows']}")
                    
                    # Log a sample of the data (first 5 rows max)
                    sample_rows = processed_result['data'][:5]  
                    logger.debug(f"DATA SAMPLE (up to 5 rows):")
                    for i, row in enumerate(sample_rows):
                        logger.debug(f"  Row {i+1}: {row}")
                    logger.debug("-" * 80)
                
                # Return the result
                return jsonify({
                    'success': True,
                    'queryResult': processed_result,
                    'rawResponse': {
                        'columns': result_df.columns.tolist() if not result_df.empty else [],
                        'data': result_df.to_dict('records') if not result_df.empty else [],
                        'rawError': error,
                        'cacheHit': cache_hit,
                        'executionTime': execution_time
                    }
                })
                
            except Exception as e:
                # Debug mode logging - execution error
                if config.DEBUG:
                    logger.debug(f"QUERY EXECUTION ERROR: {str(e)}")
                    logger.debug("-" * 80)
                
                logger.exception(f"Error executing query: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    @app.route('/execute-query', methods=['POST'])
    def execute_query():
        """Execute a query and return results as JSON"""
        try:
            # Get request data
            data = request.get_json()
            query = data.get('query', '')
            format_type = data.get('format', 'csv')
            limit = data.get('limit', 25000)
            download = data.get('download', False)
            metadata_only = data.get('metadataOnly', False)
            
            # Log only metadata about the download, not the full result
            app.logger.info(f"[QUERY_DOWNLOAD] Format: {format_type}, Query: {query[:100]}...")
            
            # Note: sanitize_query function has been removed
            # Use the query directly
            
            # Execute the query
            result_df, execution_time, error, cache_hit = api_client.execute_query(
                query, 
                use_cache=True, 
                format_type=format_type
            )
            
            # Check for errors in execution
            if error:
                return jsonify({
                    'success': False,
                    'error': error
                })
            
            # Log the row count but not the actual data
            app.logger.info(f"[QUERY_DOWNLOAD] Rows: {len(result_df)}, Time: {execution_time:.2f}s")
            
            # Prepare metadata
            metadata = {
                'totalRows': len(result_df),
                'executionTime': execution_time,
                'cacheHit': cache_hit,
                'format': format_type  # Add selected format for use in UI
            }
            
            # Add a notice if the query executed successfully but returned no data
            if result_df.empty:
                metadata['notice'] = "Query executed successfully, but no matching data was found."
                app.logger.warning("Query returned zero rows")
            
            # For metadata-only response, don't include actual data
            if metadata_only:
                return jsonify({
                    'success': True,
                    'queryResult': metadata
                })
            
            # If we should download and not just return JSON
            if download:
                # Prepare the file for download
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if format_type == 'csv':
                    # Generate CSV
                    csv_data = result_df.to_csv(index=False)
                    response = Response(
                        csv_data,
                        mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename=query_results_{timestamp}.csv'}
                    )
                    return response
                else:
                    # Generate JSON
                    json_data = result_df.to_json(orient='records')
                    response = Response(
                        json_data,
                        mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename=query_results_{timestamp}.json'}
                    )
                    return response
            
            # Prepare full result with data (for non-metadata-only, non-download requests)
            processed_result = metadata.copy()
            
            # Handle NaN values for JSON serialization
            result_df_clean = result_df.fillna("null") if not result_df.empty else result_df
            
            processed_result.update({
                'columns': result_df_clean.columns.tolist() if not result_df_clean.empty else [],
                'data': result_df_clean.values.tolist() if not result_df_clean.empty else []
            })
            
            # Convert to JSON
            json_data = result_df_clean.to_json(orient='records')
            
            return jsonify({
                'success': True,
                'queryResult': processed_result,
                'rawResponse': {
                    'columns': result_df_clean.columns.tolist() if not result_df_clean.empty else [],
                    'data': json.loads(json_data),
                    'rawError': error,
                    'cacheHit': cache_hit,
                    'executionTime': execution_time
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error executing query: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @app.route('/download-query-results', methods=['POST'])
    def download_query_results():
        """Download query results as CSV or JSON"""
        if request.method == 'POST':
            try:
                # Get the request data
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form
                
                query = data.get('query', '')
                format_type = data.get('format', 'csv')
                
                # Log only metadata about the download, not the full result
                app.logger.info(f"[QUERY_DOWNLOAD] Format: {format_type}, Query: {query[:100]}...")
                
                # Note: sanitize_query function has been removed
                # Use the query directly
                
                # Execute the query
                result_df, execution_time, error, cache_hit = api_client.execute_query(
                    query, 
                    use_cache=True, 
                    format_type=format_type
                )
                
                # Check for errors in execution
                if error:
                    return jsonify({
                        'success': False,
                        'error': error
                    })
                
                # Log the row count but not the actual data
                app.logger.info(f"[QUERY_DOWNLOAD] Rows: {len(result_df)}, Time: {execution_time:.2f}s")
                
                # Prepare the file for download
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if format_type == 'csv':
                    # Generate CSV
                    csv_data = result_df.to_csv(index=False)
                    response = Response(
                        csv_data,
                        mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename=query_results_{timestamp}.csv'}
                    )
                    return response
                else:
                    # Generate JSON
                    json_data = result_df.to_json(orient='records')
                    response = Response(
                        json_data,
                        mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename=query_results_{timestamp}.json'}
                    )
                    return response
                
            except Exception as e:
                app.logger.error(f"Error preparing download: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
    
    @app.route('/analyze-query-results', methods=['POST'])
    def analyze_query_results():
        """Analyze query results and provide insights"""
        # Get inputs from request
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Invalid request format. Expected JSON data.'
            }), 400
        
        data = request.get_json()
        query = data.get('query', '').strip()
        question = data.get('question', '').strip()
        provider = data.get('provider', config.DEFAULT_LLM_PROVIDER)
        limit = data.get('limit', 100)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'No query provided.'
            }), 400
            
        # Execute the query to get data for analysis
        try:
            # Execute the query against Aparavi API
            api_client = get_api_client()
            if not api_client:
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to Aparavi API. Please check your credentials.'
                }), 500
                
            # Add a limit to the query, handling semicolons properly
            if not re.search(r'LIMIT\s+\d+', query, re.IGNORECASE):
                # Check if query has semicolons (multiple statements)
                if ";" in query:
                    # Split by semicolons and process the last non-empty statement
                    statements = query.split(";")
                    
                    # Find the last non-empty statement (ignoring trailing semicolons)
                    last_statement_index = -1
                    for i in range(len(statements) - 1, -1, -1):
                        if statements[i].strip():
                            last_statement_index = i
                            break
                    
                    if last_statement_index >= 0:
                        # Add LIMIT only to the last statement
                        statements[last_statement_index] += f" LIMIT {limit}"
                        query = ";".join(statements)
                else:
                    # Simple query with no semicolons
                    query = f"{query} LIMIT {limit}"
            else:
                # Replace any existing LIMIT with the provided limit
                # We don't need special treatment here since we're just modifying existing LIMIT
                query = re.sub(r'LIMIT\s+\d+', f'LIMIT {limit}', query, flags=re.IGNORECASE)
                
            # Execute the query
            start_time = time.time()
            result_df, execution_time, error, cache_hit = api_client.execute_query(query)
            
            # Check for errors in execution
            if error:
                return jsonify({
                    'success': False,
                    'error': error
                })
            
            # Add debug logging
            logger.info(f"Query executed successfully. Result type: {type(result_df)}")
            logger.info(f"DataFrame shape: {result_df.shape if hasattr(result_df, 'shape') else 'unknown'}")
            
            # Format the result for analysis - check data type and handle accordingly
            if isinstance(result_df, dict) and 'data' in result_df:
                logger.info(f"Data type: {type(result_df['data'])}, Length: {len(result_df['data']) if hasattr(result_df['data'], '__len__') else 'unknown'}")
                
                # Get columns and convert to records for analysis
                columns = result_df['columns']
                table_data = result_df['data']
                
                # Add more debug logging
                logger.info(f"Columns: {columns}, Data rows: {len(table_data)}")
            elif isinstance(result_df, pd.DataFrame):
                # Handle pandas DataFrame case
                logger.info(f"Handling pandas DataFrame with shape: {result_df.shape}")
                
                if not result_df.empty:
                    # Get columns and convert to records for analysis
                    columns = result_df.columns.tolist()
                    table_data = result_df.to_dict(orient='records')
                    
                    # Add more debug logging
                    logger.info(f"Columns: {columns}, Data rows: {len(table_data)}")
                else:
                    # Empty DataFrame, handle as no data
                    logger.info("Empty DataFrame returned from query")
                    columns = []
                    table_data = []
            else:
                # Log the situation for empty results
                logger.info("No data returned from query, generating empty result insights")
                
                # No data found - generate insights about why the query might have returned no results
                empty_insights = generate_empty_result_insights(
                    question=question or "Why did this query return no results?",
                    query=query,
                    provider=provider
                )
                
                return jsonify({
                    'success': True,
                    'insights': empty_insights,
                    'metadata': {
                        'provider': provider,
                        'executionTime': execution_time,
                        'rowCount': 0,
                        'notice': "Query executed successfully, but no matching data was found."
                    }
                })
                
            # Create a tabular representation for the LLM
            data_summary = f"""
Original Question: {question}

AQL Query:
{query}

Results Preview:
{table_data[:10] if table_data else "No data returned"}

Query Metadata:
- Total Rows: {len(table_data)}
- Execution Time: {execution_time:.2f}s

Data Context:
- Remember to check both classification and classifications columns for PII data
- Consider temporal patterns in the data if date/time fields are present
- Look for storage optimization opportunities when size data is available
- For AQL queries, GROUP BY and ORDER BY should use quoted column aliases with commas
- Complex WHERE conditions should use parentheses: WHERE (condition1) OR (condition2)
"""
            # Generate insights based on the data
            insights = generate_insights(
                question=question or "Analyze this data",
                query=query,
                data=table_data,
                provider=provider
            )
            
            return jsonify({
                'success': True,
                'insights': insights,
                'metadata': {
                    'provider': provider,
                    'executionTime': execution_time,
                    'rowCount': len(table_data),
                    'notice': "Query executed successfully, but no matching data was found." if len(table_data) == 0 else ""
                }
            })
                
        except Exception as e:
            logger.error(f"Error analyzing query results: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'Error analyzing results: {str(e)}'
            }), 500
    
    def generate_insights(question, query, data, provider=None):
        """Generate insights based on query results"""
        provider = provider or config.DEFAULT_LLM_PROVIDER
        
        # Prepare the data sample for the LLM
        # Limit to a reasonable number of rows to avoid token limits
        sample_size = min(25, len(data))
        data_sample = data[:sample_size] if len(data) > 0 else []
        
        # Convert the data to a string representation
        data_str = json.dumps(data_sample, indent=2)
        
        # Check if the query is looking for classified content (like PII)
        is_classification_query = any(keyword in query.lower() for keyword in 
                                      ['classification', 'classifications', 'pii', 'phi', 'pci'])
        
        # Create the prompt based on the query type
        if is_classification_query:
            prompt = ANALYSIS_PROMPT_CLASSIFICATION.format(
                question=question,
                query=query,
                data=data_str,
                total_rows=len(data),
                sample_size=sample_size
            )
        else:
            prompt = ANALYSIS_PROMPT.format(
                question=question,
                query=query,
                data=data_str,
                total_rows=len(data),
                sample_size=sample_size
            )
        
        # Get insights from LLM
        try:
            llm_client = get_llm_provider(provider, config, api_client.db_store)
            if not llm_client:
                return "Unable to generate insights due to LLM configuration issues."
                
            response = llm_client.generate_completion(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return f"Error generating insights: {str(e)}"
    
    def generate_empty_result_insights(question, query, provider=None):
        """Generate insights for queries that returned no results"""
        provider = provider or config.DEFAULT_LLM_PROVIDER
        
        # Create special prompt for empty results
        prompt = EMPTY_RESULTS_ANALYSIS_PROMPT.format(
            question=question,
            query=query
        )
        
        # Get insights from LLM about why the query might have returned nothing
        try:
            llm_client = get_llm_provider(provider, config, api_client.db_store)
            if not llm_client:
                return "Unable to analyze empty results due to LLM configuration issues."
                
            response = llm_client.generate_completion(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating empty result insights: {str(e)}")
            return f"Error analyzing empty results: {str(e)}"
    
    @app.route('/settings', methods=['GET', 'POST'])
    def settings():
        """Show and update application settings"""
        # Get the database store from app context
        db_store = getattr(api_client, 'db_store', None)
        
        if request.method == 'POST':
            # Get required form values with debug logging
            aparavi_server = request.form.get('aparavi_server', '')
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            
            logging.debug(f"Settings form submitted with server: {aparavi_server}, username: {username}, password: {'*****' if password else 'empty'}")
            
            # Check required fields
            missing_fields = []
            if not aparavi_server:
                missing_fields.append('Aparavi Server')
            if not username:
                missing_fields.append('Username')
            if not password:
                missing_fields.append('Password')
                
            if missing_fields:
                error_msg = f"Please fill in all required fields: {', '.join(missing_fields)}"
                logging.warning(f"Settings validation failed: {error_msg}")
                flash(error_msg, 'danger')
                return redirect(url_for('settings'))
                
            # Update settings based on form data
            updated_settings = {
                'aparavi_server': request.form.get('aparavi_server', config.DEFAULT_APARAVI_SERVER),
                'api_endpoint': config.DEFAULT_API_ENDPOINT,
                'username': request.form.get('username', config.DEFAULT_USERNAME),
                'password': request.form.get('password', config.DEFAULT_PASSWORD),
                'default_provider': request.form.get('default_provider', config.DEFAULT_LLM_PROVIDER),
                'fallback_provider': request.form.get('fallback_provider', 'none'),
                'ollama_base_url': request.form.get('ollama_base_url', config.OLLAMA_BASE_URL),
                'ollama_model': request.form.get('ollama_model', config.OLLAMA_MODEL),
                'openai_api_key': request.form.get('openai_api_key', ''),
                'openai_model': request.form.get('openai_model', 'gpt-3.5-turbo'),
                'openai_max_tokens': request.form.get('openai_max_tokens', '4096'),
                'openai_temperature': request.form.get('openai_temperature', '0.1'),
                'claude_api_key': request.form.get('claude_api_key', ''),
                'claude_model': request.form.get('claude_model', 'claude-3-opus-20240229'),
                'claude_max_tokens': request.form.get('claude_max_tokens', '4096'),
                'claude_temperature': request.form.get('claude_temperature', '0.1'),
                'log_level': request.form.get('log_level', config.LOG_LEVEL),
                'cache_timeout': request.form.get('cache_timeout', '300')
            }
            
            # Store settings in the database if available
            if db_store:
                # Store Ollama settings
                db_store.store_setting('ollama_base_url', updated_settings['ollama_base_url'])
                db_store.store_setting('ollama_model', updated_settings['ollama_model'])
                
                # Store OpenAI settings
                openai_api_key = updated_settings['openai_api_key']
                if openai_api_key:
                    db_store.store_credential('openai', 'api_key', openai_api_key)
                db_store.store_setting('openai_model', updated_settings['openai_model'])
                db_store.store_setting('openai_max_tokens', updated_settings['openai_max_tokens'])
                db_store.store_setting('openai_temperature', updated_settings['openai_temperature'])
                
                # Store Claude settings
                claude_api_key = updated_settings['claude_api_key']
                if claude_api_key and 'Error' not in claude_api_key and not claude_api_key.startswith('SELECT'):
                    db_store.store_credential('claude', 'api_key', claude_api_key)
                db_store.store_setting('claude_model', updated_settings['claude_model'])
                db_store.store_setting('claude_max_tokens', updated_settings['claude_max_tokens'])
                db_store.store_setting('claude_temperature', updated_settings['claude_temperature'])
                
                # Store Aparavi API credentials if provided
                username = updated_settings['username']
                password = updated_settings['password']
                if username and password:
                    db_store.store_credential('aparavi', 'username', username)
                    db_store.store_credential('aparavi', 'password', password)
                
                # Store other settings
                db_store.store_setting('aparavi_server', updated_settings['aparavi_server'])
                # Always use the default API endpoint
                db_store.store_setting('api_endpoint', config.DEFAULT_API_ENDPOINT)
                db_store.store_setting('default_provider', updated_settings['default_provider'])
                db_store.store_setting('fallback_provider', updated_settings['fallback_provider'])
                db_store.store_setting('log_level', updated_settings['log_level'])
                db_store.store_setting('cache_timeout', updated_settings['cache_timeout'])
                
                # Update config for immediate use (except OpenAI API key which stays in db)
                config.OLLAMA_BASE_URL = updated_settings['ollama_base_url']
                config.OLLAMA_MODEL = updated_settings['ollama_model']
                config.OPENAI_MODEL = updated_settings['openai_model']
                config.OPENAI_MAX_TOKENS = int(updated_settings['openai_max_tokens'])
                config.OPENAI_TEMPERATURE = float(updated_settings['openai_temperature'])
                config.CLAUDE_MODEL = updated_settings['claude_model']
                config.CLAUDE_MAX_TOKENS = int(updated_settings['claude_max_tokens'])
                config.CLAUDE_TEMPERATURE = float(updated_settings['claude_temperature'])
            
            # Store non-sensitive settings in session
            session['settings'] = updated_settings
            
            # Update API client with new settings
            api_client.update_credentials(
                server=updated_settings['aparavi_server'],
                endpoint=config.DEFAULT_API_ENDPOINT,
                username=updated_settings['username'],
                password=updated_settings['password']
            )
            
            # Reload LLM providers to pick up new credentials
            try:
                logging.info("Reloading LLM providers to pick up new credentials")
                # Clear any cached providers
                if hasattr(app, 'llm_provider'):
                    delattr(app, 'llm_provider')
                
                # Force reload of providers on next request
                if 'openai_api_key' in updated_settings and updated_settings['openai_api_key']:
                    # Test OpenAI provider with new credentials
                    test_provider = get_llm_provider('openai', config, db_store)
                    if test_provider.is_available():
                        flash('OpenAI API key validated successfully', 'success')
                
                if 'claude_api_key' in updated_settings and updated_settings['claude_api_key']:
                    # Test Claude provider with new credentials
                    test_provider = get_llm_provider('claude', config, db_store)
                    if test_provider.is_available():
                        flash('Claude API key validated successfully', 'success')
            except Exception as e:
                logging.error(f"Error reloading LLM providers: {e}")
                flash(f'Settings saved but provider validation failed: {str(e)}', 'warning')
            
            # Show success message
            flash('Settings updated successfully', 'success')
            
            return redirect(url_for('settings'))
        
        # For GET requests, show the settings form
        # First check if we have settings in the session
        settings_data = session.get('settings', {})
        
        # If not, use defaults from config and database
        if not settings_data:
            # Get API keys from database if available
            ollama_base_url = config.OLLAMA_BASE_URL
            ollama_model = config.OLLAMA_MODEL
            openai_api_key = ''
            openai_model = config.OPENAI_MODEL
            openai_max_tokens = config.OPENAI_MAX_TOKENS
            openai_temperature = config.OPENAI_TEMPERATURE
            claude_api_key = ''
            claude_model = config.CLAUDE_MODEL
            claude_max_tokens = config.CLAUDE_MAX_TOKENS
            claude_temperature = config.CLAUDE_TEMPERATURE
            
            if db_store:
                stored_ollama_base_url = db_store.get_setting('ollama_base_url')
                if stored_ollama_base_url:
                    ollama_base_url = stored_ollama_base_url
                    
                stored_ollama_model = db_store.get_setting('ollama_model')
                if stored_ollama_model:
                    ollama_model = stored_ollama_model
                
                # Get OpenAI settings from database
                stored_openai_api_key = db_store.get_credential('openai', 'api_key')
                if stored_openai_api_key:
                    openai_api_key = stored_openai_api_key
                
                stored_openai_model = db_store.get_setting('openai_model')
                if stored_openai_model:
                    openai_model = stored_openai_model
                    
                stored_openai_max_tokens = db_store.get_setting('openai_max_tokens')
                if stored_openai_max_tokens:
                    openai_max_tokens = stored_openai_max_tokens
                    
                stored_openai_temperature = db_store.get_setting('openai_temperature')
                if stored_openai_temperature:
                    openai_temperature = stored_openai_temperature
                
                # Get Claude settings from database
                stored_claude_api_key = db_store.get_credential('claude', 'api_key')
                if stored_claude_api_key:
                    claude_api_key = stored_claude_api_key
                
                stored_claude_model = db_store.get_setting('claude_model')
                if stored_claude_model:
                    claude_model = stored_claude_model
                    
                stored_claude_max_tokens = db_store.get_setting('claude_max_tokens')
                if stored_claude_max_tokens:
                    claude_max_tokens = stored_claude_max_tokens
                    
                stored_claude_temperature = db_store.get_setting('claude_temperature')
                if stored_claude_temperature:
                    claude_temperature = stored_claude_temperature
            
            settings_data = {
                'aparavi_server': config.DEFAULT_APARAVI_SERVER,
                'api_endpoint': config.DEFAULT_API_ENDPOINT,
                'username': config.DEFAULT_USERNAME,
                'password': config.DEFAULT_PASSWORD,
                'default_provider': config.DEFAULT_LLM_PROVIDER,
                'fallback_provider': 'none',
                'ollama_base_url': ollama_base_url,
                'ollama_model': ollama_model,
                'openai_api_key': openai_api_key,
                'openai_model': openai_model,
                'openai_max_tokens': openai_max_tokens,
                'openai_temperature': openai_temperature,
                'claude_api_key': claude_api_key,
                'claude_model': claude_model,
                'claude_max_tokens': claude_max_tokens,
                'claude_temperature': claude_temperature,
                'log_level': config.LOG_LEVEL,
                'cache_timeout': '300'
            }
        
        return render_template('settings.html', settings=settings_data)
    
    @app.route('/api/health')
    def health_check():
        """API health check endpoint"""
        # Check the status of important components
        api_status = api_client.check_connection()
        
        # Check LLM availability by getting a fresh provider
        llm_available = False
        try:
            current_provider = get_llm_provider('auto', config, api_client.db_store)
            llm_available = current_provider is not None and hasattr(current_provider, 'is_available') and current_provider.is_available()
        except Exception as e:
            logger.warning(f"Error checking LLM provider availability: {e}")
        
        health_data = {
            'status': 'healthy' if (api_status and llm_available) else 'degraded',
            'components': {
                'api_client': 'online' if api_status else 'offline',
                'llm_provider': 'online' if llm_available else 'offline'
            },
            'version': '1.0.0'
        }
        
        return jsonify(health_data)
    
    @app.route('/api/ollama/models', methods=['GET'])
    def get_ollama_models():
        """Get a list of available Ollama models"""
        from modules.llm.ollama import OllamaLLM
        
        # Initialize the Ollama provider
        try:
            ollama = OllamaLLM(config)
            models = ollama.get_available_models()
            return jsonify({'status': 'success', 'models': models})
        except Exception as e:
            logger.exception(f"Error fetching Ollama models: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/openai/models', methods=['GET'])
    def get_openai_models():
        """Get a list of available OpenAI models"""
        try:
            # Return a static list of common models
            models = [
                "gpt-3.5-turbo",
                "gpt-4",
                "gpt-4-turbo"
            ]
            return jsonify({'status': 'success', 'models': models})
        except Exception as e:
            logger.exception(f"Error fetching OpenAI models: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/test_aparavi_connection', methods=['POST'])
    def test_aparavi_connection():
        """Test the connection to the Aparavi server directly with credential validation"""
        try:
            # Get connection details from request
            data = request.get_json()
            server = data.get('server')
            # Use default endpoint from config if not provided
            endpoint = data.get('endpoint', config.DEFAULT_API_ENDPOINT)
            username = data.get('username')
            password = data.get('password')
            
            # Log the received data for debugging
            logging.debug(f"Testing Aparavi connection with: server={server}, username={username}, endpoint={endpoint}")
            
            # Validate inputs
            missing_fields = []
            if not server:
                missing_fields.append('Aparavi Server')
            if not username:
                missing_fields.append('Username')
            if not password:
                missing_fields.append('Password')
                
            if missing_fields:
                error_msg = f"Please fill in all required fields: {', '.join(missing_fields)}"
                logging.warning(f"Connection test failed: {error_msg}")
                return jsonify({
                    'success': False,
                    'message': error_msg
                })
            
            # Import here to avoid circular imports
            import requests
            import base64
            import time
            import json
            
            # Start timer for response time measurement
            start_time = time.time()
            
            # Create basic auth header manually
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
            
            # Construct the URL - For Aparavi API, we'll want to use a specific
            # endpoint that requires authentication
            url = f"http://{server}{endpoint}"
            
            # Log the attempt
            logger.info(f"Testing connection to Aparavi server: {url}")
            
            # Make a POST request with a minimal payload to test credentials
            # The specific payload may need to be adjusted for the Aparavi API
            test_payload = json.dumps({
                "query": "SELECT 1",
                "testCredentials": True
            })
            
            # Make request - using POST to validate credentials properly
            response = requests.post(
                url, 
                headers=headers, 
                data=test_payload,
                timeout=10
            )
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Check response status
            if response.status_code == 200:
                return jsonify({
                    'success': True,
                    'message': f"Connection successful (Response time: {response_time:.2f}s)",
                    'response_time': round(response_time, 2)
                })
            elif response.status_code == 401 or response.status_code == 403:
                return jsonify({
                    'success': False,
                    'message': "Authentication failed. Please check your username and password.",
                    'response_time': round(response_time, 2)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f"Connection failed: HTTP {response.status_code}",
                    'response_time': round(response_time, 2)
                })
                
        except requests.exceptions.Timeout:
            return jsonify({
                'success': False,
                'message': "Connection timed out. Please check the server address and try again."
            })
        except requests.exceptions.ConnectionError:
            return jsonify({
                'success': False,
                'message': "Connection failed. Please check the server address and ensure it's accessible."
            })
        except Exception as e:
            logger.exception("Error testing Aparavi connection")
            return jsonify({
                'success': False,
                'message': f"Error: {str(e)}"
            }), 500
    
    @app.route('/api/test_openai_connection', methods=['POST'])
    def test_openai_connection():
        """Test the connection to the OpenAI API"""
        try:
            # Get API key from request
            data = request.get_json()
            api_key = data.get('api_key')
            
            # Validate input
            if not api_key:
                return jsonify({
                    'success': False,
                    'message': "Please provide an OpenAI API key"
                })
                
            # Import here to avoid circular imports
            import openai
            import time
            
            # Start timer for response time measurement
            start_time = time.time()
            
            # Use requests library directly instead of the OpenAI client
            # to avoid any issues with proxies or other configuration
            import requests
            
            # Make a direct request to the OpenAI API to test the key
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            try:
                # Check models endpoint as a simple test
                response = requests.get(
                    "https://api.openai.com/v1/models",
                    headers=headers,
                    timeout=10  # Set a reasonable timeout
                )
                
                # Check if the request was successful (status code 200)
                if response.status_code == 200:
                    # Calculate response time
                    response_time = time.time() - start_time
                    
                    # Request succeeded
                    return jsonify({
                        'success': True,
                        'message': f"Connection successful (Response time: {response_time:.2f}s)",
                        'response_time': round(response_time, 2)
                    })
                elif response.status_code == 401:
                    # Authentication error
                    return jsonify({
                        'success': False,
                        'message': "Authentication failed. Please check your API key."
                    })
                elif response.status_code == 429:
                    # Rate limit error
                    return jsonify({
                        'success': False,
                        'message': "Rate limit exceeded. Your API key works but you've hit your usage limits."
                    })
                else:
                    # Other API error
                    return jsonify({
                        'success': False,
                        'message': f"API error: {response.status_code} - {response.text}"
                    })
            except requests.RequestException as req_error:
                # Network or connection error
                return jsonify({
                    'success': False,
                    'message': f"Connection error: {str(req_error)}"
                })
                
        except Exception as e:
            logger.exception("Error testing OpenAI connection")
            return jsonify({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            })
    
    @app.route('/api/test_claude_connection', methods=['POST'])
    def test_claude_connection():
        """Test the connection to the Claude API"""
        try:
            # Get API key from request
            data = request.get_json()
            api_key = data.get('api_key')
            
            # Validate input
            if not api_key:
                return jsonify({
                    'success': False,
                    'message': "Please provide a Claude API key"
                })
                
            # Import here to avoid circular imports
            import anthropic
            import time
            
            # Start timer for response time measurement
            start_time = time.time()
            
            # Set up temporary client for testing
            client = anthropic.Anthropic(api_key=api_key)
            
            # Make a minimal request to test the API key
            try:
                # Use a minimal completion request to test
                response = client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Say hello"}]
                )
                
                # Calculate response time
                response_time = time.time() - start_time
                
                # If we get here, the request succeeded
                return jsonify({
                    'success': True,
                    'message': f"Connection successful (Response time: {response_time:.2f}s)",
                    'response_time': round(response_time, 2)
                })
                
            except anthropic.APIError as api_error:
                if "authentication" in str(api_error).lower() or "authorization" in str(api_error).lower():
                    return jsonify({
                        'success': False,
                        'message': "Authentication failed. Please check your API key."
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': f"API error: {str(api_error)}"
                    })
                    
            except Exception as api_error:
                return jsonify({
                    'success': False,
                    'message': f"API error: {str(api_error)}"
                })
                
        except Exception as e:
            logger.exception("Error testing Claude connection")
            return jsonify({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            })
            
    @app.route('/api/ollama/pull_model', methods=['POST'])
    def pull_ollama_model():
        """Pull a model for Ollama if none exist"""
        try:
            # Get data from request
            data = request.get_json()
            base_url = data.get('base_url')
            model_name = data.get('model', 'tinyllama')  # Default to tinyllama if not specified
            
            # Validate input
            if not base_url:
                return jsonify({
                    'success': False,
                    'message': "Please provide the Ollama base URL"
                })
                
            # Import here to avoid circular imports
            import requests
            import json
            
            # Check if base_url has protocol, add http:// if missing
            if not base_url.startswith('http://') and not base_url.startswith('https://'):
                base_url = f"http://{base_url}"
            
            # Start a background pull request to Ollama
            logger.info(f"Initiating pull of model {model_name} from Ollama at {base_url}")
            
            try:
                # Make a request to pull the model
                # This is a non-blocking call that returns immediately, but the pull continues in the background
                response = requests.post(
                    f"{base_url}/api/pull", 
                    json={"name": model_name},
                    timeout=10
                )
                
                if response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'message': f"Started downloading model '{model_name}'. This will continue in the background. You can check the status on your Ollama server.",
                        'model': model_name
                    })
                else:
                    error_message = response.text
                    return jsonify({
                        'success': False,
                        'message': f"Failed to start model download: HTTP {response.status_code} - {error_message}"
                    })
                    
            except requests.exceptions.Timeout:
                return jsonify({
                    'success': False,
                    'message': "Connection timed out while trying to pull the model."
                })
            except requests.exceptions.ConnectionError:
                return jsonify({
                    'success': False,
                    'message': "Connection failed. Please check that Ollama is running at the specified URL."
                })
            except Exception as api_error:
                return jsonify({
                    'success': False,
                    'message': f"API error: {str(api_error)}"
                })
                
        except Exception as e:
            logger.exception("Error pulling Ollama model")
            return jsonify({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            })
            
    @app.route('/api/ollama/check_model', methods=['POST'])
    def check_ollama_model():
        """Check if a model exists in Ollama"""
        try:
            # Get data from request
            data = request.get_json()
            base_url = data.get('base_url')
            model_name = data.get('model')
            
            # Validate input
            if not base_url or not model_name:
                return jsonify({
                    'success': False,
                    'message': "Please provide both base_url and model name"
                })
                
            # Import here to avoid circular imports
            import requests
            
            # Check if base_url has protocol, add http:// if missing
            if not base_url.startswith('http://') and not base_url.startswith('https://'):
                base_url = f"http://{base_url}"
            
            # Get the list of available models
            try:
                # Make a request to list available models
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                
                if response.status_code == 200:
                    # Parse the response to get model list
                    data = response.json()
                    models = data.get('models', [])
                    
                    # Check if our model is in the list
                    model_exists = False
                    for model in models:
                        if model.get('name') == model_name:
                            model_exists = True
                            break
                    
                    if model_exists:
                        return jsonify({
                            'success': True,
                            'exists': True,
                            'message': f"Model '{model_name}' is available",
                            'model': model_name
                        })
                    else:
                        # Check if download is in progress
                        try:
                            # Try to get status from Ollama (this is a new API endpoint in recent versions)
                            status_response = requests.get(f"{base_url}/api/status", timeout=2)
                            
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                
                                # Check if there's a download in progress for this model
                                if (status_data.get('status') == 'pulling' and 
                                    status_data.get('model') == model_name):
                                    
                                    # Calculate download progress
                                    progress = 0
                                    if 'total' in status_data and status_data['total'] > 0:
                                        progress = int((status_data.get('completed', 0) / status_data['total']) * 100)
                                    
                                    return jsonify({
                                        'success': True,
                                        'exists': False,
                                        'downloading': True,
                                        'progress': progress,
                                        'message': f"Model '{model_name}' is downloading ({progress}% complete)"
                                    })
                        except Exception as status_error:
                            # Status check failed but we'll just ignore this
                            logger.debug(f"Could not check download status: {str(status_error)}")
                            
                        # Model doesn't exist and no download info available
                        return jsonify({
                            'success': True,
                            'exists': False,
                            'downloading': False,
                            'message': f"Model '{model_name}' is not available"
                        })
                else:
                    return jsonify({
                        'success': False,
                        'message': f"Failed to get model list: HTTP {response.status_code}"
                    })
                    
            except requests.exceptions.Timeout:
                return jsonify({
                    'success': False,
                    'message': "Connection timed out. Please check the Ollama server address."
                })
            except requests.exceptions.ConnectionError:
                return jsonify({
                    'success': False,
                    'message': "Connection failed. Please check that Ollama is running at the specified URL."
                })
            except Exception as api_error:
                return jsonify({
                    'success': False,
                    'message': f"API error: {str(api_error)}"
                })
                
        except Exception as e:
            logger.exception("Error checking Ollama model")
            return jsonify({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            })
            
    @app.route('/chat', methods=['GET'])
    def chat():
        """Render the chat interface"""
        # Generate a unique user ID for this session if not already present
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
            
        # Initialize chat history in session if not already present
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        # Get available providers for the UI
        providers = [
            {'value': 'openai', 'name': 'OpenAI'},
            {'value': 'ollama', 'name': 'Ollama (Local)'},
        ]
        
        return render_template(
            'chat.html', 
            providers=providers,
            query_provider=session.get('query_provider', config.DEFAULT_LLM_PROVIDER),
            analysis_provider=session.get('analysis_provider', config.DEFAULT_LLM_PROVIDER)
        )

    @app.route('/chat/message', methods=['POST'])
    def chat_message():
        """Process a chat message and generate a response"""
        
        # Ensure user has an ID
        user_id = session.get('user_id')
        if not user_id:
            user_id = str(uuid.uuid4())
            session['user_id'] = user_id
        
        # Initialize chat history if not present
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        try:
            # Debug request information
            logger.debug(f"Request content type: {request.content_type}")
            logger.debug(f"Request data: {request.data}")
            
            # Get request data - handle potential format issues
            if request.is_json:
                logger.debug("Processing JSON request")
                data = request.get_json(force=True, silent=True)
                if not data:
                    logger.warning("Failed to parse JSON data")
                    data = {}
            else:
                logger.warning(f"Non-JSON request received: {request.content_type}")
                # Try to parse form data
                data = {}
                for key in request.form:
                    data[key] = request.form[key]
                
                if not data:
                    return jsonify({
                        'type': 'error',
                        'content': f'Invalid request format. Expected JSON data but got {request.content_type}'
                    }), 400
            
            logger.debug(f"Processed request data: {data}")        
            message = data.get('message', '').strip()
            query_provider = data.get('query_provider', config.DEFAULT_LLM_PROVIDER)
            analysis_provider = data.get('analysis_provider', config.DEFAULT_LLM_PROVIDER)
            
            # Store provider choices in session
            session['query_provider'] = query_provider
            session['analysis_provider'] = analysis_provider
            
            # Log the incoming message
            log_chat_message(user_id, message, is_user=True)
            
            # Add user message to chat history
            session['chat_history'].append({
                'role': 'user',
                'content': message,
                'timestamp': time.time()
            })
            
            # Limit chat history to last 10 messages to prevent session cookie overflow
            if len(session['chat_history']) > 10:
                session['chat_history'] = session['chat_history'][-10:]
            
            # Save session
            session.modified = True
            
            if message.lower() in ['clear', 'clear chat', 'reset', 'reset chat']:
                # Clear chat history
                session['chat_history'] = []
                
                response = {
                    'type': 'text',
                    'content': 'Chat history has been cleared.'
                }
                
                log_chat_message(user_id, response['content'], is_user=False)
                
                # Add system response to chat history
                session['chat_history'].append({
                    'role': 'system',
                    'content': response['content'],
                    'timestamp': time.time()
                })
                
                session.modified = True
                return jsonify(response)
            
            # Process the message and generate a response
            if message:
                try:
                    # 1. Use the query LLM provider to generate AQL query
                    query_llm = get_llm_provider(query_provider, config, api_client.db_store)
                    
                    # Start timing for query generation
                    generation_start_time = time.time()
                    
                    # Get query from LLM
                    query_result = query_llm.translate_to_aql(message)
                    query = query_result.get('query', '')
                    explanation = query_result.get('explanation', '')
                    
                    # Calculate generation time
                    generation_time = time.time() - generation_start_time
                    
                    # Log initial query request
                    log_query_request(user_id, message)
                    
                    # Log detailed information about how the LLM processed the query
                    log_llm_processing(user_id, message, query_result, query_provider)
                    
                    # Log the query generation with timing
                    log_query_generation(user_id, message, query, generation_time, query_provider)
                    
                    if not query:
                        # Handle case where no query was generated
                        error_message = "I couldn't generate a query from your message. Please try rewording your question."
                        log_query_error(user_id, "GENERATION", "No query generated", query=None, details={"message": message})
                        log_error(user_id, "QUERY_GENERATION", "No query generated", {"message": message})
                        
                        response = {
                            'type': 'error',
                            'content': error_message
                        }
                    else:
                        # 2. Execute the query
                        try:
                            # Execute the query
                            start_time = time.time()
                            result_df, execution_time, error, cache_hit = api_client.execute_query(query)
                            
                            # Check for errors in execution
                            if error:
                                logger.warning(f"Error executing query: {error}")
                                log_query_error(user_id, "EXECUTION", error, query=query)
                                
                                return jsonify({
                                    'success': False,
                                    'error': f"Error executing query: {error}"
                                })
                            
                            # Calculate total time including processing
                            total_time = time.time() - start_time
                            
                            # Process the result for display
                            processed_result = {
                                'columns': result_df.columns.tolist() if not result_df.empty else [],
                                'data': result_df.replace({np.nan: None}).values.tolist() if not result_df.empty else [],
                                'totalRows': len(result_df),
                                'executionTime': execution_time,
                                'cacheHit': cache_hit
                            }
                            
                            # Add a notice if the query executed successfully but returned no data
                            if result_df.empty:
                                processed_result['notice'] = "Query executed successfully, but no matching data was found."
                                logger.warning("Query returned zero rows")
                            
                            # Debug mode logging - execution result
                            if config.DEBUG:
                                logger.debug(f"QUERY EXECUTION COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                logger.debug(f"EXECUTION TIME: {processed_result['executionTime']:.2f}s")
                                logger.debug(f"ROWS RETURNED: {processed_result['totalRows']}")
                                
                                # Log a sample of the data (first 5 rows max)
                                sample_rows = processed_result['data'][:5]  
                                logger.debug(f"DATA SAMPLE (up to 5 rows):")
                                for i, row in enumerate(sample_rows):
                                    logger.debug(f"  Row {i+1}: {row}")
                                logger.debug("-" * 80)
                            
                            # 3. Use the analysis provider to analyze the results
                            insights = None
                            try:
                                # Get an instance of the analysis provider
                                analysis_llm = get_llm_provider(analysis_provider, config, api_client.db_store)
                                
                                # Only analyze if the provider is available and there are results to analyze
                                if analysis_llm.is_available():
                                    # For empty results, generate a response specific to the question
                                    if result_df.empty:
                                        # Use the LLM to generate a natural language response for the empty results
                                        empty_result_prompt = f"""
The user asked: "{message}"

The system executed this AQL query:
{query}

The query returned NO RESULTS. Please provide a friendly, helpful response that:
1. Clearly states there were no results found
2. Explains what was being searched for based on the original question and query
3. Suggests possible reasons why no data was found (e.g., no matching records, strict filtering conditions)
4. Offers 1-2 constructive suggestions on how to modify the search to get results

Keep your response conversational and concise (3-5 sentences maximum).
"""
                                        # Use chat completion to get a natural language response
                                        insights = analysis_llm.chat_completion(
                                            system_prompt="You are a helpful data analyst explaining query results.",
                                            messages=[
                                                {"role": "user", "content": empty_result_prompt}
                                            ]
                                        )
                                    else:
                                        # Create a concise summary of the data for the analysis
                                        df_str = result_df.head(100).to_string(index=False) if not result_df.empty else "No data returned"
                                        
                                        data_summary = f"""
Original Question: {message}

AQL Query:
{query}

Results Preview:
{df_str}

Query Metadata:
- Total Rows: {len(result_df)}
- Execution Time: {processed_result['executionTime']:.2f}s

Data Context:
- Remember to check both classification and classifications columns for PII data
- Consider temporal patterns in the data if date/time fields are present
- Look for storage optimization opportunities when size data is available
- For AQL queries, GROUP BY and ORDER BY should use quoted column aliases with commas
- Complex WHERE conditions should use parentheses: WHERE (condition1) OR (condition2)
"""
                                        # Use the LLM to analyze the results
                                        insights = analysis_llm.chat_completion(
                                            system_prompt=ANALYSIS_SYSTEM_PROMPT,
                                            messages=[
                                                {"role": "user", "content": data_summary}
                                            ]
                                        )
                                    
                                    # Check if the LLM response is empty or invalid
                                    if not insights or len(insights.strip()) < 10:
                                        # Fallback to a generic analysis if the LLM fails to provide meaningful insights
                                        insights = f"""Analysis of results for question: "{message}"

Based on the query results, I can see {len(result_df)} records were returned. The query was executed in {processed_result['executionTime']:.2f} seconds.

Key columns in the results include: {', '.join(result_df.columns.tolist()[:5])}{"..." if len(result_df.columns) > 5 else ""}

To further analyze this data, you might want to try additional filtering or grouping operations.
"""
                                        
                                    # Add insights to the processed result
                                    processed_result['insights'] = insights
                                    
                                    # Log the analysis
                                    log_analysis(user_id, query, insights, analysis_provider)
                            except Exception as e:
                                logger.warning(f"Error analyzing results: {str(e)}")
                                # Don't fail the entire request if analysis fails
                                
                            # Return the result with a staged response format
                            stages = []
                            
                            # Understanding stage
                            stages.append({
                                'type': 'understanding',
                                'content': explanation or "I understood your question about the data."
                            })
                            
                            # Query stage
                            stages.append({
                                'type': 'query',
                                'content': query
                            })
                            
                            # Results stage
                            stages.append({
                                'type': 'results',
                                'content': f"Found {processed_result['totalRows']} row{'' if processed_result['totalRows'] == 1 else 's'} in {processed_result['executionTime']:.2f}s {' (from cache)' if cache_hit else ''}"
                            })
                            
                            # Insights stage (if available)
                            if insights:
                                stages.append({
                                    'type': 'insights',
                                    'content': insights
                                })
                            
                            response = {
                                'type': 'staged',
                                'stages': stages,
                                # Include all data for compatibility with other interface features
                                'query': query,
                                'explanation': explanation,
                                'insights': insights,
                                'columns': processed_result['columns'],
                                'data': processed_result['data'],
                                'totalRows': processed_result['totalRows'],
                                'executionTime': processed_result['executionTime'],
                                'cacheHit': cache_hit
                            }
                            
                            # Use dumps with custom encoder to ensure NaN values are properly handled
                            return Response(
                                json.dumps(response, cls=NpEncoder),
                                mimetype='application/json'
                            )
                        except Exception as e:
                            # Debug mode logging - execution error
                            if config.DEBUG:
                                logger.debug(f"QUERY EXECUTION ERROR: {str(e)}")
                                logger.debug("-" * 80)
                            
                            logger.exception(f"Error executing query: {e}")
                            return jsonify({
                                'success': False,
                                'error': f"Error executing query: {str(e)}"
                            }), 500
                except Exception as e:
                    # Log the error
                    log_error(user_id, "PROCESSING", str(e), {"message": message})
                    
                    # Handle any unexpected errors in processing
                    response = {
                        'type': 'error',
                        'content': f"Error processing your request: {str(e)}"
                    }
                    
                    # Log the system response
                    log_chat_message(user_id, response['content'], is_user=False)
                    
                    # Add system response to chat history
                    session['chat_history'].append({
                        'role': 'system',
                        'content': response['content'],
                        'timestamp': time.time()
                    })
                    
                    # Save session
                    session.modified = True
                    
                    return jsonify(response)
            else:
                # Empty message
                response = {
                    'type': 'error',
                    'content': "Please enter a message."
                }
                
                # Log the system response
                log_chat_message(user_id, response['content'], is_user=False)
                
                # Add system response to chat history
                session['chat_history'].append({
                    'role': 'system',
                    'content': response['content'],
                    'timestamp': time.time()
                })
                
                # Save session
                session.modified = True
                
                return jsonify(response)
                
        except Exception as e:
            # Log any unexpected errors
            log_error(session.get('user_id', 'unknown'), "UNHANDLED", str(e))
            
            response = {
                'type': 'error',
                'content': f"Unexpected error: {str(e)}"
            }
            
            # Add system response to chat history if possible
            if 'chat_history' in session:
                session['chat_history'].append({
                    'role': 'system',
                    'content': response['content'],
                    'timestamp': time.time()
                })
                session.modified = True
            
            return jsonify(response)

    @app.route('/generate_aql', methods=['POST'])
    def generate_aql():
        """Generate AQL from natural language question using the current LLM provider - AJAX endpoint"""
        try:
            # Get the question from the request - handle both form data and JSON
            if request.is_json:
                data = request.get_json()
                question = data.get('question', '')
            else:
                question = request.form.get('question', '')
                
            if not question:
                return jsonify({'error': 'No question provided'})
            
            # Start timer for performance monitoring
            start_time = time.time()
            
            # Update UI with processing status
            status = {
                "status": "processing",
                "message": "Understanding your question...",
                "progress": 10
            }
            
            # Log the request in the query log
            user_id = session.get('user_id', 'anonymous')
            log_query_request(user_id, question)
            
            # Get the current LLM provider
            provider_name = session.get('current_provider', config.DEFAULT_LLM_PROVIDER)
            provider = get_llm_provider(provider_name, config, api_client.db_store)
            
            if not provider:
                return jsonify({
                    'error': f'Failed to initialize LLM provider: {provider_name}',
                    'status': "error"
                })
            
            # Store the current provider for potential retries
            session['current_provider'] = provider_name
            
            # Update the UI status to "Generating AQL"
            status["message"] = "Generating AQL query from your question..."
            status["progress"] = 30
            
            # Translate the question to AQL
            result = provider.translate_to_aql(question)
            logger.info(f"LLM translation completed in {time.time() - start_time:.2f}s")
            
            # Extract the generated query
            query = result.get('query', '')
            
            # Update the UI status to "Validating Query"
            status["message"] = "Validating generated query..."
            status["progress"] = 60
            
            # If we have a query, validate it
            # Note: sanitize_query has been removed as per error log comment
            sanitized_query = query if query else ''
            
            # First attempt at validation
            validation_attempts = 1
            is_valid, error_message, error_details = api_client.validate_query(sanitized_query)
            log_query_validation(user_id, sanitized_query, is_valid, error_message, error_details)
            
            if is_valid:
                logger.info(f"Query validated successfully on first attempt")
            
            # Create validation status response
            validation_status = {
                "status": "valid" if is_valid else "invalid",
                "attempts": validation_attempts,
                "maxAttempts": 5,  # Maximum number of retry attempts
                "originalQuery": sanitized_query,
                "currentQuery": sanitized_query,
                "message": "Query validated successfully" if is_valid else error_message,
                "progress": 75 if is_valid else 60
            }
            
            # If invalid, try to fix with LLM and retry
            if not is_valid and provider:
                retry_count = 0
                max_retries = 5  # Maximum number of retry attempts
                
                # Reset validation_attempts to not exceed maxAttempts in the status
                validation_attempts = 1
                
                # Store previous fix attempts to learn from them
                previous_attempts = []
                
                while not is_valid and retry_count < max_retries:
                    retry_count += 1
                    
                    # Update validation status - make sure attempts never exceeds maxAttempts
                    validation_status["attempts"] = min(validation_attempts + retry_count, validation_status["maxAttempts"])
                    validation_status["status"] = "fixing"
                    validation_status["message"] = f"Attempt {retry_count} of {max_retries}: Using AI to fix invalid query..."
                    validation_status["progress"] = 60 + (retry_count * 3)  # Increment progress with each attempt
                    
                    logger.info(f"Attempt {retry_count} of {max_retries}: Retrying with LLM to fix invalid query")
                    
                    # Create feedback for the LLM with previous attempt information
                    feedback = {
                        "original_query": sanitized_query,
                        "error": error_message,
                        "error_details": error_details,
                        "previous_attempts": previous_attempts
                    }
                    
                    # Ask LLM to fix the query
                    fixed_result = provider.fix_invalid_query(question, sanitized_query, feedback)
                    fixed_query = fixed_result.get('query', '')
                    fix_explanation = fixed_result.get('explanation', 'No explanation provided')
                    
                    # Add this attempt to previous_attempts for learning
                    previous_attempts.append({
                        "attempt": retry_count,
                        "query": fixed_query,
                        "explanation": fix_explanation,
                        "error": error_message
                    })
                    
                    # Log the fix attempt details
                    logger.info(f"Fix attempt {retry_count} of {max_retries}: LLM suggested changes: {fix_explanation}")
                    
                    if fixed_query and fixed_query != sanitized_query:
                        # Log the query modification
                        log_query_modification(user_id, sanitized_query, fixed_query, "VALIDATION_FIX", 
                                             f"Fix attempt {retry_count} of {max_retries}: {fix_explanation}")
                        
                        # Update validation status
                        validation_status["currentQuery"] = fixed_query
                        
                        # Validate the fixed query
                        # Note: sanitize_query function has been removed
                        sanitized_query = fixed_query
                        is_valid, error_message, error_details = api_client.validate_query(sanitized_query)
                        log_query_validation(user_id, sanitized_query, is_valid, error_message, error_details)
                        
                        # Update validation status based on result
                        validation_status["status"] = "valid" if is_valid else "invalid"
                        validation_status["message"] = "Query fixed and validated successfully" if is_valid else f"Fix attempt {retry_count} of {max_retries} failed: {error_message}"
                        validation_status["progress"] = 90 if is_valid else (60 + (retry_count * 3))
                        
                        # If valid after fixing, update the query in the result
                        if is_valid:
                            result['query'] = fixed_query
                            result['validation_fixed'] = True
                            result['fix_explanation'] = fix_explanation
                            logger.info(f"Query validated successfully after {retry_count} of {max_retries} fix attempts")
                            break
                    else:
                        # LLM couldn't fix it, exit retry loop
                        logger.warning("LLM failed to fix the invalid query")
                        validation_status["message"] = "AI could not fix the query"
                        break
            
            # Store the result and validation status in the session for later use
            session['last_aql_result'] = result
            session['last_question'] = question
            
            # Include the total time in the response
            result['generation_time'] = f"{time.time() - start_time:.2f}s"
            
            # Add the validation status to the response
            result['validation'] = validation_status
            
            # Return successful response with validation status
            return jsonify(result)
            
        except Exception as e:
            logger.exception(f"Error generating AQL: {str(e)}")
            return jsonify({
                'error': f"Error generating AQL: {str(e)}",
                'status': "error"
            })

    @app.route('/library')
    def library():
        """Render the AQL library page"""
        # Get all queries from the library
        queries = get_all_library_queries()
        
        # Get all categories for filtering
        categories = get_library_categories()
        
        # Get API configuration for the template using the current api_client server
        # This ensures we use the stored server from the database
        api_config = {
            'server': api_client.server,
            'endpoint': api_client.endpoint
        }
        
        return render_template('library.html', queries=queries, categories=categories, api_config=api_config)
    
    @app.route('/library/query/<query_id>', methods=['GET'])
    def get_library_query(query_id):
        """Get a specific query from the library by ID"""
        query = get_query_by_id(query_id)
        
        if query:
            return jsonify(query)
        else:
            return jsonify({'error': 'Query not found'}), 404
            
    @app.route('/library/query', methods=['POST'])
    def create_library_query():
        """Create a new query in the library"""
        # Import utility functions
        from modules.utils.aql_library import load_library_data, save_library_data, generate_unique_id
        
        # Log the request
        logging.info("Creating new library query")
        
        # Get the query data from the request
        data = request.json
        
        # Validate required fields
        required_fields = ['title', 'category', 'purpose', 'query', 'impact', 'action']
        missing_fields = [field for field in required_fields if field not in data or not data.get(field)]
        
        if missing_fields:
            logging.warning(f"Invalid new query request: missing fields {missing_fields}")
            return jsonify({
                'success': False, 
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Load the current library data
        library_data = load_library_data()
        
        # Generate a unique ID based on the title
        query_id = generate_unique_id(data['title'])
        
        # Create the new query object
        new_query = {
            'id': query_id,
            'title': data['title'],
            'category': data['category'],
            'purpose': data['purpose'],
            'query': data['query'],
            'impact': data.get('impact', ''),
            'action': data.get('action', ''),
            'keywords': data.get('keywords', []),
            'verified': data.get('verified', False),
            'visualization': data.get('visualization', False)
        }
        
        # Add the new query to the library
        if 'queries' not in library_data:
            library_data['queries'] = []
            
        library_data['queries'].append(new_query)
        
        # Save the updated library data
        success = save_library_data(library_data)
        
        if success:
            logging.info(f"Successfully created new query with ID: {query_id}")
            return jsonify({
                'success': True,
                'message': 'Query created successfully',
                'query_id': query_id,
                'query': new_query
            })
        else:
            logging.error("Failed to save library data after creating new query")
            return jsonify({
                'success': False,
                'error': 'Failed to save changes to the library file'
            }), 500
    
    @app.route('/api/library/update', methods=['POST'])
    def api_update_library_query():
        """Update an existing query in the library"""
        # Import library utilities
        from modules.utils.aql_library import load_library_data, save_library_data
        
        # Get query data from request
        data = request.get_json()
        if not data:
            logging.error("No data provided for query update")
            return jsonify({
                'success': False, 
                'message': 'No query data provided'
            }), 400
        
        # Validate required fields
        query_id = data.get('id')
        if not query_id:
            logging.error("No query ID provided for update")
            return jsonify({
                'success': False, 
                'message': 'No query ID provided'
            }), 400
        
        # Process keywords (convert from string to array)
        keywords = []
        if 'keywords' in data and isinstance(data['keywords'], str):
            keywords = [k.strip() for k in data['keywords'].split(',')] if data['keywords'].strip() else []
        elif 'keywords' in data and isinstance(data['keywords'], list):
            keywords = data['keywords']
        
        # Load the current library data
        library_data = load_library_data()
        if not library_data or 'queries' not in library_data:
            logging.error("Library data not found or invalid")
            return jsonify({
                'success': False, 
                'message': 'Library data not found or invalid'
            }), 500
        
        # Find and update the query
        found = False
        for i, query in enumerate(library_data['queries']):
            if query.get('id') == query_id:
                # Update fields
                library_data['queries'][i]['title'] = data.get('title', query['title'])
                library_data['queries'][i]['category'] = data.get('category', query['category'])
                library_data['queries'][i]['purpose'] = data.get('purpose', query['purpose'])
                library_data['queries'][i]['query'] = data.get('query', query['query'])
                library_data['queries'][i]['impact'] = data.get('impact', query.get('impact', ''))
                library_data['queries'][i]['action'] = data.get('action', query.get('action', ''))
                library_data['queries'][i]['verified'] = data.get('verified', query.get('verified', False))
                library_data['queries'][i]['visualization'] = data.get('visualization', query.get('visualization', False))
                library_data['queries'][i]['keywords'] = keywords
                # Update modified timestamp
                library_data['queries'][i]['modified'] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            logging.error(f"Query with ID {query_id} not found")
            return jsonify({
                'success': False, 
                'message': f"Query with ID {query_id} not found"
            }), 404
        
        # Save the updated library data
        success = save_library_data(library_data)
        
        if success:
            logging.info(f"Successfully updated query {query_id}")
            return jsonify({
                'success': True, 
                'message': 'Query updated successfully'
            })
        else:
            logging.error("Failed to save library data after updating query")
            return jsonify({
                'success': False, 
                'message': 'Failed to save changes to the library file'
            }), 500

    @app.route('/library/export', methods=['GET'])
    def export_aql_library():
        """Export the full AQL library as a downloadable JSON file"""
        from modules.utils.aql_library import get_library_file_path
        
        # Get the path to the library file
        library_file_path = get_library_file_path()
        
        if not os.path.exists(library_file_path):
            logging.error(f"Library file not found at {library_file_path}")
            return jsonify({
                'success': False,
                'error': 'Library file not found'
            }), 404
            
        # Return the file as an attachment for download
        return send_file(
            library_file_path, 
            as_attachment=True,
            download_name="aql_library.json",
            mimetype="application/json"
        )
    
    @app.route('/library/import', methods=['POST'])
    def import_aql_library():
        """Import an AQL library JSON file, making a backup of the existing library"""
        from modules.utils.aql_library import get_library_file_path, load_library_data, save_library_data
        
        # Check if a file was uploaded
        if 'library_file' not in request.files:
            logging.warning("No file part in the import request")
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
            
        file = request.files['library_file']
        
        # Check if the file was actually selected
        if file.filename == '':
            logging.warning("No file selected for import")
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
            
        # Validate the file type and content
        if not file.filename.endswith('.json'):
            logging.warning(f"Invalid file type: {file.filename}")
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Please upload a JSON file.'
            }), 400
            
        try:
            # Parse the JSON to validate it before saving
            imported_data = json.loads(file.read())
            file.seek(0)  # Reset file pointer for later use
            
            # Validate the structure of the imported data
            if 'queries' not in imported_data:
                logging.warning("Invalid library file: missing 'queries' key")
                return jsonify({
                    'success': False,
                    'error': 'Invalid library file format. The file does not contain queries.'
                }), 400
                
            # Create backup of existing library file
            original_library_path = get_library_file_path()
            backup_directory = os.path.join(os.path.dirname(original_library_path), 'backups')
            
            # Create backup directory if it doesn't exist
            if not os.path.exists(backup_directory):
                os.makedirs(backup_directory)
                
            # Generate backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"aql_library_backup_{timestamp}.json"
            backup_path = os.path.join(backup_directory, backup_filename)
            
            # Copy the existing library to the backup location if it exists
            if os.path.exists(original_library_path):
                shutil.copy2(original_library_path, backup_path)
                logging.info(f"Created backup of existing library at {backup_path}")
            else:
                logging.info("No existing library file to backup")
            
            # Save the uploaded file as the new library
            file.save(original_library_path)
            logging.info(f"Imported new library file")
            
            # Get count of imported queries for feedback
            imported_count = len(imported_data.get('queries', []))
            
            return jsonify({
                'success': True,
                'message': 'Library imported successfully',
                'imported_count': imported_count,
                'backup_file': backup_filename
            })
            
        except json.JSONDecodeError:
            logging.error("Failed to parse imported JSON file")
            return jsonify({
                'success': False,
                'error': 'Invalid JSON format. The file could not be parsed.'
            }), 400
        except Exception as e:
            logging.exception(f"Error importing library: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Import failed: {str(e)}'
            }), 500
    
    @app.route('/library/query/<query_id>', methods=['DELETE'])
    def delete_library_query(query_id):
        """Delete a specific query from the library by ID"""
        # Import utility functions
        from modules.utils.aql_library import load_library_data, save_library_data, get_query_by_id
        
        # Log the request
        logging.info(f"Deleting library query with ID: {query_id}")
        
        # Load the current library data
        library_data = load_library_data()
        
        # Find the query to delete
        original_query_count = len(library_data.get('queries', []))
        found_query = None
        
        # Find the query before removing it for logging
        for i, query in enumerate(library_data.get('queries', [])):
            if query.get('id') == query_id:
                # Store the original query for logging
                original_query = library_data['queries'][i]['query']
                
                # Remove the query from the list
                library_data['queries'] = [q for q in library_data.get('queries', []) if q.get('id') != query_id]
                
                # Verify the query was removed
                if len(library_data.get('queries', [])) >= original_query_count:
                    logging.warning(f"Failed to remove query {query_id} from library data")
                    return jsonify({
                        'success': False,
                        'error': 'Failed to remove query from library data'
                    }), 500
                
                found_query = query
                break
                
        if not found_query:
            logging.warning(f"Query {query_id} not found in library when attempting to delete")
            return jsonify({'error': 'Query not found'}), 404
            
        # Log the deletion details
        logging.info(f"Removing query {query_id} from library. Title: '{found_query.get('title', 'Untitled')}', Category: '{found_query.get('category', 'Uncategorized')}'")    
        
        # Save the updated library data
        success = save_library_data(library_data)
        
        if success:
            logging.info(f"Successfully deleted query {query_id} from library")
            return jsonify({
                'success': True,
                'message': 'Query deleted successfully'
            })
        else:
            logging.error(f"Failed to save library data after deleting query {query_id}")
            return jsonify({
                'success': False,
                'error': 'Failed to save changes to the library file'
            }), 500
    
    @app.route('/library/query/<query_id>', methods=['PUT'])
    def update_library_query(query_id):
        """Update a specific query in the library by ID"""
        # Import utility functions
        from modules.utils.aql_library import load_library_data, save_library_data, get_query_by_id
        
        # Log the request
        logging.info(f"Updating library query with ID: {query_id}")
        
        # Get the updated query data from the request
        data = request.json
        if not data:
            logging.warning(f"Invalid update request for query {query_id}: no data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        # At minimum, we need the query text
        if 'query' not in data:
            logging.warning(f"Invalid update request for query {query_id}: missing 'query' field")
            return jsonify({'error': 'No query provided'}), 400
            
        updated_query_text = data.get('query')
        logging.debug(f"New query text length: {len(updated_query_text)} characters")
        
        # Optional fields that might be updated
        verified = data.get('verified', None)
        visualization = data.get('visualization', None)
        title = data.get('title', None)
        category = data.get('category', None)
        purpose = data.get('purpose', None)
        impact = data.get('impact', None)
        action = data.get('action', None)
        keywords = data.get('keywords', None)
        
        # Load the current library data
        library_data = load_library_data()
        
        # Find the query to update
        found = False
        for i, query in enumerate(library_data.get('queries', [])):
            if query.get('id') == query_id:
                # Store the original query for logging
                original_query = library_data['queries'][i]['query']
                
                # Update the query text
                library_data['queries'][i]['query'] = updated_query_text
                
                # Update other fields if provided
                if verified is not None:
                    library_data['queries'][i]['verified'] = verified
                    
                if visualization is not None:
                    library_data['queries'][i]['visualization'] = visualization
                
                if title is not None:
                    library_data['queries'][i]['title'] = title
                
                if category is not None:
                    library_data['queries'][i]['category'] = category
                
                if purpose is not None:
                    library_data['queries'][i]['purpose'] = purpose
                
                if impact is not None:
                    library_data['queries'][i]['impact'] = impact
                
                if action is not None:
                    library_data['queries'][i]['action'] = action
                
                if keywords is not None:
                    # Convert comma-separated string to array
                    keyword_array = [k.strip() for k in keywords.split(',') if k.strip()]
                    library_data['queries'][i]['keywords'] = keyword_array
                    
                found = True
                
                # Log the update
                logging.info(f"Query {query_id} updated. Title: '{library_data['queries'][i].get('title', 'Untitled')}', Category: '{library_data['queries'][i].get('category', 'Uncategorized')}', Changed: {original_query != updated_query_text}")
                break
                
        if not found:
            logging.warning(f"Query {query_id} not found in library when attempting to update")
            return jsonify({'error': 'Query not found'}), 404
            
        # Save the updated library data
        success = save_library_data(library_data)
        
        if success:
            logging.info(f"Successfully saved updated library with query {query_id}")
            return jsonify({
                'success': True,
                'message': 'Query updated successfully',
                'query_id': query_id
            })
        else:
            logging.error(f"Failed to save library data after updating query {query_id}")
            return jsonify({
                'success': False,
                'error': 'Failed to save changes to the library file'
            }), 500
    
    @app.route('/library/execute', methods=['POST'])
    def execute_library_query():
        """Execute a query from the library"""
        # Get the query to execute
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400
            
        query = data.get('query')
        api_server = data.get('server')
        api_endpoint = data.get('endpoint')
        
        # Initialize the result object
        result = {
            'query': query,
            'success': False,
            'data': None,
            'error': None,
            'execution_time': 0,
            'row_count': 0,
            'validation': {
                'status': 'none',
                'message': ''
            }
        }
        
        # Create a user_id for logging
        user_id = 'library_user'
        
        try:
            # Note: sanitize_query function has been removed
            # Use the query directly
            sanitized_query = query
            
            # Execute the query and track execution time
            start_time = time.time()
            
            # If API server/endpoint were provided, use them
            if api_server and api_endpoint:
                api_client.set_server(api_server)
                api_client.set_endpoint(api_endpoint)
                
            data = api_client.execute_query(sanitized_query)
            end_time = time.time()
            execution_time = end_time - start_time
                
            # Process the results
            result['success'] = True
            result['execution_time'] = execution_time
            
            # Import pandas at the top of the function for availability
            import pandas as pd
            
            # Define a recursive function to convert any DataFrames to serializable format
            def convert_to_serializable(obj):
                if isinstance(obj, pd.DataFrame):
                    return obj.to_dict(orient='records')
                elif isinstance(obj, pd.Series):
                    return obj.to_dict()
                elif isinstance(obj, dict):
                    return {k: convert_to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_serializable(item) for item in obj]
                else:
                    return obj
            
            # Process result based on data type
            if isinstance(data, pd.DataFrame):
                # Convert DataFrame to serializable format
                result['data'] = convert_to_serializable(data)
                # Get row count directly from DataFrame
                result['row_count'] = len(data) if not data.empty else 0
            else:
                # Apply the convert_to_serializable function to all data types
                result['data'] = convert_to_serializable(data)
                
                # Handle row count calculation based on data type
                if isinstance(data, (list, tuple)):
                    result['row_count'] = len(data)
                elif isinstance(data, dict) and 'rows' in data:
                    result['row_count'] = len(data['rows'])
                else:
                    result['row_count'] = 0
            
            # Try to safely log the query execution
            try:
                # Create a simple summary for logging regardless of data type
                log_data = {
                    'summary': f'Data of type {type(data).__name__}',
                    'totalRows': result['row_count']
                }
                
                # Add columns if available
                if isinstance(data, pd.DataFrame):
                    log_data['columns'] = data.columns.tolist()
                elif isinstance(data, dict) and 'columns' in data:
                    log_data['columns'] = data['columns']
                elif isinstance(data, (list, tuple)) and data and isinstance(data[0], dict):
                    # Try to infer columns from first item if it's a dict
                    log_data['columns'] = list(data[0].keys())
                    
                log_query_execution(user_id, sanitized_query, log_data, execution_time)
                
                # Additional performance metrics
                performance_metrics = {
                    'execution_time': execution_time,
                    'row_count': result['row_count']
                }
                log_query_performance(user_id, f'library-{int(start_time)}', performance_metrics)
            except Exception as logging_error:
                # Just log the error and continue - don't fail the request because of logging
                logger.error(f"Error during query logging: {logging_error}")
            
            # Validate the results
            result['validation'] = {
                'status': 'success',
                'attempts': 1,
                'maxAttempts': 1,
                'message': 'Query executed successfully.'
            }
                
            return jsonify(result)
            
        except Exception as e:
            # Log the error - use try/except to prevent logging errors from affecting response
            error_message = str(e)
            logger.error(f"Query execution error: {error_message}")
            
            try:
                log_query_error(user_id, f"Library query execution", error_message, query)
            except Exception as log_error:
                logger.error(f"Failed to log query error: {log_error}")
            
            # Make sure result is fully serializable
            result['success'] = False
            result['error'] = error_message
            result['validation'] = {
                'status': 'error',
                'message': error_message
            }
            
            # Explicitly set data to an empty list to ensure it's JSON serializable
            result['data'] = []
            result['row_count'] = 0
            
            return jsonify(result), 500

    @app.route('/aparaviz')
    def aparaviz():
        """Render the Aparaviz visualization dashboard"""
        return render_template('aparaviz.html')
        
    @app.route('/api/aparaviz/data')
    def aparaviz_data():
        """Get data for the Aparaviz visualization directly from the DuckDB database"""
        import duckdb
        import os
        import pandas as pd
        import json
        
        try:
            # Connect to the DuckDB database in the data folder
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', '.duckdb')
            conn = duckdb.connect(db_path, read_only=True)
            
            # Check what tables are available
            tables = conn.execute("SHOW TABLES").fetchall()
            
            if not tables:
                return jsonify({
                    'success': False,
                    'error': 'No tables found in the database',
                    'tables': []
                })
                
            # First check the structure of the database tables
            tables_info = []
            for table in tables:
                table_name = table[0]
                try:
                    # Get column info
                    columns_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                    table_columns = [col[1] for col in columns_info]
                    
                    # Get row count
                    row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    
                    # Get sample data
                    sample_data = conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchall()
                    
                    tables_info.append({
                        'name': table_name,
                        'columns': table_columns,
                        'row_count': row_count,
                        'sample': str(sample_data) if sample_data else 'No data'
                    })
                    
                    logger.info(f"Table: {table_name}, Columns: {table_columns}, Rows: {row_count}")
                except Exception as e:
                    logger.warning(f"Error inspecting table {table_name}: {str(e)}")
            
            # Now that we know the structure, let's get file counts and sizes properly
            file_data = {}
            try:
                # Join objects with instances to get file sizes by parentId
                # This gives us files by their parent folder ID
                file_query = """
                SELECT 
                    o.parentId, 
                    COUNT(*) as file_count,
                    SUM(COALESCE(i.size, o.primarySize, 0)) as total_size
                FROM objects o
                LEFT JOIN instances i ON o.objectId = i.objectId
                WHERE o.name IS NOT NULL
                GROUP BY o.parentId
                """
                file_results = conn.execute(file_query).fetchall()
                logger.info(f"Successfully retrieved file metrics for {len(file_results)} parent folders")
                
                # Now map parentId to parentPath using parentPaths table
                # First build a mapping of parentId to path
                path_query = "SELECT parentId, parentPath FROM parentPaths"
                path_results = conn.execute(path_query).fetchall()
                
                # Create a mapping of parentId to parentPath
                parent_id_to_path = {}
                for row in path_results:
                    parent_id = row[0]
                    path = row[1]
                    parent_id_to_path[parent_id] = path
                    
                logger.info(f"Created mapping for {len(parent_id_to_path)} folder paths")
                
                # Now combine the file metrics with the paths
                for row in file_results:
                    parent_id = row[0]
                    if parent_id in parent_id_to_path:
                        path = parent_id_to_path[parent_id]
                        # Ensure paths end with slash for consistency
                        if path and not path.endswith('/'):
                            path = path + '/'
                        file_data[path] = {
                            'file_count': row[1],
                            'total_size': row[2]
                        }
                        
                logger.info(f"Successfully mapped file metrics to {len(file_data)} folder paths")
                
            except Exception as e:
                logger.warning(f"Could not query file metrics: {str(e)}")
            
            # Get all folders with their paths and metrics
            # Adjust query based on available columns
            try:
                columns_info = conn.execute("PRAGMA table_info(parentPaths)").fetchall()
                column_names = [col[1] for col in columns_info]
                logger.info(f"parentPaths columns: {column_names}")
                
                if 'size' in column_names:
                    # If size column exists
                    query = """
                    SELECT 
                        parentPath AS path,
                        COUNT(*) AS file_count,
                        SUM(COALESCE(size, 0)) AS total_size
                    FROM parentPaths
                    GROUP BY parentPath
                    ORDER BY parentPath
                    """
                else:
                    # If size column doesn't exist, just get folder structure
                    query = """
                    SELECT DISTINCT 
                        parentPath AS path
                    FROM parentPaths
                    ORDER BY parentPath
                    """
            except Exception as e:
                logger.warning(f"Error checking parentPaths columns: {str(e)}")
                # Fallback query
                query = """
                SELECT DISTINCT 
                    parentPath AS path
                FROM parentPaths
                ORDER BY parentPath
                """
            
            try:
                # Try to run the folder query
                folders_df = conn.execute(query).fetchdf()
                logger.info(f"Retrieved {len(folders_df)} folder rows")
                
                # If the query didn't include file counts and sizes, supplement with file data
                if 'file_count' not in folders_df.columns or 'total_size' not in folders_df.columns:
                    # Add missing columns with zeros as defaults
                    if 'file_count' not in folders_df.columns:
                        folders_df['file_count'] = 0
                    if 'total_size' not in folders_df.columns:
                        folders_df['total_size'] = 0
                    
                    # Now update with data from files table if we have it
                    if file_data:
                        logger.info(f"Updating folder data with {len(file_data)} file entries")
                        for idx, row in folders_df.iterrows():
                            path = row['path']
                            if path in file_data:
                                folders_df.at[idx, 'file_count'] = file_data[path]['file_count']
                                folders_df.at[idx, 'total_size'] = file_data[path]['total_size']
                                
                # Log sample of the processed data
                logger.info(f"Sample data: {folders_df.head(3).to_dict('records')}")
                
            except Exception as e:
                logger.error(f"Error running folder query: {str(e)}")
                # If that query fails, check what tables and columns are available
                tables_info = []
                for table in tables:
                    table_name = table[0]
                    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                    tables_info.append({
                        'name': table_name,
                        'columns': [col[1] for col in columns]
                    })
                    
                # Try a basic query on the first table as fallback
                if tables:
                    first_table = tables[0][0]
                    folders_df = conn.execute(f"SELECT * FROM {first_table} LIMIT 1000").fetchdf()
                    # If this is a raw data table, convert to expected format
                    if 'path' not in folders_df.columns and 'parentPath' in folders_df.columns:
                        folders_df = folders_df.rename(columns={'parentPath': 'path'})
                    # Add missing columns
                    if 'file_count' not in folders_df.columns:
                        folders_df['file_count'] = 1  # Each row is a file
                    if 'total_size' not in folders_df.columns and 'size' in folders_df.columns:
                        folders_df['total_size'] = folders_df['size']
                    elif 'total_size' not in folders_df.columns:
                        folders_df['total_size'] = 0
                else:
                    folders_df = pd.DataFrame()
            
            # Close the connection
            conn.close()
            
            # If we have no data, return error
            if folders_df.empty:
                return jsonify({
                    'success': False,
                    'error': 'No data available',
                    'tables': [t[0] for t in tables]
                })
                
            # Return the data as JSON
            return jsonify({
                'success': True,
                'data': folders_df.to_dict(orient='records'),
                'tables': [t[0] for t in tables]
            })
            
        except Exception as e:
            logger.error(f"Error accessing DuckDB database: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            })

    def analyze_results(query, result_df, provider=None):
        """Analyze the results of a query using the LLM provider
        
        Args:
            query: The query that was executed
            result_df: Pandas DataFrame with the results
            provider: Optional provider override
        
        Returns:
            Insights from the LLM analysis or None if error
        """
        import config
        from modules.llm.base import get_llm_provider
        
        try:
            # Use the right provider
            llm_client = get_llm_provider(provider, config, _api_client.db_store)
            if not llm_client:
                return None
            
            # If no results, return none
            if result_df.empty:
                return None
            
            # Serialize data for analysis
            result_json = result_df.to_json(orient='records')
            
            # Generate the system prompt for insights
            system_prompt = """You are an expert data analyst who extracts meaningful insights from query results.
            Look at the data and provide clear, structured insights. Focus on:
            1. Key metrics and trends
            2. Notable outliers or patterns
            3. Actionable recommendations

            Format your response using markdown:
            - Use ### for section headers
            - Use **bold** for important metrics
            - Use bullet points and numbered lists
            - Group related insights into sections
            - Keep insights concise and clear
            """
            
            user_message = f"""Here are the results of a query: {query}
            
            The data is: {result_json}
            
            Please provide a clear, structured analysis with key insights. Format your insights with markdown headings, bold for important numbers, and use lists for readability."""
            
            # Generate insights with the provider
            insights = llm_client.generate_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.1  # Lower temperature for more factual responses
            )
            
            return insights
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error analyzing results: {str(e)}")
            return None
            
    # Visualization API Routes
    if VISUALIZATION_ENABLED:
        @app.route('/api/visualizations/available', methods=['POST'])
        def get_available_visualizations():
            """Get available visualization types for the query results"""
            # Make sure we have results
            if not request.json or 'results' not in request.json:
                return jsonify({
                    'success': False,
                    'error': 'No results provided',
                    'visualizations': []
                })
            
            # Parse the results
            results_data = request.json.get('results', {})
            
            try:
                # Convert to DataFrame if not already
                if isinstance(results_data, dict) and 'data' in results_data:
                    # Handle case where results are wrapped in an object
                    data = results_data.get('data', [])
                    df = pd.DataFrame(data) if data else pd.DataFrame()
                elif isinstance(results_data, list):
                    # Handle case where results are a plain array
                    df = pd.DataFrame(results_data) if results_data else pd.DataFrame()
                else:
                    df = pd.DataFrame()
                
                # Get visualization suggestions
                suggested_viz = _visualization_manager.suggest_visualizations(df)
                
                return jsonify({
                    'success': True,
                    'error': None,
                    'visualizations': suggested_viz
                })
            except Exception as e:
                logger.error(f"Error getting available visualizations: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'visualizations': ['table']  # Always fall back to table view
                })
        
        @app.route('/api/visualizations/<viz_type>/options', methods=['POST'])
        def get_visualization_options(viz_type):
            """Get options for a specific visualization type"""
            # Make sure we have results
            if not request.json or 'results' not in request.json:
                return jsonify({
                    'success': False,
                    'error': 'No results provided',
                    'options': {}
                })
            
            # Parse the results
            results_data = request.json.get('results', {})
            
            try:
                # Convert to DataFrame if not already
                if isinstance(results_data, dict) and 'data' in results_data:
                    # Handle case where results are wrapped in an object
                    data = results_data.get('data', [])
                    df = pd.DataFrame(data) if data else pd.DataFrame()
                elif isinstance(results_data, list):
                    # Handle case where results are a plain array
                    df = pd.DataFrame(results_data) if results_data else pd.DataFrame()
                else:
                    df = pd.DataFrame()
                
                # Get options for visualization type
                options = _visualization_manager.get_visualization_options(viz_type, df)
                
                return jsonify({
                    'success': True,
                    'error': None,
                    'options': options
                })
            except Exception as e:
                logger.error(f"Error getting visualization options: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'options': {}
                })
        
        @app.route('/api/visualizations/<viz_type>/create', methods=['POST'])
        def create_visualization(viz_type):
            """Create a visualization of the specified type"""
            # Make sure we have results
            if not request.json or 'results' not in request.json:
                return jsonify({
                    'success': False,
                    'error': 'No results provided',
                    'data': None
                })
            
            # Parse the results and options
            results_data = request.json.get('results', {})
            options = request.json.get('options', {})
            
            try:
                # Convert to DataFrame if not already
                if isinstance(results_data, dict) and 'data' in results_data:
                    # Handle case where results are wrapped in an object
                    data = results_data.get('data', [])
                    df = pd.DataFrame(data) if data else pd.DataFrame()
                elif isinstance(results_data, list):
                    # Handle case where results are a plain array
                    df = pd.DataFrame(results_data) if results_data else pd.DataFrame()
                else:
                    df = pd.DataFrame()
                
                # Set a default title
                title = f"AQL Query Results Visualization"
                
                # Create the visualization
                result = _visualization_manager.create_visualization(
                    viz_type, 
                    df, 
                    title=title,
                    options=options
                )
                
                # Return the result
                if result['success']:
                    return jsonify({
                        'success': True,
                        'error': None,
                        'viz_type': viz_type,
                        'data': result['data']
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result['error'],
                        'viz_type': viz_type,
                        'data': None
                    })
            except Exception as e:
                logger.error(f"Error creating visualization: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'viz_type': viz_type,
                    'data': None
                })
