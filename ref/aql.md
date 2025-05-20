# Aparavi Querying Language (AQL) - Comprehensive Guide

## Introduction

Aparavi Querying Language (AQL) is a SQL-based query language designed to allow users to query and analyze passive data across distributed storage locations. AQL combines Node.js with SQL Common Table Expressions (CTEs) to provide a scalable way to query data regardless of where it's stored.

This guide provides a comprehensive overview of AQL's syntax, functionality, and practical examples to help you effectively work with your data.

## Getting Started

### Overview

AQL is designed to be SQL-92 compliant, making it familiar to those with SQL experience. However, due to its architecture which uses CTEs to query multiple tables for aggregated results, AQL cannot support:

- SQL Joins
- SQL Subqueries

### Running Queries

To run AQL queries:

1. Login to your Aparavi Portal
2. Navigate to Reports tab
3. Create Custom Report
4. Open the "By File: Name" dropdown
5. Scroll to bottom and choose "By SELECT"
6. Replace the sample query with your query
7. Click Search

### Basic Query Execution

```sql
DB QUERY "SELECT name;"
```

To view the parsed SQL query sent to aggregators:

```sql
PARSE SQL "SELECT name;"
```

## Core SQL Components

### SELECT Statement

The `SELECT` statement retrieves data about your files from aggregators:

```sql
-- Basic select for file names
SELECT name;

-- Select multiple columns
SELECT name, classification, createdAt;
```

#### Aliases

Use aliases to make columns more readable:

```sql
SELECT classification AS Class;
```

#### DISTINCT

Retrieve only distinct (different) values:

```sql
SELECT DISTINCT name;
```

#### CASE Expression

Use case statements for conditional logic:

```sql
SELECT
    classification AS "Classification",
    CASE
      WHEN confidence >= 95 THEN 'On fire!'
      WHEN confidence >= 90 THEN 'Hot'
      WHEN confidence >= 85 THEN 'Warm'
      WHEN confidence >= 80 THEN 'Cold'
      ELSE 'Ice cold!'
    END AS "Classification_Temperature";
```

### FROM Clause

The `FROM` clause is optional and takes one of two forms:

```sql
SELECT name FROM STORE;
-- or
SELECT name FROM STORE('{NODE}/path/to/directory');
```

### WHERE Clause

Filter records based on specified conditions:

```sql
SELECT name
WHERE name = 'file_name.txt';
```

### LIMIT and OFFSET

Control the number of records returned:

```sql
-- Return only 10 records
SELECT parentPath AS "RootPath"
LIMIT 10;

-- Skip first 15 records and return next 10
SELECT parentPath AS "RootPath"
LIMIT 10
OFFSET 15;
```

### ORDER BY

Sort the result set:

```sql
SELECT
    name,
    classification,
    createdAt
ORDER BY createdAt ASC
LIMIT 10;
```

## Advanced Query Features

### WHICH Clause

The `WHICH` clause adds contextualization to your queries, helping search through document content:

#### CONTAIN / CONTAINS / CONTAINING

Search for specific words or characters:

```sql
SELECT name WHICH CONTAIN 'Blue';
SELECT name WHICH CONTAINS 'Red Corvette';
SELECT name CONTAINING 'IP' AND NEAR('network', 'server');
```

#### NEAR

Find content where specified terms appear close to each other:

```sql
SELECT name CONTAINING 'IP' AND NEAR('network', 'server');
```

#### SYNONYMS

Search for synonyms of specified terms:

```sql
SELECT name WHICH CONTAINS SYNONYM('doctor');
```

#### STEM

Search for word stems:

```sql
SELECT name CONTAINING STEM('drive') AND NOT 'AAA';
```

#### PHRASE

Search for specific phrases:

```sql
SELECT name WHICH CONTAINS PHRASE('were waiting for a movie');
```

#### ANY, ALL, NONE

Control how multiple search terms are matched:

```sql
-- Match if any term is found
SET @@DEFAULT_COLUMNS=searchHit;
SELECT name, size, searchHit
WHICH CONTAIN ANY ('quido');

-- Match if all terms are found
SELECT name, size, searchHit
WHICH CONTAIN ALL ('quido');

-- Match if none of the terms are found
SELECT name, size, searchHit
WHICH CONTAIN NONE ('quido');
```

### LIKE Operator

Search for patterns:

```sql
SELECT
    osOwner AS "Owner",
    path AS "Location",
    classification AS "Classification"
WHERE classification LIKE 'U.S.%';
```

