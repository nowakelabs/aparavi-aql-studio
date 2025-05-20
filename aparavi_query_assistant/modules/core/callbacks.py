#!/usr/bin/env python3
"""
Callback functions for the Aparavi Query Assistant

This module defines callback functions that are registered with the Flask application
to handle various events such as before/after request, error handling, etc.
"""

import logging
from flask import request, session, g, jsonify

def register_callbacks(app):
    """Register callback functions with the Flask application
    
    Args:
        app: Flask application instance
    """
    logger = logging.getLogger(__name__)
    
    @app.before_request
    def before_request():
        """Called before each request"""
        # Initialize request context
        from datetime import datetime
        g.request_start_time = datetime.now().timestamp()
        
        # Log request info
        logger.debug(f"Request: {request.method} {request.path} from {request.remote_addr}")
        
        # Ensure session has necessary structures
        if 'query_history' not in session:
            session['query_history'] = []
    
    @app.after_request
    def after_request(response):
        """Called after each request"""
        # Calculate request duration
        if hasattr(g, 'request_start_time'):
            from datetime import datetime
            duration = datetime.now().timestamp() - g.request_start_time
            logger.debug(f"Request completed in {duration:.4f} seconds")
            
            # Add timing header for API requests
            if request.path.startswith('/api/'):
                response.headers['X-Response-Time'] = f"{duration:.4f}s"
        
        return response
    
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Resource not found',
                'status': 404
            }), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors"""
        logger.exception("Server error")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal server error',
                'status': 500
            }), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Forbidden',
                'status': 403
            }), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(400)
    def bad_request(e):
        """Handle 400 errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Bad request',
                'status': 400,
                'message': str(e) if hasattr(e, 'description') else 'Invalid request'
            }), 400
        return render_template('errors/400.html'), 400

def import_time():
    """Import datetime lazily to avoid circular imports"""
    from datetime import datetime
    return datetime.now()

def render_template(*args, **kwargs):
    """Import render_template lazily to avoid circular imports"""
    from flask import render_template as flask_render_template
    return flask_render_template(*args, **kwargs)