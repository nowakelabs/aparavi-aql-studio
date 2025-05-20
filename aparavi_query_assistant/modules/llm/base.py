#!/usr/bin/env python3
"""
LLM Provider Base Module

This module defines the base class and factory for LLM providers.
These providers translate natural language questions into AQL queries.
"""

import abc
import json
import logging
import os
import re
import html
import time
import random
import traceback
from datetime import datetime
from importlib import import_module
from typing import Dict, List, Any, Optional

from ..utils.prompts import SYSTEM_PROMPT
from ..utils.aql_validator import AQLValidator


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers
    
    This class defines the interface that all LLM providers must implement.
    Each LLM provider is responsible for translating natural language questions
    into AQL queries.
    """
    
    def __init__(self, config, db_store=None):
        """Initialize the LLM provider
        
        Args:
            config: Configuration module with LLM settings
            db_store: Optional database connection for caching responses
        """
        self.config = config
        self.db_store = db_store
        self.logger = logging.getLogger(f'aparavi.llm.{self.__class__.__name__.lower()}')
        self.provider_name = self.__class__.__name__.lower().replace('llm', '')
        
    @abc.abstractmethod
    def translate_to_aql(self, question):
        """Translate a natural language question into an AQL query
        
        Args:
            question (str): The natural language question to translate
            
        Returns:
            dict: JSON response with query, explanation
        """
        pass
    
    @abc.abstractmethod
    def is_available(self):
        """Check if the LLM provider is available and properly configured
        
        Returns:
            bool: True if available, False otherwise
        """
        pass
    
    def chat_completion(self, system_prompt, messages):
        """Generate a completion using the LLM provider's chat API
        
        Args:
            system_prompt (str): The system prompt to use
            messages (list): List of message objects with role and content
            
        Returns:
            str: Generated completion text
        """
        raise NotImplementedError(f"Provider {self.provider_name} does not implement chat_completion")
    
    def format_response(self, raw_response):
        """Format the LLM response into a standard structure
        
        Args:
            raw_response (str): Raw response from the LLM
            
        Returns:
            dict: Formatted response with query, explanation
        """
        try:
            # Try to parse the response as JSON
            if isinstance(raw_response, str):
                result = json.loads(raw_response)
            else:
                # Already a dict/object
                result = raw_response
                
            # Ensure all required fields are present
            required_fields = ['understanding', 'query', 'explanation']
            for field in required_fields:
                if field not in result:
                    result[field] = f"Missing {field} in LLM response"
            
            # Add provider information
            result['provider'] = self.provider_name
                    
            return result
            
        except Exception as e:
            # Handle case where response is not valid JSON
            self.logger.error(f"Failed to parse LLM response: {e}")
            return {
                'understanding': "Failed to parse LLM response",
                'query': raw_response[:1000] if isinstance(raw_response, str) else "Invalid response format",
                'explanation': f"Error: {str(e)}",
                'provider': self.provider_name
            }
    
    def fix_invalid_query(self, original_question, invalid_query, feedback):
        """Fix an invalid AQL query based on error feedback
        
        Args:
            original_question (str): The original natural language question
            invalid_query (str): The invalid AQL query
            feedback (dict): Error feedback from the validation process, containing:
                - error: The main error message
                - error_details: Detailed error information
            
        Returns:
            dict: A result object containing:
                - query: The fixed AQL query
                - explanation: Explanation of the fixes made
        """
        self.logger.info(f"Attempting to fix invalid query: {invalid_query}")
        self.logger.info(f"Error feedback: {feedback}")
        
        # Extract error information
        error_message = feedback.get('error', 'Unknown error')
        error_details = feedback.get('error_details', {})
        previous_attempts = feedback.get('previous_attempts', [])
        
        # Try automatic fixes first with the AQL validator
        try:
            validator = AQLValidator()
            fixed_query, explanation = validator.suggest_fixes(
                invalid_query, 
                error_message=error_message, 
                error_details=error_details
            )
            
            # If the validator made changes (not just returning the original query)
            if fixed_query != invalid_query:
                self.logger.info(f"Automatic AQL validation fixed the query: {fixed_query}")
                self.logger.info(f"Fix explanation: {explanation}")
                return {
                    'query': fixed_query,
                    'explanation': explanation
                }
        except Exception as e:
            self.logger.warning(f"Error in automatic AQL validation: {str(e)}")
        
        # If automatic validation failed or made no changes, fall back to LLM-based fix
        try:
            # Create a prompt for fixing the query
            system_prompt = """You are an expert in Aparavi Query Language (AQL). 
Fix the following invalid AQL query based on the error message. 
Keep these important AQL syntax requirements in mind:

