#!/usr/bin/env python3
"""
Script to add missing 'verified' and 'visualization' fields to AQL library queries.
This script will check all queries in the AQL library and add the missing fields
with a default value of false if they don't exist.
"""

import json
import os
import sys
from pathlib import Path

# Get the project root directory
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
project_root = script_dir.parent

# Path to the AQL library JSON file
AQL_LIBRARY_PATH = project_root / "aparavi_query_assistant" / "data" / "aql_library.json"

def add_missing_fields():
    """Add missing 'verified' and 'visualization' fields to all queries in the AQL library."""
    print(f"Reading AQL library from: {AQL_LIBRARY_PATH}")
    
    try:
        # Read the AQL library
        with open(AQL_LIBRARY_PATH, 'r') as file:
            aql_library = json.load(file)
    except Exception as e:
        print(f"Error reading AQL library: {e}")
        sys.exit(1)
    
    # Keep track of changes
    changes_made = False
    verified_added = 0
    visualization_added = 0
    
    # Process each query in the library
    for query in aql_library["queries"]:
        # Check if "verified" field is missing
        if "verified" not in query:
            query["verified"] = False
            verified_added += 1
            changes_made = True
            print(f"Added 'verified: false' to query: {query['id']} - {query['title']}")
        
        # Check if "visualization" field is missing
        if "visualization" not in query:
            query["visualization"] = False
            visualization_added += 1
            changes_made = True
            print(f"Added 'visualization: false' to query: {query['id']} - {query['title']}")
    
    # Write changes back to the file if any were made
    if changes_made:
        try:
            with open(AQL_LIBRARY_PATH, 'w') as file:
                json.dump(aql_library, file, indent=2)
            print(f"\nSummary of changes:")
            print(f"- Added 'verified: false' to {verified_added} queries")
            print(f"- Added 'visualization: false' to {visualization_added} queries")
            print(f"Changes successfully written to {AQL_LIBRARY_PATH}")
        except Exception as e:
            print(f"Error writing changes to AQL library: {e}")
            sys.exit(1)
    else:
        print("No missing fields found. All queries already have 'verified' and 'visualization' fields.")

if __name__ == "__main__":
    add_missing_fields()