Wildcards used with LIKE:
- `%` - Represents zero, one, or multiple characters
- `_` - Represents one single character

## Aggregation Functions

### GROUP BY

Group rows with the same values:

```sql
SELECT
    classification AS "Class",
    COUNT(osOwner) as "Files"
GROUP BY Class;
```

### HAVING

Filter groups based on conditions:

```sql
SELECT
    YEAR(createTime) AS "year",
    MONTH(createTime) AS "month",
    COUNT(size),
    SUM(size) AS totalSize
GROUP BY
    "year", "month"
HAVING 
    "year" > 2012;
```

### Aggregate Functions

- `COUNT()`: Count rows matching criteria
- `SUM()`: Calculate the sum of values
- `AVG()`: Calculate the average of values
- `MIN()`: Find the minimum value
- `MAX()`: Find the maximum value

Examples:

```sql
-- Count files by classification
SELECT
    classification AS "Class",
    COUNT(osOwner) as "Files"
GROUP BY Class;

-- Sum file sizes by classification
SELECT
    classification AS "Class",
    SUM(size) as "Size",
    SUM(storageCost) as "TotalStorageCost"
GROUP BY Class;

-- Calculate average confidence by classification
SELECT
    classification as "Class",
    AVG(confidence) as "Confidence"
GROUP BY Class;

-- Find lowest confidence by classification
SELECT
    classification AS "Class",
    MIN(confidence) as "LowestConfidence"
GROUP BY Class;

-- Find highest confidence by classification
SELECT
    classification as "Class",
    MAX(confidence) as "HigestConfidence"
GROUP BY Class;
```

## Helper Functions

### Mathematical Functions

- `ABS()`: Return absolute value
- `CEILING()`: Round up to nearest integer
- `FLOOR()`: Round down to nearest integer

```sql
SELECT ABS(-243.5) AS AbsNum;
SELECT CEILING(25.75) AS CeilValue;
SELECT FLOOR(25.75) AS FloorValue;
```

### Date/Time Functions

- `DATE()`: Extract date part
- `DAY()`: Return day of month
- `DAYOFWEEK()`: Return weekday index
- `DAYOFYEAR()`: Return day of year
- `HOUR()`: Return hour part
- `ISODATE()`: Return date in ISO format
- `MINUTE()`: Return minute part
- `MONTH()`: Return month part
- `NOW()/TODAY()`: Return current date/time
- `SECOND()`: Return seconds part
- `WEEK()`: Return week number
- `YEAR()`: Return year part
- `LOCALDATE()`: Format date for readability

Examples:

```sql
SELECT YEAR('2017/08/25') AS Year;
SELECT MONTH('2017/08/25') AS MonthIndex;
SELECT NOW() AS CurrentTime;
SELECT LOCALDATE(1670443995) AS FormattedDate;
```

### String Functions

- `COALESCE()`: Returns first non-null value
- `CONCAT()`: Combine strings
- `LEFT()`: Extract characters from left
- `RIGHT()`: Extract characters from right
- `LENGTH()`: Return string length
- `INSTR()/LOCATE()`: Find position of substring
- `ISNULL()`: Check if null
- `LPAD()/RPAD()`: Pad strings
- `LTRIM()/RTRIM()/TRIM()`: Remove whitespace
- `SUBSTR()`: Extract substring
- `UPPER()/LOWER()`: Change case

Examples:

```sql
SELECT CONCAT('aparavi-', 'academy.eu') AS ConcattedString;
SELECT LEFT('AQL Tutorial', 3) AS ExtractString;
SELECT LENGTH('AQL Tutorial') AS LengthOfString;
SELECT UPPER('AQL Tutorial is FUN!') AS UpperCase;
```

### Advanced Functions

- `COMPONENTS()`: Return directories from path
- `TRUNCATE()`: Remove decimal places
- `LOCALNUMBER()`: Format number with commas

```sql
SELECT
    COMPONENTS(parentPath, 4) AS root,
    SUM(size),
    COUNT(name)
GROUP BY
    root
ORDER BY root;

SELECT TRUNCATE(3.14159, 1) AS TruncatedValue;
SELECT LOCALNUMBER(156156456) AS FormattedValue;
```

## Variables

Variables let you establish values for use in queries. Variable names must begin with `@`.

### Custom Variables

```sql
-- Set a custom variable
SET @USER = 'USERNAME';

-- Use in query
SELECT
    osOwner as "Owner",
    path as "Location"
WHERE
    osPermission like CONCAT('%/', @USER, '%');
```

