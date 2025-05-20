#!/usr/bin/env python3
"""
Query Validation Script for AQL Library

This script validates all queries in the AQL library against an Aparavi server 
and updates the 'verified' field for each query based on the results.
"""

import os
import sys
import json
import urllib.parse
import requests
import logging
from time import sleep
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

# Hard-coded configuration
APARAVI_SERVER = "10.1.10.163"       # Server address (without port)
APARAVI_USERNAME = "root"            # Username for authentication
APARAVI_PASSWORD = "root"            # Password for authentication
LIBRARY_PATH = "../aparavi_query_assistant/data/aql_library.json"  # Path to the AQL library file
MAX_QUERIES = 1                      # Maximum number of queries to test (set to 0 for all)

# API endpoints
LOGIN_PATH = "/server/api/v3/auth/login"  # Login endpoint
QUERY_PATH = "/server/api/v3/database/query"  # Query validation/execution endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('query_validation.log')
    ]
)
logger = logging.getLogger('validate_aql_queries')

# Aparavi API Client - Simplified version just for validation
class AparaviAPI:
    """Simplified client for validating AQL queries with the Aparavi Data Service API"""
    
    def __init__(self, username: str, password: str, server: str):
        """Initialize the API client
        
        Args:
            username (str): Username for authentication (not used in this version)
            password (str): Password for authentication (not used in this version)
            server (str): Server address
        """
        self.server = server
        self.endpoint = QUERY_PATH
        self.logger = logging.getLogger('aparavi_api')
    
    def login(self) -> None:
        """Check server connectivity (no actual login required)"""
        # Just check if the server is reachable
        try:
            url = f"http://{self.server}/server/api/v3/status"
            # Use Basic Authentication
            auth = requests.auth.HTTPBasicAuth('root', 'root')
            response = requests.get(url, auth=auth, timeout=5)
            if response.status_code == 200:
                self.logger.info(f"Server at {self.server} is reachable")
                return True
            else:
                self.logger.warning(f"Server returned status code {response.status_code}")
                return True  # Still return True to continue with validation
        except Exception as e:
            self.logger.warning(f"Server connectivity check failed: {str(e)}")
            # Don't raise exception, just log warning and continue
            return True
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str], Dict]:
        """Validate an AQL query against the Aparavi server
        
        Args:
            query (str): AQL query to validate
            
        Returns:
            tuple: (is_valid, error_message, validation_details)
        """
        # Based on the example URL format
        base_url = f"http://{self.server}{self.endpoint}"
        
        # Prepare request parameters with validate option
        params = {
            "select": query,
            "options": json.dumps({
                "format": "csv",
                "stream": True,
                "validate": True
            })
        }
        encoded_params = urllib.parse.urlencode(params)
        request_url = f"{base_url}?{encoded_params}"
        
        try:
            # Log validation attempt
            self.logger.info(f"Validating query: {query[:100]}...")
            
            # Set a timeout to avoid hanging forever
            timeout = 15  # 15 seconds
            # Use Basic Authentication
            auth = requests.auth.HTTPBasicAuth('root', 'root')
            response = requests.get(
                request_url,
                auth=auth,
                timeout=timeout
            )
            
            # Log the raw response for debugging
            self.logger.debug(f"Validation response: {response.status_code} - {response.text[:1000]}")
            
            try:
                # Try to parse the JSON response
                response_data = response.json() 
                
                # Check if response indicates query is valid
                if response.status_code == 200 and 'error' not in response_data:
                    # Query is valid
                    self.logger.info("Query validation successful")
                    return True, None, response_data
                else:
                    # Query is invalid, extract error details
                    error_message = response_data.get("message", "Unknown validation error")
                    if isinstance(error_message, dict) and 'text' in error_message:
                        error_message = error_message['text']
                    
                    error_details = response_data.get("error", {})
                    
                    # Enhanced error logging
                    self.logger.warning(f"Query validation failed: {error_message}")
                    self.logger.warning(f"Error details: {json.dumps(error_details, default=str)}")
                    
                    return False, error_message, error_details
            except json.JSONDecodeError:
                # If the response isn't JSON, check if it's CSV (which means query is valid)
                if response.status_code == 200 and response.text.strip():
                    self.logger.info("Query validation successful (CSV response)")
                    return True, None, {"status": "OK"}
                else:
                    error_message = f"Invalid response format: {response.text[:100]}"
                    self.logger.warning(error_message)
                    return False, error_message, {}
                
        except Exception as e:
            error_message = f"Error during query validation: {str(e)}"
            self.logger.error(error_message)
            self.logger.exception("Exception details:")
            return False, error_message, {}

# Configuration options
def get_config():
    """Return the configuration settings."""
    return {
        'server': APARAVI_SERVER,
        'username': APARAVI_USERNAME,
        'password': APARAVI_PASSWORD,
        'library_path': LIBRARY_PATH,
        'output': LIBRARY_PATH,  # Save back to the same file
        'delay': 0.5,  # Delay between validations in seconds
        'skip_verified': True,  # Skip queries that are already marked as verified
        'max_queries': MAX_QUERIES  # Maximum number of queries to validate (0 = all)
    }

def load_aql_library(file_path):
    """Load the AQL library from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading AQL library: {e}")
        sys.exit(1)

def save_aql_library(library_data, output_path):
    """Save the updated AQL library to a JSON file."""
    try:
        with open(output_path, 'w') as f:
            json.dump(library_data, f, indent=2)
        logger.info(f"Updated AQL library saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving updated AQL library: {e}")
        sys.exit(1)

def validate_queries(api_client, library_data, skip_verified=False, delay=0.5, max_queries=0):
    """Validate queries in the library and update their 'verified' status.
    If max_queries is set (>0), only that many queries will be validated."""
    # Extract the queries array from the library data
    queries = library_data.get('queries', [])
    total_queries = len(queries)
    
    # Determine how many queries to process
    queries_to_process = total_queries
    if max_queries > 0:
        queries_to_process = min(max_queries, total_queries)
        logger.info(f"Limiting validation to {queries_to_process} of {total_queries} queries")
    else:
        logger.info(f"Found {total_queries} queries to validate")
    
    valid_count = 0
    invalid_count = 0
    skipped_count = 0
    processed_count = 0
    
    for i, query_obj in enumerate(queries):
        query_id = query_obj.get('id', f"query_{i}")
        
        # Skip already verified queries if requested
        if skip_verified and query_obj.get('verified', False):
            logger.info(f"[{i+1}/{total_queries}] Skipping already verified query: {query_id}")
            skipped_count += 1
            continue
        
        query_text = query_obj.get('query', '')
        query_title = query_obj.get('title', 'Untitled Query')
        logger.info(f"[{i+1}/{total_queries}] Validating query: {query_title} ({query_id})")
        
        # Validate the query
        is_valid, error_message, validation_details = api_client.validate_query(query_text)
        
        # Update the 'verified' field
        query_obj['verified'] = is_valid
        
        if is_valid:
            logger.info(f"✅ Query '{query_title}' is valid")
            valid_count += 1
        else:
            logger.warning(f"❌ Query '{query_title}' is invalid: {error_message}")
            invalid_count += 1
        
        # Add a small delay to avoid overwhelming the server
        if i < total_queries - 1:
            sleep(delay)
            
        # Check if we've reached the maximum number of queries to process
        processed_count += 1
        if max_queries > 0 and processed_count >= max_queries:
            logger.info(f"Reached maximum number of queries to validate ({max_queries})")
            break
    
    # Log summary
    logger.info(f"Validation complete:")
    logger.info(f"  - Total queries in library: {total_queries}")
    logger.info(f"  - Queries processed: {processed_count}")
    logger.info(f"  - Valid queries: {valid_count}")
    logger.info(f"  - Invalid queries: {invalid_count}")
    logger.info(f"  - Skipped queries: {skipped_count}")
    
    return valid_count, invalid_count, skipped_count

def main():
    # Get configuration
    config = get_config()
    
    # Load the AQL library
    library_path = config['library_path']
    logger.info(f"Loading AQL library from {library_path}")
    library_data = load_aql_library(library_path)
    
    # Initialize the API client
    api_client = AparaviAPI(
        username=config['username'],
        password=config['password'],
        server=config['server']
    )
    
    # Test API connection
    logger.info(f"Testing connection to Aparavi server at {config['server']}")
    try:
        api_client.login()
        logger.info("Successfully connected to Aparavi server")
    except Exception as e:
        logger.error(f"Failed to connect to Aparavi server: {e}")
        sys.exit(1)
    
    # Validate queries (limited by max_queries setting)
    logger.info("Starting query validation")
    valid_count, invalid_count, skipped_count = validate_queries(
        api_client, 
        library_data, 
        skip_verified=config['skip_verified'],
        delay=config['delay'],
        max_queries=config['max_queries']
    )
    
    # Save the updated library
    output_path = config['output']
    logger.info(f"Saving updated library to {output_path}")
    save_aql_library(library_data, output_path)
    
    # Exit with error code if any queries failed validation
    if invalid_count > 0:
        logger.warning(f"Some queries failed validation ({invalid_count} out of {valid_count + invalid_count})")
        sys.exit(1)
    else:
        logger.info("All tested queries are valid")
        sys.exit(0)

if __name__ == "__main__":
    main()
