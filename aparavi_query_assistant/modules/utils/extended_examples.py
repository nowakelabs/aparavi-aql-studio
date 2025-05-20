#!/usr/bin/env python3
"""
Extended example queries for the Aparavi Query Assistant

This module provides a comprehensive set of example queries for the web interface,
categorized by their purpose. Each example includes a title, description, and
the natural language question that would generate the corresponding AQL query.

These examples cover a wide range of use cases from basic file analysis to
advanced compliance and data governance scenarios.
"""

def get_file_analysis_examples():
    """Get comprehensive file analysis example queries
    
    Returns:
        list: A list of file analysis example dictionaries
    """
    return [
        # Basic File Analysis
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
        },
        {
            'title': 'Oldest Files',
            'description': 'Identify the oldest files in the system by creation date.',
            'question': 'What are the 50 oldest files in our system by creation date?'
        },
        {
            'title': 'File Distribution by Size',
            'description': 'Analyze how files are distributed across different size ranges.',
            'question': 'Show me the distribution of files across different size ranges (0-1MB, 1-10MB, 10-100MB, >100MB)'
        },
        {
            'title': 'Compressed Files',
            'description': 'Find all compressed archives that could be extracted to save space.',
            'question': 'Find all compressed files (zip, rar, tar.gz) larger than 50MB'
        },
        {
            'title': 'Hidden Files',
            'description': 'Identify hidden files that might be overlooked in manual cleanup.',
            'question': 'Find all hidden files and directories in the system'
        },
        {
            'title': 'Binary Executables',
            'description': 'Find all executable files to assess security risks.',
            'question': 'Show me all executable files (.exe, .bin, .sh) in the system'
        },
        {
            'title': 'Recent Images',
            'description': 'Find recently added image files that might be taking up space.',
            'question': 'Find all image files (jpg, png, gif) added in the last 30 days'
        },
        {
            'title': 'Inactive Projects',
            'description': 'Identify project folders with no recent activity.',
            'question': 'Find project directories with no file modifications in the past 6 months'
        }
    ]

def get_storage_optimization_examples():
    """Get comprehensive storage optimization example queries
    
    Returns:
        list: A list of storage optimization example dictionaries
    """
    return [
        # Storage Optimization
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
        },
        {
            'title': 'Large Directories',
            'description': 'Identify the directories consuming the most storage space.',
            'question': 'Which directories are consuming the most storage space?'
        },
        {
            'title': 'Redundant Backups',
            'description': 'Find backup files that might be redundant or outdated.',
            'question': 'Find redundant backup files with multiple versions'
        },
        {
            'title': 'Multiple Format Files',
            'description': 'Identify content stored in multiple formats that could be consolidated.',
            'question': 'Find cases where the same content exists in multiple formats (e.g., PDF and DOCX)'
        },
        {
            'title': 'File Type Storage Ratio',
            'description': 'Analyze which file types are consuming disproportionate amounts of storage.',
            'question': 'What percentage of our total storage is used by media files (images, videos, audio)?'
        },
        {
            'title': 'Cache Files',
            'description': 'Find cache files that could be safely deleted.',
            'question': 'Find all cache files and directories that could be safely deleted'
        },
        {
            'title': 'Unused Applications',
            'description': 'Find installed applications that haven\'t been used recently.',
            'question': 'Identify installed applications that haven\'t been used in over 6 months'
        },
        {
            'title': 'Migration Candidates',
            'description': 'Find files that are good candidates for migration to cheaper storage.',
            'question': 'Find files rarely accessed but still kept on high-performance storage'
        },
        {
            'title': 'Inefficient Storage',
            'description': 'Identify small files that would be more efficient if consolidated.',
            'question': 'Find directories with thousands of very small files that could be consolidated'
        }
    ]

