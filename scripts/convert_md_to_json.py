#!/usr/bin/env python3
"""
Convert AQL Library Markdown Files to JSON

This script converts the existing AQL library markdown files in the aql_library directory
into a single consolidated JSON file in the aparavi_query_assistant/data directory.
"""

import os
import re
import json
import logging
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Regular expressions for parsing markdown files
QUERY_PATTERN = re.compile(r'```sql\s*(.*?)\s*```', re.DOTALL)
TITLE_PATTERN = re.compile(r'##\s*(.*?)(?:\n|\r\n)')
PURPOSE_PATTERN = re.compile(r'\*\*Purpose:\*\*\s*(.*?)(?:\n\n|\r\n\r\n)', re.DOTALL)
IMPACT_PATTERN = re.compile(r'\*\*Business Impact:\*\*\s*(.*?)(?:\n\n|\r\n\r\n)', re.DOTALL)
ACTION_PATTERN = re.compile(r'\*\*Action Items:\*\*\s*(.*?)(?:\n\n|\r\n\r\n|$)', re.DOTALL)

def get_markdown_library_path():
    """Get the path to the AQL library markdown files directory"""
    # Start from the current directory
    script_path = Path(__file__).resolve()
    
    # Navigate to project root (parent directory of aparavi_query_assistant)
    project_root = script_path.parent.parent.parent
    
    # Return the path to the aql_library directory
    return project_root / 'aql_library'

def get_json_library_path():
    """Get the path to the output JSON file"""
    # Start from the current directory
    script_path = Path(__file__).resolve()
    
    # Navigate to data directory in aparavi_query_assistant
    app_dir = script_path.parent.parent  # aparavi_query_assistant directory
    data_dir = app_dir / 'data'
    
    # Create data directory if it doesn't exist
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        
    return data_dir / 'aql_library.json'

def parse_markdown_file(file_path):
    """Parse an AQL library markdown file to extract queries and metadata"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the category from the filename
        filename = Path(file_path).name
        category_with_prefix = Path(file_path).stem
        category_match = re.match(r'^(\d+)_(.+)$', category_with_prefix)
        
        # Get the category name and sort order
        if category_match:
            sort_order = int(category_match.group(1))
            category_name = category_match.group(2).replace('_', ' ').title()
        else:
            sort_order = 999  # Default high number for unknown sort order
            category_name = category_with_prefix.replace('_', ' ').title()
            
        # Skip README and index files
        if filename.lower() in ('readme.md', 'index.md'):
            return None, None
        
        # Get category description from the first paragraph if possible
        first_section = content.split('##')[0].strip() if '##' in content else ''
        category_description = first_section[:200] + '...' if len(first_section) > 200 else first_section
        
        category = {
            'name': category_name,
            'description': category_description,
            'sort_order': sort_order
        }
        
        # Extract queries and their metadata
        queries = []
        
        # Find all sections starting with ## (h2 headers)
        sections = re.split(r'##\s+', content)
        
        # Skip the first section as it's usually the introduction
        if len(sections) > 1:
            for i, section in enumerate(sections[1:], 1):
                # Skip sections without SQL code blocks
                if '```sql' not in section:
                    continue
                
                # Extract the query title
                title_match = re.match(r'(.*?)(?:\n|\r\n)', section)
                title = title_match.group(1).strip() if title_match else f"Query {i}"
                
                # Extract the SQL query
                query_match = QUERY_PATTERN.search(section)
                if not query_match:
                    continue
                
                query = query_match.group(1).strip()
                
                # Extract purpose, impact, and action items
                purpose_match = PURPOSE_PATTERN.search(section)
                purpose = purpose_match.group(1).strip() if purpose_match else ""
                
                impact_match = IMPACT_PATTERN.search(section)
                impact = impact_match.group(1).strip() if impact_match else ""
                
                action_match = ACTION_PATTERN.search(section)
                action = action_match.group(1).strip() if action_match else ""
                
                # Generate a unique ID from the title
                query_id = title.lower().replace(' ', '_').replace('-', '_')
                query_id = re.sub(r'[^a-z0-9_]', '', query_id)
                
                # Add the query to the list
                queries.append({
                    'id': query_id,
                    'title': title,
                    'category': category_name,
                    'purpose': purpose,
                    'query': query,
                    'impact': impact,
                    'action': action
                })
        
        return category, queries
        
    except Exception as e:
        logger.error(f"Error parsing library file {file_path}: {e}")
        return None, None

def convert_library():
    """Convert all markdown library files to a single JSON file"""
    markdown_lib_path = get_markdown_library_path()
    json_file_path = get_json_library_path()
    
    # Check if markdown library exists
    if not markdown_lib_path.exists():
        logger.error(f"Markdown library directory not found at {markdown_lib_path}")
        return False
    
    # Initialize JSON structure
    library_data = {
        "version": "1.0",
        "lastUpdated": "2025-03-24",
        "description": "Consolidated AQL Library with predefined queries for Aparavi Data Suite",
        "categories": [],
        "queries": []
    }
    
    categories = {}
    
    # Process all markdown files
    for file_path in sorted(markdown_lib_path.glob('*.md')):
        # Skip README and index files
        if file_path.name.lower() in ('readme.md', 'index.md'):
            continue
        
        logger.info(f"Processing file: {file_path.name}")
        category, queries = parse_markdown_file(file_path)
        
        if category and queries:
            # Add unique category
            if category['name'] not in categories:
                categories[category['name']] = category
                
            # Add all queries from this file
            library_data["queries"].extend(queries)
    
    # Add all categories (sorted by sort_order)
    library_data["categories"] = sorted(
        [cat for cat in categories.values()],
        key=lambda x: x.get('sort_order', 999)
    )
    
    # Remove sort_order from categories (not needed in the final JSON)
    for cat in library_data["categories"]:
        if 'sort_order' in cat:
            del cat['sort_order']
    
    # Write the JSON file
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(library_data, f, indent=2)
        logger.info(f"Successfully created library JSON file at {json_file_path}")
        logger.info(f"Total queries converted: {len(library_data['queries'])}")
        logger.info(f"Total categories: {len(library_data['categories'])}")
        return True
    except Exception as e:
        logger.error(f"Error writing library JSON file: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting conversion of AQL library from markdown to JSON")
    success = convert_library()
    if success:
        logger.info("Conversion completed successfully")
        sys.exit(0)
    else:
        logger.error("Conversion failed")
        sys.exit(1)
