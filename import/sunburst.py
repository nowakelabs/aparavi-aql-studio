#!/usr/bin/env python
# Created on: 23/03/2025 10:38:03
"""
Interactive Recursive Sunburst Visualization with Dash

This application creates an interactive sunburst visualization for exploring
folder hierarchies at different depth levels. It allows users to:
1. Adjust the depth level to explore
2. Switch between visualizing by file count or total size
3. See statistics about the data
4. View detailed file information for selected folders

The visualization uses Dash and Plotly for interactive elements and DuckDB
for efficient querying of the data.
"""

import os
import time
import traceback
from datetime import datetime

import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

# Import the query parameters and configuration utilities
import query_parameters as qp
import config_utils as cfg

# Global variables
conn = None
max_db_depth = 0
selected_folder_path = None

def connect_to_database():
    """
    Connect to DuckDB database.
    
    Returns:
        duckdb.DuckDBPyConnection: A connection to the database.
    """
    try:
        # Get database path and read-only setting from config
        db_path = cfg.get_database_path()
        read_only = cfg.get_database_readonly()
        
        print(f"Attempting to connect to database at: {db_path} (read_only={read_only})")
        conn = duckdb.connect(db_path, read_only=read_only)
        print("Successfully connected to database")
        
        # Get database info
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"Database contains {len(tables)} tables: {', '.join([t[0] for t in tables])}")
        
        # Get all statistics in one query
        totals_result = conn.execute(qp.get_query('totals')).fetchone()
        total_folders = totals_result[0] if totals_result else 0
        total_files = totals_result[1] if totals_result else 0
        total_size = totals_result[2] if totals_result else 0
        
        # print(f"Database contains {total_folders:,} total folders")
        # print(f"Database contains {total_files:,} total files")
        # print(f"Total data size: {total_size / (1024*1024*1024):.2f} GB")
        
        # Detect max depth in database
        max_db_depth = get_max_folder_depth(conn)
        # print(f"Maximum folder depth in database: {max_db_depth}")
        
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        traceback.print_exc()
        return None

def get_max_folder_depth(conn):
    """
    Determine the maximum folder depth in the database.
    
    Args:
        conn (duckdb.DuckDBPyConnection): A connection to the database.
        
    Returns:
        int: The maximum folder depth.
    """
    try:
        # Get query from parameters file
        query = qp.get_query('max_depth')
        
        # Print the query for debugging
        # print(f"Executing max depth query: {query}")
        
        # Execute with more detailed error handling
        result = conn.execute(query).fetchone()
        max_depth = result[0] if result and result[0] is not None else 3
        
        # Detailed debug output
        # print(f"Raw max depth query result: {result}")
        # print(f"Interpreted maximum depth: {max_depth}")
        
        # Verify with a simple alternative query
        try:
            # Get alternative depth calculation query
            alt_query = qp.get_query('alt_depth')
            alt_result = conn.execute(alt_query).fetchone()
            # print(f"Alternative depth calculation (slash count): {alt_result[0] if alt_result else 'N/A'}")
            
            # Get example deep paths using the centralized query
            deep_paths_query = qp.get_query('deep_paths')
            deep_paths = conn.execute(deep_paths_query).fetchall()
            print("Example deep paths:")
            # for path in deep_paths:
                # print(f"  {path[0]} (depth: {path[0].count('/') + 1})")
                
        except Exception as e:
            print(f"Error in alternative depth calculation: {e}")
            
        return max_depth
    except Exception as e:
        print(f"Error determining max folder depth: {e}")
        return 3  # Default to depth 3 if there's an issue

def get_subfolder_data(conn, path_components, current_depth, max_depth):
    """
    Recursively get subfolder data up to the specified max depth.
    
    Args:
        conn (duckdb.DuckDBPyConnection): A connection to the database.
        path_components (list): The path components of the current folder.
        current_depth (int): The current depth in the recursion.
        max_depth (int): The maximum depth to recurse to.
        
    Returns:
        list: List of subfolder data dictionaries.
    """
    # Early return if we've reached our depth limit
    if current_depth > max_depth:
        # print(f"Reached max depth {max_depth}, stopping recursion")
        return []
    
    # Build current path from path components
    current_path = ""
    if path_components:
        current_path = "/".join(path_components)
    
    # print(f"DEPTH {current_depth}/{max_depth}: Processing path: '{current_path}'")
    
    try:
        # Get appropriate query from parameters file
        if not current_path:
            # Root level query
            query = qp.get_query('rootfolders')
        else:
            # Subfolder query with path parameters
            path_length = len(current_path) + 2  # +2 for the slash and first character
            query = qp.get_query('subfolders', 
                                path_prefix=current_path,
                                path_length=path_length,
                                path_length_minus_1=path_length-1)
        
        # print(f"Executing query for path: '{current_path}'")
        results = conn.execute(query).fetchall()
        
        # Enhanced debugging for deeper levels
        if current_depth >= 7:
            # print(f"DEPTH {current_depth}/{max_depth}: DEEP LEVEL - Query for '{current_path}' returned {len(results)} results")
            if len(results) == 0:
                # If we're getting no results at deeper levels, log the query for debugging
                # print(f"No results at deep level. Query used: {query.replace('{', '{{').replace('}', '}}')}")
                
                # Check if this path exists in parentPaths
                if current_path:
                    verify_query = f"""
                        SELECT COUNT(*) 
                        FROM parentPaths 
                        WHERE parentPath LIKE '{current_path}/%'
                    """
                    try:
                        verify_count = conn.execute(verify_query).fetchone()
                        # print(f"Verification: Path '{current_path}/%' has {verify_count[0]} matches in parentPaths")
                    except Exception as e:
                        print(f"Verification query error: {e}")
        else:
            print(f"DEPTH {current_depth}/{max_depth}: Query for '{current_path}' returned {len(results)} results")
        
        # Process results
        subfolder_data = []
        
        for result in results:
            folder_name = result[0]
            
            # Skip empty folder names
            if not folder_name or folder_name == "":
                continue
                
            # Build full path
            folder_path = current_path + "/" + folder_name if current_path else folder_name
            
            # print(f"DEPTH {current_depth}/{max_depth}: Found subfolder '{folder_name}' at path '{folder_path}'")
            
            # Get file statistics using the stats query from parameters file
            try:
                stats_query = qp.get_query('folder_stats', folder_path=folder_path)
                stats = conn.execute(stats_query).fetchone()
                file_count = stats[0] if stats and stats[0] is not None else 0
                folder_count = stats[1] if stats and stats[1] is not None else 0
                total_size = stats[2] if stats and stats[2] is not None else 0
                # print(f"Stats for '{folder_path}': {folder_count} folders,{file_count} files, {total_size} bytes")
            except Exception as e:
                # print(f"Error getting stats for '{folder_path}': {e}")
                file_count = 0
                total_size = 0
            
            # Create folder data dictionary
            folder_data = {
                "name": folder_name,
                "path": folder_path,
                "file_count": file_count,
                "total_size": total_size,
                "folder_count": folder_count,
                "subfolders": []
            }
            
            # Recursively get subfolders if we haven't reached max depth
            if current_depth < max_depth:
                # Build new path components for recursion
                new_path_components = path_components + [folder_name] if path_components else [folder_name]
                
                # if current_depth >= 7:
                    # print(f"DEEP RECURSION: Going from depth {current_depth} to {current_depth+1} for path {folder_path}")
                
                subfolder_subfolders = get_subfolder_data(conn, new_path_components, current_depth + 1, max_depth)
                folder_data["subfolders"] = subfolder_subfolders
            
            # Add to results
            subfolder_data.append(folder_data)
        
        # print(f"DEPTH {current_depth}/{max_depth}: Returning {len(subfolder_data)} subfolders for path '{current_path}'")
        return subfolder_data
        
    except Exception as e:
        print(f"Error getting subfolder data for '{current_path}': {e}")
        traceback.print_exc()
        return []