def get_compliance_security_examples():
    """Get comprehensive compliance and security example queries
    
    Returns:
        list: A list of compliance and security example dictionaries
    """
    return [
        # Compliance & Security
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
        },
        {
            'title': 'Credit Card Data',
            'description': 'Find files that might contain credit card information.',
            'question': 'Which files might contain credit card numbers or financial data?'
        },
        {
            'title': 'HIPAA Compliance',
            'description': 'Identify files with potential health information for HIPAA compliance.',
            'question': 'Find files that may contain health information subject to HIPAA regulations'
        },
        {
            'title': 'Legal Hold Files',
            'description': 'Identify files that should be under legal hold.',
            'question': 'Show me all files related to the Smith lawsuit that should be under legal hold'
        },
        {
            'title': 'Unencrypted Sensitive Data',
            'description': 'Find sensitive files that are not properly encrypted.',
            'question': 'Find sensitive files that are not encrypted but should be'
        },
        {
            'title': 'Leaked Credentials',
            'description': 'Identify files that might contain passwords or access keys.',
            'question': 'Which files might contain passwords, API keys, or credentials?'
        },
        {
            'title': 'Export Controlled Data',
            'description': 'Find files that might be subject to export controls.',
            'question': 'Identify files that might contain export-controlled technical data'
        },
        {
            'title': 'Social Security Numbers',
            'description': 'Find files containing potential Social Security Numbers.',
            'question': 'Which documents might contain Social Security Numbers?'
        },
        {
            'title': 'Contract Expiration',
            'description': 'Identify contracts approaching expiration dates.',
            'question': 'Find all vendor contracts expiring in the next 90 days'
        },
        {
            'title': 'Data Sovereignty',
            'description': 'Ensure data is stored in appropriate geographical regions.',
            'question': 'Are there any EU citizen data files stored on non-EU servers?'
        }
    ]

def get_data_cleanup_examples():
    """Get data cleanup and management example queries
    
    Returns:
        list: A list of data cleanup example dictionaries
    """
    return [
        # Data Cleanup
        {
            'title': 'Redundant Files',
            'description': 'Find redundant copies of files across the system.',
            'question': 'Find redundant copies of the same file across different directories'
        },
        {
            'title': 'Old Log Files',
            'description': 'Identify outdated log files that can be archived or deleted.',
            'question': 'Find all log files older than 6 months that can be archived'
        },
        {
            'title': 'Corrupt Files',
            'description': 'Detect potentially corrupt files based on various indicators.',
            'question': 'Identify potentially corrupt files in the system'
        },
        {
            'title': 'Empty Directories',
            'description': 'Find empty directories that can be safely removed.',
            'question': 'Show me all empty directories in the system'
        },
        {
            'title': 'Historical Versions',
            'description': 'Find historical versions of files that could be archived.',
            'question': 'Show me historical versions of documents that can be archived'
        },
        {
            'title': 'Software Installation Files',
            'description': 'Find installation files that are no longer needed.',
            'question': 'Find all software installation files (.iso, .dmg, .exe) older than 1 year'
        },
        {
            'title': 'Inconsistent Naming',
            'description': 'Identify files with inconsistent naming conventions.',
            'question': 'Find files with inconsistent naming patterns compared to their peers'
        },
        {
            'title': 'Broken Links',
            'description': 'Find symbolic links or shortcuts that point to non-existent files.',
            'question': 'Identify all broken symbolic links or shortcuts in the system'
        },
        {
            'title': 'System Generated Files',
            'description': 'Find temporary or system-generated files that can be cleaned up.',
            'question': 'Find all system-generated temporary files that can be safely deleted'
        },
        {
            'title': 'Old User Accounts',
            'description': 'Identify files belonging to former employees or inactive users.',
            'question': 'Show files belonging to employees who have left the company'
        },
        {
            'title': 'Fragmented File Storage',
            'description': 'Find files that are causing storage fragmentation.',
            'question': 'Find small files scattered across the filesystem causing fragmentation'
        },
        {
            'title': 'Unneeded Metadata',
            'description': 'Identify files with unnecessary metadata that can be stripped.',
            'question': 'Find documents with excessive metadata that could be cleaned'
        },
        {
            'title': 'Abandoned Projects',
            'description': 'Identify project directories with no recent activity.',
            'question': 'Identify abandoned project directories with no activity in the last year'
        },
        {
            'title': 'Wrongly Placed Files',
            'description': 'Find files that don\'t belong in their current directories.',
            'question': 'Find misplaced files that don\'t match the content of their directories'
        },
        {
            'title': 'Mixed Content Types',
            'description': 'Identify directories with mixed content types that should be separated.',
            'question': 'Find directories containing mixed content types that should be reorganized'
        }
    ]

