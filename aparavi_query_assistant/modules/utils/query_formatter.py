#!/usr/bin/env python3
"""
Query Formatter Module

This module provides utility functions to format AQL queries for various use cases,
particularly for API compatibility with GET requests.
"""

import re
import logging

logger = logging.getLogger('aparavi.query_formatter')

def format_query_for_api(query):
    """
    Format a query to be safe for API GET requests
    
    This function preserves double quotes in identifiers as the Aparavi API expects.
    
    Args:
        query (str): The original AQL query
        
    Returns:
        str: API-safe query with proper quoting
    """
    # The Aparavi API expects double quotes for identifiers, not backticks
    # Simply return the original query without modifications
    
    logger.debug("Query formatter no longer modifies quotes - preserving original query")
    
    return query

def replace_spaces_with_underscores(query):
    """
    Replace spaces in column aliases with underscores
    
    This is an alternative approach for API compatibility
    
    Args:
        query (str): The original AQL query
        
    Returns:
        str: Query with underscores instead of spaces in identifiers
    """
    # Replace spaces in column aliases
    as_pattern = r'AS\s+"([^"]+)"'
    
    def replace_spaces(match):
        identifier = match.group(1).replace(' ', '_')
        return f'AS "{identifier}"'
    
    return re.sub(as_pattern, replace_spaces, query, flags=re.IGNORECASE)

if __name__ == "__main__":
    # Example usage
    test_query = """SELECT CASE WHEN size <= 1048576 THEN '0-1MB' WHEN size <= 10485760 THEN '1-10MB' ELSE '>10MB' END AS "Size Range", COUNT(name) AS "File Count" GROUP BY "Size Range" ORDER BY "File Count" DESC;"""
    
    # Format for API
    api_safe = format_query_for_api(test_query)
    print("API SAFE VERSION:")
    print(api_safe)
    
    # Format with underscores
    underscore_version = replace_spaces_with_underscores(test_query)
    print("\nUNDERSCORE VERSION:")
    print(underscore_version)
