#!/usr/bin/env python3
"""
Quick script to fix all sanitize_query references in the codebase
"""

import os
import re

def fix_sanitize_query(file_path):
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Count instances before replacement
    matches = re.findall(r'sanitize_query\(([^)]+)\)', content)
    if not matches:
        print(f"No instances found in {file_path}")
        return 0
    
    count = len(matches)
    print(f"Found {count} instances in {file_path}")
    
    # Replace all instances of sanitize_query(x) with just x
    modified_content = re.sub(r'sanitize_query\(([^)]+)\)', r'\1', content)
    
    # Replace comment lines about sanitize_query
    modified_content = re.sub(r'# Sanitize the query.*\n', '# Note: sanitize_query function has been removed\n', modified_content)
    
    # Write the file back
    with open(file_path, 'w') as f:
        f.write(modified_content)
    
    return count

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    routes_path = os.path.join(base_dir, 'modules', 'core', 'routes.py')
    
    total_fixed = 0
    if os.path.exists(routes_path):
        fixed = fix_sanitize_query(routes_path)
        total_fixed += fixed
        print(f"Fixed {fixed} instances in routes.py")
    else:
        print(f"Could not find routes.py at {routes_path}")
    
    print(f"Total fixed: {total_fixed}")

if __name__ == "__main__":
    main()
