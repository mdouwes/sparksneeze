Metadata Module
===============

Overview
--------

SparkSneeze automatically enriches all data with standardized metadata fields for tracking, auditing, and data lineage. This ensures consistent data governance across all strategies and operations.

Every record processed by SparkSneeze receives metadata fields that track:

- **Validity periods** - When records are valid from/to
- **Active status** - Whether records are currently active  
- **Data fingerprinting** - Hash of data columns for change detection
- **System information** - Strategy, version, and processing details

Metadata Fields
---------------

All metadata fields use a configurable prefix (default: ``_META``):

``_META_valid_from`` (TimestampType)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Record validity start timestamp. Set to the current time when records are processed, ensuring all records in a batch have the same timestamp.

``_META_valid_to`` (TimestampType) 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Record validity end timestamp. Set to ``2999-12-31 23:59:59`` for active records, indicating they are currently valid.

``_META_active`` (BooleanType)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Active record indicator. Always ``True`` for records processed by DropCreate, Truncate, Append, and Upsert strategies. The Historize strategy may set this to ``False`` for superseded records.

``_META_row_hash`` (StringType)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Hash of data columns using Spark's MurmurHash3 algorithm. Automatically excludes:

- All metadata fields (``_META_*``)
- Key columns (for Upsert and Historize strategies)
- Any columns specified in ``hash_columns`` configuration

``_META_system_info`` (StringType)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
JSON containing system metadata about the processing operation:

.. code-block:: json

   {
     "sparksneeze_version": "0.1.2",
     "strategy": "DropCreate", 
     "created_at": "2025-06-19T10:30:00Z",
     "user": "system"
   }

Configuration
-------------

MetadataConfig Class
~~~~~~~~~~~~~~~~~~~~

Customize metadata behavior using the ``MetadataConfig`` class:

.. py:class:: MetadataConfig

   :param str prefix: Prefix for metadata field names (default: "_META")
   :param str valid_from_field: Name of valid from field (default: "valid_from")
   :param str valid_to_field: Name of valid to field (default: "valid_to")
   :param str active_field: Name of active field (default: "active")
   :param str row_hash_field: Name of row hash field (default: "row_hash")
   :param str system_info_field: Name of system info field (default: "system_info")
   :param datetime default_valid_from: Default valid from timestamp (default: current time)
   :param datetime default_valid_to: Default valid to timestamp (default: 2999-12-31)
   :param List[str] hash_columns: Specific columns to hash (default: auto-detect)

Usage Examples
--------------

Basic Usage (Default Metadata)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparksneeze import sparksneeze
   from sparksneeze.strategy import DropCreate
   
   # Automatic metadata with default configuration
   result = sparksneeze(df, "my_table", DropCreate()).run()
   
   # Resulting table will have columns:
   # - Original data columns
   # - _META_valid_from
   # - _META_valid_to  
   # - _META_active
   # - _META_row_hash
   # - _META_system_info

Custom Prefix
~~~~~~~~~~~~~

.. code-block:: python

   from sparksneeze.metadata import MetadataConfig
   from sparksneeze.strategy import Append
   
   # Use custom prefix for metadata fields
   config = MetadataConfig(prefix="_AUDIT")
   strategy = Append(metadata_config=config)
   
   result = sparksneeze(df, "my_table", strategy).run()
   
   # Resulting columns: _AUDIT_valid_from, _AUDIT_valid_to, etc.

Specific Hash Columns
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparksneeze.metadata import MetadataConfig
   from sparksneeze.strategy import Upsert
   
   # Only hash specific columns for change detection
   config = MetadataConfig(
       hash_columns=["name", "email", "department"]
   )
   
   strategy = Upsert(key="employee_id", metadata_config=config)
   result = sparksneeze(df, "employees", strategy).run()
   
   # Hash will only include name, email, department
   # Key column (employee_id) automatically excluded

Custom Validity Periods
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import datetime
   from sparksneeze.metadata import MetadataConfig
   from sparksneeze.strategy import Historize
   
   # Set specific validity period
   config = MetadataConfig(
       default_valid_from=datetime(2025, 1, 1),
       default_valid_to=datetime(2025, 12, 31)
   )
   
   strategy = Historize(
       key="user_id", 
       metadata_config=config,
       valid_from=datetime(2025, 6, 1)  # Override for this operation
   )
   
   result = sparksneeze(df, "user_history", strategy).run()

Strategy-Specific Behavior
---------------------------

DropCreate Strategy
~~~~~~~~~~~~~~~~~~~
- All records get ``_META_active=True``
- ``_META_valid_from`` set to current timestamp
- ``_META_valid_to`` set to 2999-12-31
- Hash includes all data columns

Truncate Strategy  
~~~~~~~~~~~~~~~~~
- Same behavior as DropCreate
- All records treated as new and active

Append Strategy
~~~~~~~~~~~~~~~
- New records get ``_META_active=True``
- Same timestamp behavior as DropCreate
- Hash includes all data columns

Upsert Strategy
~~~~~~~~~~~~~~~
- All records get ``_META_active=True``
- Key columns automatically excluded from hash
- Enables change detection on non-key columns

Historize Strategy
~~~~~~~~~~~~~~~~~~
- Uses custom ``valid_from`` and ``valid_to`` parameters
- Key columns automatically excluded from hash  
- Active status managed by historization logic
- Supports slowly changing dimensions (SCD Type 2)

Querying Data with Metadata
----------------------------

Active Records Only
~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

   SELECT * FROM my_table 
   WHERE _META_active = true

Current State (Latest Records)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

   SELECT * FROM my_table 
   WHERE _META_active = true 
   AND _META_valid_from <= current_timestamp()
   AND _META_valid_to > current_timestamp()

Change Detection
~~~~~~~~~~~~~~~~

.. code-block:: sql

   -- Find records that changed between runs
   SELECT a.id, a._META_row_hash as old_hash, b._META_row_hash as new_hash
   FROM previous_table a
   JOIN current_table b ON a.id = b.id
   WHERE a._META_row_hash != b._META_row_hash

Data Lineage Tracking
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

   -- Track which strategy processed each record
   SELECT 
       get_json_object(_META_system_info, '$.strategy') as strategy,
       get_json_object(_META_system_info, '$.created_at') as processed_at,
       count(*) as record_count
   FROM my_table
   GROUP BY 1, 2
   ORDER BY processed_at DESC

Best Practices
--------------

1. **Consistent Configuration**: Use the same ``MetadataConfig`` across related tables for consistency

2. **Hash Column Selection**: For large tables, consider specifying ``hash_columns`` to include only business-critical fields

3. **Query Patterns**: Always filter on ``_META_active=true`` when querying current data

4. **Archival Strategy**: Use metadata timestamps to implement data retention policies

5. **Change Detection**: Leverage ``_META_row_hash`` for efficient change detection in ETL pipelines

6. **Monitoring**: Query ``_META_system_info`` to track data processing patterns and strategy usage