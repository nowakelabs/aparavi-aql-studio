# Aparavi Available Columns Reference

This document provides a comprehensive list of column names available in Aparavi's reporting system. Use these exact column names when constructing AQL queries.

## Core Columns

| Pretty Name | DB Column Name | Advanced | Description |
|-------------|----------------|----------|-------------|
| Access Date | accessTime | No | Date file was last accessed on the local file system |
| Added Date | createdAt | Yes | Time the file was first added to the Aggregator's database |
| Audit Message | instanceMessage | Yes | Short message of action(s) taken on an instance of a file on an Aggregator |
| Audit Message Time | instanceMessageTime | Yes | The time an action was taken on an instance of a file |
| Category | category | No | Category for which the file's extension belong to |
| Class Id | classId | Yes | Type of file, directory, or node (ex: Aggregator, Collector, Client, User, Container etc.) |
| Classification | classification | No | Name of the Classification being applied to file |
| Classification Hit | classificationHit | Yes | Content detected to be a classification hit |
| Classification Hit Confidence | classificationHitConfidence | Yes | Threshold required for a file to be classified |
| Classification Hit Context | classificationHits | Yes | Context of a classification hit |
| Classification Hit Leading Words | classificationHitWordsBefore | Yes | Words leading up to classification hit |
| Classification Hit Policy | classificationHitPolicy | Yes | Number representing how many classification are associated with the file |
| Classification Hit Rule | classificationHitRule | Yes | Rules of a classification associated with the file |
| Classification Hit Trailing Words | classificationHitWordsAfter | Yes | Words trailing the classification hit |
| Classification Id | classificationId | Yes | ID number associated with a classification |
| Classifications | classifications | Yes | Set of classifications associated with a file |
| Compression Ratio | compressionRatio | No | Ratio of the actual size that file occupies to the size of the actual file |
| Confidence % | confidence | No | Confidence level of a classification hit |
| Create Date | createTime | No | Date file was first created on the local file system |
| Deleted Date | deletedAt | Yes | Time the file was deleted from the Aggregator's database |
| Document Created By | docCreator | No | User by whom the document was created |
| Document Creation Time | docCreateTime | No | Date that the document was created |
| Document Modified By | docModifier | No | User by whom the document was last modified |
| Document Modify Time | docModifyTime | No | Date that the document was last modified |
| Duplicate Count | dupCount | No | Number of identical copies of a file found in an Aggregator's database |
| Extension | extension | No | Extension associated with the file |
| File Signature | dupKey | Yes | Cryptographic algorithm representing the unique content of a file |
| Is Deleted | isDeleted | Yes | Determines if the data has been removed |
| Is Storage Container | isContainer | Yes | Determines if this item is a directory |
| Is Storage Object | isObject | Yes | Determines if this item is a file |
| Local Path | localPath | No | Local path of file |
| Metadata | metadata | No | A document internal information (ex: creator, original create date, modification date, etc.) |
| Metadate Object | metadataObject | Yes | A document internal information in JSON format (ex: creator, original create date, modification date, etc.) |
| Modify Date | modifyTime | No | Date file was last modified on the local file system |
| Name | name | No | Name of file or directory |
| Node Name | node | Yes | Name of the aggregator or collector |
| OS Permissions | osPermissions | Yes | The Operating Systems permissions associated with a file |
| Owner | osOwner | No | Owner of the file |
| Parent Path | parentPath | No | Path to the corresponding directory of a file |
| Path | path | No | Path to the corresponding file |
| Permission | osPermission | No | A file's Operating System permission |
| Retrieval Cost | retrievalCost | No | Cost for retrieving a file |
| Retrieval Time | retrievalTime | No | The estimated time for retrieving a file |
| Search Hit | searchHit | Yes | Search entry sucessfully found |
| Search Hit Context | searchHits | Yes | Context of a search hit |
| Search Hit Leading Words | searchHitWordsBefore | Yes | Words leading to the word being searched for |
| Search Hit Trailing Words | searchHitWordsAfter | Yes | Words trailing the word being searched for |
| Service Mode | serviceMode | No | Source or Target |
| Service Name | service | No | Name of the target or source service |
| Service Type | serviceType | No | The type of the service this can be a target or a source |
| Size | size | No | The size of the file on the local file system |
| Size on Disk | storeSize | No | The size of the file as stored by the Aggregator's database |
| Storage Cost | storageCost | No | Cost of maintaining a file in storage for up to 30 days |
| Store Date | storeTime | No | Date a file was stored to the Aggregator's database |
| Tag | userTag | No | Tag(s) associatd with file |
| Tags | userTags | Yes | Set of tags for files |
| Updated Date | updatedAt | Yes | Date a file was last edited in the Aggregator's database |
| Version | version | No | Number of times a file has changed, each number represent a new version of the file |

## Additional Columns

| DB Column Name | Description |
|----------------|-------------|
| attrib | Number of attributes associated with file |
| batchId | Batch Id of Batch the file(s) belonged to when processed |
| classificationObjects | Returns the classification being applied to be processed by backend |
| componentId | Id of component as text |
| dataset | Name of the set of data |
| datasetId | Id number of the set of data |
| encryptionId | Encryption Id of file |
| iFlags | Instance flags indicating current status of file |
| instanceBatchId | Instance Batch Id of file |
| instanceId | Instance Id of file |
| instanceMessageObjects | Returns the Audit Message with associated transaction to be processed by backend |
| instanceTags | Returns the instance tags as a collection of Ids to be processed by backend |
| instanceTagString | Returns the instance tags as text |
| isClassified | True or false value representing whether file is classified |
| isIndexed | True or false value representing whether file is indexed |
| isSigned | Represents if a cryptographic algorithm has been used to identify the unique content of a file |
| keyId | Encryption key id which is a hash of encryption key of file |
| localParentPath | Path to file on local disk |
| localParentUrlScheme | Local Parent URL Scheme |
| nodeObjectId | Id of the returned node |
| objectId | Id of file |
| objectMessage | Returns message associated with file as text |
| objectMessageObjects | Returns message associated with file to be processed by backend |
| objectMessageTime | Returns time when corresponding file message was sent |
| osOwnerObject | Owner of the file on disk |
| osPermissionObjects | Returns associated OS permission to be processed by backend |
| parentId | Parent Id of file |
| processPipe | Id of file |
| processTime | The time is took to assess a files index, classification, and metadata |
| serviceId | The target or source unique identifier |
| tags | Returns the tags as a collection of Ids to be processed by backend |
| tagString | Returns the tags as a single line of text |
| uniqueName | Unique name of file or directory (only unique inside its parent directory) |
| userTagObjects | Returns a user tag to be processed by backend |
| winLocalParentPath | Windows local parent path of file |
| winLocalPath | Windows local path of file |
| winParentPath | Windows parent path of file |
| winPath | Windows absolute path of file |
| wordBatchId | The Batch Id of Batch containing the words in file |
