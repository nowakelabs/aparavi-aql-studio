#!/usr/bin/env python3
"""
Configuration settings for the Aparavi Query Assistant

This file contains all configurable settings for the application.
Settings can be overridden by environment variables or via the settings page.
"""

# Web server configuration
HOST = "0.0.0.0"  # Listen on all interfaces (needed for Docker)
PORT = 8080  # Using port 8080
DEBUG = False  # Set to False in production

# Aparavi API configuration
DEFAULT_APARAVI_SERVER = "localhost"  # Default server address
DEFAULT_API_ENDPOINT = "/server/api/v3/database/query"  # API endpoint path
DEFAULT_USERNAME = "root"  # Default username for Aparavi API
DEFAULT_PASSWORD = "root"  # Default password for Aparavi API

# LLM Configuration
DEFAULT_LLM_PROVIDER = "auto"  # Auto will try OpenAI first, then Ollama
OLLAMA_BASE_URL = "http://localhost:11434"  # Ollama API base URL
OLLAMA_MODEL = "tinyllama"  # Ollama model to use (e.g., llama2, mistral, gemma, etc.)

# OpenAI Configuration
# Note: API key should be stored in the database, not here
OPENAI_MODEL = "gpt-3.5-turbo"  # OpenAI model to use (e.g., gpt-3.5-turbo, gpt-4)
OPENAI_API_BASE = "https://api.openai.com/v1"  # OpenAI API base URL
OPENAI_MAX_TOKENS = 4096  # Maximum tokens for completion
OPENAI_TEMPERATURE = 0.1  # Temperature for generation (lower = more deterministic)

# Claude Configuration
# Note: API key should be stored in the database, not here
CLAUDE_MODEL = "claude-3-opus-20240229"  # Claude model to use (e.g., claude-3-opus, claude-3-sonnet)
CLAUDE_API_BASE = "https://api.anthropic.com/v1"  # Claude API base URL
CLAUDE_MAX_TOKENS = 4096  # Maximum tokens for completion
CLAUDE_TEMPERATURE = 0.1  # Temperature for generation (lower = more deterministic)

# Cache and Database Configuration
ENABLE_CACHE = False  # Cache LLM responses for improved performance
CACHE_EXPIRY = 86400  # Cache expiry time in seconds (24 hours)
LLM_CACHE_EXPIRY = 3600  # LLM response cache expiry in seconds (1 hour)
QUERY_RESULT_CACHE_EXPIRY = 600  # Query result cache expiry in seconds (10 minutes)

# DuckDB Configuration
DUCKDB_PATH = None  # None = use default path (~/.aparavi_query_assistant/aparavi_db.duckdb)
ENABLE_QUERY_HISTORY = True  # Store query history in database
MAX_QUERY_HISTORY = 100  # Maximum number of queries to store in history
ENABLE_USER_TEMPLATES = True  # Allow users to save query templates

# Security Configuration
ENABLE_AUTHENTICATION = False  # Require login for the web interface
SECRET_KEY = "change-this-in-production"  # Flask session secret key

# Query Execution Configuration
MAX_QUERY_TIMEOUT = 30  # Maximum query execution timeout in seconds
DEFAULT_QUERY_LIMIT = 1000  # Default row limit for queries if not specified
ENABLE_QUERY_OPTIMIZATION = True  # Apply automatic query optimization
ALLOW_DIRECT_QUERY_EXECUTION = True  # Allow executing user-provided AQL directly

# Logging Configuration
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "aparavi_assistant.log"  # Log file path
ENABLE_QUERY_LOGGING = True  # Log all executed queries

# UI Configuration
DARK_MODE_DEFAULT = False  # Default to dark mode in UI
CODE_SYNTAX_HIGHLIGHTING = True  # Enable syntax highlighting for queries
ENABLE_VISUALIZATIONS = True  # Enable query result visualizations