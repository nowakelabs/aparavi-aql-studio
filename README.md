# AQL Studio

A professional environment for crafting, managing, and executing Aparavi Query Language (AQL) queries with AI-powered natural language translation. AQL Studio provides both AI assistance and manual precision for data analysts and business users working with the Aparavi Data Service.

## Studio Features

- **Query Composer**: Ask questions in plain English and get professional AQL queries
- **Multiple AI Assistants**: Support for OpenAI GPT models, Claude AI, and Ollama with seamless automatic switching
- **Advanced Query Testing**: Sophisticated retry system with up to 5 attempts to fix invalid queries
- **Intelligent Optimization**: System learns from previous attempts to improve query quality
- **Real-time Progress**: Detailed feedback throughout the entire query generation process
- **Analysis History**: Track and revisit your previously executed queries with context
- **Performance Cache**: DuckDB-powered caching for faster query responses
- **Studio Templates**: Save and organize successful queries as templates for future use
- **Query Enhancement**: Automatic optimization of generated AQL queries for best performance
- **API Compatibility**: Intelligent handling of queries with different identifier formats
- **Visualization Tools**: Rich data visualizations for clearer query result interpretation
- **Secure Credential Management**: Encrypted storage for API keys and connection settings
- **Query Gallery**: Comprehensive collection of pre-defined AQL queries organized by category

## Studio Installation

### Prerequisites

- Python 3.8 or higher
- Access to an Aparavi Data Service instance
- For OpenAI AI Assistant: OpenAI API key (see "AI Assistant Configuration" section below)
- (Optional) For Ollama AI Assistant: Ollama installed locally or access to an Ollama server

### Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/nowakemc/AQL-AI.git
   cd AQL-AI
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure your studio preferences:
   - Edit `aparavi_query_assistant/config.py` to set your defaults
   - Or use command-line arguments when running the application
   - Or configure via the Studio Preferences page in the web interface

### Security Configuration

AQL Studio securely stores API keys, credentials, and user configuration in a DuckDB database located at `~/.aparavi-query-assistant/.duckdb`. This database is automatically created on first run. This includes:

- AI Assistant API keys (OpenAI, Claude, etc.)
- Data Connection details (server address, credentials)
- Studio preferences and user settings

The database ensures settings persist between sessions, so you only need to configure your connections and preferences once.

## Using AQL Studio

### Launching the Studio

Start AQL Studio with default settings:
```
cd aparavi_query_assistant
python3 app.py
```

With custom settings or flags:
```
python3 app.py --in-memory  # Run with in-memory database
```

```
python3 app.py --alternate-db /path/to/custom/database.duckdb  # Use alternate database path
```

```
python3 app.py --port 8081  # Use a different port than the default 8080
```

Note: If you encounter an error about port 8080 being in use, you can either specify a different port or terminate the existing process using that port.

### Configuration Options

The application is configured through multiple layers:

1. **Default settings** in `config.py` serve as fallbacks
2. **User-configured settings** stored in the database take precedence
3. **Command-line arguments** can override both for testing

Key configuration parameters include:

- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to bind to (default: 9000)
- `DEBUG`: Enable debug mode (default: True)
- `DEFAULT_APARAVI_SERVER`: Aparavi server address (default: localhost, configurable via settings)
- `DEFAULT_API_ENDPOINT`: Aparavi API endpoint (default: /server/api/v3/database/query)
- `DEFAULT_USERNAME`: Aparavi API username
- `DEFAULT_PASSWORD`: Aparavi API password
- `DEFAULT_LLM_PROVIDER`: LLM provider to use (openai, ollama, claude, or auto)
- `OPENAI_API_KEY`: OpenAI API key (set via settings page)
- `OPENAI_MODEL`: OpenAI model to use (gpt-3.5-turbo, gpt-4, etc.)
- `OPENAI_MAX_TOKENS`: Maximum tokens for OpenAI response
- `OPENAI_TEMPERATURE`: Temperature setting for OpenAI (0.0-1.0)
- `OLLAMA_BASE_URL`: URL for Ollama server
- `OLLAMA_MODEL`: Ollama model to use (llama2, mistral, etc.)
- `CLAUDE_API_KEY`: Claude API key (set via settings page)
- `CLAUDE_MODEL`: Claude model to use (claude-3-opus-20240229, etc.)
- `CLAUDE_MAX_TOKENS`: Maximum tokens for Claude response
- `CLAUDE_TEMPERATURE`: Temperature setting for Claude (0.0-1.0)
- `LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FILE`: Log file path
- `SECRET_KEY`: Secret key for Flask sessions and encryption

