# AQL Library Format

The AQL (Aparavi Query Language) Library is now stored in a consolidated JSON file located at `aparavi_query_assistant/data/aql_library.json`. This document explains the structure and how to manage queries in this format.

## File Structure

The AQL library JSON file follows this structure:

```json
{
  "version": "1.0",
  "lastUpdated": "YYYY-MM-DD",
  "description": "Description of the library",
  "categories": [
    {
      "name": "Category Name",
      "description": "Description of the category"
    },
    // More categories...
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
    },
    // More queries...
  ]
}
```

## Field Descriptions

### Top-level fields

- `version`: Version number of the library format
- `lastUpdated`: Date when the library was last updated (YYYY-MM-DD)
- `description`: General description of the library
- `categories`: Array of category objects
- `queries`: Array of query objects

### Category Object

- `name`: Name of the category (should match the `category` field in query objects)
- `description`: Description of the category

### Query Object

- `id`: Unique identifier for the query (lowercase with underscores)
- `title`: Display title for the query
- `category`: The category this query belongs to (must match a category name)
- `purpose`: Description of what the query is used for
- `query`: The actual AQL query string
- `impact`: Description of the business impact of this query
- `action`: Suggested action items based on query results

## Adding New Queries

To add a new query to the library:

1. Open the `aparavi_query_assistant/data/aql_library.json` file
2. Add your new query to the `queries` array with all required fields
3. If using a new category, add it to the `categories` array
4. Update the `lastUpdated` field with the current date

Example new query:

```json
{
  "id": "my_new_query",
  "title": "My New Query",
  "category": "Existing Category",
  "purpose": "This query finds...",
  "query": "SELECT * FROM ...",
  "impact": "Helps identify...",
  "action": "Review the results and..."
}
```

## Converting from Markdown

If you have queries in markdown format, you can use the conversion utility:

```bash
python3 utils/convert_md_to_json.py
```

This script will convert queries from the markdown files in the `aql_library` directory to the JSON format and save them in `aparavi_query_assistant/data/aql_library.json`.
