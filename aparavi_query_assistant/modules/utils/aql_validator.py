#!/usr/bin/env python3
"""
AQL Query Validator and Auto-Fix Utility

This module provides centralized validation logic for AQL queries,
including automatic error detection and correction suggestions.
"""

import re
import logging
from typing import Dict, Tuple, List, Optional, Any, Union

# Configure logging
logger = logging.getLogger(__name__)

class AQLValidator:
    """AQL Query validator with automatic error detection and fix suggestions"""
    
    # Known AQL syntax limitations
    UNSUPPORTED_PATTERNS = [
        # Date functions
        (r'YEAR\s*\(\s*(\w+)\s*\)', r'SUBSTRING(\1, 1, 4)'),
        (r'MONTH\s*\(\s*(\w+)\s*\)', r'SUBSTRING(\1, 6, 2)'),
        (r'DAY\s*\(\s*(\w+)\s*\)', r'SUBSTRING(\1, 9, 2)'),
        # Other SQL functions not supported in AQL
        (r'DATE_ADD\s*\(', None),
        (r'DATE_SUB\s*\(', None),
        (r'INTERVAL', None),
        # Aggregate function issues
        (r'COUNT\s*\(\s*DISTINCT', None)
    ]
    
    # Column aliases pattern
    GROUP_BY_PATTERN = r'GROUP\s+BY\s+(.*?)(?:ORDER\s+BY|HAVING|$)'
    ORDER_BY_PATTERN = r'ORDER\s+BY\s+(.*?)(?:LIMIT|$)'
    
    def __init__(self):
        """Initialize the validator"""
        self.logger = logger
    
    def validate_query(self, query: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate AQL query and detect common syntax errors
        
        Args:
            query: The AQL query to validate
            
        Returns:
            Tuple containing:
            - Boolean indicating if the query has detectable issues
            - List of detected issues with suggestions for fixing
        """
        issues = []
        
        # Check for unsupported SQL functions
        for pattern, replacement in self.UNSUPPORTED_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                if replacement:
                    issue = {
                        "type": "unsupported_function",
                        "pattern": pattern,
                        "matches": matches,
                        "suggestion": f"Replace {pattern} with {replacement}"
                    }
                else:
                    issue = {
                        "type": "unsupported_function",
                        "pattern": pattern,
                        "matches": matches,
                        "suggestion": f"AQL does not support {pattern}"
                    }
                issues.append(issue)
        
        # Check for incorrect GROUP BY syntax (missing quotes around aliases)
        group_by_match = re.search(self.GROUP_BY_PATTERN, query, re.IGNORECASE | re.DOTALL)
        if group_by_match:
            group_by_columns = group_by_match.group(1).strip()
            # Check for aliased columns without proper quoting
            if re.search(r'(?:AS|as)\s+([^",\s]+)', group_by_columns):
                issues.append({
                    "type": "incorrect_group_by",
                    "suggestion": "In GROUP BY, use original column names, not aliases"
                })
        
        # Check for incorrect ORDER BY syntax (missing quotes around aliases)
        order_by_match = re.search(self.ORDER_BY_PATTERN, query, re.IGNORECASE | re.DOTALL)
        if order_by_match:
            order_by_columns = order_by_match.group(1).strip()
            # Check for unquoted column aliases
            if re.search(r'([^"\s,]+)(?:\s+(?:ASC|DESC))?', order_by_columns):
                # Check if these might be aliases without quotes
                if not all('"' in col for col in order_by_columns.split(',')):
                    issues.append({
                        "type": "incorrect_order_by",
                        "suggestion": "In ORDER BY, use quoted column aliases: ORDER BY \"Column\"" 
                    })
        
        # Check for missing default columns
        if not query.strip().upper().startswith("SET @@DEFAULT_COLUMNS"):
            issues.append({
                "type": "missing_default_columns",
                "suggestion": "Always start AQL queries with SET @@DEFAULT_COLUMNS="
            })
        
        return len(issues) == 0, issues
    
    def suggest_fixes(self, query: str, error_message: str = None, error_details: Dict = None) -> Tuple[str, str]:
        """
        Suggest fixes for common AQL syntax issues
        
        Args:
            query: The original AQL query with issues
            error_message: Optional error message from the API
            error_details: Optional error details from the API
            
        Returns:
            Tuple containing:
            - Fixed query or original if no automatic fix is possible
            - Explanation of changes made
        """
        fixed_query = query
        changes = []
        
        # Apply automatic fixes for known patterns
        for pattern, replacement in self.UNSUPPORTED_PATTERNS:
            if replacement:  # Only attempt to fix if we have a replacement
                # Count matches before replacing
                matches_count = len(re.findall(pattern, fixed_query, re.IGNORECASE))
                if matches_count > 0:
                    # Apply the fix
                    fixed_query = re.sub(pattern, replacement, fixed_query, flags=re.IGNORECASE)
                    changes.append(f"Replaced {matches_count} instances of {pattern} with {replacement}")
        
        # Fix column aliases in GROUP BY (if needed)
        group_by_match = re.search(self.GROUP_BY_PATTERN, fixed_query, re.IGNORECASE | re.DOTALL)
        if group_by_match:
            group_by_section = group_by_match.group(0)
            group_by_columns = group_by_match.group(1).strip()
            
            # Check for and replace any function calls in GROUP BY with their full expression
            # Example: Replace GROUP BY YEAR(date) with GROUP BY SUBSTRING(date, 1, 4)
            for pattern, replacement in self.UNSUPPORTED_PATTERNS:
                if replacement and re.search(pattern, group_by_columns, re.IGNORECASE):
                    new_group_by = re.sub(pattern, replacement, group_by_columns, flags=re.IGNORECASE)
                    fixed_query = fixed_query.replace(group_by_section, f"GROUP BY {new_group_by}")
                    changes.append(f"Updated GROUP BY clause with proper date extraction")
        
        # If column refs specified in error details, suggest correction
        if error_details and 'params' in error_details:
            params = error_details.get('params', {})
            token = params.get('token', '')
            expecting = params.get('expecting', [])
            
            # Check if the error is about an unrecognized column or function
            if token and expecting and any('column' in str(e).lower() for e in expecting):
                changes.append(f"The token '{token}' is not recognized. Expected column types: {', '.join(expecting)}")
        
        # Check if we actually made any changes
        if not changes:
            return query, "No automatic fixes could be applied"
        
        return fixed_query, "; ".join(changes)