### Command Line Arguments

- `--in-memory`: Run with an in-memory database (useful for testing)
- `--alternate-db PATH`: Use an alternate database path for testing

### Using the Studio Interface

1. Open your browser and navigate to `http://localhost:9000` (or your configured host/port)
2. Enter your natural language question in the input field
3. Review the generated AQL query and explanation
4. Execute the query to see results
5. Save useful queries as templates for future use

### API Keys and Settings

To set up your LLM providers:

1. Navigate to the Settings page from the main menu
2. Configure your preferred LLM provider(s):

#### OpenAI Configuration

1. **Get an OpenAI API Key**:
   - Sign up for an account at [platform.openai.com](https://platform.openai.com)
   - Navigate to the [API keys section](https://platform.openai.com/api-keys)
   - Create a new API key and copy it
   - Note: API usage will incur charges based on your OpenAI account's plan

2. **Configure in the application**:
   - Enter your OpenAI API key in the Settings page
   - Select a model (recommended options below)
   - Set Max Tokens (4096 recommended for most use cases)
   - Adjust Temperature (0.1 recommended for AQL queries for deterministic results)

3. **Recommended Models**:
   - **GPT-3.5-Turbo**: More economical, good for most standard queries
   - **GPT-4**: Higher accuracy for complex queries, better understanding of database concepts
   - **GPT-4-Turbo**: Latest model with improved capabilities and bigger context window

#### Ollama Configuration

1. **Set up Ollama** (if using locally):
   - Install Ollama from [ollama.ai](https://ollama.ai)
   - Download your preferred models

2. **Configure in the application**:
   - Enter your Ollama server URL (default: http://localhost:11434)
   - Select a model from the available options

3. **Provider Selection**:
   - Choose your default provider (OpenAI recommended for highest accuracy)
   - Optionally set a fallback provider to use if the primary is unavailable

API keys are securely stored in an encrypted DuckDB database and are never exposed in plaintext or logs.

## Documentation

### User Guides

- **Basic Usage**: For basic usage instructions, refer to the [Usage](#usage) section above.
- **Example Queries**: A comprehensive collection of example queries is available in the [Example Questions](docs/example-questions.md) document.
- **Template System**: Learn how to create and use templates in the application's Templates page.

### Technical Documentation

- **API Endpoints**: The application provides several API endpoints for integration with other tools.
- **API Compatibility**: For information on API compatibility and query formatting, see the [API Compatibility Issues](#api-compatibility-issues) section.
- **Database Schema**: The application uses DuckDB for caching and key management.

## How It Works: AQL Query Generation System

The core functionality of the Aparavi Query Assistant relies on a sophisticated Natural Language to AQL query generation system. Here's how it works:

### 1. Query Generation Process

1. **User Input**: The process begins when a user submits a natural language question through the web interface.

2. **LLM Processing**: The question is sent to the configured LLM provider (OpenAI or Ollama) along with:
   - A detailed system prompt containing AQL syntax guidelines 
   - Current date/time for proper date handling
   - Comprehensive column references
   - Example queries demonstrating proper syntax

3. **AQL Generation**: The LLM generates a properly formatted AQL query following strict syntax requirements:
   - Starts with `SET @@DEFAULT_COLUMNS=` directive specifying required columns
   - Translates the natural language intent into proper AQL syntax
   - Applies date handling, filtering, and formatting according to AQL requirements

4. **Query Execution**: The generated AQL query is sent to the Aparavi Data Service API
   - Results are retrieved asynchronously
   - Data is processed and formatted for display
   - Visualizations are generated based on result type

### 2. Key AQL Syntax Requirements

The system enforces specific syntax requirements for AQL:

- **Column References**:
  - `SET @@DEFAULT_COLUMNS=` must contain only physical columns, never derived or computed values
  - Double quotes for column aliases: `fieldName as "Display Name"`
  - Only original column names in `GROUP BY` clauses (no aliases)
  - Quoted column aliases in `ORDER BY` clauses: `ORDER BY "Year", "Month"`

- **Date Handling**:
  - ISO date format: 'YYYY-MM-DD'
  - Explicit date literals for relative dates
  - Both lower and upper bounds in date ranges
  - `YEAR(createTime)` and `MONTH(createTime)` for time-based extraction

- **Complex Conditions**:
  - Parentheses around `WHERE` conditions: `WHERE (condition1) OR (condition2)`
  - Proper handling of array fields like `classifications`

### 3. Date Handling System

The application includes a sophisticated date handling system:

- **Current Date Inclusion**: Each question automatically includes the current date/time
- **Date Placeholder Substitution**: Supports various time period references:
  - `{LAST_30_DAYS}`: Replaced with date 30 days ago
  - `{LAST_YEAR}`: Replaced with date 1 year ago
  - `{LAST_WEEK}`: Replaced with date 7 days ago
  - `{TODAY}`: Replaced with current date

- **Date Range Handling**: Automatically adds appropriate date ranges based on query context

### 4. Classification Handling

Special handling is implemented for classification-related queries:

- **Dual Column Checking**: Always checks both `classification` (primary) and `classifications` (array) columns
- **Array Field Syntax**: Uses proper syntax for searching within array fields (`LIKE '%PII%'`)
- **Combined Conditions**: Combines conditions with OR and uses parentheses for clarity
- **Result Display**: Includes classifications in the SELECT clause for context

### 5. Complete Example Workflow

1. User asks: "Show me Word documents containing PII created in the last 30 days"

2. System processes this by:
   - Identifying the need for Microsoft Word extensions (docx, doc, docm, etc.)
   - Recognizing PII classification requirements
   - Adding date range for last 30 days
   - Generating a proper AQL query with all required syntax elements

3. Generated AQL query:
   ```sql
   SET @@DEFAULT_COLUMNS=parentPath,name,size,createTime,modifyTime,objectId,instanceId,classification,classifications;
   SELECT 
     parentPath as "File Path", 
     name as "File Name", 
     size as "Size", 
     createTime as "Creation Date",
     classification as "Primary Classification",
     classifications as "All Classifications"
   WHERE 
     (extension IN ('docx', 'doc', 'docm', 'dotx', 'dotm', 'dot') 
     AND (classifications LIKE '%PII%' OR classification = 'PII')
     AND createTime >= '2025-02-11' AND createTime <= '2025-03-12')
   ORDER BY
     modifyTime DESC
   ```

4. Query is executed and results are displayed with appropriate visualizations

## Project Structure

```
aparavi_query_assistant/
├── app.py              # Main entry point for the application
├── config.py          # Application configuration settings
├── modules/
│   ├── core/
│   │   ├── app.py     # Flask application creation and configuration
│   │   ├── api.py     # Aparavi Data Service API client
│   │   ├── routes.py  # Web routes and request handling
│   │   ├── callbacks.py  # Callback functions for data processing
│   │   └── layout.py  # UI layout components
│   ├── db/
│   │   └── database.py  # Secure credential and settings storage
│   ├── llm/
│   │   ├── base.py    # Base LLM provider interface
│   │   ├── openai.py  # OpenAI GPT integration
│   │   ├── ollama.py  # Ollama integration for local LLMs
│   │   └── mock.py    # Mock provider for testing
│   ├── reports/
│   │   ├── sunburst.py  # Subfolder hierarchy visualization
│   │   ├── creation_time.py  # File creation time analysis
│   │   ├── modify_time.py  # File modification time analysis
│   │   └── access_time.py  # File access time analysis
│   └── utils/
│       ├── helpers.py  # Common utility functions
│       └── prompts.py  # System prompts for LLM providers
├── static/
│   ├── css/           # Stylesheets
│   ├── js/            # JavaScript files
│   └── images/        # Image assets
└── templates/
    ├── base.html      # Base template
    ├── index.html     # Home page
    ├── query.html     # Query page
    ├── settings.html  # Settings page
    └── errors/        # Error pages
```

### Component Relationships

1. **Initialization Flow**
   - `app.py` initializes the database connection (`CredentialStore`) and creates the Flask application
   - `create_app()` sets up routes, LLM providers, and API clients

2. **Data Flow**
   - User submits a natural language query through the web interface
   - Query is sent to the chosen LLM provider (OpenAI/Ollama)
   - LLM generates AQL query using system prompts from `prompts.py`
   - Generated query is executed against Aparavi API
   - Results are processed, visualized, and returned to the user

3. **Security Flow**
   - API keys and credentials are stored encrypted in DuckDB
   - Encryption is handled by `database.py` using Fernet symmetric encryption
   - Keys are derived from the application's secret key

## Technical Implementation Details

### 1. LLM Integration

The application supports multiple LLM providers:

- **OpenAI Integration**:
  - Supports GPT-3.5-Turbo, GPT-4, GPT-4-Turbo
  - Configurable parameters (temperature, max_tokens)
  - Automatic retry mechanism for API failures

- **Ollama Integration**:
  - Support for locally hosted models (llama2, mistral, etc.)
  - Custom model configuration
  - Fallback mechanism to alternate providers

- **Prompt Engineering**:
  - Sophisticated system prompts with examples and guidelines
  - Context-aware query generation
  - Error detection and correction for common AQL syntax issues

### 2. Date Utils System

The `date_utils.py` module provides:

- Current date/time retrieval in proper format
- Time range calculations for relative dates
- Automatic date range addition to queries
- Support for date placeholder substitution

### 3. Security System

- **Credential Storage**:
  - Encrypted DuckDB database for API keys and settings
  - Fernet symmetric encryption
  - Secret key derivation for maximum security

- **API Security**:
  - No plaintext credentials in logs or UI
  - Token-based authentication for Aparavi API
  - Secure HTTPS communication

### 4. Caching System

- **Query Caching**:
  - DuckDB-powered cache for previous queries and results
  - Cache invalidation based on time and relevance
  - Memory-efficient storage for large result sets

- **Template System**:
  - User-savable query templates
  - Parameterized templates for reuse
  - Category-based template organization

### 5. Query Gallery System

- **Consolidated Query Collection**:
  - JSON-based storage for pre-defined AQL queries
  - Located at `data/aql_library.json`
  - Organized into business-focused collections
  - Easily extensible professional format

- **Gallery Structure**:
  - Each query includes ID, title, collection, purpose, impact, and action items
  - Collections with descriptive metadata
  - Direct analysis from gallery to results view
  - Documentation in `docs/query_gallery_format.md`

- **Conversion Utility**:
  - Tools for converting from markdown to JSON format
  - Streamlined process for adding new queries

## Troubleshooting Guide

### Database Connection Issues

**Symptoms**: Error messages about database locks or failed connections.

**Solutions**:
1. **Database Locks**: The application automatically attempts to use read-only mode when write locks exist, and falls back to in-memory mode if that fails.
   ```
   Error connecting to database: IO Error: Could not set lock on file "/Users/.../aparavi_db.duckdb"
   ```
   - Use the `--in-memory` flag to run completely in memory
   - Shut down other instances of the application that might be holding locks
   - Delete the database file if corruption is suspected: `rm ~/.aparavi_query_assistant/aparavi_db.duckdb`

2. **Database Corruption**: If the database becomes corrupted, you'll see errors like:
   ```
   Error initializing database tables: IO Error: Database file is corrupt
   ```
   - Delete the database file and restart the application

### API Key Management Issues

**Symptoms**: "Failed to initialize any LLM provider" or authentication errors.

**Solutions**:
1. **Missing API Keys**: 
   - Verify API keys are entered correctly in the settings page
   - Check that keys are being saved properly by viewing settings page again
   - Try running with the `--in-memory` flag and setting keys again

2. **Invalid API Keys**:
   - Ensure API keys are valid and have not expired
   - Check API provider dashboards for usage limits or restrictions

### LLM Provider Issues

**Symptoms**: Errors or timeouts when generating queries.

**Solutions**:
1. **Rate Limiting**:
   - LLM providers have rate limits that may cause request failures
   - The application will show relevant error messages
   - Consider switching to a different provider temporarily

2. **Network Issues**:
   - Ensure network connectivity to LLM provider APIs
   - Check firewall settings if in a corporate environment

3. **OpenAI Specific Issues**:
   - Check your [OpenAI usage dashboard](https://platform.openai.com/usage) for quota limitations
   - Verify that your billing information is up to date
   - For "token limit exceeded" errors, try reducing the max tokens setting
   - For complex queries, consider using models with larger context windows (like GPT-4-Turbo)

4. **Ollama Specific Issues**:
   - Ensure Ollama service is running (`ollama serve`)
   - Verify that models are downloaded (`ollama list`)
   - Check Ollama logs for any errors or resource constraints

### API Compatibility Issues

**Symptoms**: Queries work directly in the application but fail when accessed via API endpoints with syntax errors.

**Solutions**:
1. **Double-Quoted Identifiers in GET Requests**:
   - The application now automatically converts double-quoted column identifiers to backtick-quoted identifiers for API requests
   - This fixes issues where column names with spaces cause syntax errors in URL-encoded GET requests
   - Example transformation:
     ```sql
     -- Original query (works in UI):
     SELECT name AS "File Name" GROUP BY "File Name"
     
     -- API-compatible transformation (happens automatically):
     SELECT name AS `File Name` GROUP BY `File Name`
     ```

2. **Alternative Manual Solution**:
   - If automatic transformation doesn't work for your case, avoid spaces in column aliases:
     ```sql
     -- Alternative syntax:
     SELECT name AS "File_Name" GROUP BY "File_Name"
     ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
