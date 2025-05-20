#!/usr/bin/env python3
"""
Query Logger

This module provides dedicated logging functionality for AQL queries
to track query generation, execution, and performance metrics.
"""

import os
import logging
import json
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Set up query logger
query_logger = logging.getLogger('aparavi.query')
query_logger.setLevel(logging.DEBUG)

# Clear existing handlers (in case of reloads)
if query_logger.handlers:
    query_logger.handlers.clear()

# Prevent propagation to the root logger to avoid duplicate logs
query_logger.propagate = False

# Create rotating file handler for query logs
query_log_file = os.path.join(logs_dir, 'query.log')
query_handler = RotatingFileHandler(
    query_log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
query_handler.setLevel(logging.DEBUG)

# Create formatter with more detailed timestamp
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                              datefmt='%Y-%m-%d %H:%M:%S')
query_handler.setFormatter(formatter)

# Add handlers to logger
query_logger.addHandler(query_handler)

# Add a console handler for immediate feedback during development
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
query_logger.addHandler(console_handler)

# Verify logger setup and test with an initial log message
try:
    # Initialize the logger silently
    query_logger.info("Query logger initialized")
    
    # Ensure message is written by flushing all handlers
    for handler in query_logger.handlers:
        handler.flush()
except Exception as e:
    # If there's any issue with logger setup, print to stdout
    print(f"Query Logger: ERROR setting up logger: {str(e)}")