1. AQL DOES NOT SUPPORT standard SQL date functions like YEAR(), MONTH(), DATE_ADD(), DATE_SUB() - these are invalid
2. For date extraction, use SUBSTRING() instead:
   - For year: SUBSTRING(createTime, 1, 4)
   - For month: SUBSTRING(createTime, 6, 2)
   - For day: SUBSTRING(createTime, 9, 2)
3. When using GROUP BY or ORDER BY, always use quoted column aliases with commas: `GROUP BY "Year", "Month"`
4. For complex WHERE conditions, use parentheses: `WHERE (condition1) OR (condition2)`
5. For date period comparisons, use CASE WHEN statements:
   SUM(CASE WHEN createTime >= '2024-12-13' AND createTime <= '2025-03-13' THEN size ELSE 0 END) AS "Current Period"
6. When searching for classifications, check both `classification` (primary) and `classifications` (array) columns
7. For array fields like 'classifications', use LIKE operator with wildcards: `classifications LIKE '%PII%'`
8. Only reference columns that exist in the database
9. Make minimal changes to fix the specific error

Your response should include only the fixed query, formatted exactly as it should be executed."""
            
            # Extract expected tokens if available
            expecting_tokens = []
            if isinstance(error_details, dict) and 'params' in error_details:
                params = error_details.get('params', {})
                context = params.get('context', [])
                token = params.get('token', '')
                error_name = params.get('errorName', '')
                expecting = params.get('expecting', [])
                
                if expecting:
                    expecting_tokens = expecting
            
            # Formulate a prompt message about the error with expected tokens
            prompt = f"""ORIGINAL QUESTION: {original_question}

INVALID QUERY:
{invalid_query}

ERROR MESSAGE:
{error_message}

ERROR DETAILS:
{json.dumps(error_details, indent=2) if isinstance(error_details, dict) else str(error_details)}"""

            # Add expected tokens if available
            if expecting_tokens:
                prompt += f"""

EXPECTED TOKENS AT ERROR POSITION:
{', '.join(expecting_tokens)}

The error occurred where the parser encountered '{token if 'token' in locals() else "unknown token"}' but was expecting one of the tokens listed above."""

            prompt += """

PREVIOUS ATTEMPTS:
{json.dumps(previous_attempts, indent=2) if isinstance(previous_attempts, list) else str(previous_attempts)}

