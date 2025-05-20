#!/usr/bin/env python3
"""
Anthropic Claude LLM Provider

This module implements the LLM provider for Anthropic's Claude models,
allowing the use of Claude models for AQL query generation.
"""

import json
import logging
import hashlib
import requests
from datetime import datetime
from ..utils.date_utils import add_date_range_to_query
from .base import LLMProvider
from ..utils.prompts import SYSTEM_PROMPT
from ..utils.aql_validator import AQLValidator
import traceback

class ClaudeLLM(LLMProvider):
    """Claude LLM provider for translating natural language to AQL
    
    This class implements the LLM provider for Anthropic's Claude models,
    allowing users to leverage these models for AQL query generation.
    """
    
    def __init__(self, config, db_store=None):
        """Initialize the Claude LLM provider
        
        Args:
            config: Configuration module with Claude settings
            db_store: Optional database connection for caching responses
        """
        super().__init__(config, db_store)
        self.api_base = getattr(config, 'CLAUDE_API_BASE', 'https://api.anthropic.com/v1')
        self.model = getattr(config, 'CLAUDE_MODEL', 'claude-3-opus-20240229')
        self.max_tokens = getattr(config, 'CLAUDE_MAX_TOKENS', 4096)
        self.temperature = getattr(config, 'CLAUDE_TEMPERATURE', 0.1)
        self.logger = logging.getLogger('aparavi.llm.claude')
        self.logger.info(f"Claude provider initialized with model {self.model}")
        
    def _get_api_key(self):
        """Get the Anthropic API key from the database
        
        Returns:
            str: The API key if available, None otherwise
        """
        if not self.db_store:
            self.logger.error("No database connection available for retrieving API key")
            return None
            
        try:
            self.logger.info("Attempting to retrieve Claude API key from database")
            
            # Check if the database connection is active
            if not hasattr(self.db_store, 'get_credential'):
                self.logger.error("Database connection does not have get_credential method")
                return None
                
            api_key = self.db_store.get_credential('claude', 'api_key')
            
            if api_key:
                # Mask key for security in logs
                masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
                self.logger.info(f"Successfully retrieved Claude API key: {masked_key}")
                return api_key
            else:
                self.logger.error("Claude API key not found in database - please configure it in settings")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving Claude API key from database: {e}")
            # Log the full exception traceback for detailed debugging
            self.logger.error(traceback.format_exc())
            return None
        
    def translate_to_aql(self, question):
        """Translate a natural language question into an AQL query
        
        Args:
            question (str): The natural language question to translate
            
        Returns:
            dict: JSON response with query and explanation
        """
        # Get API key from database
        api_key = self._get_api_key()
        if not api_key:
            self.logger.error("Claude API key not found")
            return {
                'understanding': 'Unable to process your question',
                'query': '',
                'explanation': 'Claude API key not configured. Please check settings.',
                'visualization': None,
                'provider': self.provider_name
            }
            
        try:
            # Check if we have a cached response
            if self.db_store:
                try:
                    # Calculate cache key
                    cache_key = self.calculate_cache_key(question)
                    
                    # Check if the get_cached_query_result method exists
                    if hasattr(self.db_store, 'get_cached_query_result'):
                        cached_result = self.db_store.get_cached_query_result(cache_key)
                        if cached_result:
                            self.logger.info(f"Using cached response for question: {question[:50]}...")
                            return cached_result
                except Exception as e:
                    self.logger.warning(f"Error accessing cache: {e}")
            
            # Append current date/time to the question
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            question_with_datetime = f"{question}\n\nThe current date and time is: {current_datetime}"
            
            # Call the Claude API
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # Claude API format is different from OpenAI
            payload = {
                "model": self.model,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": question_with_datetime}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                f"{self.api_base}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            response_data = response.json()
            response_text = response_data.get("content", [{}])[0].get("text", "").strip()
            
            # Process the response to extract the structured data
            result = self.parse_response(response_text, question)
            
            # Validate the AQL syntax before returning
            if 'query' in result and result['query']:
                try:
                    # Perform automatic validation using AQLValidator
                    validator = AQLValidator()
                    is_valid, issues = validator.validate_query(result['query'])
                    
                    # If issues found, try to fix them
                    if not is_valid:
                        fixed_query, explanation = validator.suggest_fixes(result['query'])
                        if fixed_query != result['query']:
                            self.logger.info(f"AQL Validator automatically fixed query: {explanation}")
                            result['query'] = fixed_query
                            # Add note about automatic correction to explanation
                            if 'explanation' in result:
                                result['explanation'] += f"\n\nNote: Query was automatically optimized for AQL syntax ({explanation})."
                except Exception as e:
                    self.logger.warning(f"Error in AQL validation: {str(e)}")
            
            # Cache the result if caching is enabled
            if self.db_store and hasattr(self.db_store, 'cache_query_result') and 'query' in result and result['query']:
                try:
                    cache_key = self.calculate_cache_key(question)
                    self.db_store.cache_query_result(cache_key, result)
                    self.logger.info(f"Cached response for question: {question[:50]}...")
                except Exception as e:
                    self.logger.warning(f"Error caching result: {e}")
            
            return result
        except Exception as e:
            self.logger.exception(f"Error calling Claude API: {e}")
            return {
                'understanding': "Claude API Error",
                'query': f"SELECT 'Error: {str(e)}' AS error",
                'explanation': f"Error calling Claude API: {str(e)}"
            }
    
    def is_available(self):
        """Check if the Claude API is available and properly configured
        
        Returns:
            bool: True if API is accessible with the provided key, False otherwise
        """
        api_key = self._get_api_key()
        if not api_key:
            self.logger.warning("Claude API key not found in database")
            return False
        
        # Validate the API key by making a minimal API call
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # Make a minimal request just to check if the API key is valid
            payload = {
                "model": self.model,
                "system": "You are a helpful assistant.",
                "messages": [
                    {"role": "user", "content": "Test connection"}
                ],
                "max_tokens": 5
            }
            
            response = requests.post(
                f"{self.api_base}/messages",
                headers=headers,
                json=payload
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Error validating Claude API key: {e}")
            return False
    
    def chat_completion(self, system_prompt, messages):
        """Generate a completion using the Claude chat API
        
        Args:
            system_prompt (str): The system prompt to use
            messages (list): List of message objects with role and content
            
        Returns:
            str: Generated completion text
        """
        # Get API key from database
        api_key = self._get_api_key()
        if not api_key:
            self.logger.error("Claude API key not found in database")
            return "Error: Claude API key not configured in the database."
            
        try:
            # Call the Claude API
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # Claude has a different API format than OpenAI
            payload = {
                "model": self.model,
                "system": system_prompt,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                f"{self.api_base}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            response_data = response.json()
            content = response_data.get("content", [{}])[0].get("text", "").strip()
            self.logger.info(f"Claude API chat completion received, length: {len(content)}")
            
            return content
                
        except Exception as e:
            self.logger.exception(f"Error calling Claude API for chat completion: {e}")
            return f"Error calling Claude API: {str(e)}"
    
    def generate_completion(self, prompt):
        """Generate a completion for a single prompt
        
        This method is used for simple prompts that don't need the full chat interface.
        It's primarily used for analysis of query results and other single-prompt tasks.
        
        Args:
            prompt (str): The prompt to send to the LLM
            
        Returns:
            str: Generated completion text
        """
        # Get API key from database
        api_key = self._get_api_key()
        if not api_key:
            self.logger.error("Claude API key not found in database")
            return "Error: Claude API key not configured in the database."
            
        try:
            # Call the Claude API
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # Claude has a different API format than OpenAI
            payload = {
                "model": self.model,
                "system": "You are a helpful assistant.",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                f"{self.api_base}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            response_data = response.json()
            content = response_data.get("content", [{}])[0].get("text", "").strip()
            self.logger.info(f"Claude API completion received, length: {len(content)}")
            
            return content
                
        except Exception as e:
            self.logger.exception(f"Error calling Claude API for completion: {e}")
            return f"Error calling Claude API: {str(e)}"
    
    def fix_invalid_query(self, original_question, invalid_query, feedback):
        """Fix an invalid AQL query based on error feedback using Claude
        
        Args:
            original_question (str): The original natural language question
            invalid_query (str): The invalid AQL query
            feedback (dict): Error feedback from the validation process
            
        Returns:
            dict: A result object with the fixed query and explanation
        """
        # Get API key from database
        api_key = self._get_api_key()
        if not api_key:
            self.logger.error("Claude API key not found for fix_invalid_query")
            return {
                'query': invalid_query,
                'explanation': "Unable to fix query: Claude API key not configured"
            }
            
        try:
            # Extract error information
            error_message = feedback.get('error', 'Unknown error')
            error_details = feedback.get('error_details', {})
            
            # Create system prompt for fixing the query
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
                expecting = params.get('expecting', [])
                token = params.get('token', '')
                
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

The error occurred where the parser encountered '{token}' but was expecting one of the tokens listed above."""

            prompt += """

Please fix this query by addressing the error. Return only the corrected query with no other text."""
            
            # Call the Claude API
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Low temperature for more deterministic response
                "max_tokens": 2048
            }
            
            response = requests.post(
                f"{self.api_base}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API returned status code {response.status_code}: {response.text}")
            
            # Extract the response
            response_data = response.json()
            fixed_query = response_data.get("content", [{}])[0].get("text", "").strip()
            
            # Log the fixed query
            self.logger.info(f"Claude fixed query: {fixed_query}")
            
            return {
                'query': fixed_query,
                'explanation': f"Query fixed based on error: {error_message}"
            }
                
        except Exception as e:
            self.logger.exception(f"Error fixing query with Claude: {e}")
            return {
                'query': invalid_query,
                'explanation': f"Error fixing query: {str(e)}"
            }
