#!/usr/bin/env python3
"""
Database Module for the Aparavi Query Assistant

Provides functionality for credential storage and database operations.
"""

import os
import json
import logging
import sqlite3
import duckdb
from typing import Dict, Any, Optional, List, Tuple
import hashlib

logger = logging.getLogger(__name__)

class CredentialStore:
    """
    Manages storage and retrieval of credentials and application settings.
    
    This class provides an interface to a DuckDB database for storing API keys,
    connection information, and other application data securely.
    """
    
    def __init__(self, config, db_path=None, in_memory=False):
        """
        Initialize the credential store.
        
        Args:
            config: Application configuration object
            db_path: Optional custom path to the database file
            in_memory: If True, use an in-memory database
        """
        self.config = config
        self.in_memory = in_memory
        
        if in_memory:
            logger.info("Using in-memory database")
            self.conn = duckdb.connect(database=':memory:')
        else:
            if db_path:
                self.db_path = db_path
            else:
                # Default path in user's home directory
                home_dir = os.path.expanduser("~")
                data_dir = os.path.join(home_dir, ".aparavi-query-assistant")
                
                # Create directory if it doesn't exist
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)
                
                self.db_path = os.path.join(data_dir, ".duckdb")
            
            logger.info(f"Using database at: {self.db_path}")
            
            try:
                # Using the supported parameters format for DuckDB
                self.conn = duckdb.connect(database=self.db_path)
            except Exception as e:
                logger.warning(f"Error connecting to database: {e}")
                # Fallback to in-memory if we can't connect to the file
                logger.warning("Falling back to in-memory database")
                self.conn = duckdb.connect(database=':memory:')
                self.in_memory = True
        
        # Initialize database schema
        self._init_schema()
    
    def _init_schema(self):
        """Create necessary tables if they don't exist"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY,
                provider VARCHAR NOT NULL,
                key_name VARCHAR NOT NULL,
                value VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, key_name)
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR PRIMARY KEY,
                value VARCHAR NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY,
                natural_language_query VARCHAR NOT NULL,
                aql_query VARCHAR NOT NULL,
                results_summary VARCHAR,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create query cache table - drop and recreate to ensure correct schema
        self.conn.execute("DROP TABLE IF EXISTS query_cache")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash VARCHAR PRIMARY KEY,
                question VARCHAR NOT NULL,
                query_text VARCHAR NOT NULL,
                explanation VARCHAR,
                llm_provider VARCHAR,
                result_data VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
    def _execute(self, query: str, params: Optional[List] = None) -> Any:
        """Execute a query with optional parameters.
        
        Args:
            query: SQL query to execute
            params: Optional list of parameters for the query
            
        Returns:
            Query result
        """
        try:
            if params:
                return self.conn.execute(query, params)
            return self.conn.execute(query)
        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            raise
            
    def store_credential(self, provider: str, key_name: str, value: str) -> bool:
        """
        Store a credential in the database.
        
        Args:
            provider: Service provider name (e.g., 'aparavi', 'openai')
            key_name: Name of the credential (e.g., 'api_key')
            value: Value of the credential
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if credential exists
            exists = self._execute("""
                SELECT COUNT(*) FROM credentials
                WHERE provider = $1 AND key_name = $2
            """, [provider, key_name]).fetchone()[0] > 0
            
            if exists:
                # Update existing credential
                self._execute("""
                    UPDATE credentials 
                    SET value = $1
                    WHERE provider = $2 AND key_name = $3
                """, [value, provider, key_name])
            else:
                # For new credential, get the next ID value
                next_id = 1
                max_id = self._execute("SELECT MAX(id) FROM credentials").fetchone()[0]
                if max_id is not None:
                    next_id = max_id + 1
                
                # Insert new credential with explicit ID
                self._execute("""
                    INSERT INTO credentials (id, provider, key_name, value)
                    VALUES ($1, $2, $3, $4)
                """, [next_id, provider, key_name, value])
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing credential: {e}")
            return False
    
    def get_credential(self, provider: str, key_name: str = None) -> Optional[str]:
        """
        Retrieve a credential from the database.
        
        Args:
            provider: Service provider name
            key_name: Name of the credential (optional if retrieving all for a provider)
            
        Returns:
            The credential value or None if not found
        """
        try:
            if key_name is None:
                # Return all credentials for this provider as a dict
                results = self._execute("""
                    SELECT key_name, value FROM credentials
                    WHERE provider = $1
                """, [provider]).fetchall()
                
                return {row[0]: row[1] for row in results} if results else None
            
            result = self._execute("""
                SELECT value FROM credentials
                WHERE provider = $1 AND key_name = $2
            """, [provider, key_name]).fetchone()
            
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error retrieving credential: {e}")
            return None
    
    def delete_credential(self, provider: str, key_name: str) -> bool:
        """
        Delete a credential from the database.
        
        Args:
            provider: Service provider name
            key_name: Name of the credential
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._execute("""
                DELETE FROM credentials
                WHERE provider = $1 AND key_name = $2
            """, [provider, key_name])
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting credential: {e}")
            return False
    
    def list_credentials(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all credentials, optionally filtered by provider.
        
        Args:
            provider: Optional service provider name to filter by
            
        Returns:
            List of credential dictionaries
        """
        try:
            query = "SELECT provider, key_name, created_at FROM credentials"
            params = []
            
            if provider:
                query += " WHERE provider = $1"
                params.append(provider)
            
            results = self._execute(query, params).fetchall()
            
            return [
                {
                    "provider": row[0],
                    "key_name": row[1],
                    "created_at": row[2]
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error listing credentials: {e}")
            return []
    
    def store_setting(self, key: str, value: Any) -> bool:
        """
        Store an application setting.
        
        Args:
            key: Setting name
            value: Setting value (will be JSON-serialized)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert to JSON if complex type
            if not isinstance(value, (str, int, float, bool, type(None))):
                value = json.dumps(value)
            else:
                value = str(value)
            
            self._execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
            """, [key, value])
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing setting: {e}")
            return False
    
    def get_setting(self, key: str, default=None) -> Any:
        """
        Retrieve an application setting.
        
        Args:
            key: Setting name
            default: Default value if setting not found
            
        Returns:
            The setting value or default if not found
        """
        try:
            result = self._execute("""
                SELECT value FROM settings
                WHERE key = $1
            """, [key]).fetchone()
            
            if not result:
                return default
            
            value = result[0]
            
            # Try to parse as JSON if it looks like it
            if value.startswith('{') or value.startswith('['):
                try:
                    return json.loads(value)
                except:
                    pass
            
            return value
        except Exception as e:
            logger.error(f"Error retrieving setting: {e}")
            return default
    
    def store_query_history(self, natural_language_query: str, aql_query: str, 
                           results_summary: Optional[str] = None) -> int:
        """
        Store a query in history.
        
        Args:
            natural_language_query: The original natural language query
            aql_query: The generated AQL query
            results_summary: Optional summary of query results
            
        Returns:
            int: ID of the stored query history entry or -1 if failed
        """
        try:
            result = self._execute("""
                INSERT INTO query_history (natural_language_query, aql_query, results_summary)
                VALUES ($1, $2, $3)
                RETURNING id
            """, [natural_language_query, aql_query, results_summary]).fetchone()
            
            self.conn.commit()
            return result[0] if result else -1
        except Exception as e:
            logger.error(f"Error storing query history: {e}")
            return -1
    
    def get_query_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent query history.
        
        Args:
            limit: Maximum number of entries to retrieve
            
        Returns:
            List of query history entries
        """
        try:
            results = self._execute("""
                SELECT id, natural_language_query, aql_query, results_summary, timestamp
                FROM query_history
                ORDER BY timestamp DESC
                LIMIT $1
            """, [limit]).fetchall()
            
            return [
                {
                    "id": row[0],
                    "natural_language_query": row[1],
                    "aql_query": row[2],
                    "results_summary": row[3],
                    "timestamp": row[4]
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error retrieving query history: {e}")
            return []
    
    def cache_query_result(self, query: str, result: Dict, expiry_minutes: int = 60) -> bool:
        """
        Cache a query result for future retrieval.
        
        Args:
            query: The query key to cache
            result: The query results to cache
            expiry_minutes: Time-to-live in minutes for the cache entry (default 60)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Cache has been disabled in config.py
        return True

    def get_cached_query_result(self, query: str) -> Optional[Dict]:
        """
        Retrieve cached query results if available and not expired.
        
        Args:
            query: The query key to lookup in cache
            
        Returns:
            Optional[Dict]: The cached results if available and not expired, otherwise None
        """
        # Cache has been disabled in config.py
        return None

    def get_query_history_from_cache(self, limit: int = 10) -> List[Dict]:
        """
        Retrieve history of queries from the cache.
        
        Args:
            limit: Maximum number of history items to return
            
        Returns:
            List[Dict]: List of query history objects
        """
        try:
            results = self._execute("""
                SELECT question, query_text, explanation, llm_provider, created_at
                FROM query_cache
                ORDER BY created_at DESC
                LIMIT $1
            """, [limit]).fetchall()
            
            return [
                {
                    'question': row[0],
                    'query': row[1],
                    'explanation': row[2],
                    'provider': row[3],
                    'timestamp': row[4]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving query history from cache: {e}")
            return []
    
    def clear_query_cache(self) -> bool:
        """
        Clear all cached query results.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._execute("DELETE FROM query_cache")
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error clearing query cache: {e}")
            return False
    
    def close(self):
        """Close the database connection"""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