def get_user_activity_examples():
    """Get user activity and behavior example queries
    
    Returns:
        list: A list of user activity example dictionaries
    """
    return [
        # User Activity & Behavior
        {
            'title': 'Active Users',
            'description': 'Identify the most active users in the system.',
            'question': 'Who are the most active users based on file creation and modification?'
        },
        {
            'title': 'User Storage Trends',
            'description': 'Analyze how user storage consumption has changed over time.',
            'question': 'Show me how each user\'s storage usage has changed over the past year'
        },
        {
            'title': 'Collaboration Patterns',
            'description': 'Identify patterns in how users collaborate on files.',
            'question': 'What are the collaboration patterns between departments based on file access?'
        },
        {
            'title': 'Off-hours Activity',
            'description': 'Detect unusual activity outside of normal business hours.',
            'question': 'Find file activities occurring outside normal business hours (8am-6pm)'
        },
        {
            'title': 'Resource Hogs',
            'description': 'Identify users consuming disproportionate system resources.',
            'question': 'Which users are consuming the most storage resources?'
        },
        {
            'title': 'Inactive Users',
            'description': 'Find user accounts that have been inactive for an extended period.',
            'question': 'Which user accounts have been inactive for more than 90 days?'
        },
        {
            'title': 'Access Pattern Changes',
            'description': 'Detect changes in user access patterns that might indicate issues.',
            'question': 'Find users whose file access patterns have changed significantly in the last month'
        },
        {
            'title': 'Shared File Usage',
            'description': 'Analyze how shared files are being used across departments.',
            'question': 'How are shared files being used across different departments?'
        },
        {
            'title': 'Peak Usage Times',
            'description': 'Identify peak system usage times for capacity planning.',
            'question': 'What are the peak times for file system activity during the week?'
        },
        {
            'title': 'Department Activity',
            'description': 'Compare activity levels across different departments.',
            'question': 'Compare file activity levels between departments over the last quarter'
        }
    ]

def get_data_governance_examples():
    """Get data governance and lifecycle example queries
    
    Returns:
        list: A list of data governance example dictionaries
    """
    return [
        # Data Governance & Lifecycle
        {
            'title': 'Data Lifecycle Status',
            'description': 'Analyze files by their stage in the data lifecycle.',
            'question': 'Categorize files by their stage in the data lifecycle (active, archival, obsolete)'
        },
        {
            'title': 'Ownership Verification',
            'description': 'Verify that all files have clear and appropriate ownership.',
            'question': 'Find files without clear ownership assignment'
        },
        {
            'title': 'Compliance Tagging',
            'description': 'Verify that files are properly tagged for compliance.',
            'question': 'Are there files subject to compliance requirements that aren\'t properly tagged?'
        },
        {
            'title': 'Lifecycle Transitions',
            'description': 'Identify files ready for transition to the next lifecycle stage.',
            'question': 'Which files are ready to transition from active to archive status?'
        },
        {
            'title': 'Metadata Completeness',
            'description': 'Check if files have complete and accurate metadata.',
            'question': 'Find files with incomplete or missing required metadata fields'
        },
        {
            'title': 'Classification Consistency',
            'description': 'Verify consistency in how files are classified.',
            'question': 'Find inconsistencies in how similar files are classified across the system'
        },
        {
            'title': 'Retention Compliance',
            'description': 'Verify compliance with retention policies across file types.',
            'question': 'Are we compliant with retention policies for all financial documents?'
        },
        {
            'title': 'Access Control Verification',
            'description': 'Verify that access controls match file sensitivity.',
            'question': 'Find sensitive files with overly permissive access controls'
        },
        {
            'title': 'Workflow Documentation',
            'description': 'Find workflow documentation that might be outdated.',
            'question': 'Find workflow documentation files that haven\'t been updated in over a year'
        },
        {
            'title': 'Regulatory Documentation',
            'description': 'Ensure all required regulatory documentation is present and current.',
            'question': 'Do we have all required regulatory documentation for our financial data?'
        }
    ]

