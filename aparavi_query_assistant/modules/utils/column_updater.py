#!/usr/bin/env python3
"""
Column Updater Utility

This module provides a utility function to update the system prompt with
the latest Aparavi column information from the reference document.
"""

import re
import os
import markdown
from bs4 import BeautifulSoup


def update_system_prompt_columns(prompt_file, columns_md_file):
    """
    Update the system prompt with the latest Aparavi column information
    
    Args:
        prompt_file (str): Path to the prompts.py file
        columns_md_file (str): Path to the aparavi-columns.md reference file
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    if not os.path.exists(prompt_file) or not os.path.exists(columns_md_file):
        print(f"Error: One or more files don't exist")
        return False
        
    try:
        # Read the reference markdown file
        with open(columns_md_file, 'r') as f:
            md_content = f.read()
            
        # Convert markdown to HTML for easier parsing
        html = markdown.markdown(md_content)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract column information from the first table (core columns)
        columns = []
        for row in soup.find_all('table')[0].find_all('tr')[1:]:  # Skip header
            cells = row.find_all('td')
            if len(cells) >= 4:
                pretty_name = cells[0].text.strip()
                db_name = cells[1].text.strip()
                description = cells[3].text.strip()
                
                if db_name and not db_name.isspace():
                    columns.append((db_name, pretty_name, description))
        
        # Sort by column name
        columns.sort(key=lambda x: x[0])
        
        # Generate the new column definitions for the prompt
        column_text = []
        for db_name, pretty_name, description in columns[:30]:  # Limit to most important columns
            column_text.append(f"   - {db_name}: {description[:50] + '...' if len(description) > 50 else description}")
        
        # Read the current prompt file
        with open(prompt_file, 'r') as f:
            prompt_content = f.read()
            
        # Find the section where we list field names and update it
        field_section_pattern = r"4\. Use exact field names from Aparavi's schema, including:.*?(?=\n\n)"
        field_section_replacement = f"4. Use exact field names from Aparavi's schema, including:\n" + "\n".join(column_text)
        
        updated_content = re.sub(field_section_pattern, field_section_replacement, prompt_content, flags=re.DOTALL)
        
        # Write the updated content back to the file
        with open(prompt_file, 'w') as f:
            f.write(updated_content)
            
        print(f"Successfully updated {prompt_file} with column information from {columns_md_file}")
        return True
        
    except Exception as e:
        print(f"Error updating system prompt: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    prompt_file = os.path.join(current_dir, "prompts.py")
    columns_md_file = os.path.join(project_dir, "ref", "aparavi-columns.md")
    
    update_system_prompt_columns(prompt_file, columns_md_file)
