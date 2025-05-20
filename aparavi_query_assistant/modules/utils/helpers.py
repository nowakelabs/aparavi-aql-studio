#!/usr/bin/env python3
"""
Helper Utility Functions

This module provides common utility functions used throughout the application.
"""

import time
import json
import logging
from datetime import datetime


def format_size(size_bytes):
    """Format byte size into human-readable format
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Human-readable size (e.g. '2.5 MB')
    """
    if size_bytes is None or size_bytes < 0:
        return "Unknown"
        
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size_bytes < 1024 or unit == 'PB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024


def format_timestamp(timestamp):
    """Convert timestamp to human-readable date/time
    
    Args:
        timestamp (str or int): Timestamp value
        
    Returns:
        str: Formatted date/time string
    """
    if not timestamp:
        return "N/A"
        
    try:
        # Handle different timestamp formats
        if isinstance(timestamp, (int, float)):
            # Unix timestamp (seconds since epoch)
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            # ISO format or similar
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                # Try parsing as generic datetime
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            return str(timestamp)
            
        return dt.strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        logging.warning(f"Error formatting timestamp {timestamp}: {e}")
        return str(timestamp)


def log_timing(func):
    """Decorator for logging function execution time
    
    Args:
        func: Function to be timed
        
    Returns:
        Wrapped function with timing functionality
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Get function name
        func_name = func.__name__
        
        # Log execution time
        logging.debug(f"{func_name} executed in {end_time - start_time:.4f} seconds")
        
        return result
    return wrapper


def safe_json_loads(json_str, default=None):
    """Safely parse JSON string without raising exceptions
    
    Args:
        json_str (str): JSON string to parse
        default: Default value to return if parsing fails
        
    Returns:
        dict or default: Parsed JSON or default value
    """
    if not json_str:
        return default
        
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.warning(f"Error parsing JSON: {e}")
        return default


def sanitize_query(query):
    """Sanitize AQL query for safe execution
    
    Args:
        query (str): The raw AQL query
        
    Returns:
        str: Sanitized query
    """
    if not query:
        return ""
        
    # Strip comments
    query_lines = []
    for line in query.split('\n'):
        # Remove inline comments
        if '--' in line:
            line = line.split('--', 1)[0]
        # Skip empty lines after comment removal
        if line.strip():
            query_lines.append(line)
            
    # Rejoin without comments
    clean_query = '\n'.join(query_lines)
    
    # Remove escaped quotes that can cause syntax errors (like \')
    clean_query = clean_query.replace("\\'", "'").replace('\\"', '"')
    
    # Remove any other problematic escape sequences
    clean_query = clean_query.replace('\\\\', '\\')
    
    return clean_query.strip()


def truncate_string(s, max_length=100, suffix='...'):
    """Truncate a string to a maximum length
    
    Args:
        s (str): String to truncate
        max_length (int): Maximum length of the result
        suffix (str): Suffix to append if truncated
        
    Returns:
        str: Truncated string
    """
    if not s or len(s) <= max_length:
        return s
        
    return s[:max_length - len(suffix)] + suffix