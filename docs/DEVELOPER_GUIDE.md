# Aparavi Query Assistant Developer Guide

This technical guide is designed for developers who need to quickly understand, troubleshoot, or extend the Aparavi Query Assistant. It provides in-depth information about the application architecture, key components, and common development challenges.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Components](#key-components)
3. [Database System](#database-system)
4. [LLM Integration](#llm-integration)
5. [AQL Query Requirements](#aql-query-requirements)
6. [Aparavi API Integration](#aparavi-api-integration)
7. [Advanced Troubleshooting](#advanced-troubleshooting)
8. [Development Workflow](#development-workflow)
9. [Testing](#testing)

## Architecture Overview

The Aparavi Query Assistant follows a modular Flask-based architecture with clear separation of concerns and a layered configuration system:

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│                   │     │                   │     │                   │
│  Web Interface    │────▶│  Core Application │────▶│  LLM Providers    │
│  (Flask Routes)   │     │  (Processing)     │     │  (Query Gen)      │
│                   │     │                   │     │                   │
└───────────────────┘     └───────────────────┘     └───────────────────┘
         │                         │                         │
         │                         │                         │
         ▼                         ▼                         ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│                   │     │                   │     │                   │
│  DuckDB Storage   │◀───▶│  Aparavi API      │◀───▶│  Visualization    │
│  (Credentials)    │     │  (Data Source)    │     │  (Reports)        │
│                   │     │                   │     │                   │
└───────────────────┘     └───────────────────┘     └───────────────────┘
```

The application uses a series of Flask blueprints for modularity and follows the factory pattern for application creation.

## Key Components

### 1. Entry Point (`app.py`)

The main entry point configures logging, initializes the database connection, and registers cleanup handlers for proper resource management:

- Creates a single global database connection
- Registers atexit handlers to properly close database connections
- Handles signal interrupts for graceful shutdown
- Passes the database connection to the Flask app factory

### 2. Flask Application Factory (`modules/core/app.py`)

This is where the Flask application is created and configured:

- Registers Flask blueprints for different sections of the application
- Sets up error handlers and context processors
- Initializes application extensions and middleware
- Configures session handling and security settings
- Loads server configuration from database on startup
- Creates API client with either default or database-stored server settings
- Detects available LLM providers and sets application flags accordingly

### 3. API Client (`modules/core/api.py`)

The API client handles all communication with the Aparavi Data Service:

- Manages authentication and session handling
- Provides methods for executing AQL queries
- Transforms raw API responses into usable data structures
- Handles error conditions and retries
- Manages server configuration via `set_server()` and `set_endpoint()` methods
- Supports dynamic updating of server address and credentials without restart

### 4. Database Module (`modules/db/database.py`)

The most critical component for credential management:

- Uses DuckDB as the underlying storage engine
- Implements a `CredentialStore` class for secure credential storage
- Uses Fernet symmetric encryption for protecting sensitive data
- Handles database locking and concurrent access issues

## Database System

The application uses DuckDB for storage, which is an in-process SQL OLAP database system. Our implementation focuses on secure credential storage and persistent configuration.

### Database Schema

The database contains several tables:

- `credentials`: Stores API keys and login credentials (Aparavi, OpenAI, Claude)
- `settings`: Application settings and user preferences, including:
  - `aparavi_server`: The configured Aparavi server address (defaults to localhost)
  - `api_endpoint`: The API endpoint path
  - `default_provider`: The default LLM provider to use
  - Other LLM-specific settings (temperature, max tokens, etc.)
- `query_history`: History of executed queries
- `query_cache`: Cache of query results with expiration
- `templates`: Saved query templates

### Connection Management

Database connections are carefully managed to prevent lock issues:

```python
# Connection initialization with automatic mode to prevent locks
conn = duckdb.connect(
    database=db_path, 
    read_only=read_only,
    access_mode='automatic'  # Handles locking gracefully
)
```

### Lock Management

The application implements several strategies to handle database locks:

1. **Graceful Fallback**: If the database is locked, it tries read-only mode first
2. **In-Memory Fallback**: If read-only fails, it falls back to in-memory mode
3. **Connection Cleanup**: Proper transaction completion and connection closure
4. **Signal Handling**: Ensures proper database cleanup on application shutdown

### Concurrency Issues

Common concurrency issues:

- **Problem**: "Could not set lock on file" error when multiple instances try to access the database
- **Solution**: The application handles this gracefully:
  - Detects when database is locked by another process
  - Falls back to in-memory mode if needed
  - Provides clear error messages in logs with the PID of the locking process
  - Properly closes connections on application exit

- **Problem**: Port 9000 already in use by another process
- **Solution**: The user can specify an alternate port using the `--port` command-line argument

## LLM Integration

The application supports multiple LLM providers through a unified interface.

### LLM Provider Interface

All LLM providers implement a common interface:

- `translate_to_aql(question)`: Translates natural language questions into AQL queries
- `is_available()`: Checks if the provider is properly configured and available
- `format_response(raw_response)`: Formats the raw LLM response into a standardized structure

### Provider-Specific Implementations

- `openai.py`: OpenAI GPT implementation
- `ollama.py`: Ollama implementation for local LLMs
- `mock.py`: Mock provider for testing

### Provider Selection Logic

The application uses a provider selection strategy defined in `modules/llm/base.py`:

1. When set to "auto", it tries providers in this order: OpenAI, Claude, Ollama, Mock
2. Each provider is tested with `is_available()` to check if it's properly configured
3. The first available provider is used
4. If no provider is available, the application will show a warning in the UI but still function with limited capabilities

The LLM provider availability is checked:
- During application initialization
- Each time the user loads the index page
- When the user updates settings

### OpenAI Integration

The OpenAI provider implementation:

1. **Configuration**: 
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `OPENAI_MODEL`: Model to use (default: gpt-3.5-turbo)
   - `OPENAI_MAX_TOKENS`: Maximum tokens for completion (default: 4096)
   - `OPENAI_TEMPERATURE`: Controls randomness (default: 0.1)

2. **Implementation Details**:
   - Uses the OpenAI API's chat completion endpoint
   - Sends a carefully crafted system prompt with AQL syntax guidance
   - Implements response caching to improve performance and reduce API costs
   - Handles error conditions gracefully

3. **Best Practices**:
   - Keep `OPENAI_TEMPERATURE` low (0.1-0.2) for deterministic query generation
   - Ensure proper error handling for API rate limits and token limits
   - Use caching for frequently asked questions

### Ollama Integration

The Ollama provider allows using local LLMs:

1. **Configuration**:
   - `OLLAMA_BASE_URL`: URL of Ollama server (default: http://localhost:11434)
   - `OLLAMA_MODEL`: Model to use (default: llama2)

2. **Implementation Details**:
   - Connects to a local or remote Ollama server
   - Supports various open-source models (llama2, mistral, etc.)
   - Provides fallback capability when cloud providers are unavailable

## AQL Query Requirements

The system enforces specific AQL syntax requirements to ensure valid queries:

1. **Column Aliases and Quotes**:
   - Column aliases must use double quotes: `fieldName as "Display Name"`
   - In ORDER BY clauses, use quoted column aliases: `ORDER BY "Year", "Month"`
   - In GROUP BY clauses, use original column names: `GROUP BY classification, extension`

2. **FROM Clause Usage**:
   - Standard AQL queries must NOT include a FROM clause (e.g., "FROM files")
   - FROM is only valid with the STORE function: `SELECT * FROM STORE('/path/to/data/')`
   - Aggregation queries should follow this pattern:
     ```sql
     SELECT column as "Alias", COUNT(column) as "Count" 
     WHERE (conditions) 
     GROUP BY column
     ORDER BY "Count" DESC
     ```

3. **Date Handling**:
   - Use placeholders for relative dates: `createTime >= '{LAST_30_DAYS}'`
   - These placeholders are replaced at runtime by the `date_utils.py` module
   - Supported placeholders include: `{TODAY}`, `{YESTERDAY}`, `{LAST_7_DAYS}`, `{LAST_30_DAYS}`, `{LAST_YEAR}`
   - Date extraction uses `YEAR()` and `MONTH()` functions

4. **Classification Handling**:
   - Queries for classified content must check both `classification` and `classifications` columns
   - Use proper array search syntax: `classifications LIKE '%PII%'`
   - Combine with OR and use parentheses: `(classifications LIKE '%PII%' OR classification = 'PII')`

5. **WHERE Conditions**:
   - Always add parentheses around complex conditions: `WHERE (condition1) OR (condition2)`

The system prompt (`modules/utils/prompts.py`) provides detailed guidelines and examples for LLMs to follow when generating queries.

## Aparavi API Integration

The application integrates with the Aparavi Data Service API to execute AQL queries and retrieve results.

### Authentication Flow

1. Application stores encrypted Aparavi credentials in DuckDB
2. When needed, credentials are decrypted and used to authenticate
3. Session tokens are managed and refreshed as needed

### Query Execution Flow

1. Natural language question is sent to LLM
2. LLM generates AQL query
3. AQL query is sent to Aparavi API
4. Results are processed and returned to the user

### Enhanced Query Validation Process

The application implements an advanced validation system for AQL queries:

1. **Initial Generation**: The natural language question is processed by the LLM to generate an initial AQL query
2. **Validation Step**: The generated query is validated against the Aparavi API
3. **Retry Mechanism**: If invalid, the system attempts to fix the query up to 5 times
4. **Learning from Failures**: Each retry provides feedback from previous attempts to the LLM
5. **Progressive UI Updates**: The interface shows detailed progress with status messages at each step:
   - "Understanding your question..."
   - "Generating AQL query from your question..."
   - "Validating generated query..."
   - "Attempt X of 5: Using AI to fix invalid query..."

The validation process uses the following components:

```python
# Feedback structure sent to LLM for learning
feedback = {
    "original_query": sanitized_query,
    "error": error_message,
    "error_details": error_details,
    "previous_attempts": previous_attempts  # List of previous fix attempts
}

# Previous attempts structure
previous_attempts = [
    {
        "attempt": retry_count,
        "query": fixed_query,
        "explanation": fix_explanation,
        "error": error_message
    },
    # More attempts...
]
```

This enhanced validation provides several benefits:
- Increased success rate for query generation
- Progressive learning from errors
- Transparent feedback to users
- Better error handling for complex queries

### Enhanced UI Feedback

The frontend provides detailed real-time feedback during query generation and validation:

1. **Progress Bar**: Visual indication of the validation process with percentage completed
2. **Status Messages**: Clear indications of the current processing state
3. **Attempt Counter**: Shows current retry attempt against maximum allowed (e.g., "Attempt 2 of 5")
4. **AJAX Implementation**: Uses asynchronous requests to update the UI without page reloads

The UI updates follow these stages:
1. "Understanding the Question" (10% progress)
2. "Generating AQL" (30% progress)
3. "Validating Query" (60% progress)
4. "Fixing Query" (60-90% progress, incremental with each attempt)
5. "Query Validation Complete" (100% progress)

This design ensures users always know what's happening with their query and provides transparency into the AI's efforts to generate and validate AQL queries.

### Result Processing

The application processes query results in several ways:

1. **Data Formatting**: Converts timestamps, file sizes, and other data types to human-readable formats
2. **Result Limiting**: Caps large result sets to avoid performance issues
3. **Insight Generation**: Sends results back to LLM for analysis and insight generation
4. **Visualization Preparation**: Formats data for chart rendering (if applicable)
5. **Raw Response Display**: Provides collapsible sections showing the raw API response for debugging

## Advanced Troubleshooting

### Database Lock Issues

Diagnosing database lock issues:

1. Check application logs for lock-related errors:
   ```
   Error connecting to database: IO Error: Could not set lock on file
   ```

2. Use process monitoring to find processes holding locks:
   ```bash
   lsof | grep aparavi_db.duckdb
   ```

3. If needed, force close database by removing lock files:
   ```bash
   rm ~/.aparavi_query_assistant/aparavi_db.duckdb.wal
   ```

### Connection Pool Exhaustion

If you see errors related to database connections not being released:

1. Check for proper use of connection closure in custom code
2. Make sure all error handlers properly close connections
3. Add additional logging to track connection lifecycle

### Memory Leaks

If the application consumes increasing amounts of memory:

1. Check for proper cleanup of large result sets
2. Ensure connections are being closed properly
3. Look for circular references in custom code

## Development Workflow

### Setting Up Development Environment

1. Clone the repository
2. Install dependencies
3. Use the `--in-memory` flag during development to avoid database lock issues
4. Use the `--debug` flag for detailed logging

### Adding New Features

When adding new features:

1. Identify the appropriate module for your feature
2. Follow existing patterns and coding standards
3. Ensure proper error handling and resource cleanup
4. Add appropriate logging
5. Update documentation

### Adding a New LLM Provider

To add a new LLM provider:

1. Create a new file in `modules/llm/`
2. Implement the provider interface
3. Register the provider in `modules/llm/__init__.py`
4. Update the settings UI to include the new provider

## Testing

The application includes several types of tests:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **End-to-End Tests**: Test the entire application flow

### Running Tests

```bash
# Run unit tests
pytest tests/unit

# Run with in-memory database
pytest tests/unit --database=:memory:

# Run integration tests
pytest tests/integration

# Run all tests
pytest
```

### Test Database

Tests use a separate in-memory database to avoid interfering with production data:

```python
@pytest.fixture
def db_store():
    # Create in-memory database for testing
    return CredentialStore(config, in_memory=True)
```

## Performance Optimization

### Caching Strategies

The application implements several caching strategies:

1. **LLM Response Caching**: Similar queries use cached responses
2. **API Result Caching**: Frequent queries use cached results
3. **Session Caching**: User sessions and authentication tokens are cached

### Query Optimization

For large result sets or complex queries:

1. Use pagination to fetch results in chunks
2. Apply filters on the server side rather than client side
3. Use appropriate indexing in custom database extensions