def prepare_sunburst_data(folder_hierarchy):
    """
    Prepare data for the sunburst visualization from the folder hierarchy.
    
    Args:
        folder_hierarchy (list): List of folder data dictionaries.
        
    Returns:
        tuple: (labels, parents, values, sizes, paths, display_names, folder_counts, parent_paths)
    """
    # Initialize data arrays
    labels = []
    parents = []
    values = []
    sizes = []
    paths = []
    display_names = []  # Store display names for nodes (without uniqueness suffix)
    folder_counts = []  # Track number of subfolders for each node
    parent_paths = []   # Paths of parent folders
    
    # Create a root node
    root_folder_name = cfg.get_setting('Visualization', 'root_folder', 'Root')
    labels.append(root_folder_name)
    parents.append("")
    values.append(0)  # Will be updated to sum of children
    sizes.append(0)   # Will be updated to sum of children
    paths.append("")
    display_names.append(root_folder_name)
    folder_counts.append(0)  # Will be updated with count of immediate children
    parent_paths.append("")  # Root has no parent
    
    # Dictionary to track used labels to ensure uniqueness
    used_labels = {root_folder_name: 1}
    
    # Track total values for properly calculating percentages
    total_folders = 0
    total_files = 0
    total_size = 0
    
    def process_folder(folder, parent_label=None, prefix="", is_top_level=False):
        """Process a folder and its subfolders recursively."""
        # Use the root folder name as default parent if None is provided
        if parent_label is None:
            parent_label = root_folder_name
        
        # Extract folder information
        folder_name = folder["name"]
        folder_path = folder["path"]
        file_count = folder["file_count"]
        folder_count = folder["folder_count"]  # Use the actual folder count from the database
        total_size = folder["total_size"]
        
        # Create a unique label for this folder by combining name with the path
        # This prevents issues with duplicate folder names at different paths
        if prefix:
            full_path = f"{prefix}/{folder_name}"
        else:
            full_path = folder_name
            
        # Ensure the label is unique
        base_label = full_path
        if base_label in used_labels:
            counter = used_labels[base_label]
            used_labels[base_label] += 1
            unique_label = f"{base_label}_{counter}"
        else:
            used_labels[base_label] = 1
            unique_label = base_label
        
        # Add folder to data arrays
        labels.append(unique_label)
        parents.append(parent_label)
        values.append(max(file_count, 1))  # Ensure at least 1 so it's visible
        sizes.append(max(total_size, 1))  # Ensure at least 1 so it's visible
        folders.append(max(folder_count, 1))  # Ensure at least 1 so it's visible
        paths.append(folder_path)
        display_names.append(folder_name)  # Use just the name for display
        
        
        # Extract parent path - get the directory containing this folder
        if is_top_level:
            # Top-level folders have Root as their parent
            parent_paths.append(root_folder_name)
        elif "/" in folder_path:
            parent_path = folder_path.rsplit("/", 1)[0]
            parent_paths.append(parent_path)
        else:
            parent_paths.append("")
        
        # Process subfolders
        for subfolder in folder.get("subfolders", []):
            process_folder(subfolder, unique_label, full_path, False)
        
        return unique_label, file_count, folder_size
    
    # Process all top-level folders
    for folder in folder_hierarchy:
        _, folder_files, folder_size = process_folder(folder, root_folder_name, "", True)
        # Add to root node values
        values[0] += max(folder_files, 1)
        sizes[0] += max(folder_size, 1)
        folders[0] += max(folder_count, 1)
        # Track totals
        total_folders += folder_count
        total_files += folder_files
        total_size += folder_size
    
    # Ensure the root has a substantial value for visualization
    if values[0] < 10:
        values[0] = max(sum(values[1:]), 10)  # Use sum of children or minimum of 10
    if sizes[0] < 10:
        sizes[0] = max(sum(sizes[1:]), 10)  # Use sum of children or minimum of 10
    
    # Update root folder count with number of top-level folders
    #folder_counts[0] = len(folder_hierarchy)
    
    # print(f"Prepared data with {len(labels)} entries, total folders: {total_folders}, total files: {total_files}, total size: {total_size}")
    
    return labels, parents, values, sizes, paths, display_names, folder_counts, parent_paths

def create_sunburst_figure(labels, parents, values, sizes, paths, display_names, folder_counts, parent_paths, metric='count'):
    """
    Create a sunburst figure for visualization.
    
    Args:
        labels (list): List of node labels.
        parents (list): List of parent labels.
        values (list): List of values for each node.
        sizes (list): List of sizes for each node.
        paths (list): List of full paths for each node.
        display_names (list): List of display names for each node.
        folder_counts (list): List of subfolder counts for each node.
        parent_paths (list): List of parent paths for each node.
        metric (str): The metric to display ('count' or 'size').
        
    Returns:
        plotly.graph_objects.Figure: A sunburst figure.
    """
    # Set title based on metric
    #title = "Folder Hierarchy - File Count" if metric == 'count' else "Folder Hierarchy - Size (MB)"
    title=""
    # Convert sizes to MB for better readability
    sizes_mb = [size / (1024 * 1024) for size in sizes]
    
    # Prepare hover data
    hover_data = []
    
    # Add debug print to diagnose folder counts
    print("Hover data folder counts (first 5):")
    # for i in range(min(5, len(folder_counts))):
        # print(f"  {i}: {display_names[i]} - {folder_counts[i]} folders, {values[i]} files/size")
    
    for i in range(len(display_names)):
        hover_data.append({
            'name': display_names[i],
            'path': paths[i],
            'files': values[i],
            'folders': folder_counts[i],
            'size_mb': sizes_mb[i],
        })
    
    # Common hover template that includes both file count and size
    hovertemplate = (
        '<b>%{customdata.name}</b><br>' + 
        'Path: %{customdata.path}<br>' + 
        'Files: %{customdata.files:,}<br>' +  
        'Subfolder Count: %{customdata.folders:,}<br>' +  # Rename to clarify this is showing subfolder count
        'Size: %{customdata.size_mb:.2f} MB<br>' + 
        '<extra></extra>'
    )
    
    # Determine values to use based on metric
    display_values = sizes_mb if metric == 'size' else values
    
    # Create sunburst figure - Using go.Sunburst for more control
    fig = go.Figure(go.Sunburst(
        labels=display_names,  # Use display names for visual labels
        ids=labels,  # Use unique labels as node IDs
        parents=['' if p == '' else p for p in parents],  # Keep parent relationships
        values=display_values,
        customdata=hover_data,  # Use our rich custom data for hovering
        branchvalues='total',  # 'total' means the sum of all descendants
        hovertemplate=hovertemplate,
        insidetextorientation='radial',  # Text follows the circular path
        sort=False,  # Don't sort by value automatically
    ))
    
    # Ensure the figure uses a full circle layout
    fig.update_layout(
        margin=dict(t=60, l=0, r=0, b=0),
                autosize=True,  # Prevent auto-sizing
        showlegend=False,  # Hide legend for cleaner look
        clickmode='event'  # Ensure click events are captured
    )
    
    return fig

