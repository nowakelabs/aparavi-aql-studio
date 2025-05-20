#!/usr/bin/env python3
"""
Date Utilities for AQL Query Assistant

This module provides utility functions for handling date-related operations for AQL queries.
"""

import re
from datetime import datetime, timedelta

def get_current_date():
    """
    Returns the current date in 'YYYY-MM-DD' format
    """
    return datetime.now().strftime('%Y-%m-%d')

def get_date_last_year():
    """
    Returns the date from one year ago in 'YYYY-MM-DD' format
    """
    return (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

def get_date_last_month():
    """
    Returns the date from 30 days ago in 'YYYY-MM-DD' format
    """
    return (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

def get_date_last_week():
    """
    Returns the date from 7 days ago in 'YYYY-MM-DD' format
    """
    return (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

def add_date_range_to_query(query, time_range="year"):
    """
    Add a date range to a query based on the specified time range
    
    Args:
        query (str): The AQL query string
        time_range (str): The time range to add (year, month, week)
        
    Returns:
        str: The query with date range added
    """
    if not query:
        return query
        
    # Default to the current date for the upper bound
    today = get_current_date()
    
    # Determine lower bound based on time_range
    if time_range == "year":
        from_date = get_date_last_year()
    elif time_range == "month":
        from_date = get_date_last_month()
    elif time_range == "week":
        from_date = get_date_last_week()
    else:
        # Default to year if not specified
        from_date = get_date_last_year()
    
    # Simplistic approach - find the end of WHERE clause and add date criteria
    # This is a basic implementation that will need more testing in production
    where_pattern = re.compile(r'(WHERE\s*\(.*?\))', re.IGNORECASE)
    
    if 'WHERE' in query:
        if 'createTime >=' not in query and 'createTime <=' not in query:
            # Modify existing WHERE clause to add date range
            date_condition = f" AND (createTime >= '{from_date}' AND createTime <= '{today}')"
            modified_query = where_pattern.sub(r'\1' + date_condition, query)
            return modified_query
    
    # If we get here, just return the original query
    return query
