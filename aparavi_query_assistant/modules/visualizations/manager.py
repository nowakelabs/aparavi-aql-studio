#!/usr/bin/env python3
"""
Visualization Manager for AQL Studio

This module manages different visualization types for AQL query results.
It determines which visualization to use based on the query result structure
and provides a unified interface for the application.
"""

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Tuple, Optional, Union, Any

# Import visualization modules
from modules.visualizations.sunburst import create_sunburst_visualization, get_plotly_json


class VisualizationManager:
    """Manages different visualization types for AQL query results."""
    
    VIZ_TYPES = {
        "sunburst": {
            "name": "Sunburst Chart",
            "description": "Hierarchical data visualization showing parent-child relationships",
            "suitable_for": ["file paths", "hierarchical data", "nested categories"],
            "min_rows": 10,
            "module": "sunburst"
        },
        "table": {
            "name": "Data Table",
            "description": "Standard tabular data display",
            "suitable_for": ["all data types"],
            "min_rows": 1,
            "module": None  # Built-in to AQL Studio
        }
    }
    
    def __init__(self):
        """Initialize the visualization manager."""
        self.available_visualizations = list(self.VIZ_TYPES.keys())
    
    def get_available_visualizations(self) -> List[Dict[str, Any]]:
        """
        Get list of available visualization types.
        
        Returns:
            List of visualization type dictionaries
        """
        return [
            {"id": viz_id, **viz_info}
            for viz_id, viz_info in self.VIZ_TYPES.items()
        ]
    
    def suggest_visualizations(self, df: pd.DataFrame) -> List[str]:
        """
        Suggest appropriate visualization types based on the data.
        
        Args:
            df: DataFrame with query results
            
        Returns:
            List of recommended visualization type IDs
        """
        if df.empty:
            return []
            
        recommendations = []
        
        # Always include table as fallback
        recommendations.append("table")
        
        # Check if any columns contain path-like data for sunburst
        if any('path' in col.lower() for col in df.columns):
            recommendations.append("sunburst")
        elif any('/' in str(val) for val in df.iloc[0].values if isinstance(val, str)):
            recommendations.append("sunburst")
            
        return recommendations
    
    def create_visualization(self, 
                             viz_type: str, 
                             df: pd.DataFrame, 
                             title: str = "Query Results Visualization",
                             options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a visualization of the specified type.
        
        Args:
            viz_type: Visualization type ID
            df: DataFrame with query results
            title: Title for the visualization
            options: Additional options for the visualization
            
        Returns:
            Dictionary with visualization data and metadata
        """
        if options is None:
            options = {}
            
        if viz_type not in self.available_visualizations:
            return {
                "success": False,
                "error": f"Visualization type '{viz_type}' not supported",
                "viz_type": viz_type,
                "data": None
            }
            
        try:
            # Handle each visualization type
            if viz_type == "sunburst":
                path_column = options.get("path_column")
                value_column = options.get("value_column")
                
                result = create_sunburst_visualization(
                    df, 
                    path_column=path_column,
                    value_column=value_column,
                    title=title
                )
                
                if result["success"]:
                    # Convert Plotly figure to JSON for frontend
                    plotly_json = get_plotly_json(result["figure"])
                    
                    return {
                        "success": True,
                        "error": None,
                        "viz_type": viz_type,
                        "title": title,
                        "data": {
                            "plotly_figure": plotly_json,
                            "path_column": result["path_column"],
                            "value_column": result["value_column"]
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": result["error"],
                        "viz_type": viz_type,
                        "data": None
                    }
                    
            elif viz_type == "table":
                # Table view is the default in AQL Studio, just return success
                return {
                    "success": True,
                    "error": None,
                    "viz_type": viz_type,
                    "title": title,
                    "data": None  # No special data needed
                }
                
            else:
                return {
                    "success": False,
                    "error": f"Visualization type '{viz_type}' implementation not found",
                    "viz_type": viz_type,
                    "data": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating visualization: {str(e)}",
                "viz_type": viz_type,
                "data": None
            }
            
    def get_visualization_options(self, viz_type: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get configuration options for a visualization type based on data.
        
        Args:
            viz_type: Visualization type ID
            df: DataFrame with query results
            
        Returns:
            Dictionary of configuration options
        """
        options = {
            "columns": df.columns.tolist()
        }
        
        if viz_type == "sunburst":
            # Import the detection functions from sunburst module
            from modules.visualizations.sunburst import detect_hierarchy_columns, detect_value_columns
            
            # Add sunburst-specific options
            options["detected_path_columns"] = detect_hierarchy_columns(df)
            options["detected_value_columns"] = detect_value_columns(df)
            
        return options
