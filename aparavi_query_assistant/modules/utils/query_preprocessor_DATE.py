#!/usr/bin/env python3
"""
Query Preprocessor

This module handles preprocessing of AQL queries, including resolving template variables
before sending queries to the Aparavi API.
"""

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Define standard date template variables with their timedelta values
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
        
    # Get current date
    today = datetime.now()
    
    # Replace all date variables
    processed_query = query_text
    for var_name, delta in DATE_VARIABLES.items():
        # Calculate the actual date for this variable
        target_date = today - delta
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Replace all occurrences of the variable
        processed_query = processed_query.replace(var_name, date_str)
    
    # Log any remaining unreplaced variables as warnings
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