### System Variables

System variables begin with `@@` and control query behavior:

- `@@ADD_DEFAULT_COLUMNS`: Auto-add default columns
- `@@DEFAULT_COLUMNS`: Define default columns
- `@@DISABLE_AGGREGATION`: Disable aggregation expressions
- `@@LEFT_JOIN`: Control if rows without selected columns are returned
- `@@CONTEXTWORDS`: Control words retrieved for context columns
- `@@CONTEXTCOUNT`: Set maximum number of hits to return

Example:

```sql
-- Turn off containers
SET @@LEFT_JOIN=false;

-- Set default columns
SET @@DEFAULT_COLUMNS=searchHit;
```

## Type System

AQL supports these data types:

- `NUMBER`
- `DATE`
- `STRING`
- `OBJECT`

Use `CAST()` to convert between types:

```sql
SELECT CAST(3 AS STRING) AS "Cast_String";
```

## Practical Examples

### 1. Files by Creation Time

```sql
SELECT
    YEAR(createTime) AS yr,
    MONTH(createTime) AS mo,
    SUM(size) AS totalSize,
    COUNT(size) AS totalCount
GROUP BY
    yr, mo
HAVING
    totalCount > 0
ORDER BY
    yr, mo;
```

### 2. Total Size of Subdirectories

```sql
SELECT
    COMPONENTS(parentPath, 4) AS root,
    SUM(size),
    COUNT(name)
GROUP BY
    root
ORDER BY root;
```

### 3. Classification Distribution

```sql
SET @@LEFT_JOIN=false;

SELECT
    classification AS Class,
    COUNT(osOwner) as Files,
    SUM(size) as "Size",
    SUM(storageCost) as "Total_Storage"
GROUP BY 
    Class;
```

### 4. Classification Status

```sql
SET @@LEFT_JOIN=false;

SELECT
    path,
    CASE
        WHEN size = 0 THEN 'Zero Size'
        WHEN INSTR(metadata, 'IsEncrypted') > 0 THEN 'Encrypted File'
        WHEN !isIndexed THEN 'Not indexed'
        WHEN classification = 'Unclassified' THEN 'No classifications'
        ELSE 'Unknown'
    END AS classificationState
FROM STORE('/')
WHERE
    isObject AND
    classification = 'Unclassified' AND
    (
         LENGTH(metadata) < 100 AND 
         metadata LIKE '%IsEncrypted%' OR
         !isIndexed
    );
```

### 5. Top Data Users

```sql
SET @@LEFT_JOIN=false;

SELECT
    osOwner,
    COUNT(name) AS "File_Count",
    SUM(size) AS "File_Size",
    SUM(storageCost) AS "Total_Storage_Cost"
GROUP BY
    osOwner
ORDER BY
    "File_Size" DESC
LIMIT
    10;
```

### 6. User Access to Protected Data

```sql
SET @USER = 'USERNAME';
SET @@LEFT_JOIN=false;

SELECT
    osOwner as "Owner",
    path as "Location",
    classification as "Classification"
WHERE
    osPermission like CONCAT('%/', @USER, '%') AND
    classification like 'U.S.%';
```

### 7. Search for Specific Content

```sql
SET @@DEFAULT_COLUMNS=searchHit;
SELECT
  name,
  size,
  createTime,
  modifyTime,
  searchHit
WHICH CONTAIN ANY ('quido');
```

## Available Columns Reference

AQL provides access to numerous file and metadata properties. Below is a comprehensive list of available columns:

### File Information
- `name` - Name of file or directory
- `uniqueName` - Unique name of file/directory (unique within parent directory)
- `path` - Path to the corresponding file
- `parentPath` - Path to the directory containing the file
- `localPath` - Local path of file
- `localParentPath` - Path to file on local disk
- `winPath` - Windows absolute path of file
- `winParentPath` - Windows parent path of file
- `winLocalPath` - Windows local path of file
- `winLocalParentPath` - Windows local parent path of file
- `classId` - Type of file, directory, or node (e.g., Aggregator, Collector, Client, User, Container)
- `size` - File size on local file system
- `storeSize` - File size in Aggregator's database
- `compressionRatio` - Ratio of actual size to file size
- `version` - Number of times a file has changed
- `dupCount` - Number of identical copies in Aggregator's database
- `dupKey` - Cryptographic algorithm representing the unique content
- `attrib` - Number of attributes associated with file

