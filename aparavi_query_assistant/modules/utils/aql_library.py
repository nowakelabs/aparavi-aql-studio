#!/usr/bin/env python3
"""
AQL Library Utilities

This module handles the loading and management of AQL queries from the consolidated JSON library file.
"""

import os
import json
import logging
import re
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

def get_library_file_path():
    """Get the path to the AQL library JSON file
    
    Returns:
        Path: Path to the aql_library.json file
    """
    # Start from the current file's location
    current_file = Path(__file__)
    
    # Navigate up to the project root (2 levels up from utils)
    project_root = current_file.parent.parent.parent
    
    # Return the path to the aql_library.json file in the data directory
    data_dir = project_root / 'data'
    
    # Create data directory if it doesn't exist
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        
    return data_dir / 'aql_library.json'

def load_library_data():
    """Load AQL queries from the JSON library file
    
    Returns:
        dict: Dictionary containing the AQL library data including queries and categories
    """
    library_file = get_library_file_path()
    
    try:
        if not library_file.exists():
            logger.warning(f"Library file not found at {library_file}")
            return {"categories": [], "queries": []}
            
        with open(library_file, 'r', encoding='utf-8') as f:
            library_data = json.load(f)
            
        # Validate the structure of the loaded data
        if not isinstance(library_data, dict):
            logger.error("Library data is not a valid JSON object")
            return {"categories": [], "queries": []}
            
        if "queries" not in library_data or not isinstance(library_data["queries"], list):
            logger.error("Library data is missing 'queries' array")
            return {"categories": [], "queries": []}
            
        if "categories" not in library_data or not isinstance(library_data["categories"], list):
            logger.error("Library data is missing 'categories' array")
            return {"categories": [], "queries": []}
            
        return library_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing library JSON file: {e}")
        return {"categories": [], "queries": []}
        
    except Exception as e:
        logger.error(f"Error loading library data: {e}")
        return {"categories": [], "queries": []}

def get_all_library_queries():
    """Get all queries from the AQL library
    
    Returns:
        list: List of query dictionaries with metadata
    """
    try:
        library_data = load_library_data()
        return library_data.get("queries", [])
    except Exception as e:
        logger.error(f"Error getting library queries: {e}")
        return []

def get_library_categories():
    """Get all categories from the AQL library
    
    Returns:
        list: List of unique category objects with name and description
    """
    try:
        library_data = load_library_data()
        return library_data.get("categories", [])
    except Exception as e:
        logger.error(f"Error getting library categories: {e}")
        return []

def generate_unique_id(title):
    """Generate a unique ID based on the title of the query
    
    Args:
        title (str): The title of the query
        
    Returns:
        str: A unique ID string for the query
    """
    # Create a slug from the title
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[\s_-]+', '_', slug)
    slug = slug.strip('-_')
    
    # Truncate if too long
    if len(slug) > 30:
        slug = slug[:30]
    
    # Add a short unique suffix to ensure uniqueness
    unique_suffix = str(uuid.uuid4())[:8]
    
    # Combine with a short unique ID to ensure uniqueness
    unique_id = f"{slug}_{unique_suffix}"
    
    # Check if ID already exists, if so, generate another one
    all_queries = get_all_library_queries()
    existing_ids = [query.get('id') for query in all_queries]
    
    if unique_id in existing_ids:
        # Try again with a different suffix
        return generate_unique_id(title)
    
    return unique_id

def get_query_by_id(query_id):
    """Get a specific query by its ID
    
    Args:
        query_id (str): The ID of the query to retrieve
        
    Returns:
        dict: Query data or None if not found
    """
    all_queries = get_all_library_queries()
    
    for query in all_queries:
        if query['id'] == query_id:
            return query
            
    return None


def save_library_data(library_data):
    """Save AQL library data to the JSON file
    
    Args:
        library_data (dict): Library data to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    library_file = get_library_file_path()
    
    try:
        # Validate the data structure
        if not isinstance(library_data, dict):
            logger.error("Cannot save library: data is not a dictionary")
            return False
            
        if "queries" not in library_data or not isinstance(library_data["queries"], list):
            logger.error("Cannot save library: missing or invalid 'queries' array")
            return False
            
        if "categories" not in library_data or not isinstance(library_data["categories"], list):
            logger.error("Cannot save library: missing or invalid 'categories' array")
            return False
        
        # Ensure the data directory exists
        data_dir = library_file.parent
        if not data_dir.exists():
            data_dir.mkdir(parents=True)
            
        # Write the data to the file
        with open(library_file, 'w', encoding='utf-8') as f:
            json.dump(library_data, f, indent=2)
            
        return True
        
    except Exception as e:
        logger.error(f"Error saving library data: {e}")
        return False