def create_dash_app(folder_hierarchy, total_files, total_size, total_folders):
    """
    Create and configure the Dash application.
    
    Args:
        folder_hierarchy (list): Initial folder hierarchy data.
        total_files (int): Total number of files in the database.
        total_size (float): Total size of all files in bytes.
        total_folders (int): Total number of folders in the database.
        
    Returns:
        dash.Dash: Configured Dash application.
    """
    # Format total size for display
    total_size_gb = total_size / (1024 * 1024 * 1024)
    
    # Get default depth and metrics from config
    default_depth = cfg.get_default_depth()
    max_allowed_depth = min(cfg.get_max_allowed_depth(), max_db_depth)
    
    # Create the Dash app
    app = dash.Dash(
        __name__, 
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://use.fontawesome.com/releases/v5.15.4/css/all.css"  # Add Font Awesome for icons
        ]
    )
    app.title = "Aparavi File Statistics"
    
    # Create settings modal
    settings_modal = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Settings")),
            dbc.ModalBody([
                html.H5("Visualization Settings"),
                dbc.Form([
                    dbc.Row([
                        dbc.Label("Default Depth", width=6),
                        dbc.Col(
                            dbc.Input(
                                type="number", 
                                id="settings-default-depth",
                                value=default_depth,
                                min=1,
                                max=max_allowed_depth
                            ),
                            width=6,
                        ),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Label("Include Files in Subfolders", width=6),
                        dbc.Col(
                            dbc.Checkbox(
                                id="settings-include-subfolders",
                                value=False,
                                className="mt-2"
                            ),
                            width=6,
                        ),
                    ], className="mb-3"),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Save", id="settings-save", className="ms-auto", color="primary"),
                dbc.Button("Close", id="settings-close", className="ms-2", color="secondary"),
            ]),
        ],
        id="settings-modal",
        is_open=False,
    )
    
    # Build app layout
    app.layout = dbc.Container([
        # Container for settings button in top right
        html.Div(
            dbc.Button(
                html.I(className="fas fa-cog", style={"font-size": "20px"}),
                id="settings-button",
                color="light",
                className="rounded-circle",
                style={
                    "position": "absolute", 
                    "top": "15px", 
                    "right": "15px",
                    "width": "40px",
                    "height": "40px",
                    "padding": "0",
                    "display": "flex",
                    "align-items": "center",
                    "justify-content": "center",
                    "z-index": "1000"
                },
            ),
            style={"position": "relative"},
        ),
        
        # Settings modal
        settings_modal,
        
        dbc.Row([
            dbc.Col([
                html.H1("Aparavi File Statistics", className="text-center my-4"),
                html.P(id="timestamp", className="text-center text-muted"),
                html.P(id="status-message", className="text-center text-info small"),
            ]),
        ],className="h-15"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Statistics"),
                    dbc.CardBody([
                        html.P("Visualization Metric:"),
                        dbc.RadioItems(
                            id="metric-selector",
                            options=[
                                {"label": "File Count", "value": "count"},
                                {"label": "Total Size", "value": "size"},
                            ],
                            value="count",
                            inline=True,
                            className="mb-3"
                        ),
                        html.P(f"Total Folders: {total_folders:,}"),
                        html.P(f"Total Files: {total_files:,}"),
                        html.P(f"Total Size: {total_size_gb:.2f} GB"),
                        html.P(id="depth-debug"),
                    ])
                ], className="mb-4")
            ], width=2),
            dbc.Col([
                dbc.Alert(
                    id="depth-warning",
                    color="warning",
                    is_open=False,
                    dismissable=True,
                    style={"display": "none"},
                ),
                dbc.Card([
                    dbc.CardHeader("Folder Hierarchy", className="fw-bold"),
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading",
                            type="circle",
                            children=[
                                dcc.Graph(
                                    id="sunburst-chart",
                                    figure={},
                                    
                                    config={
                                        "displayModeBar": True,
                                        "scrollZoom": True,
                                        "displaylogo": False,
                                    },
                                )
                            ],
                        ),
                        # Store for clicked data
                        dcc.Store(id='selected-folder-store'),
                        # Store for sunburst chart data
                        dcc.Store(id='sunburst-data-store'),
                    ]),
                ], className="mb-4"),
            ], width=5),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("File Summary", className="fw-bold"),
                    dbc.CardBody([
                        dbc.Tabs([
                            dbc.Tab(
                                dcc.Graph(
                                    id='bargraph1-chart',
                                    figure={},
                                    config={
                                        'displayModeBar': True,
                                        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                                        'displaylogo': False
                                    }
                                ),
                                label="File Types",
                                tab_id="tab-1",
                            ),
                            dbc.Tab(
                                dcc.Graph(
                                    id='bargraph2-chart',
                                    figure={},
                                    config={
                                        'displayModeBar': True,
                                        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                                        'displaylogo': False
                                    }
                                ),
                                label="File Sizes",
                                tab_id="tab-2",
                            ),
                            dbc.Tab(
                                dcc.Graph(
                                    id='bargraph3-chart',
                                    figure={},
                                    config={
                                        'displayModeBar': True,
                                        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                                        'displaylogo': False
                                    }
                                ),
                                label="File Ages",
                                tab_id="tab-3",
                            ),
                        ], id="tabs", active_tab="tab-1"),
                    ]),
                ], className="mb-4"),
            ], width=5),
        ],className="h-55"),
        
        dbc.Row([
            
            # File details table section
            dbc.Col([
                html.Div([
                    html.H5("File Details"),
                    html.Div(id='file-table-info', className='mb-2'),
                    # File details table
                    dash_table.DataTable(
                        id='file-table',
                        columns=[
                            {'name': 'File Name', 'id': 'filename', 'type': 'text'},
                            {'name': 'Extension', 'id': 'extension', 'type': 'text'},
                            {'name': 'Type', 'id': 'file_type', 'type': 'text'},
                            {'name': 'Classification', 'id': 'classification', 'type': 'text'},
                            # Keep the formatted size column
                            {'name': 'Size', 'id': 'size_raw', 'type': 'text'},
                            # Correctly format numeric column with proper locale settings
                            {'name': 'Size (bytes)', 'id': 'file_size_display', 'type': 'numeric', 
                             'format': {'locale': {'group': ','}, 'specifier': ',d'}},
                            {'name': 'Modified', 'id': 'modify_time', 'type': 'text'},
                        ],
                        data=[],
                        filter_action='native',
                        sort_action='native',
                        sort_mode='multi',
                        page_size=20,
                        style_table={'overflowX': 'auto'},
                        style_cell={
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'minWidth': '30px',
                            'padding': '8px'
                        },
                        style_cell_conditional=[
                            {'if': {'column_id': 'filename'}, 'width': '25%', 'textAlign': 'left'},
                            {'if': {'column_id': 'extension'}, 'width': '8%', 'textAlign': 'center'},
                            {'if': {'column_id': 'type'}, 'width': '10%', 'textAlign': 'left'},
                            {'if': {'column_id': 'classification'}, 'width': '10%', 'textAlign': 'left'},
                            {'if': {'column_id': 'size'}, 'width': '8%', 'textAlign': 'right'},
                            {'if': {'column_id': 'size_bytes'}, 'width': '10%', 'textAlign': 'right'},
                            {'if': {'column_id': 'modified'}, 'width': '15%', 'textAlign': 'left'},
                            {'if': {'column_id': 'owner'}, 'width': '7%', 'textAlign': 'left'},
                            {'if': {'column_id': 'permissions'}, 'width': '7%', 'textAlign': 'center'},
                        ],
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                    ),
                ], className='mb-4'),
            ], width=12)
        ]),
    ], fluid=True)
    
    # Callback to update the timestamp
    @app.callback(
        Output('timestamp', 'children'),
        [Input('sunburst-chart', 'figure')]
    )
    def update_timestamp(_):
        """Update the timestamp displayed on the page."""
        now = datetime.now()
        return f"Last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Callback for updating the file table when a folder is clicked in the sunburst
    @app.callback(
        [Output('file-table', 'data'),
         Output('file-table-info', 'children'),
         Output('selected-folder-store', 'data')],
        [Input('sunburst-chart', 'clickData'),
         Input('settings-include-subfolders', 'value')],
        [State('selected-folder-store', 'data'),
         State('sunburst-data-store', 'data')]
    )
    def update_file_table(click_data, include_subfolders, stored_folder, sunburst_data):
        """
        Update the file details table when a folder is clicked in the sunburst chart.
        
        Args:
            click_data (dict): Click data from the sunburst chart.
            include_subfolders (bool): Whether to include files in subfolders.
            stored_folder (dict): Previously stored folder data.
            sunburst_data (dict): Data from the sunburst chart including labels and paths.
            
        Returns:
            tuple: (table_data, table_info, stored_folder)
        """
        folder_path = None
        
        # Get sunburst data
        labels = sunburst_data.get('labels', []) if sunburst_data else []
        paths = sunburst_data.get('paths', []) if sunburst_data else []
        
        # Debug print
        # print(f"Click data received: {click_data}")
        # print(f"Sunburst data available: {len(labels)} labels, {len(paths)} paths")
        
        # Check if triggered by click event
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        if trigger_id == 'sunburst-chart' and click_data:
            try:
                # Extract folder path from click data
                points = click_data.get('points', [])
                if points and len(points) > 0:
                    point = points[0]
                    # Print the clicked point data for debugging
                    # print(f"Clicked point: {point}")
                    
                    if 'id' in point:
                        # Extract the folder path based on the id
                        node_id = point['id']
                        # print(f"Clicked node ID: {node_id}")
                        
                        # Find the matching path from our paths list
                        for i, label in enumerate(labels):
                            if label == node_id and i < len(paths):
                                folder_path = paths[i]
                                # print(f"Found matching folder path: {folder_path}")
                                stored_folder = {'path': folder_path}
                                break
                    
                    # Also try to extract from customdata if available
                    elif 'customdata' in point and 'path' in point['customdata']:
                        folder_path = point['customdata']['path']
                        # print(f"Extracted folder path from customdata: {folder_path}")
                        stored_folder = {'path': folder_path}
            except Exception as e:
                print(f"Error extracting folder path from click data: {str(e)}")
                traceback.print_exc()
                
        # If only recursive checkbox changed, use stored folder path
        elif trigger_id == 'settings-include-subfolders' and stored_folder:
            folder_path = stored_folder.get('path')
            # print(f"Using stored folder path from recursive checkbox change: {folder_path}")
            
        # If no valid folder path, return empty table
        if not folder_path:
            print("No folder path available - returning empty table")
            return [], "No folder selected - click on a folder in the chart", stored_folder
            
        # Get file data for the selected folder
        try:
            # print(f"Getting file data for folder: {folder_path}, include_subfolders={include_subfolders}")
            conn = connect_to_database()
            if not conn:
                raise Exception("Failed to connect to database")
                
            df = get_file_data_for_folder(conn, folder_path, include_subfolders=include_subfolders)
            
            if df.empty:
                # print(f"No files found in {folder_path}")
                return [], f"No files found in {folder_path}", stored_folder
                
            # Convert the DataFrame to a list of dictionaries for the DataTable
            table_data = df.to_dict('records')
            # print(f"Returning {len(table_data)} files for table")
            # print(f"First row data: {table_data[0] if table_data else None}")
            
            info_text = f"{len(df)} files in {folder_path}"
            if include_subfolders:
                info_text += " (including subfolders)"
                
            return table_data, info_text, stored_folder
            
        except Exception as e:
            print(f"Error updating file table: {str(e)}")
            traceback.print_exc()
            return [], f"Error loading files: {str(e)}", stored_folder
    
    # Callback to update the visualization
    @app.callback(
        [Output('sunburst-chart', 'figure'),
         Output('depth-warning', 'style'),
         Output('depth-warning', 'children'),
         Output('status-message', 'children'),
         Output('depth-debug', 'children'),
         Output('sunburst-data-store', 'data')],
        [Input('settings-save', 'n_clicks'),
         Input('metric-selector', 'value')],
        [State('settings-default-depth', 'value'),
         State('settings-include-subfolders', 'value'),
         State('sunburst-data-store', 'data')]
    )
    def update_visualization(save_click, metric, depth, include_subfolders, stored_data):
        """
        Update the visualization based on the selected depth and metric.
        
        Args:
            save_click: Number of times the save button has been clicked
            metric: The metric to display ('count' or 'size')
            depth: The maximum depth to display
            include_subfolders: Whether to include files in subfolders
            stored_data: Previously stored sunburst data
            
        Returns:
            tuple: (figure, warning_style, warning_message, status_message, depth_debug, sunburst_data)
        """
        # Start timer
        start_time = time.time()
        
        # Use default depth if none specified or on initial load
        if depth is None:
            depth = default_depth
        
        # Create empty figure as fallback
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        
        # Initialize warning variables
        warning_message = ""
        warning_style = {'display': 'none'}
        
        try:
            # Get max depth available in the database
            max_db_depth = get_max_folder_depth(conn)
            # print(f"Max depth in database: {max_db_depth}")
            
            # Show warning if trying to view more than the database provides
            if depth > max_db_depth:
                warning_message = f"Warning: Database only has data up to depth {max_db_depth}. Showing everything available."
                warning_style = {'display': 'block', 'color': 'orange'}
            
            # Prepare the data for the sunburst visualization
            labels = []      # Labels for each segment
            parents = []     # Parents for hierarchy
            values = []      # Values for segment size
            sizes = []       # Raw byte sizes
            paths = []       # Full paths for each segment
            display_names = []  # Display names (short names)
            folder_counts = []  # Number of files in each folder
            parent_paths = []   # Store parent paths for each node
            
            # Add ROOT node
            labels.append('')
            parents.append('')
            values.append(0)  # Value will be calculated from children
            sizes.append(0)
            paths.append('')
            display_names.append('Center of the Universe')
            folder_counts.append(0)  # Will be updated with count of immediate children
            parent_paths.append("")  # Root has no parent
            
            # print(f"Processing folders at depth {depth}")
            
            # First, get the top-level folders
            df_top = get_top_level_folders(conn, metric)
            
            if df_top.empty:
                print("No top-level folders found")
                return empty_fig, warning_style, warning_message, "No data found", f"No data at depth {depth}", {}
            
            # print(f"Found {len(df_top)} top-level folders")
            
            subfolders_found = False
            
            # Process each top-level folder
            for idx, row in df_top.iterrows():
                top_folder = row['folderPath']
                size = row['totalsize'] or 0
                filecount = int(row['filecount']) if row['filecount'] else 0
                foldercount = int(row['foldercount']) if row['foldercount'] else 0
                
                # Debug output to check folder count
                # print(f"DEBUG Row data for {top_folder}:")
                # print(f"  Raw folder count: {row['foldercount']}")
                # print(f"  Converted folder count: {foldercount}")
                # print(f"  Available columns: {row.index.tolist()}")
                
                # Use the appropriate value based on selected metric
                value = filecount if metric == 'count' else size
                
                # Get display name (last part of path)
                display_name = top_folder.split('/')[-1] if '/' in top_folder else top_folder
                
                # Add top-level folder
                labels.append(top_folder)
                parents.append('')  # Top-level folders have the ROOT as parent
                values.append(value)
                sizes.append(size)
                paths.append(top_folder)
                display_names.append(display_name)
                folder_counts.append(foldercount)  # Use the foldercount from the query
                parent_paths.append('')
                
                # Process subfolders if depth > 1
                if depth > 1:
                    process_subfolders(conn, top_folder, depth, 1, labels, parents, values, 
                                      sizes, paths, display_names, folder_counts, parent_paths, metric)
                    subfolders_found = True
                
                # Print debug info for the first few folders
                if idx < 3:
                    # print(f"Top folder: {top_folder}, value: {value}, folders: {foldercount}")
                    
                    # Check if the folder has immediate children
                    child_count = sum(1 for p in parents if p == top_folder)
                    # if child_count > 0:
                    #     print(f"  - Has {child_count} immediate children")
                    # else:
                    #     print("  - No immediate children")
            
            # Add some diagnostics
            if depth > 1:
                if not subfolders_found:
                    print("WARNING: No subfolders found in any top-level folders!")
            
            # Prepare data storage for callbacks
            sunburst_data = {
                'labels': labels,
                'paths': paths,
                'parents': parents
            }
            
            # Create the sunburst figure
            fig = create_sunburst_figure(
                labels, parents, values, sizes, paths, 
                display_names, folder_counts, parent_paths, metric
            )
            
            # Force complete redraw by clearing any caches
            fig.update_layout(uirevision=f"depth_{depth}_metric_{metric}_{time.time()}")
            
            # Calculate the time taken and update the status message
            time_taken = round(time.time() - start_time, 2)
            status_message = f"Visualization updated with {len(labels)} items in {time_taken} seconds"
            
            # Debug information
            depth_debug = f"Current Depth: {depth} (Max Allowed: {max_allowed_depth})"
            
            # print(f"\n\n----- COMPLETED DEPTH CHANGE TO {depth} -----\n\n")
            
            return fig, warning_style, warning_message, status_message, depth_debug, sunburst_data
            
        except Exception as e:
            print(f"Error updating visualization: {str(e)}")
            traceback.print_exc()
            
            # Return an error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            
            return fig, {'display': 'none'}, "", f"Error: {str(e)}", "", {}
    
    # Callback to open/close the settings modal
    @app.callback(
        Output("settings-modal", "is_open"),
        [Input("settings-button", "n_clicks"), Input("settings-close", "n_clicks"), Input("settings-save", "n_clicks")],
        [State("settings-modal", "is_open")],
    )
    def toggle_settings_modal(settings_click, close_click, save_click, is_open):
        """
        Toggle the settings modal when the settings button, close button, or save button is clicked.
        
        Args:
            settings_click: Number of times the settings button has been clicked
            close_click: Number of times the close button has been clicked
            save_click: Number of times the save button has been clicked
            is_open: Current state of the modal
            
        Returns:
            bool: The new state of the modal
        """
        # Early return if no clicks
        if not any([settings_click, close_click, save_click]):
            return is_open
            
        # Toggle modal state based on which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open
            
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "settings-button":
            return not is_open
        elif button_id in ["settings-close", "settings-save"]:
            return False
            
        return is_open
    
    # Callback to save settings
    @app.callback(
        [Output("settings-default-depth", "value"),
         Output("settings-include-subfolders", "value")],
        [Input("settings-save", "n_clicks")],
        [State("settings-default-depth", "value"), State("settings-include-subfolders", "value")],
        prevent_initial_call=True,
    )
    def save_settings(save_click, depth_value, include_subfolders_value):
        """
        Save the settings from the modal and update the main controls.
        
        Args:
            save_click: Number of times the save button has been clicked
            depth_value: New default depth value
            include_subfolders_value: New include subfolders value
            
        Returns:
            tuple: (depth_value, include_subfolders_value) to update the main controls
        """
        # Early return if no save click
        if not save_click:
            raise dash.exceptions.PreventUpdate
            
        # Validate inputs
        if depth_value is not None and depth_value >= 1 and depth_value <= max_allowed_depth:
            new_depth = depth_value
        else:
            new_depth = default_depth
            
        new_include_subfolders = include_subfolders_value
        
        # Update the config file (if implementing persistence)
        # cfg.set_default_depth(new_depth)
        # cfg.set_default_metric(new_metric)
        
        return new_depth, new_include_subfolders

    # Add callback for the size distribution graph (tab 2)
    @app.callback(
        Output('bargraph2-chart', 'figure'),
        [Input('selected-folder-store', 'data'),
         Input('metric-selector', 'value')]
    )
    def update_size_graph(selected_folder_data, metric):
        """
        Update the file size distribution graph based on the selected folder.
        
        Args:
            selected_folder_data: Data from the selected folder in the sunburst chart
            metric: The metric to display ('count' or 'size')
            
        Returns:
            plotly.graph_objects.Figure: Bar graph of file size distribution
        """
        # Use root folder if no folder is selected
        folder_path = selected_folder_data.get('path', '') if selected_folder_data else ''
        
        try:
            # Get file data for the selected folder (recursive)
            conn = connect_to_database()
            if not conn:
                raise Exception("Failed to connect to database")
                
            df = get_file_data_for_folder(conn, folder_path, include_subfolders=True)
            
            # Early return if no file data
            if df.empty:
                no_data_fig = go.Figure()
                no_data_fig.update_layout(
                    title=f"No files found in {folder_path or 'root'}",
                    annotations=[dict(
                        text="No file data available for this folder",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5
                    )]
                )
                return no_data_fig
                
            # Create the file size distribution graph using our size bucket function
            # Apply get_size_bucket to categorize each file by size
            df['size_category'] = df['file_size'].apply(get_size_bucket)
            
            # Define the order of size categories for proper display
            size_order = [
                "Empty (0 bytes)",
                "0-10KB",
                "10-100KB",
                "100KB-1MB",
                "1-10MB",
                "10-100MB",
                "100MB-1GB",
                "1GB+"
            ]
            
            if metric == 'count':
                # Count files by size category
                size_data = df['size_category'].value_counts().reindex(size_order).fillna(0)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=size_data.index,
                    y=size_data.values,
                    text=size_data.values,
                    textposition='auto',
                    marker_color='rgb(55, 83, 109)'
                ))
                
                y_axis_title = "Number of Files"
                
            else:  # metric == 'size'
                # Sum file sizes by size category
                size_grouped = df.groupby('size_category')['file_size'].sum().reindex(size_order).fillna(0)
                
                # Convert to MB for display
                size_data_mb = size_grouped / (1024 * 1024)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=size_data_mb.index,
                    y=size_data_mb.values,
                    text=[f"{size:.1f} MB" for size in size_data_mb.values],
                    textposition='auto',
                    marker_color='rgb(55, 83, 109)'
                ))
                
                y_axis_title = "Total Size (MB)"
            
            fig.update_layout(
                title=f"File Size Distribution in {folder_path or 'root'}",
                xaxis_title="File Size Range",
                yaxis_title=y_axis_title,
                autosize=True
            )
            
            return fig
            
        except Exception as e:
            # Log the error
            print(f"Error creating size distribution graph: {str(e)}")
            
            error_fig = go.Figure()
            error_fig.update_layout(
                title="Error Loading Data",
                annotations=[dict(
                    text=f"An error occurred: {str(e)}",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5
                )]
            )
            
            return error_fig

    # Add callback for the file age distribution graph (tab 3)
    @app.callback(
        Output('bargraph3-chart', 'figure'),
        [Input('selected-folder-store', 'data'),
         Input('metric-selector', 'value')]
    )
    def update_age_graph(selected_folder_data, metric):
        """
        Update the file age distribution graph based on the selected folder.
        
        Args:
            selected_folder_data: Data from the selected folder in the sunburst chart
            metric: The metric to display ('count' or 'size')
            
        Returns:
            plotly.graph_objects.Figure: Bar graph of file age distribution
        """
        # Use root folder if no folder is selected
        folder_path = selected_folder_data.get('path', '') if selected_folder_data else ''
        
        try:
            # Get file data for the selected folder (recursive)
            conn = connect_to_database()
            if not conn:
                raise Exception("Failed to connect to database")
                
            df = get_file_data_for_folder(conn, folder_path, include_subfolders=True)
            
            # Early return if no file data
            if df.empty:
                no_data_fig = go.Figure()
                no_data_fig.update_layout(
                    title=f"No files found in {folder_path or 'root'}",
                    annotations=[dict(
                        text="No file data available for this folder",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5
                    )]
                )
                return no_data_fig
                
            # Create the file age distribution graph using our age bucket function
            # Check if modify_time column exists in the data
            if 'modify_time' in df.columns:
                try:
                    # Apply get_age_bucket to categorize each file by age based on last modified date
                    df['age_category'] = df['modify_time'].apply(get_age_bucket)
                    
                    # Define the order of age categories for proper display
                    age_order = [
                        "Today",
                        "This week",
                        "This month",
                        "Last 3 months",
                        "Last 6 months",
                        "Last year",
                        "1-2 years",
                        "2-3 years",
                        "3+ years",
                        "Unknown age"
                    ]
                    
                    if metric == 'count':
                        # Count files by age category
                        age_data = df['age_category'].value_counts().reindex(age_order).fillna(0)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=age_data.index,
                            y=age_data.values,
                            text=age_data.values,
                            textposition='auto',
                            marker_color='rgb(107, 174, 214)'
                        ))
                        
                        y_axis_title = "Number of Files"
                        
                    else:  # metric == 'size'
                        # Sum file sizes by age category
                        age_grouped = df.groupby('age_category')['file_size'].sum().reindex(age_order).fillna(0)
                        
                        # Convert to MB for display
                        age_data_mb = age_grouped / (1024 * 1024)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=age_data_mb.index,
                            y=age_data_mb.values,
                            text=[f"{size:.1f} MB" for size in age_data_mb.values],
                            textposition='auto',
                            marker_color='rgb(107, 174, 214)'
                        ))
                        
                        y_axis_title = "Total Size (MB)"
                    
                    fig.update_layout(
                        title=f"File Age Distribution in {folder_path or 'root'}",
                        xaxis_title="File Age (Last Modified)",
                        yaxis_title=y_axis_title,
                        autosize=True
                    )
                    
                    # Rotate x-axis labels for better readability
                    fig.update_xaxes(tickangle=45)
                    
                    return fig
                    
                except Exception as e:
                    print(f"Error creating age distribution graph: {str(e)}")
                    traceback.print_exc()
                    
                    error_fig = go.Figure()
                    error_fig.update_layout(
                        title="Error Processing Age Data",
                        annotations=[dict(
                            text=f"An error occurred: {str(e)}",
                            showarrow=False,
                            xref="paper",
                            yref="paper",
                            x=0.5,
                            y=0.5
                        )]
                    )
                    
                    return error_fig
            else:
                # Handle case where modify_time column is not available
                missing_fig = go.Figure()
                missing_fig.update_layout(
                    title="File Age Data Unavailable",
                    annotations=[dict(
                        text="Last modified date information is not available for these files",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5
                    )]
                )
                
                return missing_fig
            
        except Exception as e:
            # Log the error
            print(f"Error creating age distribution graph: {str(e)}")
            
            error_fig = go.Figure()
            error_fig.update_layout(
                title="Error Loading Data",
                annotations=[dict(
                    text=f"An error occurred: {str(e)}",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5
                )]
            )
            
            return error_fig

    # Add callback for the file type graph (tab 1)
    @app.callback(
        Output('bargraph1-chart', 'figure'),
        [Input('selected-folder-store', 'data'),
         Input('metric-selector', 'value')]
    )
    def update_file_type_graph(selected_folder_data, metric):
        """
        Update the file type distribution graph based on the selected folder.
        Shows either file count or total size grouped by file type.
        
        Args:
            selected_folder_data: Data from the selected folder in the sunburst chart
            metric: The metric to display ('count' or 'size')
            
        Returns:
            plotly.graph_objects.Figure: Bar graph of file types distribution
        """
        # Use root folder if no folder is selected
        folder_path = selected_folder_data.get('path', '') if selected_folder_data else ''
        
        try:
            # Get file data for the selected folder (recursive if checkbox is selected)
            conn = connect_to_database()
            if not conn:
                raise Exception("Failed to connect to database")
                
            # Determine if we should include files in subfolders
            include_subfolders = True  # Default to include subfolders
            
            # Get the file data based on recursive option
            df = get_file_data_for_folder(conn, folder_path, include_subfolders=True)
            
            # Early return if no file data
            if df.empty:
                no_data_fig = go.Figure()
                no_data_fig.update_layout(
                    title=f"No files found in {folder_path or 'root'}",
                    annotations=[dict(
                        text="No file data available for this folder",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5
                    )]
                )
                return no_data_fig
                
            # Apply get_file_type to categorize each file
            df['file_type'] = df['extension'].apply(get_file_type)
            
            # Group by file type based on metric
            if metric == 'count':
                # Count files by type
                type_distribution = df['file_type'].value_counts().reset_index()
                type_distribution.columns = ['file_type', 'count']
                
                # Sort by count descending
                type_distribution = type_distribution.sort_values('count', ascending=False)
                
                # Set up the figure
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=type_distribution['file_type'],
                    y=type_distribution['count'],
                    text=type_distribution['count'],
                    textposition='auto',
                    marker_color='rgb(26, 118, 255)'
                ))
                
                y_axis_title = "Number of Files"
                
            else:  # metric == 'size'
                # Group by file type and sum the sizes
                type_distribution = df.groupby('file_type')['file_size'].sum().reset_index()
                
                # Convert bytes to MB for display
                type_distribution['size_mb'] = type_distribution['file_size'] / (1024 * 1024)
                
                # Sort by size descending
                type_distribution = type_distribution.sort_values('size_mb', ascending=False)
                
                # Set up the figure
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=type_distribution['file_type'],
                    y=type_distribution['size_mb'],
                    text=[f"{size:.1f} MB" for size in type_distribution['size_mb']],
                    textposition='auto',
                    marker_color='rgb(56, 166, 165)'
                ))
                
                y_axis_title = "Total Size (MB)"
            
            # Update layout with appropriate titles and labels
            fig.update_layout(
                title=f"File Type Distribution in {folder_path or 'root'}",
                xaxis_title="File Type",
                yaxis_title=y_axis_title,
                autosize=True,
                margin=dict(t=50, l=50, r=50, b=100),  # Add margin for long x-axis labels
            )
            
            # Adjust x-axis for readability
            fig.update_xaxes(tickangle=45)
            
            return fig
            
        except Exception as e:
            # Log the error
            print(f"Error creating file type distribution graph: {str(e)}")
            traceback.print_exc()
            
            error_fig = go.Figure()
            error_fig.update_layout(
                title="Error Loading Data",
                annotations=[dict(
                    text=f"An error occurred: {str(e)}",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5
                )]
            )
            
            return error_fig

    return app