Please fix this query by addressing the error. Return only the corrected query."""
            
            # This should be implemented by each provider - delegating to translate_to_aql with special parameters
            # Since it's abstract, we'll provide a generic implementation here that can be overridden
            # Each provider will use their own LLM to get a fixed query
            
            # In a real implementation, each provider would call their LLM with the appropriate prompts
            # Here we'll just return a placeholder result
            self.logger.warning("Using base implementation of fix_invalid_query - providers should override this")
            
            # Detect common errors and make simple fixes
            fixed_query = invalid_query
            
            # Column not found errors
            if "Column" in error_message and "was not found" in error_message:
                # Try to extract the problematic column
                import re
                column_match = re.search(r'Column "(.*?)" was not found', error_message)
                if column_match:
                    bad_column = column_match.group(1)
                    
                    # Check for common typos in classification fields
                    if "classif" in bad_column.lower():
                        if "classificat" in bad_column.lower() and "s" in bad_column.lower():
                            fixed_query = fixed_query.replace(bad_column, "classifications")
                        else:
                            fixed_query = fixed_query.replace(bad_column, "classification")
            
            # Syntax errors in GROUP BY or ORDER BY
            if "Syntax error" in error_message and ("GROUP BY" in error_message or "ORDER BY" in error_message):
                # Add quotes to column names in GROUP BY/ORDER BY clauses
                groups = re.findall(r'GROUP BY\s+(.*?)(?:LIMIT|ORDER BY|$)', fixed_query, re.IGNORECASE)
                for group in groups:
                    columns = [col.strip() for col in group.split(',')]
                    quoted_columns = [f'"{col}"' if not col.startswith('"') and not col.endswith('"') else col 
                                     for col in columns]
                    fixed_query = fixed_query.replace(f"GROUP BY {group}", f"GROUP BY {', '.join(quoted_columns)}")
                
                orders = re.findall(r'ORDER BY\s+(.*?)(?:LIMIT|$)', fixed_query, re.IGNORECASE)
                for order in orders:
                    columns = [col.strip() for col in order.split(',')]
                    quoted_columns = [f'"{col}"' if not col.startswith('"') and not col.endswith('"') else col 
                                     for col in columns]
                    fixed_query = fixed_query.replace(f"ORDER BY {order}", f"ORDER BY {', '.join(quoted_columns)}")
            
            # Add parentheses to complex WHERE conditions
            if "Syntax error" in error_message and "WHERE" in error_message:
                where_matches = re.findall(r'WHERE\s+(.*?)(?:GROUP BY|ORDER BY|LIMIT|$)', fixed_query, re.IGNORECASE)
                for where_clause in where_matches:
                    if ' AND ' in where_clause or ' OR ' in where_clause:
                        if not where_clause.startswith('('):
                            new_where = f"({where_clause})"
                            fixed_query = fixed_query.replace(f"WHERE {where_clause}", f"WHERE {new_where}")
            
            explanation = f"Fixed query based on error: {error_message}"
            
            if fixed_query == invalid_query:
                explanation = "Could not automatically fix the query. Please check the original error message."
            
            result = {
                'query': fixed_query,
                'explanation': explanation,
                'understanding': 'Query required validation fixes',
                'provider': self.provider_name
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to fix invalid query: {e}")
            return {
                'query': invalid_query,  # Return the original query
                'explanation': f"Failed to fix query: {str(e)}",
                'understanding': 'Error occurred during query fix attempt',
                'provider': self.provider_name
            }


def get_llm_provider(provider_name, config, db_store=None):
    """Factory function to get an instance of the specified LLM provider
    
    Args:
        provider_name (str): Name of the LLM provider to use
        config: Configuration module with LLM settings
        db_store: Optional database connection for credentials and caching
        
    Returns:
        LLMProvider: Instance of the specified LLM provider
        
    Raises:
        RuntimeError: If no provider is available or initialization fails
    """
    logger = logging.getLogger('aparavi.llm')
    
    # Normalize provider name to lowercase
    if provider_name:
        provider_name = provider_name.lower()
    
    # Special case for 'auto': try to find an available provider
    if provider_name == 'auto' or not provider_name:
        logger.info("Auto-selecting LLM provider")
        
        # Try providers in order of preference
        providers_to_try = ['openai', 'claude', 'ollama']
        
        for provider in providers_to_try:
            try:
                logger.info(f"Trying {provider}...")
                
                # Recursive call with specific provider
                instance = get_llm_provider(provider, config, db_store)
                
                if instance and instance.is_available():
                    logger.info(f"Selected {provider} as LLM provider")
                    return instance
                else:
                    logger.info(f"Provider {provider} is not available, trying next...")
                    
            except Exception as e:
                logger.warning(f"Error initializing {provider}: {e}")
                
        # If we get here, no provider was available
        logger.warning("No LLM provider is available - you will need to configure an API key in settings")
        # Return None - the application will need to handle this case
        return None
    
    # Specific provider requested
    try:
        if provider_name == 'openai':
            # Import and initialize OpenAI provider
            logger.info("Initializing OpenAI provider")
            from .openai import OpenAILLM
            return OpenAILLM(config, db_store)
            
        elif provider_name == 'claude':
            # Import and initialize Claude provider
            logger.info("Initializing Claude provider")
            from .claude import ClaudeLLM
            return ClaudeLLM(config, db_store)
            
        elif provider_name == 'ollama':
            # Import and initialize Ollama provider
            logger.info("Initializing Ollama provider")
            from .ollama import OllamaLLM
            return OllamaLLM(config, db_store)
            
        else:
            # Unknown provider
            logger.warning(f"Unknown LLM provider '{provider_name}', falling back to ollama")
            from .ollama import OllamaLLM
            return OllamaLLM(config, db_store)
            
    except ImportError as e:
        # Handle import errors (e.g., missing dependencies)
        if provider_name == 'openai':
            logger.warning(f"Failed to import OpenAI provider: {e}")
            logger.warning("Trying fallback provider...")
            return get_llm_provider('auto', config, db_store)
            
        elif provider_name == 'claude':
            logger.warning(f"Failed to import Claude provider: {e}")
            logger.warning("Trying fallback provider...")
            return get_llm_provider('auto', config, db_store)
            
        elif provider_name == 'ollama':
            logger.error(f"Failed to import Ollama provider: {e}")
            raise RuntimeError(f"Failed to initialize LLM providers. Please ensure either OpenAI, Claude or Ollama is properly configured.")
            
        else:
            logger.error(f"Failed to import LLM provider '{provider_name}': {e}")
            raise RuntimeError(f"Failed to initialize LLM provider. Error: {str(e)}")
            
    except Exception as e:
        # Handle other errors
        logger.exception(f"Failed to initialize LLM provider '{provider_name}': {e}")
        raise RuntimeError(f"Failed to initialize LLM provider. Error: {str(e)}")