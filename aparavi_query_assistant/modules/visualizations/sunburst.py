#!/usr/bin/env python3
"""
Sunburst Visualization for AQL Studio

This module adapts the sunburst visualization technique for displaying hierarchical
query results from Aparavi Data Suite AQL queries. It transforms tabular data with
hierarchical relationships into an interactive sunburst chart.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re
import json
from typing import Dict, List, Tuple, Optional, Union, Any


def prepare_sunburst_data(df: pd.DataFrame, 
                          path_column: str, 
                          value_column: Optional[str] = None,
                          path_delimiter: str = '/',
                          max_depth: int = 5) -> Tuple[List, List, List, List, List]:
    """
    Prepare data for the sunburst visualization from the dataframe with path information.
    
    Args:
        df: DataFrame containing hierarchical data
        path_column: Column name containing the hierarchical path
        value_column: Column name for values/sizes (optional)
        path_delimiter: Delimiter used in the path strings
        max_depth: Maximum depth to display in the visualization
        
    Returns:
        tuple: (labels, parents, values, ids, paths)
    """
    # Initialize lists to store the hierarchical structure
    labels = ['Root']  # Start with root node
    parents = ['']     # Root has no parent
    values = [0]       # Initialize root value
    ids = ['root']     # Unique ID for root
    paths = ['']       # Path for root
    
    # Process each row in the dataframe
    for _, row in df.iterrows():
        # Get path and split it
        path = str(row[path_column])
        if not path:
            continue
            
        path_components = path.split(path_delimiter)
        # Limit depth if needed
        path_components = path_components[:max_depth] if len(path_components) > max_depth else path_components
        
        # Get value if value column provided
        value = float(row[value_column]) if value_column and value_column in row else 1
        
        # Add value to root's total
        values[0] += value
        
        # Process each level of the path
        current_path = ""
        current_id = "root"
        parent_id = "root"
        
        for i, component in enumerate(path_components):
            if not component:  # Skip empty components
                continue
                
            # Build the current path
            if i == 0:
                current_path = component
            else:
                current_path = f"{current_path}{path_delimiter}{component}"
                
            # Create ID for this level
            current_id = f"id_{current_path.replace(path_delimiter, '_')}"
            
            # Check if this node already exists
            if current_id in ids:
                # Node exists, just add the value
                idx = ids.index(current_id)
                values[idx] += value
            else:
                # Node doesn't exist, add it
                labels.append(component)
                parents.append(parent_id)
                values.append(value)
                ids.append(current_id)
                paths.append(current_path)
            
            # Update parent for next level
            parent_id = current_id
    
    return labels, parents, values, ids, paths


def create_sunburst_figure(labels: List[str], 
                           parents: List[str], 
                           values: List[float], 
                           ids: List[str],
                           paths: List[str],
                           title: str = "Hierarchy Visualization") -> go.Figure:
    """
    Create a sunburst figure for visualization.
    
    Args:
        labels: List of node labels
        parents: List of parent labels
        values: List of values for each node
        ids: List of unique ids for each node
        paths: List of full paths for each node
        title: Title for the visualization
        
    Returns:
        plotly.graph_objects.Figure: A sunburst figure
    """
    # Create sunburst trace
    sunburst = go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        ids=ids,
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Value: %{value}<br>Path: %{customdata}<extra></extra>',
        customdata=paths,
        maxdepth=3,  # Default display depth
    )
    
    # Create the figure and update layout
    fig = go.Figure(sunburst)
    fig.update_layout(
        title=title,
        margin=dict(t=60, l=0, r=0, b=0),
        height=600,
        width=800,
    )
    
    # Add buttons to control depth
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                buttons=[
                    dict(
                        args=[{"maxdepth": i+1}],
                        label=f"Depth {i+1}",
                        method="restyle"
                    ) for i in range(5)  # Buttons for depths 1-5
                ],
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.1,
                yanchor="top"
            )
        ]
    )
    
    return fig


def detect_hierarchy_columns(df: pd.DataFrame) -> List[str]:
    """
    Detect columns that might contain hierarchical path information.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        List of column names that likely contain path data
    """
    potential_path_columns = []
    
    # Regular expression patterns that suggest path data
    path_patterns = [
        r'.*path.*',
        r'.*location.*',
        r'.*directory.*',
        r'.*folder.*',
        r'.*hierarchy.*'
    ]
    
    # Check each string column
    for column in df.columns:
        # Check column name against patterns
        if any(re.match(pattern, column.lower()) for pattern in path_patterns):
            potential_path_columns.append(column)
            continue
            
        # Only check string columns
        if df[column].dtype != 'object':
            continue
            
        # Sample values to check for path-like strings
        sample = df[column].dropna().astype(str).sample(min(10, len(df[column]))).tolist()
        
        # Count samples with path-like characteristics
        path_like_count = sum(1 for s in sample if '/' in s and s.count('/') >= 2)
        
        # If most samples contain path separators, it's likely a path column
        if path_like_count >= len(sample) * 0.7:
            potential_path_columns.append(column)
    
    return potential_path_columns


def detect_value_columns(df: pd.DataFrame) -> List[str]:
    """
    Detect columns that might contain numeric values useful for sizing nodes.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        List of column names that contain numeric data
    """
    # Get numeric columns
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    
    # Prioritize columns with size-related names
    size_related_columns = []
    for column in numeric_columns:
        if any(keyword in column.lower() for keyword in ['size', 'bytes', 'count', 'num', 'total', 'sum']):
            size_related_columns.append(column)
    
    # Return prioritized list
    return size_related_columns + [col for col in numeric_columns if col not in size_related_columns]


def create_sunburst_visualization(df: pd.DataFrame, 
                                  path_column: Optional[str] = None,
                                  value_column: Optional[str] = None,
                                  title: str = "Hierarchy Visualization") -> Dict[str, Any]:
    """
    Create a sunburst visualization from query results.
    
    Args:
        df: DataFrame containing query results
        path_column: Column name containing hierarchical paths (if None, will attempt to detect)
        value_column: Column name containing values for sizing (if None, will attempt to detect)
        title: Title for the visualization
        
    Returns:
        Dictionary with:
        - 'figure': Plotly figure object
        - 'path_column': Path column used
        - 'value_column': Value column used
        - 'success': Boolean indicating success
        - 'error': Error message if any
    """
    try:
        if df.empty:
            return {
                'success': False,
                'error': 'No data available for visualization',
                'figure': None,
                'path_column': None,
                'value_column': None
            }
        
        # Detect path column if not provided
        if not path_column:
            potential_path_columns = detect_hierarchy_columns(df)
            if potential_path_columns:
                path_column = potential_path_columns[0]
            else:
                return {
                    'success': False,
                    'error': 'No suitable hierarchy path column detected',
                    'figure': None,
                    'path_column': None,
                    'value_column': None
                }
        
        # Detect value column if not provided
        if not value_column:
            potential_value_columns = detect_value_columns(df)
            if potential_value_columns:
                value_column = potential_value_columns[0]
        
        # Prepare sunburst data
        labels, parents, values, ids, paths = prepare_sunburst_data(
            df, 
            path_column=path_column,
            value_column=value_column
        )
        
        # Create the figure
        fig = create_sunburst_figure(
            labels, 
            parents, 
            values, 
            ids,
            paths,
            title=title
        )
        
        return {
            'success': True,
            'error': None,
            'figure': fig,
            'path_column': path_column,
            'value_column': value_column
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'figure': None,
            'path_column': path_column,
            'value_column': value_column
        }


def get_plotly_json(fig: go.Figure) -> str:
    """
    Convert a Plotly figure to JSON for use in JavaScript.
    
    Args:
        fig: Plotly figure object
        
    Returns:
        JSON string representation of the figure
    """
    return json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder)


class PlotlyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Plotly figures"""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict('records')
            if isinstance(obj, pd.Series):
                return obj.tolist()
        except:
            pass
        
        return json.JSONEncoder.default(self, obj)