def get_top_level_folders(conn, metric='count'):
    """
    Get all top-level folders from the database with their metrics.
    
    Args:
        conn: Database connection
        metric: The metric to use ('count' or 'size')
        
    Returns:
        DataFrame: A DataFrame containing top-level folders with their metrics
    """
    try:
        # Use the rootfolders query to get all top-level folders
        query = qp.get_query('rootfolders')
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("No top-level folders found in database")
            return pd.DataFrame()
            
        # Rename columns for consistency
        if 'folder' in df.columns:
            df.rename(columns={'folder': 'folderPath'}, inplace=True)
            
        if 'filecount' in df.columns:
            df.rename(columns={'filecount': 'file_count'}, inplace=True)
            
        if 'foldercount' in df.columns:
            df.rename(columns={'foldercount': 'folder_count'}, inplace=True)
            
        # Add size column if it doesn't exist (we'll populate it later)
        if 'totalsize' not in df.columns:
            df['totalsize'] = 0
            
        # For each folder, get the actual statistics
        for idx, row in df.iterrows():
            folder_path = row['folderPath']
            stats_query = qp.get_query('folder_stats', folder_path=folder_path)
            stats_df = pd.read_sql_query(stats_query, conn)
            
            if stats_df.empty:
                # print(f"No statistics found for path '{folder_path}'")
                continue
                
            # Extract metrics
            file_count = stats_df['filecount'].iloc[0] if 'filecount' in stats_df.columns else 0
            folder_count = stats_df['foldercount'].iloc[0] if 'foldercount' in stats_df.columns else 0
            total_size = stats_df['totalsize'].iloc[0] if 'totalsize' in stats_df.columns else 0
            
            # Skip folders with no files
            if file_count == 0 and total_size == 0:
                # print(f"Skipping empty folder '{folder_path}'")
                continue
                
            # print(f"Stats for '{folder_path}': {folder_count} folders, {file_count} files, {total_size} bytes")
            
            # Update the metrics in the main dataframe
            df.at[idx, 'filecount'] = file_count
            df.at[idx, 'foldercount'] = folder_count
            df.at[idx, 'totalsize'] = total_size
                
        return df
        
    except Exception as e:
        print(f"Error getting top-level folders: {str(e)}")
        traceback.print_exc()
        return pd.DataFrame()


