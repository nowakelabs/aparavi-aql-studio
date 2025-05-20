#!/usr/bin/env python3
"""
Dummy LLM Provider

This is a placeholder LLM provider that allows the application to start
even when no real LLM provider (OpenAI, Claude, Ollama) is configured.
It will return predefined responses directing users to configure a real provider.
"""

import logging
from .base import LLMProvider

logger = logging.getLogger(__name__)

class DummyLLM(LLMProvider):
    """
    A dummy LLM provider that doesn't actually call any API.
    Used to allow the application to start for configuration
    when no real LLM provider is available.
    """
    
    def __init__(self, config, db_store):
        """Initialize the dummy provider"""
        super().__init__(config, db_store)
        self.name = "dummy"
        self.model = "dummy-model"
        logger.warning("Using dummy LLM provider - chat functionality will be limited")
        
    def is_available(self):
        """Check if real providers are available, otherwise return True to allow app to start"""
        # Check if OpenAI API key is now available
        if self.db_store.get_credential('openai', 'api_key'):
            self.logger.info("OpenAI API key found, returning False to trigger provider switch")
            return False
            
        # Check if Claude API key is now available
        if self.db_store.get_credential('claude', 'api_key'):
            self.logger.info("Claude API key found, returning False to trigger provider switch")
            return False
            
        # No real provider available, so dummy stays active
        return True
        
    def get_completion(self, prompt, system_prompt=None, max_tokens=None, temperature=None):
        """Return a predefined response"""
        return {
            "text": "⚠️ No LLM provider is configured. Please go to Settings and configure an API key for OpenAI or Claude, or set up Ollama locally."
        }
        
    def get_chat_completion(self, messages, max_tokens=None, temperature=None):
        """Return a chat completion - tries real provider if available"""
        # Try to use a real provider if API keys are now available
        try:
            # Check for OpenAI first
            openai_key = self.db_store.get_credential('openai', 'api_key')
            if openai_key:
                from .base import get_llm_provider
                self.logger.info("Attempting to use OpenAI provider for chat")
                openai_provider = get_llm_provider('openai', self.config, self.db_store)
                if openai_provider.is_available():
                    return openai_provider.get_chat_completion(messages, max_tokens, temperature)
                    
            # Then try Claude
            claude_key = self.db_store.get_credential('claude', 'api_key')
            if claude_key:
                from .base import get_llm_provider
                self.logger.info("Attempting to use Claude provider for chat")
                claude_provider = get_llm_provider('claude', self.config, self.db_store)
                if claude_provider.is_available():
                    return claude_provider.get_chat_completion(messages, max_tokens, temperature)
        except Exception as e:
            self.logger.error(f"Error attempting to use real provider: {e}")
            
        # Fall back to dummy response if no real provider is available
        return {
            "text": "⚠️ No LLM provider is configured. Please go to Settings and configure an API key for OpenAI or Claude, or set up Ollama locally."
        }
        
    def translate_to_aql(self, question):
        """Implement required abstract method from LLMProvider - tries real provider if available"""
        # Try to use a real provider if API keys are now available
        try:
            # Check for OpenAI first
            openai_key = self.db_store.get_credential('openai', 'api_key')
            if openai_key:
                from .base import get_llm_provider
                self.logger.info("Attempting to use OpenAI provider for translation")
                openai_provider = get_llm_provider('openai', self.config, self.db_store)
                if openai_provider.is_available():
                    return openai_provider.translate_to_aql(question)
                    
            # Then try Claude
            claude_key = self.db_store.get_credential('claude', 'api_key')
            if claude_key:
                from .base import get_llm_provider
                self.logger.info("Attempting to use Claude provider for translation")
                claude_provider = get_llm_provider('claude', self.config, self.db_store)
                if claude_provider.is_available():
                    return claude_provider.translate_to_aql(question)
        except Exception as e:
            self.logger.error(f"Error attempting to use real provider: {e}")
            
        # Fall back to dummy response if no real provider is available
        return {
            "aql": "-- No LLM provider configured\n-- Please configure API keys in settings",
            "explanation": "No LLM provider is available. Please configure API keys in the settings page.",
            "visualization": None,
            "error": "No LLM provider configured"
        }
