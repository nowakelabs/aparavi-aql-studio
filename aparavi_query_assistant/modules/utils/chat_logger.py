#!/usr/bin/env python3
"""
Chat Logger

This module provides logging functionality specifically for the chat interface
to help with troubleshooting and debugging chat interactions.
"""

import os
import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Set up chat logger
chat_logger = logging.getLogger('aparavi.chat')
chat_logger.setLevel(logging.DEBUG)

# Clear existing handlers (in case of reloads)
if chat_logger.handlers:
    chat_logger.handlers.clear()

# Prevent propagation to the root logger to avoid duplicate logs
chat_logger.propagate = False

# Create rotating file handler for chat logs
chat_log_file = os.path.join(logs_dir, 'chat.log')
chat_handler = RotatingFileHandler(
    chat_log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
chat_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
chat_handler.setFormatter(formatter)

# Add handlers to logger
chat_logger.addHandler(chat_handler)

# Add a console handler for immediate feedback during development
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
chat_logger.addHandler(console_handler)

# Logger setup complete

def log_chat_message(user_id, message, is_user=True):
    """Log a chat message
    
    Args:
        user_id (str): User identifier
        message (str): The chat message
        is_user (bool): True if message is from user, False if from system
    """
    sender = 'USER' if is_user else 'SYSTEM'
    chat_logger.info(f"[{user_id}] [{sender}] {message}")

def log_query_generation(user_id, question, query, provider):
    """Log generated query
    
    Args:
        user_id (str): User identifier
        question (str): Original question from user
        query (str): Generated AQL query
        provider (str): LLM provider used
    """
    chat_logger.info(f"[{user_id}] [QUERY_GEN] Provider: {provider}")
    chat_logger.info(f"[{user_id}] [QUERY_GEN] Question: {question}")
    chat_logger.info(f"[{user_id}] [QUERY_GEN] Query: {query}")

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
    chat_logger.info(f"[{user_id}] [QUERY_EXEC] Status: {status}")
    chat_logger.info(f"[{user_id}] [QUERY_EXEC] Time: {execution_time:.2f}s")
    chat_logger.info(f"[{user_id}] [QUERY_EXEC] Query: {query}")
    
    if error:
        chat_logger.error(f"[{user_id}] [QUERY_EXEC] Error: {error}")
    else:
        # Log basic result info without full data
        row_count = result.get('totalRows', 0) if result else 0
        columns = result.get('columns', []) if result else []
        chat_logger.info(f"[{user_id}] [QUERY_EXEC] Results: {row_count} rows, {len(columns)} columns")

def log_analysis(user_id, question, insights, provider):
    """Log analysis of query results
    
    Args:
        user_id (str): User identifier
        question (str): Original question from user
        insights (str): Generated insights
        provider (str): LLM provider used for analysis
    """
    chat_logger.info(f"[{user_id}] [ANALYSIS] Provider: {provider}")
    chat_logger.info(f"[{user_id}] [ANALYSIS] Question: {question}")
    chat_logger.info(f"[{user_id}] [ANALYSIS] Insights: {insights[:500]}...")  # Log only first 500 chars

def log_error(user_id, error_type, error_message, details=None):
    """Log an error in the chat process
    
    Args:
        user_id (str): User identifier
        error_type (str): Type of error
        error_message (str): Error message
        details (dict, optional): Additional error details
    """
    # Format the error message
    message = f"[{user_id}] [{error_type}] {error_message}"
    
    # Log the error
    chat_logger.error(message)
    
    # Add details if provided - keep the original error detail format for consistency
    if details:
        try:
            chat_logger.error(f"[{user_id}] [ERROR_DETAILS] {json.dumps(details)}")
        except:
            chat_logger.error(f"[{user_id}] [ERROR_DETAILS] Could not serialize error details")

def log_info(user_id, info_type, info_message, details=None):
    """Log informational messages in the chat process
    
    Args:
        user_id (str): User identifier
        info_type (str): Type of information
        info_message (str): Information message
        details (dict, optional): Additional details
    """
    # Format the info message
    message = f"[{user_id}] [{info_type}] {info_message}"
    
    # Add details if provided
    if details:
        message += f" Details: {json.dumps(details)}"
    
    # Log the info message
    chat_logger.info(message)