def process_subfolders(conn, parent_path, max_depth, current_depth, labels, parents, values, 
                      sizes, paths, display_names, folder_counts, parent_paths, metric='count'):
    """
    Recursively process subfolders up to the specified maximum depth.
    
    Args:
        conn: Database connection
        parent_path: The parent folder path
        max_depth: The maximum depth to process
        current_depth: The current depth in the recursion
        labels: List of labels for the sunburst chart
        parents: List of parent labels for the sunburst chart
        values: List of values for the sunburst chart
        sizes: List of sizes for the sunburst chart
        paths: List of full paths for the sunburst chart
        display_names: List of display names for the sunburst chart
        folder_counts: List of folder counts for the sunburst chart
        parent_paths: List of parent paths for the sunburst chart
        metric: The metric to use ('count' or 'size')
    """
    if current_depth >= max_depth:
        return
        
    # Get subfolders for the current parent path
    try:
        # Calculate the prefix length for the SQL query
        path_length = len(parent_path) + 2  # +2 for the trailing slash and offset
        path_length_minus_1 = path_length - 1
        
        # Get all subfolders
        query = qp.get_query('subfolders', path_prefix=parent_path, path_length=path_length, 
                           path_length_minus_1=path_length_minus_1)
        df = pd.read_sql_query(query, conn)
        
        # print(f"DEPTH {current_depth + 1}/{max_depth}: Processing path: '{parent_path}'")
        
        if df.empty:
            # print(f"No subfolders found for path '{parent_path}'")
            return
            
        subfolders = df['folder'].tolist()
        # print(f"DEPTH {current_depth + 1}/{max_depth}: Returning {len(subfolders)} subfolders for path '{parent_path}'")
        
        # Process each subfolder
        for subfolder in subfolders:
            if not subfolder or subfolder == '':
                continue
                
            # Build the full path for this subfolder
            subfolder_path = f"{parent_path}/{subfolder}"
            
            # Get metrics for this subfolder
            stats_query = qp.get_query('folder_stats', folder_path=subfolder_path)
            stats_df = pd.read_sql_query(stats_query, conn)
            
            if stats_df.empty:
                # print(f"No statistics found for path '{subfolder_path}'")
                continue
                
            # Extract metrics
            file_count = stats_df['filecount'].iloc[0] if 'filecount' in stats_df.columns else 0
            folder_count = stats_df['foldercount'].iloc[0] if 'foldercount' in stats_df.columns else 0
            total_size = stats_df['totalsize'].iloc[0] if 'totalsize' in stats_df.columns else 0
            
            # Skip folders with no files
            if file_count == 0 and total_size == 0:
                # print(f"Skipping empty folder '{subfolder_path}'")
                continue
                
            # print(f"DEPTH {current_depth + 1}/{max_depth}: Found subfolder '{subfolder}' at path '{subfolder_path}'")
            # print(f"Stats for '{subfolder_path}': {folder_count} folders, {file_count} files, {total_size} bytes")
            
            # Use the appropriate value based on selected metric
            value = file_count if metric == 'count' else total_size
            
            # Add this subfolder to our data structures
            labels.append(subfolder_path)
            parents.append(parent_path)
            values.append(value)
            sizes.append(total_size)
            paths.append(subfolder_path)
            display_names.append(subfolder)
            folder_counts.append(folder_count)
            parent_paths.append(parent_path)
            
            # Recursively process subfolders
            process_subfolders(conn, subfolder_path, max_depth, current_depth + 1, 
                             labels, parents, values, sizes, paths, display_names, 
                             folder_counts, parent_paths, metric)
                             
    except Exception as e:
        # print(f"Error processing subfolders for '{parent_path}': {str(e)}")
        traceback.print_exc()


