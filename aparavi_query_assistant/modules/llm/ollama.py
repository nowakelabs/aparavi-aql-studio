#!/usr/bin/env python3
"""
Ollama LLM Provider

This module implements the LLM provider for Ollama, an open-source
interface for running local LLMs.
"""

import json
import logging
import hashlib
import requests
import re
from datetime import datetime
from modules.llm.base import LLMProvider
from modules.utils.prompts import SYSTEM_PROMPT
from modules.utils.date_utils import add_date_range_to_query

class OllamaLLM(LLMProvider):
    """Ollama LLM provider for translating natural language to AQL
    
    This class implements the LLM provider for Ollama, allowing users
    to run local language models instead of relying on cloud APIs.
    """
    
    def __init__(self, config, db_store=None):
        """Initialize the Ollama LLM provider
        
        Args:
            config: Configuration module with Ollama settings
            db_store: Optional database connection for caching responses
        """
        super().__init__(config, db_store)
        self.base_url = getattr(config, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = getattr(config, 'OLLAMA_MODEL', 'llama3')
        self.logger = logging.getLogger('aparavi.llm.ollama')
        self.logger.info(f"Ollama provider initialized with model {self.model}")
        
    def translate_to_aql(self, question):
        """Translate a natural language question into an AQL query
        
        Args:
            question (str): The natural language question to translate
            
        Returns:
            dict: JSON response with query and explanation
        """
        if not self.is_available():
            self.logger.error("Ollama API is not available")
            return {
                'understanding': "Ollama API Error",
                'query': "SELECT 'Error: Ollama API not available' AS error",
                'explanation': "The Ollama API is not available. Please check if Ollama is running."
            }
        
        try:
            # Check cache first if db_store is available
            if self.db_store:
                try:
                    cache_key = f"ollama_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
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
            
            # Construct the prompt
            prompt = f"{SYSTEM_PROMPT}\n\nUser Question: {question_with_datetime}\n\nResponse:"
            
            # Call the Ollama API
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more deterministic results
                    "num_predict": 4096  # Maximum token output
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            content = response.json().get("response", "")
            self.logger.info(f"Ollama API response received, length: {len(content)}")
            
            # Try to parse the response as JSON
            try:
                # Look for JSON-formatted content in the response
                json_start = content.find('{')
                json_end = content.rfind('}')
                
                if json_start != -1 and json_end != -1:
                    json_content = content[json_start:json_end+1]
                    
                    # Try to parse the JSON, with fallback extraction if it fails
                    try:
                        result = json.loads(json_content)
                        
                        # Process the query to add date ranges
                        if 'query' in result:
                            result['query'] = add_date_range_to_query(result['query'], "year")
                        
                        # Cache the result if db_store is available
                        if self.db_store and hasattr(self.db_store, 'cache_query_result'):
                            try:
                                cache_key = f"ollama_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
                                self.db_store.cache_query_result(cache_key, result)
                            except Exception as e:
                                self.logger.warning(f"Error caching result: {e}")
                        
                        return result
                    except json.JSONDecodeError:
                        # JSON parsing failed, but we might still be able to extract the query
                        # Try to extract key elements using regex
                        self.logger.warning("JSON parsing failed, trying to extract query using regex")
                        query_pattern = r'(SELECT|WITH|SET)[\s\S]*?;'
                        explanation_pattern = r'"explanation":\s*"([^"]*)"'
                        understanding_pattern = r'"understanding":\s*"([^"]*)"'
                        
                        # Extract query
                        query_match = re.search(query_pattern, content, re.IGNORECASE)
                        query = query_match.group(0) if query_match else "SELECT 'Error: Could not parse query' AS error"
                        
                        # Extract explanation and understanding
                        explanation_match = re.search(explanation_pattern, content)
                        explanation = explanation_match.group(1) if explanation_match else "Extracted query from non-standard response"
                        
                        understanding_match = re.search(understanding_pattern, content)
                        understanding = understanding_match.group(1) if understanding_match else "Query extracted from response"
                        
                        # Create a properly structured result
                        result = {
                            'understanding': understanding,
                            'query': query,
                            'explanation': explanation
                        }
                        
                        # Add date range to the query
                        query = add_date_range_to_query(query, "year")
                        
                        # Cache this extracted result
                        if self.db_store and hasattr(self.db_store, 'cache_query_result'):
                            try:
                                cache_key = f"ollama_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
                                self.db_store.cache_query_result(cache_key, result)
                            except Exception as e:
                                self.logger.warning(f"Error caching result: {e}")
                        
                        return result
                else:
                    # No JSON found, try to extract just the query
                    self.logger.warning("No JSON found in Ollama response, looking for SQL query patterns")
                    
                    # Look for SQL-like patterns
                    query_pattern = r'(?:```sql|```)([\s\S]*?)(?:```|$)'
                    sql_match = re.search(query_pattern, content)
                    
                    # For analysis responses (which shouldn't be JSON), extract valuable insights
                    if 'analyze these query results' in content.lower():
                        self.logger.info("Analysis response detected, returning plain text")
                        # Clean up the response - remove any markdown code blocks and formatting
                        clean_content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                        clean_content = re.sub(r'```.*?$', '', clean_content, flags=re.DOTALL)
                        clean_content = clean_content.strip()
                        
                        # If it's too short, it might not be a proper analysis
                        if len(clean_content) < 10:
                            clean_content = "Query results show the requested information. Please refer to the data for details."
                        
                        # For responses about counts, ensure it mentions the count value
                        if 'count' in content.lower() and re.search(r'\b\d+\b', content):
                            # Extract the first number from the response
                            count_match = re.search(r'\b(\d+)\b', content)
                            count_value = count_match.group(1) if count_match else None
                            
                            if count_value and 'pdf' in content.lower():
                                clean_content = f"There are {count_value} PDF files in the system."
                            elif count_value:
                                clean_content = f"Count result: {count_value} items found."
                        
                        return {
                            'understanding': "Analysis of query results",
                            'query': "Analysis response",
                            'explanation': clean_content
                        }
                        
                    if sql_match:
                        # Found a SQL block, use it as the query
                        query = sql_match.group(1).strip()
                    else:
                        # Try a more general pattern for SELECT statements
                        query_pattern = r'(SELECT|WITH|SET)[\s\S]*?;'
                        query_match = re.search(query_pattern, content, re.IGNORECASE)
                        query = query_match.group(0) if query_match else content[:500]
                    
                    # Clean up the query
                    query = query.replace('```', '').strip()
                    
                    # Add date range to the query
                    query = add_date_range_to_query(query, "year")
                    
                    formatted_result = self.format_response({
                        'understanding': "Query extracted from Ollama response",
                        'query': query,
                        'explanation': "Query extracted from Ollama response"
                    })
                    
                    # Cache this response to avoid repeated failures
                    if self.db_store:
                        try:
                            cache_key = f"ollama_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
                            self.db_store.cache_query_result(cache_key, formatted_result, 1800)  # Cache for 30 minutes
                        except Exception as e:
                            self.logger.warning(f"Error caching response: {e}")
                    
                    return formatted_result
            except Exception as e:
                self.logger.error(f"Failed to parse Ollama response as JSON: {e}")
                formatted_result = self.format_response({
                    'understanding': "Failed to parse Ollama response",
                    'query': content[:500],
                    'explanation': f"Error parsing response: {str(e)}"
                })
                
                # Cache this response to avoid repeated failures
                if self.db_store:
                    try:
                        cache_key = f"ollama_{self.model}_{hashlib.md5(question.encode()).hexdigest()}"
                        self.db_store.cache_query_result(cache_key, formatted_result, 1800)  # Cache for 30 minutes
                    except Exception as e:
                        self.logger.warning(f"Error caching response: {e}")
                
                return formatted_result
                
        except Exception as e:
            self.logger.exception(f"Error calling Ollama API: {e}")
            return {
                'understanding': "Ollama API Error",
                'query': f"SELECT 'Error: {str(e)}' AS error",
                'explanation': f"Error calling Ollama API: {str(e)}"
            }
    
    def get_available_models(self):
        """Get a list of available models from Ollama
        
        Returns:
            list: List of available model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # Extract model names from the response
                models = [model['name'] for model in data.get('models', [])]
                return models
            else:
                self.logger.warning(f"Failed to get available models from Ollama: {response.status_code}")
                return []
        except Exception as e:
            self.logger.warning(f"Error getting available models from Ollama: {e}")
            return []
    
    def is_available(self):
        """Check if the Ollama API is available
        
        Returns:
            bool: True if available, False otherwise
        """
        try:
            # Try to ping the Ollama API
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                self.logger.warning(f"Ollama API health check failed: {response.status_code} - {response.text}")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error checking Ollama API health: {e}")
            return False
            
    def chat_completion(self, system_prompt, messages):
        """Generate a completion using the Ollama chat API
        
        Args:
            system_prompt (str): The system prompt to use
            messages (list): List of message objects with role and content
            
        Returns:
            str: Generated completion text
        """
        if not self.is_available():
            self.logger.error("Ollama API is not available")
            return "Error: Ollama API is not available. Please ensure the Ollama server is running."
            
        try:
            # Build the prompt from system and messages
            combined_prompt = system_prompt + "\n\n"
            
            # Add each message with its role
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                # Format based on role
                if role == "user":
                    combined_prompt += f"User: {content}\n"
                elif role == "assistant":
                    combined_prompt += f"Assistant: {content}\n"
                else:
                    combined_prompt += f"{role.capitalize()}: {content}\n"
            
            combined_prompt += "Assistant: "
            
            # Call the Ollama API
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "prompt": combined_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more deterministic results
                    "num_predict": 4096  # Maximum token output
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            content = response.json().get("response", "")
            self.logger.info(f"Ollama API chat completion received, length: {len(content)}")
            
            return content
                
        except Exception as e:
            self.logger.exception(f"Error calling Ollama API for chat completion: {e}")
            return f"Error calling Ollama API: {str(e)}"
    
    def generate_completion(self, prompt):
        """Generate a completion for a single prompt
        
        This method is used for simple prompts that don't need the full chat interface.
        It's primarily used for analysis of query results and other single-prompt tasks.
        
        Args:
            prompt (str): The prompt to send to the LLM
            
        Returns:
            str: Generated completion text
        """
        if not self.is_available():
            self.logger.error("Ollama API is not available")
            return "Error: Ollama API is not available. Please ensure the Ollama server is running."
            
        try:
            # Call the Ollama API
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more deterministic results
                    "num_predict": 4096  # Maximum token output
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status code {response.status_code}: {response.text}")
            
            # Extract and parse the response
            content = response.json().get("response", "")
            self.logger.info(f"Ollama API completion received, length: {len(content)}")
            
            return content
                
        except Exception as e:
            self.logger.exception(f"Error calling Ollama API for completion: {e}")
            return f"Error calling Ollama API: {str(e)}"
