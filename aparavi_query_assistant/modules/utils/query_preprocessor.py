#!/usr/bin/env python3
"""
Query Preprocessor

This module handles preprocessing of AQL queries, including resolving template variables
before sending queries to the Aparavi API.
"""

import logging
import re
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Define standard date template variables with their timedelta values
# These are kept as fallbacks in case the dates.aql file can't be loaded
DATE_VARIABLES = {
    '{{TODAY}}': timedelta(days=0),
    '{{DATE_MINUS_30_DAYS}}': timedelta(days=30),
    '{{DATE_MINUS_90_DAYS}}': timedelta(days=90),
    '{{DATE_MINUS_6_MONTHS}}': timedelta(days=182),  # Approximately 6 months
    '{{DATE_MINUS_1_YEAR}}': timedelta(days=365),
    '{{DATE_MINUS_2_YEARS}}': timedelta(days=730),
    '{{DATE_MINUS_3_YEARS}}': timedelta(days=1095),
    '{{DATE_MINUS_5_YEARS}}': timedelta(days=1825),
    '{{DATE_MINUS_7_YEARS}}': timedelta(days=2555),
    '{{DATE_MINUS_10_YEARS}}': timedelta(days=3650),
}

def _load_aql_date_expressions():
    """
    Load AQL date expressions from the dates.aql file
    
    Returns:
        dict: Dictionary of date variable names and their AQL expressions
    """
    # Get the path to the dates.aql file relative to this module
    current_dir = Path(__file__).parent.parent.parent
    dates_file_path = current_dir / 'data' / 'dates.aql'
    
    try:
        if not dates_file_path.exists():
            logger.warning(f"dates.aql file not found at {dates_file_path}")
            return {}
            
        with open(dates_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract the JSON part from the file
        json_match = re.search(r'({.*})', content, re.DOTALL)
        if not json_match:
            logger.warning("Could not find JSON data in dates.aql")
            return {}
            
        json_str = json_match.group(1)
        aql_expressions = json.loads(json_str)
        
        logger.info(f"Loaded {len(aql_expressions)} date variables from dates.aql")
        return aql_expressions
    except Exception as e:
        logger.error(f"Error loading AQL date expressions: {e}")
        return {}

# Load AQL expressions from dates.aql file
AQL_DATE_EXPRESSIONS = _load_aql_date_expressions()

def preprocess_query(query_text):
    """
    Preprocess an AQL query by replacing template variables with actual values.
    
    Args:
        query_text (str): The original query text with potential template variables
        
    Returns:
        str: The processed query with all variables replaced
    """
    if not query_text:
        return query_text
        
    # Replace all date variables
    processed_query = query_text
    
    # First try to replace with AQL expressions from the dates.aql file
    for var_name, aql_expr in AQL_DATE_EXPRESSIONS.items():
        if var_name in processed_query:
            processed_query = processed_query.replace(var_name, aql_expr)
    
    # Check if any date variables remain (fallback to old method)
    remaining_vars = [var for var in DATE_VARIABLES.keys() if var in processed_query]
    
    if remaining_vars:
        # Get current date
        today = datetime.now()
        
        # Use fallback method for any remaining variables
        for var_name in remaining_vars:
            # Calculate the actual date for this variable
            target_date = today - DATE_VARIABLES[var_name]
            date_str = target_date.strftime('%Y-%m-%d')
            
            # Replace all occurrences of the variable
            processed_query = processed_query.replace(var_name, date_str)
    
    # Log any unreplaced variables as warnings
    unreplaced_vars = re.findall(r'{{.*?}}', processed_query)
    if unreplaced_vars:
        logger.warning(f"Unreplaced variables in query: {', '.join(unreplaced_vars)}")
    
    return processed_query

def add_date_variable_comments(query_text):
    """
    Add helpful comments to queries with date variables to explain their purpose.
    
    Args:
        query_text (str): The query text that may contain date variables
        
    Returns:
        str: Query with added comments explaining date variables
    """
    if not query_text or not any(var in query_text for var in DATE_VARIABLES):
        return query_text
    
    # Get today's date for reference
    today = datetime.now()
    
    # Create a header comment explaining the date variables
    header = "-- Query uses date template variables which will be automatically replaced with actual dates\n"
    header += "-- based on the current date when the query is executed.\n"
    header += "-- Currently available variables:\n"
    
    # Add each variable with its current value
    for var_name, delta in DATE_VARIABLES.items():
        target_date = today - delta
        date_str = target_date.strftime('%Y-%m-%d')
        header += f"-- {var_name} = {date_str}\n"
    
    # Add the header to the query
    return header + "\n" + query_text