def get_file_data_for_folder(conn, folder_path, include_subfolders=False):
    """
    Get file data for a specific folder, with option to include files in subfolders.
    
    Args:
        conn: Database connection
        folder_path (str): Path of the folder to get files from
        include_subfolders (bool): Whether to recursively include files in subfolders
        
    Returns:
        DataFrame: DataFrame containing file details
    """
    try:
        # Choose the appropriate query based on whether to include subfolders
        if include_subfolders:
            query_name = 'detailed_files'
        else:
            query_name = 'folder_files'
            
        # Get the query and execute it
        query = qp.get_query(query_name, folder_path=folder_path)
        # print(f"Executing {query_name} query for folder: {folder_path}")
        
        # Execute the query and fetch results as a DataFrame
        df = conn.execute(query).fetchdf()
        
        if df.empty:
            # print(f"No files found in folder: {folder_path}")
            return pd.DataFrame()
            
        # Process file data for display
        if 'file_size' in df.columns:
            # Store original size value for proper sorting
            df['size_raw'] = df['file_size'].astype(float)
            # Convert file size to KB or MB as appropriate
            df['file_size_display'] = df['file_size'].apply(
                lambda x: f"{x/1024:.2f} KB" if x < 1024*1024 else f"{x/(1024*1024):.2f} MB"
            )
            
        # Format timestamps for readability
        for col in df.columns:
            if 'time' in col or 'timestamp' in col:
                if col in df.columns and df[col].dtype != 'object':
                    try:
                        # Check if we're dealing with milliseconds since epoch (very large numbers)
                        # Unix timestamps typically don't exceed 2 billion (seconds since 1970)
                        if df[col].max() > 2000000000000:  # Threshold for milliseconds
                            # Convert from milliseconds to seconds
                            df[col] = df[col] / 1000
                            
                        # Convert to datetime (unit='s' interprets as seconds since epoch)
                        df[col] = pd.to_datetime(df[col], errors='coerce', unit='s')
                        
                        # Filter out invalid dates (typically 1970-01-01 indicating null values)
                        min_valid_date = pd.Timestamp('1980-01-01')
                        df[col] = df[col].apply(lambda x: None if pd.isnull(x) or x < min_valid_date else x)
                        
                        # Format valid dates as strings
                        df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if x is not None else 'Unknown')
                    except Exception as e:
                        print(f"Error converting timestamp for column {col}: {str(e)}")
                        # If conversion fails, leave as is and continue
        # Add file type column based on extension
        # Check if extension column exists
        if 'extension' in df.columns:
            # Clean up extension values to ensure proper format
            df['extension'] = df['extension'].fillna('')
            df['extension'] = df['extension'].astype(str).str.strip().str.lower()
            
            # Early return for empty extension values
            df['extension'] = df['extension'].apply(lambda x: x[1:] if x and x.startswith('.') else x)
            
            # Apply get_file_type with improved error handling
            df['file_type'] = df['extension'].apply(get_file_type)
        else:
            print("Warning: 'extension' column not found in DataFrame")
            # Create a placeholder column if extension is missing
            df['file_type'] = "Unknown"
        
        # For owner and permissions - these may not be in our dataset, so we'll add placeholders
        if 'file_owner' not in df.columns:
            df['file_owner'] = 'Unknown'
        if 'file_permissions' not in df.columns:
            df['file_permissions'] = 'Unknown'
        
        # print(f"Found {len(df)} files in folder: {folder_path}")
        return df
        
    except Exception as e:
        # print(f"Error retrieving file data: {str(e)}")
        traceback.print_exc()
        return pd.DataFrame()


