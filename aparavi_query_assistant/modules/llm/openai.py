#!/usr/bin/env python3
"""
OpenAI LLM Provider

This module implements the LLM provider for OpenAI's GPT models,
allowing the use of models like GPT-3.5 and GPT-4 for AQL query generation.
"""

import json
import logging
import hashlib
import requests
from datetime import datetime
from modules.llm.base import LLMProvider
from modules.utils.prompts import SYSTEM_PROMPT
from modules.utils.date_utils import add_date_range_to_query

class OpenAILLM(LLMProvider):
    """OpenAI LLM provider for translating natural language to AQL
    
    This class implements the LLM provider for OpenAI's models, allowing
    users to leverage cloud-based models for AQL query generation.
    """
    
    def __init__(self, config, db_store=None):
        """Initialize the OpenAI LLM provider
        
        Args:
            config: Configuration module with OpenAI settings
            db_store: Optional database connection for caching responses
        """
        super().__init__(config, db_store)
        self.api_base = getattr(config, 'OPENAI_API_BASE', 'https://api.openai.com/v1')
        self.model = getattr(config, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        self.max_tokens = getattr(config, 'OPENAI_MAX_TOKENS', 4096)
        self.temperature = getattr(config, 'OPENAI_TEMPERATURE', 0.1)
        self.logger = logging.getLogger('aparavi.llm.openai')
        self.logger.info(f"OpenAI provider initialized with model {self.model}")
        
    def _get_api_key(self):
        """Get the OpenAI API key from the database
        
        Returns:
            str: The API key if available, None otherwise
        """
        if not self.db_store:
            self.logger.error("No database connection available for retrieving API key")
            return None
            
        try:
            api_key = self.db_store.get_credential('openai', 'api_key')
            return api_key
        except Exception as e:
            self.logger.error(f"Error retrieving OpenAI API key from database: {e}")
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
            self.logger.error("OpenAI API key not found in database")
            return {
                'understanding': "OpenAI API Error",
                'query': "SELECT 'Error: OpenAI API key not found in database' AS error",
                'explanation': "The OpenAI API key is not configured in the database. Please add it through the settings page."
            }
            
        try:
            # Check cache first if db_store is available
            if self.db_store:
                try:
                    cache_key = f"openai_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
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
            
            # Call the OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question_with_datetime}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self.logger.info(f"OpenAI API response received, length: {len(content)}")
            
            # Try to parse the response as JSON
            try:
                # Look for JSON-formatted content in the response
                json_start = content.find('{')
                json_end = content.rfind('}')
                
                if json_start != -1 and json_end != -1:
                    json_content = content[json_start:json_end+1]
                    result = json.loads(json_content)
                    
                    # Post-process the query to add date ranges if needed
                    if 'query' in result:
                        result['query'] = add_date_range_to_query(result['query'], "year")
                    
                    # Cache the result if db_store is available
                    if self.db_store and hasattr(self.db_store, 'cache_query_result'):
                        try:
                            cache_key = f"openai_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
                            self.db_store.cache_query_result(cache_key, result)
                        except Exception as e:
                            self.logger.warning(f"Error caching result: {e}")
                    
                    return result
                else:
                    # No JSON found, return the raw response
                    self.logger.warning("No JSON found in OpenAI response")
                    formatted_result = self.format_response({
                        'understanding': "Unable to parse response",
                        'query': "",
                        'explanation': content[:500]  # Limit explanation to 500 chars
                    })
                    
                    # Cache this response to avoid repeated failures
                    if self.db_store:
                        try:
                            cache_key = f"openai_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
                            self.db_store.cache_query_result(cache_key, formatted_result, 1800)  # Cache for 30 minutes
                        except Exception as e:
                            self.logger.warning(f"Error caching response: {e}")
                    
                    return formatted_result
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                formatted_result = self.format_response({
                    'understanding': "Failed to parse OpenAI response",
                    'query': content[:500],
                    'explanation': f"Error parsing response: {str(e)}"
                })
                
                # Cache this response to avoid repeated failures
                if self.db_store:
                    try:
                        cache_key = f"openai_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
                        self.db_store.cache_query_result(cache_key, formatted_result, 1800)  # Cache for 30 minutes
                    except Exception as e:
                        self.logger.warning(f"Error caching response: {e}")
                
                return formatted_result
                
        except Exception as e:
            self.logger.exception(f"Error calling OpenAI API: {e}")
            return {
                'understanding': "OpenAI API Error",
                'query': f"SELECT 'Error: {str(e)}' AS error",
                'explanation': f"Error calling OpenAI API: {str(e)}"
            }
    
    def is_available(self):
        """Check if the OpenAI API is available and properly configured
        
        Returns:
            bool: True if API key is configured in database, False otherwise
        """
        api_key = self._get_api_key()
        if not api_key:
            self.logger.warning("OpenAI API key not found in database")
            return False
            
        return True
        
    def chat_completion(self, system_prompt, messages):
        """Generate a completion using the OpenAI chat API
        
        Args:
            system_prompt (str): The system prompt to use
            messages (list): List of message objects with role and content
            
        Returns:
            str: Generated completion text
        """
        # Get API key from database
        api_key = self._get_api_key()
        if not api_key:
            self.logger.error("OpenAI API key not found in database")
            return "Error: OpenAI API key not configured in the database."
            
        try:
            # Call the OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Prepare all messages including system prompt
            all_messages = [{"role": "system", "content": system_prompt}]
            
            # Add user messages
            for message in messages:
                all_messages.append(message)
                
            payload = {
                "model": self.model,
                "messages": all_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self.logger.info(f"OpenAI API chat completion received, length: {len(content)}")
            
            return content
                
        except Exception as e:
            self.logger.exception(f"Error calling OpenAI API for chat completion: {e}")
            return f"Error calling OpenAI API: {str(e)}"
    
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
            self.logger.error("OpenAI API key not found in database")
            return "Error: OpenAI API key not configured in the database."
            
        try:
            # Call the OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Prepare the message with the prompt
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self.logger.info(f"OpenAI API completion received, length: {len(content)}")
            
            return content
                
        except Exception as e:
            self.logger.exception(f"Error calling OpenAI API for completion: {e}")
            return f"Error calling OpenAI API: {str(e)}"