### Timestamps
- `modifyTime` - Last modified time on local file system
- `createTime` - Creation time on local file system
- `accessTime` - Last accessed time on local file system
- `storeTime` - Time stored to Aggregator's database
- `updatedAt` - Last edited time in Aggregator's database
- `createdAt` - Time first added to Aggregator's database
- `deletedAt` - Time deleted from Aggregator's database
- `processTime` - Time to assess file's index, classification, and metadata
- `instanceMessageTime` - Time an action was taken on file instance
- `objectMessageTime` - Time when file message was sent
- `docModifyTime` - Document last modified date
- `docCreateTime` - Document creation date

### Document Metadata
- `metadata` - Document internal information (creator, dates, etc.)
- `metadataObject` - Document internal information in JSON format
- `docModifier` - User who last modified the document
- `docCreator` - User who created the document

### Classification & Search
- `classification` - Classification name applied to file
- `classifications` - Set of classifications associated with file
- `classificationObjects` - Classifications to be processed by backend
- `classificationId` - ID associated with classification
- `confidence` - Classification confidence level
- `isClassified` - Whether file is classified (true/false)
- `isIndexed` - Whether file is indexed (true/false)
- `searchHit` - Search entry successfully found
- `searchHits` - Context of search hits
- `searchHitWordsBefore` - Words leading to searched word
- `searchHitWordsAfter` - Words trailing searched word
- `classificationHit` - Content detected as classification hit
- `classificationHits` - Context of classification hits
- `classificationHitWordsBefore` - Words before classification hit
- `classificationHitWordsAfter` - Words after classification hit
- `classificationHitConfidence` - Classification threshold
- `classificationHitPolicy` - Number of classifications associated
- `classificationHitRule` - Classification rules

### Ownership & Permissions
- `osOwner` - File owner
- `osOwnerObject` - File owner on disk
- `osPermission` - File's Operating System permission
- `osPermissions` - OS permissions associated with file
- `osPermissionObjects` - OS permissions for backend processing

### System IDs
- `objectId` - File ID
- `parentId` - Parent ID
- `nodeObjectId` - Node ID
- `processPipe` - Process ID
- `componentId` - Component ID
- `instanceId` - Instance ID
- `batchId` - Batch ID
- `instanceBatchId` - Instance Batch ID
- `wordBatchId` - Word Batch ID
- `datasetId` - Dataset ID
- `dataset` - Dataset name

### Storage Information
- `storageCost` - Cost to maintain file in storage (30 days)
- `retrievalCost` - Cost to retrieve file
- `retrievalTime` - Estimated retrieval time
- `encryptionId` - Encryption ID
- `keyId` - Encryption key ID
- `iFlags` - Instance flags indicating status

### Service Information
- `serviceId` - Target/source unique identifier
- `service` - Target/source service name
- `serviceType` - Service type (target/source)
- `serviceMode` - Source or Target
- `node` - Aggregator or collector name
- `localParentUrlScheme` - Local Parent URL Scheme

### Tags & Messages
- `tags` - Tags as collection of IDs for backend
- `tagString` - Tags as single text line
- `instanceTags` - Instance tags as ID collection
- `instanceTagString` - Instance tags as text
- `userTag` - Tags associated with file
- `userTags` - Set of file tags
- `userTagObjects` - User tag for backend processing
- `instanceMessage` - Action message on file instance
- `instanceMessageObjects` - Audit message with transaction
- `objectMessage` - File message as text
- `objectMessageObjects` - File message for backend processing

### Status Flags
- `isContainer` - Whether item is directory (true/false)
- `isDeleted` - Whether data is removed (true/false)
- `isObject` - Whether item is file (true/false)
- `isSigned` - Whether cryptographic algorithm used (true/false)

## Best Practices

1. **Use System Variables** to control query behavior, especially `@@LEFT_JOIN` when working with classifications.

2. **Leverage CASE Statements** for complex conditional logic.

3. **Apply CONTAINING and NEAR** for content-based searches.

4. **Use Aggregations** for data summarization and analysis.

5. **Employ COMPONENTS() Function** for hierarchical path analysis.

6. **Apply Proper Filtering** in WHERE clauses to improve performance.

7. **Use Variables** to make queries more readable and maintainable.

8. **Consider LIMIT and OFFSET** for large result sets.

## Conclusion

AQL provides a powerful SQL-based approach to query and analyze your data across distributed storage. With its rich set of functions, aggregations, and search capabilities, you can extract valuable insights from your file metadata and content.

By mastering AQL's syntax and features, you'll be able to efficiently query, filter, group, and analyze your data to meet your specific needs.