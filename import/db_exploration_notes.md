# DuckDB Database Exploration Notes

## Database Overview
This document contains notes from exploring the DuckDB database (`.duckdb` file) for the ADS Dashboard project.

## Initial Database Structure
From the Database Structure and Schema.txt file, we understand the database contains these main tables:

- **objects**: Stores file and folder metadata
  - `objectId`: Primary identifier for files and folders
  - `parentId`: Reference to parent directory's objectId
  - `classId`: Type identifier (e.g., 'idxobject' for files, 'idxcontainer' for folders)
  - `name`: Name of the file or directory
  - `extension`: File extension (null for directories)
  - `nodeObjectId`: Used for linking to classifications and permissions

- **instances**: Contains detailed file instance information
  - `instanceId`: Instance identifier
  - `objectId`: Foreign key to objects table
  - `size`: File size in bytes
  - `createTime`: File creation timestamp
  - `modifyTime`: Last modification timestamp
  - `accessTime`: Last access timestamp
  - `tags`: File tags

- **parentPaths**: Stores path information for containers/directories
  - `parentId`: Directory identifier
  - `uri`: URI representation of the path
  - `parentPath`: Full path to the container

- **classifications**: Contains classification metadata
  - `nodeObjectId`: Reference to the object
  - `classificationSet`: Classification information

- **osPermissions**: Stores permission information
  - `nodeObjectId`: Reference to the object
  - `permissionSet`: Permission metadata

## Script Exploration Findings
After running our exploration script, we discovered more details about the database structure and content.

### Table Statistics
The database contains 11 tables with the following row counts:
- objects: 22,516 rows
- instances: 21,949 rows
- parentPaths: 339 rows
- classifications: 249 rows
- messages: 246 rows
- osPermissions: 145 rows
- osSecurity: 30 rows
- services: 5 rows
- tagSets: 4 rows
- datasets: 1 row
- encryption: 0 rows

### Schema Details
Additional columns found in key tables:

**objects**:
- Additional columns include: createdAt, updatedAt, and other metadata fields

**instances**:
- Contains numerous fields beyond the basic ones, including:
  - messageIds
  - flags
  - processTime, processPipe
  - storeTime, storeSize
  - version
  - metadata
  - classificationId

**Additional tables discovered**:
- messages: Likely stores content referenced by messageIds in instances
- tagSets: Appears to define tag collections
- datasets: Defines dataset context
- services: Core services information
- osSecurity: Security-related information

### Relationships
Strong relationships detected:
- parentPaths.parentId → objects.objectId (100% match)
- instances.objectId → objects.objectId
- objects.nodeObjectId → classifications.nodeObjectId
- objects.nodeObjectId → osPermissions.nodeObjectId
- services.nodeObjectId → objects.nodeObjectId

### Data Insights
1. **File Types**:
   - Text files (txt) are the most common with 19,165 files
   - PDF files: 1,416
   - Email files (eml): 425 
   - JavaScript files (js): 333
   - Office documents (docx, doc, xlsx, pptx): 225+

2. **Directory Structure**:
   - Major top-level directories: Science (8,851 files), Politics (6,002), Crime (2,200), Entertainment (2,106)
   - There are 191 directories in total

3. **File Size Distribution**:
   - Under 1KB: 7,811 files
   - 1KB to 1MB: 13,839 files
   - 1MB to 10MB: 260 files
   - 10MB to 100MB: 39 files
   - No files over 100MB

## Dashboard Requirements
Based on the database structure, a dashboard should provide:

1. File system hierarchy visualization
2. File type distribution charts
3. Size distribution analysis
4. Time-based analysis (creation/modification patterns)
5. Classification and permission insights
6. Storage usage by directory/container

## Sunburst Visualization Development

### Double-Counting Issue and Resolution
We developed multiple versions of a sunburst visualization to display the file system hierarchy:

1. **Initial approach (simple_sunburst.py)**:
   - Used the CSV export (foldersummary.csv)
   - Built a basic visualization but had limited interactivity

2. **DuckDB integration (duckdb_sunburst.py)**:
   - Connected directly to the DuckDB database
   - Queried parentPaths, objects, and instances tables
   - Encountered a significant issue with file counts:
     - UI reported ~44K total files while database only contained ~22K files
     - Root cause: double-counting during hierarchy aggregation

3. **Fixed version (fixed_duckdb_sunburst.py)**:
   - Fixed SQL query to count distinct object IDs
   - Completely rewrote the hierarchy aggregation logic
   - Added direct database count verification
   - Added prominent display of correct total metrics (21,949 files, 1.8 GB)

### Key Improvements in fixed_duckdb_sunburst.py:
1. **SQL Query Update**:
   ```sql
   COUNT(DISTINCT objectId) as Count  -- Instead of COUNT(*)
   ```

2. **Hierarchy Aggregation Fix**:
   - Identified leaf nodes (those that don't have children)
   - Reset intermediate nodes to zero to prevent double-counting
   - Propagated counts up from leaf to root in a single pass
   - Set the root node stats directly from database totals

3. **Verification Steps**:
   - Added detailed logging of counts at each processing step
   - Cross-checked with direct database queries
   - Ensured consistent total counts throughout the application

4. **UI Enhancements**:
   - Added prominent metrics cards showing total files and size
   - Improved tooltip formatting
   - Added toggling between file count and size views

### Database Statistics
The visualization confirms the following database statistics:
- Total files: 21,949
- Total size: 1.8 GB
- Total directories: 340 (including the root)



## File Metadata Exploration

### Available File Metadata

The database contains rich metadata for files across several tables:

#### From the objects table:
- **Basic File Info**: name, extension, uniqueName
- **Identifiers**: objectId, parentId, uniqueId
- **Classification**: classId
- **Size Info**: primarySize
- **Timestamps**: createdAt, updatedAt
- **Metadata**: tags, flags

#### From the instances table:
- **Size Information**: size, storeSize
- **Time Information**:
  - createTime, modifyTime, accessTime, storeTime
  - docCreateTime, docModifyTime
- **User Information**:
  - docCreator, docModifier
- **Classification**: classificationId
- **Versioning**: version
- **Security**: encryptionId
- **Deletion Status**: deletedAt

#### From the parentPaths table:
- **Location Info**: parentPath, uri

### Path Structure Notes

File paths in the database follow this pattern:
- All paths consistently end with a trailing slash (e.g., "File System/D:/data/DriveD/HR/")
- The top-level folder is "File System/"
- Actual file data is stored in objects and instances tables, linked by parentId

### Implemented Queries

Two new queries have been implemented in `query_parameters.py`:

1. **RECURSIVE_FILES_QUERY**: Retrieves all files in a specified folder AND all its subfolders
   - Uses `LIKE '{folder_path}%'` to match all paths starting with the given folder
   - Includes comprehensive file metadata (name, extension, size, timestamps, etc.)
   - Sorts results by path and filename

2. **FOLDER_FILES_QUERY**: Retrieves ONLY files directly in the specified folder (non-recursive)
   - Uses `= '{folder_path}/'` for exact path matching
   - Includes the same comprehensive file metadata
   - Sorts results by filename only

### Example Usage

```python
# Get all files in a folder and its subfolders (recursive)
recursive_query = qp.get_query('detailed_files', folder_path='File System/D:/data/DriveD')
recursive_results = conn.execute(recursive_query).fetchdf()

# Get only files directly in a folder (non-recursive)
folder_query = qp.get_query('folder_files', folder_path='File System/D:/data/DriveD')
folder_results = conn.execute(folder_query).fetchdf()
```

### Future Enhancements

Potential enhancements to the file metadata visualization:
