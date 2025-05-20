#!/usr/bin/env python3
"""
Aparavi API Module

This module handles communication with the Aparavi Data Service API.
"""

import time
import base64
import logging
import urllib.parse
import json
import hashlib
import pandas as pd
import requests
from io import StringIO
import os
from datetime import datetime

# Optional DuckDB import
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

# Import utility modules
from modules.utils.query_logger import log_query_execution, log_query_error
from modules.utils.query_formatter import format_query_for_api
from modules.utils.query_preprocessor import preprocess_query

class AparaviAPI:
    """Client for interacting with the Aparavi Data Service API
    
    This class handles authentication, request formation, and query execution
    for the Aparavi Data Service API.
    """
    
    def __init__(self, server, endpoint, username, password, db_store=None):
        """Initialize the Aparavi API client
        
        Args:
            server (str): The Aparavi server address
            endpoint (str): The API endpoint path
            username (str): Username for API authentication
            password (str): Password for API authentication
            db_store (CredentialStore, optional): Database connection for caching
        """
        self.server = server
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.db_store = db_store
        self.logger = logging.getLogger('aparavi.api')
        
    def get_auth_header(self):
        """Generate basic authentication header for API requests
        
        Returns:
            dict: Authentication header for API requests
        """
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded_credentials}"}
    
    def test_connection(self, server=None):
        """Test the connection to the Aparavi server
        
        Args:
            server (str, optional): Override server address
            
        Returns:
            tuple: (success (bool), message (str), response_time (float))
        """
        start_time = time.time()
        try:
            # Use provided server or default
            target_server = server or self.server
            
            # Construct the API URL for a simple endpoint
            url = f"http://{target_server}{self.endpoint}"
            
            # Execute a simple request to test connectivity
            self.logger.info(f"Testing connection to: {url}")
            response = requests.get(
                url,
                headers=self.get_auth_header(),
                timeout=10
            )
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Check for successful response
            if response.status_code == 200:
                return (True, f"Connection successful (Response time: {response_time:.2f}s)", response_time)
            else:
                return (False, f"Error: HTTP {response.status_code} - {response.text}", response_time)
                
        except requests.exceptions.Timeout:
            return (False, "Connection timed out. Please check the server address and try again.", time.time() - start_time)
        except requests.exceptions.ConnectionError:
            return (False, "Connection failed. Please check the server address and ensure it's accessible.", time.time() - start_time)
        except Exception as e:
            return (False, f"Error testing connection: {str(e)}", time.time() - start_time)
    
    def execute_query(self, query, server=None, use_cache=True, db_store=None, format_type='csv'):
        """Execute an AQL query against the Aparavi Data Service
        
        Args:
            query (str): AQL query to execute
            server (str, optional): Override server address
            use_cache (bool): Whether to use query result caching
            db_store (CredentialStore, optional): Database connection for caching
            format_type (str, optional): Response format type ('csv' or 'json')
            
        Returns:
            tuple: (pandas DataFrame of results, execution time in seconds, error message if any, cache_hit)
        """
        start_time = time.time()
        error_message = None
        result_df = pd.DataFrame()
        cache_hit = False
        
        # Generate a user ID for logging
        user_id = "api_user"
        
        self.logger.info(f"Executing query: {query}")
        self.logger.info(f"Format type: {format_type}")
        
        # Log query execution start with the query logger
        try:
            # Log initial query execution (with empty result and 0 execution time)
            log_query_execution(user_id, query, {"totalRows": 0}, 0)
        except Exception as e:
            self.logger.warning(f"Failed to log query execution: {e}")
        
        # Try to get cached result if caching is enabled
        # If db_store isn't provided, use the one from initialization
        cache_store = db_store if db_store is not None else self.db_store
        if use_cache and cache_store is not None:
            cached_result = cache_store.get_cached_query_result(query)
            if cached_result is not None:
                self.logger.info(f"Using cached result for query: {query}")
                result_df = pd.DataFrame(cached_result['data'], columns=cached_result['columns'])
                execution_time = cached_result['executionTime']
                cache_hit = True
                return result_df, execution_time, error_message, cache_hit
        
        try:
            # Use provided server or default
            target_server = server or self.server
            
            # Construct the API URL
            url = f"http://{target_server}{self.endpoint}"
            
            # Add LIMIT clause if not already present, handling semicolons properly
            if "LIMIT" not in query.upper():
                # Check if query has semicolons (multiple statements)
                if ";" in query:
                    # Split by semicolons and process the last non-empty statement
                    statements = query.split(";")
                    
                    # Find the last non-empty statement (ignoring trailing semicolons)
                    last_statement_index = -1
                    for i in range(len(statements) - 1, -1, -1):
                        if statements[i].strip():
                            last_statement_index = i
                            break
                    
                    if last_statement_index >= 0:
                        # Add LIMIT only to the last statement
                        statements[last_statement_index] += " LIMIT 25000"
                        query = ";".join(statements)
                else:
                    # Simple query with no semicolons
                    query = f"{query} LIMIT 25000"
            
            # Preprocess query to substitute date template variables
            preprocessed_query = preprocess_query(query)
            self.logger.info(f"Preprocessed query with date variables: {preprocessed_query}")
            
            # Format query for API compatibility
            api_safe_query = self._format_query_for_api(preprocessed_query)
            
            # Prepare request parameters matching the exact format needed by Aparavi API
            params = {
                "select": api_safe_query,
                "options": json.dumps({
                    "format": format_type,
                    "stream": True
                })
            }
            encoded_params = urllib.parse.urlencode(params)
            request_url = f"{url}?{encoded_params}"
            
            # Execute the query
            self.logger.info(f"Executing query: {api_safe_query}")
            self.logger.info(f"Format type: {format_type}")
            
            # Log request details at info level for troubleshooting
            self.logger.info(f"Full API request URL: {request_url}")
            self.logger.info(f"Request headers: {self.get_auth_header()}")
            
            # Set a timeout to avoid hanging forever
            timeout = 30  # 30 seconds
            response = requests.get(
                request_url,
                headers=self.get_auth_header(),
                timeout=timeout
            )
            
            # Check for successful response
            if response.status_code == 200:
                # Log response details at INFO level for troubleshooting
                self.logger.info(f"Response status: {response.status_code}")
                self.logger.info(f"Response headers: {dict(response.headers)}")
                self.logger.debug(f"Response content length: {len(response.text)}")
                
                # Check if response is empty
                if not response.text.strip():
                    self.logger.warning("Received empty response from server")
                    error_message = "Server returned an empty response. No data available."
                else:
                    try:
                        # Parse CSV result into DataFrame
                        if format_type == 'csv':
                            result_df = pd.read_csv(StringIO(response.text))
                        elif format_type == 'json':
                            result_df = pd.json_normalize(response.json())
                        
                        # Log result details
                        self.logger.debug(f"Query returned {len(result_df)} rows, {len(result_df.columns)} columns")
                        
                        if result_df.empty:
                            self.logger.info("Query executed successfully but returned no matching data")
                        
                        # Store query results in cache if caching is enabled
                        if use_cache and cache_store is not None and time.time() - start_time > 0.1:
                            # Use the original query (not the API-safe version) for caching
                            # This ensures cache lookups work regardless of how the query is executed
                            success = cache_store.cache_query_result(query, {
                                'columns': result_df.columns.tolist(),
                                'data': result_df.to_dict('records'),
                                'executionTime': time.time() - start_time
                            })
                            self.logger.info(f"Query result cached: {success}")
                    except pd.errors.EmptyDataError:
                        self.logger.warning("Empty data returned or malformed CSV")
                        error_message = "Server returned an empty or malformed dataset"
                    except pd.errors.ParserError as pe:
                        self.logger.error(f"Error parsing CSV data: {pe}")
                        error_message = f"Error parsing server response: {pe}"
            else:
                error_message = f"Query failed with status code {response.status_code}: {response.text}"
                self.logger.error(error_message)
                
        except requests.exceptions.Timeout:
            error_message = "Query timed out. The server took too long to respond."
            self.logger.error(error_message)
        except requests.exceptions.ConnectionError:
            error_message = f"Connection error. Unable to connect to server at {target_server}."
            self.logger.error(error_message)
        except Exception as e:
            error_message = f"Error executing query: {str(e)}"
            self.logger.error(error_message)
            self.logger.exception("Detailed exception information:")
            
            # Log query error with the query logger
            try:
                log_query_error(user_id, query, str(e))
            except Exception as e:
                self.logger.warning(f"Failed to log query error: {e}")
            
        execution_time = time.time() - start_time
        
        # Log query result details
        try:
            # Determine status
            status = "SUCCESS" if error_message is None else "FAILURE"
            
            # Log final query execution with results
            log_query_execution(
                user_id, 
                query, 
                {
                    "totalRows": len(result_df),
                    "columnCount": len(result_df.columns) if not result_df.empty else 0,
                    "cacheHit": cache_hit,
                    "status": status
                },
                execution_time,
                error_message
            )
        except Exception as e:
            self.logger.warning(f"Failed to log query execution results: {e}")
            
        # Return results
        return result_df, execution_time, error_message, cache_hit
    
    def _format_query_for_api(self, query):
        """
        Format a query to be safe for API GET requests
        
        This handles special cases like double-quoted column identifiers
        that can cause problems when URL-encoded.
        
        Args:
            query (str): The original AQL query
            
        Returns:
            str: API-safe query with proper quoting
        """
        # Use the utility function from query_formatter module
        return format_query_for_api(query)
    
    def validate_query(self, query, server=None):
        """Validate an AQL query against the Aparavi Data Service
        
        Args:
            query (str): AQL query to validate
            server (str, optional): Override server address
            
        Returns:
            tuple: (is_valid, error_message, validation_details)
        """
        # Use provided server or default
        target_server = server or self.server
        
        # Construct the API URL
        url = f"http://{target_server}{self.endpoint}"
        
        # Preprocess query to substitute date template variables
        preprocessed_query = preprocess_query(query)
        self.logger.info(f"Preprocessing query for validation: {preprocessed_query}")
        
        # Prepare request parameters with validate option
        params = {
            "select": preprocessed_query,
            "options": json.dumps({
                "format": "csv",
                "stream": True,
                "validate": True
            })
        }
        encoded_params = urllib.parse.urlencode(params)
        request_url = f"{url}?{encoded_params}"
        
        try:
            # Log validation attempt
            self.logger.info(f"Validating query: {query}")
            
            # Set a timeout to avoid hanging forever
            timeout = 10  # 10 seconds
            response = requests.get(
                request_url,
                headers=self.get_auth_header(),
                timeout=timeout
            )
            
            # Log the raw response for debugging
            self.logger.debug(f"Validation response: {response.status_code} - {response.text[:1000]}")
            
            # Parse the JSON response
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("status") == "OK":
                # Query is valid
                self.logger.info("Query validation successful")
                return True, None, response_data
            else:
                # Query is invalid, extract error details
                error_message = response_data.get("message", "Unknown validation error")
                error_details = response_data.get("error", {})
                
                # Enhanced error logging
                self.logger.warning(f"Query validation failed: {error_message}")
                self.logger.warning(f"Error details: {json.dumps(error_details, default=str)}")
                
                # Check for specific AQL syntax issues - to help with debugging
                self._check_common_aql_issues(query, error_message, error_details)
                
                return False, error_message, error_details
                
        except Exception as e:
            error_message = f"Error during query validation: {str(e)}"
            self.logger.error(error_message)
            self.logger.exception("Exception details:")
            return False, error_message, {}
    
    def _check_common_aql_issues(self, query, error_message, error_details):
        """Check for common AQL syntax issues to help with debugging
        
        Args:
            query (str): The query being validated
            error_message (str): Error message from validation
            error_details (dict): Detailed error information
        """
        import re
        
        # Log detailed information about the query
        self.logger.debug("Analyzing query for common AQL syntax issues...")
        
        # Check for unquoted identifiers in GROUP BY
        if "GROUP BY" in query:
            group_clauses = re.findall(r'GROUP BY\s+(.*?)(?:ORDER BY|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
            if group_clauses:
                group_columns = [col.strip() for col in group_clauses[0].split(',')]
                unquoted = [col for col in group_columns if col and not (col.startswith('"') and col.endswith('"'))]
                if unquoted:
                    self.logger.warning(f"GROUP BY has unquoted columns: {', '.join(unquoted)}")
        
        # Check for unquoted identifiers in ORDER BY
        if "ORDER BY" in query:
            order_clauses = re.findall(r'ORDER BY\s+(.*?)(?:LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
            if order_clauses:
                order_columns = [col.strip() for col in order_clauses[0].split(',')]
                unquoted = [col for col in order_columns if col and not (col.startswith('"') and col.endswith('"'))]
                if unquoted:
                    self.logger.warning(f"ORDER BY has unquoted columns: {', '.join(unquoted)}")
        
        # Check for complex WHERE conditions without parentheses
        if "WHERE" in query:
            where_clauses = re.findall(r'WHERE\s+(.*?)(?:GROUP BY|ORDER BY|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
            if where_clauses:
                where_clause = where_clauses[0].strip()
                if (" AND " in where_clause or " OR " in where_clause) and not where_clause.startswith('('):
                    self.logger.warning(f"Complex WHERE condition missing parentheses: {where_clause}")
        
        # Check for classification field references
        if "classification" in query.lower():
            # Check if both classification fields are used when searching for PII
            if "PII" in query:
                if "classification LIKE" in query.lower() and "classifications LIKE" not in query.lower():
                    self.logger.warning("Query references 'classification' but not 'classifications' when searching for PII")
                if "classifications LIKE" in query.lower() and "classification LIKE" not in query.lower():
                    self.logger.warning("Query references 'classifications' but not 'classification' when searching for PII")
    
    def test_connection(self, db_store=None):
        """Test the connection to the Aparavi Data Service
        
        Args:
            db_store (CredentialStore, optional): Database connection for caching
            
        Returns:
            bool: True if connection is successful, False otherwise
        """
        # Use provided db_store or the one from initialization
        cache_store = db_store if db_store is not None else self.db_store
        try:
            # Simple test query with no caching
            test_query = "SELECT 1 AS test"
            df, _, error, _ = self.execute_query(test_query, use_cache=False, db_store=cache_store)
            
            if error is None and not df.empty:
                self.logger.info("Connection test successful")
                return True
                
            self.logger.warning(f"Connection test failed: {error}")
            return False
            
        except Exception as e:
            self.logger.exception("Connection test failed with exception")
            return False
            
    def update_credentials(self, server, endpoint, username, password):
        """Update API client credentials
        
        Args:
            server (str): The Aparavi server address
            endpoint (str): The API endpoint path
            username (str): Username for API authentication
            password (str): Password for API authentication
        """
        self.server = server
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.logger.info("API credentials updated")
        
    def set_server(self, server):
        """Update the server address
        
        Args:
            server (str): The new Aparavi server address
        """
        self.server = server
        self.logger.info(f"API server updated to: {server}")
        
    def set_endpoint(self, endpoint):
        """Update the API endpoint path
        
        Args:
            endpoint (str): The new API endpoint path
        """
        self.endpoint = endpoint
        self.logger.info(f"API endpoint updated to: {endpoint}")
        
    def get_schema_metadata(self, db_store=None):
        """Get schema metadata from the Aparavi Data Service
        
        This method retrieves information about available tables and fields
        in the Aparavi Data Service to assist with query generation.
        
        Args:
            db_store (CredentialStore, optional): Database connection for caching
            
        Returns:
            dict: Schema metadata including tables and fields
        """
        # Use provided db_store or the one from initialization
        cache_store = db_store if db_store is not None else self.db_store
        schema = {
            "tables": [],
            "fields": {}
        }
        
        try:
            # Query for available tables
            tables_query = "SHOW TABLES"
            tables_df, _, error, _ = self.execute_query(tables_query, db_store=cache_store)
            
            if error is None and not tables_df.empty:
                # Process table list
                for _, row in tables_df.iterrows():
                    table_name = row['table_name'] if 'table_name' in row else row[0]
                    schema["tables"].append(table_name)
                    
                    # For each table, get field information
                    fields_query = f"DESCRIBE {table_name}"
                    fields_df, _, field_error, _ = self.execute_query(fields_query, db_store=cache_store)
                    
                    if field_error is None and not fields_df.empty:
                        schema["fields"][table_name] = []
                        for _, field_row in fields_df.iterrows():
                            field_name = field_row['column_name'] if 'column_name' in field_row else field_row[0]
                            field_type = field_row['column_type'] if 'column_type' in field_row else field_row[1]
                            
                            schema["fields"][table_name].append({
                                "name": field_name,
                                "type": field_type
                            })
            
            self.logger.info(f"Retrieved schema metadata for {len(schema['tables'])} tables")
            return schema
            
        except Exception as e:
            self.logger.exception("Failed to retrieve schema metadata")
            return schema