def format_file_size(size_bytes):
    """
    Format file size from bytes to human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        str: Formatted file size (KB, MB, GB)
    """
    if size_bytes is None:
        return "0 B"
        
    size_bytes = float(size_bytes)
    
    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"


def get_file_type(extension):
    """
    Get a user-friendly file type based on extension.
    
    Args:
        extension: File extension (without the dot)
        
    Returns:
        str: User-friendly file type
    """
    if not extension:
        return "Unknown"
        
    extension = extension.lower()
    
    # Document types
    if extension in ['doc', 'docx', 'txt', 'rtf', 'odt', 'pdf']:
        return "Document"
    # Spreadsheet types
    elif extension in ['xls', 'xlsx', 'csv', 'ods']:
        return "Spreadsheet"
    # Presentation types
    elif extension in ['ppt', 'pptx', 'odp']:
        return "Presentation"
    # Image types
    elif extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg']:
        return "Image"
    # Audio types
    elif extension in ['mp3', 'wav', 'ogg', 'flac', 'aac']:
        return "Audio"
    # Video types
    elif extension in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv']:
        return "Video"
    # Archive types
    elif extension in ['zip', 'rar', '7z', 'tar', 'gz']:
        return "Archive"
    # Code types
    elif extension in ['py', 'js', 'html', 'css', 'java', 'cpp', 'c', 'go', 'php']:
        return "Code"
    # Database types
    elif extension in ['db', 'sqlite', 'sql']:
        return "Database"
    # Executable types
    elif extension in ['exe', 'msi', 'bat', 'sh']:
        return "Executable"
    # Default for unknown types
    else:
        return f"{extension} file"


