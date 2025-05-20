#!/usr/bin/env python3
"""
Example queries for the Aparavi Query Assistant

This module provides example queries for the web interface, categorized by their purpose.
Each example includes a title, description, and the natural language question
that would generate the corresponding AQL query.
"""

def get_home_examples():
    """Get example queries for the home page
    
    Returns:
        list: A list of example query dictionaries
    """
    return [
        {
            'title': 'Large Files',
            'description': 'Find large files that could be taking up unnecessary storage space.',
            'question': 'Show me all files larger than 100MB'
        },
        {
            'title': 'Recent Documents',
            'description': 'Analyze documents modified in the past 30 days.',
            'question': 'What documents were modified in the last 30 days?'
        },
        {
            'title': 'File Types',
            'description': 'Summarize storage usage by file type.',
            'question': 'Show me storage usage by file type'
        },
        {
            'title': 'Duplicate Files',
            'description': 'Identify potential duplicate files in the system.',
            'question': 'Find potential duplicate files in my system'
        },
        {
            'title': 'Sensitive Data',
            'description': 'Identify files containing sensitive information.',
            'question': 'Which files might contain sensitive personal information?'
        },
        {
            'title': 'Storage Trends',
            'description': 'Analyze how storage usage has changed over time.',
            'question': 'How has my storage usage grown over the past year?'
        }
    ]

def get_file_examples():
    """Get file analysis example queries
    
    Returns:
        list: A list of file analysis example dictionaries
    """
    return [
        {
            'title': 'Large Files',
            'description': 'Find all files larger than 100MB to identify storage hogs.',
            'question': 'Show me all files larger than 100MB ordered by size descending'
        },
        {
            'title': 'Old Documents',
            'description': 'Find documents that have not been accessed in over a year.',
            'question': 'Find all documents not accessed in over 1 year'
        },
        {
            'title': 'File Types by Count',
            'description': 'Count files by their extension to understand data composition.',
            'question': 'Count how many files I have of each file type'
        },
        {
            'title': 'Recently Modified',
            'description': 'Track files modified in the past week for activity monitoring.',
            'question': 'What files were modified in the past 7 days?'
        },
        {
            'title': 'Extension Analysis',
            'description': 'Analyze total size used by each file extension.',
            'question': 'Show me the total size of files for each extension'
        },
        {
            'title': 'Owner Distribution',
            'description': 'See how files are distributed among owners.',
            'question': 'Show the distribution of files by owner'
        },
        {
            'title': 'Empty Files',
            'description': 'Find files with zero bytes that might be corrupt or placeholders.',
            'question': 'Find all empty files in the system'
        },
        {
            'title': 'Path Analysis',
            'description': 'Find files with extremely long path names that could cause issues.',
            'question': 'Find files with paths longer than 200 characters'
        }
    ]

def get_storage_examples():
    """Get storage optimization example queries
    
    Returns:
        list: A list of storage optimization example dictionaries
    """
    return [
        {
            'title': 'Duplicate Detection',
            'description': 'Find potential duplicate files based on name, size, and hash.',
            'question': 'Find potential duplicate files based on size and name'
        },
        {
            'title': 'Storage by Department',
            'description': 'Analyze storage usage patterns across different departments.',
            'question': 'Show me storage usage by department'
        },
        {
            'title': 'Orphaned Files',
            'description': 'Find files that don\'t belong to any active user.',
            'question': 'Identify orphaned files not owned by active users'
        },
        {
            'title': 'Archival Candidates',
            'description': 'Find files that haven\'t been accessed in years and could be archived.',
            'question': 'Find files that should be archived (not accessed in over 3 years)'
        },
        {
            'title': 'Temporary Files',
            'description': 'Find temporary files that could be cleaned up.',
            'question': 'Show all temporary files (.tmp, .temp) older than 30 days'
        },
        {
            'title': 'Storage Growth',
            'description': 'Analyze how storage usage has grown over time.',
            'question': 'Analyze how our storage usage has grown each month over the past year'
        },
        {
            'title': 'Deletion Candidates',
            'description': 'Find non-essential files that could be deleted to save space.',
            'question': 'Find large log files older than 90 days that could be deleted'
        }
    ]

def get_compliance_examples():
    """Get compliance and security example queries
    
    Returns:
        list: A list of compliance example dictionaries
    """
    return [
        {
            'title': 'PII Detection',
            'description': 'Find files that might contain personal identifiable information.',
            'question': 'Which files might contain PII or sensitive personal information?'
        },
        {
            'title': 'Retention Policy',
            'description': 'Check if files are being retained according to policy.',
            'question': 'Are there any financial documents older than 7 years that should be deleted per our retention policy?'
        },
        {
            'title': 'Unusual Access Patterns',
            'description': 'Detect files with unusual access patterns that might indicate security issues.',
            'question': 'Find files with unusual access patterns in the last 30 days'
        },
        {
            'title': 'Permission Analysis',
            'description': 'Analyze file permissions to identify security risks.',
            'question': 'Show files with world-writable permissions that pose a security risk'
        },
        {
            'title': 'Regulatory Files',
            'description': 'Find files that are subject to regulatory requirements.',
            'question': 'Find all files that might be subject to GDPR regulations'
        },
        {
            'title': 'Classification Verification',
            'description': 'Verify that files are properly classified according to policy.',
            'question': 'Are there any files with sensitive content that are not properly classified?'
        }
    ]

def get_advanced_examples():
    """Get advanced example queries
    
    Returns:
        list: A list of advanced example dictionaries
    """
    return [
        {
            'title': 'Complex File Search',
            'description': 'Find specific file types with multiple constraints.',
            'question': 'Find PDF files larger than 10MB that contain "confidential" in their content and were modified in the last 90 days'
        },
        {
            'title': 'Storage Anomalies',
            'description': 'Detect anomalies in storage patterns that might indicate issues.',
            'question': 'Identify storage anomalies where a user\'s storage has increased by more than 50% in the past month'
        },
        {
            'title': 'Content Analysis',
            'description': 'Analyze file content for specific patterns or keywords.',
            'question': 'Find all documents that mention "project alpha" in their content'
        },
        {
            'title': 'Cross-Repository Analysis',
            'description': 'Compare file statistics across different repositories.',
            'question': 'Compare storage usage patterns between our US and EU data repositories'
        },
        {
            'title': 'Time-Series Analysis',
            'description': 'Analyze trends in file creation and modification over time.',
            'question': 'Show me the trend of document creation by department over the past year by month'
        },
        {
            'title': 'User Behavior Analysis',
            'description': 'Analyze patterns in how users interact with files.',
            'question': 'Analyze which users are creating the most files and of what types'
        }
    ]
