"""
Temporary module to debug where sanitize_query is being called
"""

def sanitize_query(query):
    """Replacement for sanitize_query that prints debug info"""
    import inspect
    import traceback
    
    # Get the caller's info
    frame = inspect.currentframe().f_back
    filename = frame.f_code.co_filename
    line_number = frame.f_lineno
    function_name = frame.f_code.co_name
    
    # Print debug information
    print(f"\n\nDEBUG INFO: sanitize_query called from:")
    print(f"File: {filename}")
    print(f"Line: {line_number}")
    print(f"Function: {function_name}")
    print(f"Query: {query[:50]}...")
    
    # Print stack trace
    print("\nStack trace:")
    traceback.print_stack()
    
    # Just return the query unchanged
    return query