def log_query_request(user_id, question, context=None):
    """Log an incoming query request
    
    Args:
        user_id (str): User identifier
        question (str): Natural language question from user
        context (dict, optional): Additional context for the query
    """
    query_logger.info(f"[{user_id}] [QUERY_REQUEST] Question: {question}")
    if context:
        try:
            query_logger.debug(f"[{user_id}] [QUERY_REQUEST] Context: {json.dumps(context)}")
        except:
            query_logger.debug(f"[{user_id}] [QUERY_REQUEST] Context: Could not serialize context")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_generation(user_id, question, query, generation_time, query_provider=None):
    """Log the generation of an AQL query
    
    Args:
        user_id (str): User identifier
        question (str): Original question from user
        query (str): Generated AQL query
        generation_time (float): Time taken to generate the query in seconds
        query_provider (str, optional): LLM provider used for query generation
    """
    query_logger.info(f"[{user_id}] [QUERY_GEN] Question: {question}")
    query_logger.info(f"[{user_id}] [QUERY_GEN] Query: {query}")
    query_logger.info(f"[{user_id}] [QUERY_GEN] Time: {generation_time:.2f}s")
    
    # Log AQL syntax patterns identified
    # These patterns help identify if proper AQL syntax is being used
    if "GROUP BY" in query:
        query_logger.info(f"[{user_id}] [QUERY_GEN] Contains GROUP BY clause")
    if "ORDER BY" in query:
        query_logger.info(f"[{user_id}] [QUERY_GEN] Contains ORDER BY clause")  
    if "WHERE" in query:
        query_logger.info(f"[{user_id}] [QUERY_GEN] Contains WHERE clause")
    
    if query_provider:
        query_logger.info(f"[{user_id}] [QUERY_GEN] Provider: {query_provider}")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_execution(user_id, query, result, execution_time, error=None):
    """Log query execution details
    
    Args:
        user_id (str): User identifier
        query (str): Executed AQL query
        result (dict): Query result data
        execution_time (float): Execution time in seconds
        error (str, optional): Error message if query failed
    """
    status = "ERROR" if error else "SUCCESS"
    query_logger.info(f"[{user_id}] [QUERY_EXEC] Status: {status}")
    query_logger.info(f"[{user_id}] [QUERY_EXEC] Time: {execution_time:.2f}s")
    # Make sure to log the properly formatted query with LIMIT in the right position
    formatted_query = query
    
    # Check if the query ends with semicolon followed by LIMIT - an incorrect format
    semicolon_limit_pattern = re.compile(r'(.*?);\s*LIMIT\s+(\d+)\s*$', re.IGNORECASE | re.DOTALL)
    match = semicolon_limit_pattern.match(formatted_query)
    
    if match:
        # Extract the parts: everything before the last semicolon, and the LIMIT value
        query_part = match.group(1)
        limit_value = match.group(2)
        
        # Split into statements to find the last one
        statements = query_part.split(';')
        
        # Find the last non-empty statement
        last_statement_index = -1
        for i in range(len(statements) - 1, -1, -1):
            if statements[i].strip():
                last_statement_index = i
                break
        
        if last_statement_index >= 0:
            # Add LIMIT to the last statement instead
            statements[last_statement_index] = f"{statements[last_statement_index].strip()} LIMIT {limit_value}"
            formatted_query = ";".join(statements)
    
    query_logger.info(f"[{user_id}] [QUERY_EXEC] Query: {formatted_query}")
    
    if error:
        query_logger.error(f"[{user_id}] [QUERY_EXEC] Error: {error}")
    else:
        # Log basic result info without full data - handle different types
        row_count = 0
        columns = []
        
        # Handle different result types
        if isinstance(result, dict) and result:
            row_count = result.get('totalRows', result.get('rowCount', 0))
            columns = result.get('columns', [])
        elif isinstance(result, (list, tuple)) and result:
            row_count = len(result)
            # Try to infer columns from first item if possible
            if result and isinstance(result[0], dict):
                columns = list(result[0].keys())
        elif hasattr(result, 'shape'):  # Handle pandas DataFrame-like objects
            # For DataFrame-like objects with shape attribute
            row_count = result.shape[0] if len(result.shape) > 0 else 0
            columns = result.columns.tolist() if hasattr(result, 'columns') else []
        query_logger.info(f"[{user_id}] [QUERY_EXEC] Results: {row_count} rows, {len(columns)} columns")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_modification(user_id, original_query, modified_query, modification_reason=None):
    """Log when a query is modified (manually or automatically)
    
    Args:
        user_id (str): User identifier
        original_query (str): Original AQL query
        modified_query (str): Modified AQL query
        modification_reason (str, optional): Reason for modification
    """
    query_logger.info(f"[{user_id}] [QUERY_MODIFY] Original: {original_query}")
    query_logger.info(f"[{user_id}] [QUERY_MODIFY] Modified: {modified_query}")
    if modification_reason:
        query_logger.info(f"[{user_id}] [QUERY_MODIFY] Reason: {modification_reason}")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_error(user_id, message, error_message, query=None):
    """Log an error that occurred during query processing
    
    Args:
        user_id (str): Unique identifier for the user
        message (str): The original user question
        error_message (str): The error message
        query (str, optional): The query that caused the error
    """
    query_logger.info(f"[{user_id}] [QUERY_ERROR] Message: {message}")
    query_logger.info(f"[{user_id}] [QUERY_ERROR] Error: {error_message}")
    if query:
        query_logger.info(f"[{user_id}] [QUERY_ERROR] Query: {query}")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_performance(user_id, query_id, metrics):
    """Log performance metrics for a query
    
    Args:
        user_id (str): User identifier
        query_id (str): Unique identifier for the query
        metrics (dict): Performance metrics (e.g., generation_time, execution_time, total_time)
    """
    try:
        query_logger.info(f"[{user_id}] [QUERY_PERF] [{query_id}] {json.dumps(metrics)}")
    except:
        query_logger.info(f"[{user_id}] [QUERY_PERF] [{query_id}] Could not serialize metrics")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_feedback(user_id, query_id, query, feedback, rating=None):
    """Log user feedback on a query
    
    Args:
        user_id (str): User identifier
        query_id (str): Unique identifier for the query
        query (str): The AQL query
        feedback (str): User feedback on the query
        rating (int, optional): Numerical rating (e.g., 1-5)
    """
    query_logger.info(f"[{user_id}] [QUERY_FEEDBACK] [{query_id}] Feedback: {feedback}")
    if rating is not None:
        query_logger.info(f"[{user_id}] [QUERY_FEEDBACK] [{query_id}] Rating: {rating}")
    query_logger.debug(f"[{user_id}] [QUERY_FEEDBACK] [{query_id}] Query: {query}")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_llm_processing(user_id, question, llm_response, provider):
    """Log detailed information about how the LLM processed a user question
    
    Args:
        user_id (str): User identifier
        question (str): Original natural language question from user
        llm_response (dict): The complete response from the LLM, including understanding,
                            query, explanation, and visualization recommendations
        provider (str): LLM provider used (e.g., openai, ollama)
    """
    query_logger.info(f"[{user_id}] [LLM_PROCESS] Question: {question}")
    query_logger.info(f"[{user_id}] [LLM_PROCESS] Provider: {provider}")
    
    # Log how the LLM understood the question
    understanding = llm_response.get('understanding', 'No understanding provided')
    query_logger.info(f"[{user_id}] [LLM_PROCESS] Understanding: {understanding}")
    
    # Log the explanation of how the query was constructed
    explanation = llm_response.get('explanation', 'No explanation provided')
    query_logger.info(f"[{user_id}] [LLM_PROCESS] Explanation: {explanation}")
    
    # Log visualization recommendations
    visualization = llm_response.get('visualization', {})
    try:
        viz_info = json.dumps(visualization) if visualization else "None"
        query_logger.info(f"[{user_id}] [LLM_PROCESS] Visualization: {viz_info}")
    except:
        query_logger.info(f"[{user_id}] [LLM_PROCESS] Visualization: Could not serialize")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_validation(user_id, query, is_valid, error_message=None, error_details=None, is_retry=False):
    """Log a query validation attempt and result
    
    Args:
        user_id (str): Unique identifier for the user
        query (str): The query being validated
        is_valid (bool): Whether the query is valid
        error_message (str, optional): Error message if validation failed
        error_details (dict, optional): Detailed error information
        is_retry (bool, optional): Whether this is a retry attempt
    """
    # Tag for determining if this is an initial attempt or a retry
    attempt_tag = "RETRY" if is_retry else "INITIAL"
    
    query_logger.info(f"[{user_id}] [QUERY_VALIDATION] [{attempt_tag}] Attempt")
    query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Query: {query}")
    
    # Log validation result
    status = "VALID" if is_valid else "INVALID"
    query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Status: {status}")
    
    # Log success details if validation succeeded
    if is_valid:
        query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Result: Query validated successfully" + 
                        (f" after {attempt_tag} attempt" if is_retry else ""))
    # Log error details if validation failed
    elif not is_valid and error_message:
        query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Error: {error_message}")
        
        # Log detailed error information if available
        if error_details:
            if isinstance(error_details, dict):
                # Try to extract the specific error context if available
                params = error_details.get('params', {})
                context = params.get('context', [])
                token = params.get('token', 'unknown')
                error_name = params.get('errorName', 'unknown')
                expecting = params.get('expecting', [])
                
                if context:
                    query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Error Context: {' '.join(context)}")
                
                query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Error Token: {token}")
                query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Error Type: {error_name}")
                
                # Log expected tokens if available
                if expecting:
                    query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Expected Tokens: {', '.join(expecting)}")
            else:
                # Log the error details as is
                query_logger.info(f"[{user_id}] [QUERY_VALIDATION] Error Details: {error_details}")
    
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()

def log_query_modification(user_id, original_query, modified_query, reason_code, details=None):
    """Log a query modification event with detailed information
    
    Args:
        user_id (str): Unique identifier for the user
        original_query (str): The original query before modification
        modified_query (str): The modified query
        reason_code (str): Code indicating reason for modification (e.g., VALIDATION_FIX)
        details (str, optional): Additional details about the modification
    """
    query_logger.info(f"[{user_id}] [QUERY_MODIFICATION] Reason: {reason_code}")
    query_logger.info(f"[{user_id}] [QUERY_MODIFICATION] Original: {original_query}")
    query_logger.info(f"[{user_id}] [QUERY_MODIFICATION] Modified: {modified_query}")
    
    # Log detailed information about the modification if available
    if details:
        query_logger.info(f"[{user_id}] [QUERY_MODIFICATION] Details: {details}")
        
    # Force flush to ensure logs are written
    for handler in query_logger.handlers:
        handler.flush()
