# Developer Guide: Working with the Query Gallery

This guide explains how to work with the consolidated Query Gallery in the AQL Studio application.

## Overview

The Query Gallery has been migrated from multiple markdown files to a single consolidated JSON file located at `aparavi_query_assistant/data/aql_library.json`. This makes it easier to maintain, extend, and integrate with the Studio environment.

## Gallery Structure

The Query Gallery is stored as a JSON file with the following structure:

```json
{
  "version": "1.0",
  "lastUpdated": "YYYY-MM-DD",
  "description": "Consolidated Query Gallery with predefined queries for Aparavi Data Suite",
  "categories": [
    {
      "name": "Category Name",
      "description": "Description of the category"
    }
  ],
  "queries": [
    {
      "id": "unique_query_id",
      "title": "Query Title",
      "category": "Category Name", 
      "purpose": "Purpose of the query",
      "query": "The actual AQL query",
      "impact": "Business impact of the query",
      "action": "Recommended action items"
    }
  ]
}
```

## Working with the Gallery in Code

### Loading Gallery Data

The gallery is managed through the `modules/utils/aql_library.py` module. To access the gallery data in your code:

```python
from modules.utils.aql_library import get_all_library_queries, get_library_categories, get_query_by_id

# Get all queries
all_queries = get_all_library_queries()

# Get all categories
categories = get_library_categories()

# Get a specific query by ID
query = get_query_by_id('duplicate_files')
```

### Adding New Queries Programmatically

To add new queries to the Query Gallery programmatically:

```python
from modules.utils.aql_library import load_library_data, save_library_data

# Load the current library data
library_data = load_library_data()

# Add a new query
new_query = {
    'id': 'new_query_id',
    'title': 'New Query Title',
    'category': 'Existing Category Name',
    'purpose': 'Purpose of the query',
    'query': 'SELECT * FROM ...',
    'impact': 'Business impact description',
    'action': 'Recommended actions'
}

# Add the query to the Gallery
library_data['queries'].append(new_query)

# Update the lastUpdated date
from datetime import datetime
library_data['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')

# Save the updated library
save_library_data(library_data)
```

### Adding a New Category

To add a new category:

```python
from modules.utils.aql_library import load_library_data, save_library_data

# Load the current library data
library_data = load_library_data()

# Add a new category
new_category = {
    'name': 'New Category',
    'description': 'Description of the new category'
}

# Add the category to the library
library_data['categories'].append(new_category)

# Update the lastUpdated date
from datetime import datetime
library_data['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')

# Save the updated library
save_library_data(library_data)
```

## Converting from Markdown to JSON

If you have existing markdown files in the old format (located in the `/aql_library` directory), you can convert them to the new JSON format using the conversion utility:

```bash
# Run from the aparavi_query_assistant directory
python3 utils/convert_md_to_json.py
```

This will:
1. Read all markdown files in the `/aql_library` directory
2. Extract queries, categories, and metadata
3. Generate a consolidated JSON file in `data/aql_library.json`

## Extending the Query Gallery

When adding new queries to the Gallery, make sure to:

1. Use unique IDs for each query (lowercase with underscores)
2. Provide all required fields (id, title, category, purpose, query)
3. Match the category name to an existing category in the `categories` array
4. Update the `lastUpdated` field with the current date

## Best Practices

1. **Query Formatting**:
   - Format SQL queries with proper indentation for readability
   - Use consistent capitalization for SQL keywords (e.g., SELECT, WHERE, GROUP BY)
   - Include comments for complex logic

2. **Documentation**:
   - Provide clear, concise descriptions in the purpose field
   - Document business impact to help users understand the value
   - Include specific action items based on query results

3. **Testing**:
   - Always test new queries before adding them to the Gallery
   - Verify that queries work with the target Aparavi API version
   - Check for common syntax errors and edge cases

4. **Maintenance**:
   - Periodically review and update queries for accuracy
   - Remove deprecated or non-functioning queries
   - Keep category descriptions up-to-date

## Direct Query Execution

Queries from the library can be executed directly without LLM translation. This is handled by the `/execute-aql` endpoint in the application, which:

1. Takes the raw AQL query from the library
2. Validates it directly with the Aparavi API
3. Executes the query if valid
4. Displays any validation errors if invalid

The gallery UI automatically uses this endpoint when a user clicks "Run Analysis" on a gallery query.