def get_advanced_analytics_examples():
    """Get advanced analytics example queries
    
    Returns:
        list: A list of advanced analytics example dictionaries
    """
    return [
        # Advanced Analytics
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
        },
        {
            'title': 'Predictive Storage',
            'description': 'Predict future storage needs based on current trends.',
            'question': 'Based on current trends, predict our storage needs for the next 12 months'
        },
        {
            'title': 'Security Pattern Detection',
            'description': 'Identify patterns that might indicate security issues.',
            'question': 'Find patterns of access that might indicate data exfiltration attempts'
        },
        {
            'title': 'Content Similarity',
            'description': 'Find files with similar content that might be redundant.',
            'question': 'Find documents with highly similar content that might be redundant'
        },
        {
            'title': 'Multi-dimension Analysis',
            'description': 'Analyze data across multiple dimensions simultaneously.',
            'question': 'Show me file growth patterns by department, type, and sensitivity level over time'
        },
        {
            'title': 'Compliance Risk Score',
            'description': 'Calculate a compliance risk score based on multiple factors.',
            'question': 'Calculate a compliance risk score for each department based on their data practices'
        },
        {
            'title': 'Access Pattern Correlation',
            'description': 'Correlate access patterns with other factors.',
            'question': 'Is there a correlation between file access patterns and security incidents?'
        },
        {
            'title': 'Seasonal Patterns',
            'description': 'Identify seasonal patterns in data usage and creation.',
            'question': 'Are there seasonal patterns in how our data is created and accessed?'
        },
        {
            'title': 'Exception Reporting',
            'description': 'Find exceptions to normal patterns and policies.',
            'question': 'Show me all exceptions to our standard file naming and organization policies'
        },
        {
            'title': 'Resource Optimization',
            'description': 'Identify opportunities for resource optimization.',
            'question': 'Where are the biggest opportunities to optimize our storage resources?'
        },
        {
            'title': 'Compliance Trend Analysis',
            'description': 'Analyze compliance trends over time.',
            'question': 'How has our compliance posture changed over the past year?'
        },
        {
            'title': 'Impact Assessment',
            'description': 'Assess the potential impact of policy changes.',
            'question': 'What would be the impact of changing our file retention policy from 7 to 5 years?'
        },
        {
            'title': 'Process Bottlenecks',
            'description': 'Identify bottlenecks in data workflows.',
            'question': 'Where are the bottlenecks in our document approval workflow?'
        },
        {
            'title': 'Continuous Monitoring',
            'description': 'Set up continuous monitoring for critical data.',
            'question': 'Set up continuous monitoring for any unauthorized changes to financial records'
        },
        {
            'title': 'Comprehensive Audit',
            'description': 'Perform a comprehensive audit of data management practices.',
            'question': 'Perform a comprehensive audit of our data management practices for compliance'
        }
    ]

def get_all_examples():
    """Get all examples for the examples page
    
    Returns:
        dict: A dictionary containing all example categories
    """
    return {
        'file_examples': get_file_analysis_examples(),
        'storage_examples': get_storage_optimization_examples(),
        'compliance_examples': get_compliance_security_examples(),
        'cleanup_examples': get_data_cleanup_examples(),
        'user_examples': get_user_activity_examples(),
        'governance_examples': get_data_governance_examples(),
        'advanced_examples': get_advanced_analytics_examples()
    }

def get_home_examples():
    """Get a subset of examples for the home page
    
    Returns:
        list: A list of example query dictionaries
    """
    # Take a subset of examples from various categories for the home page
    all_examples = get_all_examples()
    home_examples = []
    
    # Add 2 examples from each category
    for category in all_examples.values():
        home_examples.extend(category[:2])
    
    # Return a random selection of 6 examples from the combined list
    import random
    if len(home_examples) > 6:
        return random.sample(home_examples, 6)
    return home_examples