def get_size_bucket(size_bytes):
    """
    Categorize a file size into a human-readable size bucket.
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Size bucket category
    """
    # Early return for zero or negative sizes
    if size_bytes <= 0:
        return "Empty (0 bytes)"
        
    # Define size thresholds in bytes
    if size_bytes < 10 * 1024:  # Less than 10KB
        return "0-10KB"
    elif size_bytes < 100 * 1024:  # 10KB to 100KB
        return "10-100KB"
    elif size_bytes < 1024 * 1024:  # 100KB to 1MB
        return "100KB-1MB"
    elif size_bytes < 10 * 1024 * 1024:  # 1MB to 10MB
        return "1-10MB"
    elif size_bytes < 100 * 1024 * 1024:  # 10MB to 100MB
        return "10-100MB"
    elif size_bytes < 1024 * 1024 * 1024:  # 100MB to 1GB
        return "100MB-1GB"
    else:  # 1GB or larger
        return "1GB+"


def get_age_bucket(timestamp):
    """
    Categorize a file by age based on last modified date.
    
    Args:
        timestamp: File timestamp (either a string date or datetime object)
        
    Returns:
        str: Age bucket category
    """
    # Early return if timestamp is None or invalid
    if timestamp is None:
        return "Unknown age"
        
    # Convert timestamp to datetime if it's a string
    if isinstance(timestamp, str):
        try:
            file_date = pd.to_datetime(timestamp)
        except:
            return "Unknown age"
    elif isinstance(timestamp, (pd.Timestamp, datetime)):
        file_date = timestamp
    else:
        return "Unknown age"
    
    # Get current date
    current_date = datetime.now()
    
    # Calculate the age in days
    age_days = (current_date - file_date).days
    
    # Define age buckets
    if age_days < 1:
        return "Today"
    elif age_days < 7:
        return "This week"
    elif age_days < 30:
        return "This month"
    elif age_days < 90:
        return "Last 3 months"
    elif age_days < 180:
        return "Last 6 months"
    elif age_days < 365:
        return "Last year"
    elif age_days < 730:
        return "1-2 years"
    elif age_days < 1095:
        return "2-3 years"
    else:
        return "3+ years"


def process_folder_data(conn, parent_path='', max_depth=5, current_depth=0):
    """
    Get folder data for sunburst chart visualization.
    
    Args:
        conn: Database connection
        parent_path (str): Parent path to get subfolders for
        max_depth (int): Maximum depth to traverse
        current_depth (int): Current depth in the recursion
        
    Returns:
        tuple: (labels, parents, values, sizes, paths, display_names, folder_counts, parent_paths)
    """
    if current_depth >= max_depth:
        return [], [], [], [], [], [], [], []
    
    # Get the appropriate query for folder statistics
    query = qp.get_query('folder_stats', folder_path=parent_path)
    # print(f"DEPTH {current_depth+1}/{max_depth}: Processing path: '{parent_path}'")
    
    try:
        # Execute query
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            # print(f"No subfolders found for path '{parent_path}'")
            return [], [], [], [], [], [], [], []
            
        # Debug output - print folder stats columns
        # print(f"Folder stats columns: {df.columns.tolist()}")
        # if 'file_count' in df.columns and 'subfolder_count' in df.columns:
            # print(f"Sample folder counts - Files: {df['file_count'].head().tolist()}, Folders: {df['subfolder_count'].head().tolist()}")
    except Exception as e:
        print(f"Error processing subfolders at '{parent_path}': {str(e)}")
        traceback.print_exc()
        return [], [], [], [], [], [], [], []
    
    # Initialize arrays for chart data
    labels = []
    parents = []
    values = []  # Will store file counts
    sizes = []   # Will store folder sizes in bytes
    paths = []
    display_names = []
    folder_counts = [] # Will store subfolder counts
    parent_paths = []
    
    # Get parent label
    if parent_path == '':
        parent_label = ''
        prefix = ''
    else:
        # For non-root nodes, use the last part of the path as the parent label
        path_parts = parent_path.split('/')
        prefix = parent_path
        parent_label = parent_path  # Use full path as label for parent
        
    # Process each folder in the current level
    for i, row in df.iterrows():
        folder_name = row['folder_name']
        file_count = row['file_count']
        folder_size = row['folder_size']
        subfolder_count = row.get('subfolder_count', 0)  # Use get with default value
        
        # Create path for this folder
        if parent_path:
            folder_path = f"{parent_path}/{folder_name}"
        else:
            folder_path = folder_name
            
        # Use the full path as the unique label
        folder_label = folder_path
        
        # Get just the folder name for display
        display_name = folder_name
        
        # Add this folder to the chart data
        labels.append(folder_label)
        parents.append(parent_label)
        values.append(file_count)  # Number of files directly in this folder
        sizes.append(folder_size)  # Size of all files in this folder and subfolders
        folders.append(max(subfolder_count, 1))  # Ensure at least 1 so it's visible
        paths.append(folder_path)
        display_names.append(display_name)
        folder_counts.append(subfolder_count)  # Number of immediate subfolders
        parent_paths.append(parent_path)
        
        # Process subfolders recursively
        sub_labels, sub_parents, sub_values, sub_sizes, sub_paths, sub_display_names, sub_folder_counts, sub_parent_paths = process_folder_data(
            conn, folder_path, max_depth, current_depth + 1
        )
        
        # Add subfolder data to the charts
        labels.extend(sub_labels)
        parents.extend(sub_parents)
        values.extend(sub_values)
        sizes.extend(sub_sizes)
        paths.extend(sub_paths)
        display_names.extend(sub_display_names)
        folder_counts.extend(sub_folder_counts)
        parent_paths.extend(sub_parent_paths)
        
    # print(f"DEPTH {current_depth+1}/{max_depth}: Returning {len(df)} subfolders for path '{parent_path}'")
    return labels, parents, values, sizes, paths, display_names, folder_counts, parent_paths


def main():
    """
    Main function to run the Dash application.
    """
    global conn, max_db_depth
    
    # Print version information
    # print(f"Using Plotly version: {plotly.__version__}")
    # print(f"Using Dash version: {dash.__version__}")
    
    try:
        # Connect to DuckDB using config settings
        conn = connect_to_database()
        if conn is None:
            print("Failed to connect to database. Exiting.")
            return
        
        # Get database stats
        tables = conn.execute("SHOW TABLES").fetchall()
        # print(f"Database contains {len(tables)} tables: {', '.join([t[0] for t in tables])}")
        
        # Get data from database
        totals_result = conn.execute(qp.get_query('totals')).fetchone()
        total_folders = totals_result[0] if totals_result else 0
        total_files = totals_result[1] if totals_result else 0
        total_size = totals_result[2] if totals_result else 0
        
        # print(f"Database contains {total_folders:,} total folders")
        # print(f"Database contains {total_files:,} total files")
        # print(f"Total data size: {total_size / (1024*1024*1024):.2f} GB")
        
        # Detect max depth in database
        max_db_depth = get_max_folder_depth(conn)
        # print(f"Maximum folder depth in database: {max_db_depth}")
        
        # Start with empty hierarchy, will be populated on demand
        initial_hierarchy = []
        
        # Create and run the Dash app
        app = create_dash_app(initial_hierarchy, total_files, total_size, total_folders)
        
        # Get server settings from config
        port = cfg.get_server_port()
        debug = cfg.get_server_debug()
        
        # Start the server
        # print(f"Starting server on port {port} (debug={debug})")
        app.run(debug=debug, port=port)
        
    except Exception as e:
        print(f"Error connecting to database or running app: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
