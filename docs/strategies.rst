Strategies
===========

Introduction
-------------
A strategy is given as a parameter to the sparksneeze class. For example:

.. py:function:: sparksneeze(source_entity, target_entity, strategy=Strategy(args, kwargs)).run()

   Create a sparksneeze instance with a specific strategy, and then run it.

   :param SnarpSneezeStrategy strategy: A strategy class instance
   :param args: Positional arguments
   :param kwargs: Key-word arguments
   :returns: Strategy result
   :rtype: SparkSneezeResult

Automatic Metadata Enrichment
------------------------------

All strategies automatically add standardized metadata fields to every record. This ensures consistent tracking and auditing across all data operations.

**Metadata Fields Added:**

- ``_META_valid_from`` (TimestampType) - Record validity start timestamp
- ``_META_valid_to`` (TimestampType) - Record validity end timestamp (2999-12-31 for active records)
- ``_META_active`` (BooleanType) - Active record indicator (True for all records except in Historize operations)
- ``_META_row_hash`` (StringType) - Hash of data columns (excludes metadata and key columns)
- ``_META_system_info`` (StringType) - JSON containing system metadata (strategy, version, timestamp, etc.)

**Customizing Metadata:**

.. code-block:: python

   from sparksneeze.metadata import MetadataConfig
   from sparksneeze.strategy import DropCreate
   
   # Custom metadata configuration
   config = MetadataConfig(
       prefix="_AUDIT",  # Custom prefix instead of _META
       hash_columns=["id", "name"]  # Only hash specific columns
   )
   
   # Use with any strategy
   strategy = DropCreate(metadata_config=config)
   result = sparksneeze(df, "target_table", strategy).run()

-----

Strategies
----------

DropCreate
~~~~~~~~~~
.. py:Class:: DropCreate(metadata_config=None)

   Remove the target entity and create it anew based on the schema of the source entity. There are no parameters, no data or schema will be kept of the old target.

   All records will have metadata fields added with ``_META_active=True``.

   :param MetadataConfig metadata_config: Optional metadata configuration. Uses default if None.
   :returns: SparkSneezeResult
   :rtype: dict

.. dropdown:: Example

   Randy takes over as the new park supervisor and needs to replace the old resident roster with a fresh start.

   **Source (New Resident Data):**

   +----------+-----+-------------------+-----------------+
   | name     | age | occupation        | location        |
   +==========+=====+===================+=================+
   | Ricky    | 31  | Convenience Store | Trailer Park    |
   +----------+-----+-------------------+-----------------+
   | Julian   | 34  | Bar Owner         | Trailer Park    |
   +----------+-----+-------------------+-----------------+
   | Bubbles  | 33  | Cat Caretaker     | Shed            |
   +----------+-----+-------------------+-----------------+

   **Existing Target (Old Registry):**

   +----------+-----+---------------+
   | name     | age | job_title     |
   +==========+=====+===============+
   | Randy    | 36  | Supervisor    |
   +----------+-----+---------------+
   | Mr Lahey | 54  | Manager       |
   +----------+-----+---------------+

   **Result (Completely New Registry):**

   +---------+-----+-------------------+--------------+---------------------------+----------------------------+--------------------+---------------------------+----------------------------+
   | name    | age | occupation        | location     | _META_valid_from          | _META_valid_to             | _META_active       | _META_row_hash            | _META_system_info          |
   +=========+=====+===================+==============+===========================+============================+====================+===========================+============================+
   | Ricky   | 31  | Convenience Store | Trailer Park | 2024-03-01 00:00:00       | 2999-12-31 23:59:59        | true               | [hash]                    | {"strategy":"DropCreate"}  |
   +---------+-----+-------------------+--------------+---------------------------+----------------------------+--------------------+---------------------------+----------------------------+
   | Julian  | 34  | Bar Owner         | Trailer Park | 2024-03-01 00:00:00       | 2999-12-31 23:59:59        | true               | [hash]                    | {"strategy":"DropCreate"}  |
   +---------+-----+-------------------+--------------+---------------------------+----------------------------+--------------------+---------------------------+----------------------------+
   | Bubbles | 33  | Cat Caretaker     | Shed         | 2024-03-01 00:00:00       | 2999-12-31 23:59:59        | true               | [hash]                    | {"strategy":"DropCreate"}  |
   +---------+-----+-------------------+--------------+---------------------------+----------------------------+--------------------+---------------------------+----------------------------+

   The old registry was completely wiped and replaced with the new resident data.


Truncate
~~~~~~~~
.. py:Class:: Truncate(auto_expand=True, auto_shrink=False, metadata_config=None)

   Clear the target entity and load the data from the source entity. By default it automatically expands the schema when new columns are found. Columns that are removed from the source entity will remain in the target entity. By enabling auto_shrink it will automatically drop columns from the target entity as well.

   When auto_expand and auto_shrink are turned on simultaneously it will mimic the DropCreate strategy. This is useful for database logging or when there is no DROP and CREATE permissions granted. In the case of Delta tables history is preserved, whereas a DropCreate would replace the Delta table entirely.

   All records will have metadata fields added with ``_META_active=True``.

   :param bool auto_expand: Automatically add new columns to the target_entity
   :param bool auto_shrink: Automatically remove nonexistent columns from the target_entity
   :param MetadataConfig metadata_config: Optional metadata configuration. Uses default if None.
   :returns: SparkSneezeResult
   :rtype: dict

.. dropdown:: Example

   Julian gets a new liquor shipment and needs to clear out the old inventory and load the fresh stock.

   **Source (New Liquor Inventory):**

   +----------+-----+-------------+
   | name     | age | job         |
   +==========+=====+=============+
   | Ricky    | 31  | Sales Agent |
   +----------+-----+-------------+
   | Julian   | 34  | Manager     |
   +----------+-----+-------------+
   | Bubbles  | 33  | Analyst     |
   +----------+-----+-------------+

   **Existing Target (Old Inventory):**

   +----------+-----+-------------+
   | name     | age | job         |
   +==========+=====+=============+
   | Randy    | 36  | Supervisor  |
   +----------+-----+-------------+
   | Mr Lahey | 54  | Manager     |
   +----------+-----+-------------+

   **Result (Fresh Inventory Only):**

   +---------+-----+-------------+---------------------------+---------------------------+----------+----------+-------------------------+
   | name    | age | job         | _META_valid_from          | _META_valid_to            | _META... | _META... | _META_system_info       |
   +=========+=====+=============+===========================+===========================+==========+==========+=========================+
   | Ricky   | 31  | Sales Agent | 2024-05-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Truncate"} |
   +---------+-----+-------------+---------------------------+---------------------------+----------+----------+-------------------------+
   | Julian  | 34  | Manager     | 2024-05-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Truncate"} |
   +---------+-----+-------------+---------------------------+---------------------------+----------+----------+-------------------------+
   | Bubbles | 33  | Analyst     | 2024-05-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Truncate"} |
   +---------+-----+-------------+---------------------------+---------------------------+----------+----------+-------------------------+

   All old inventory was cleared and replaced with the new shipment data.

Append
~~~~~~~~~~~~~~~~~~~~~~~
.. py:Class:: Append(auto_expand=True, auto_shrink=False, metadata_config=None)

   Load the data from the source entity into the target entity. By default it automatically expands the schema when new columns are found. Columns that are removed from the source entity will remain in the target entity. By enabling auto_shrink it will automatically drop columns from the target entity as well.

   No rows will be removed from the target entity. All records will have metadata fields added with ``_META_active=True``.

   :param bool auto_expand: Automatically add new columns to the target_entity
   :param bool auto_shrink: Automatically remove nonexistent columns from the target_entity
   :param MetadataConfig metadata_config: Optional metadata configuration. Uses default if None.
   :returns: SparkSneezeResult
   :rtype: dict

.. dropdown:: Example

   New people are moving into Sunnyvale Trailer Park and need to be added to the existing resident registry.

   **Source (New Residents):**

   +----------+-----+----------------+--------+
   | name     | age | business       | income |
   +==========+=====+================+========+
   | Ricky    | 31  | Get Rich Quick | 2500   |
   +----------+-----+----------------+--------+
   | Julian   | 34  | Bar Business   | 5000   |
   +----------+-----+----------------+--------+
   | Bubbles  | 33  | Cart Business  | 1200   |
   +----------+-----+----------------+--------+

   **Existing Target (Current Residents):**

   +----------+-----+---------------+--------+
   | name     | age | business      | income |
   +==========+=====+===============+========+
   | Randy    | 36  | Security      | 3000   |
   +----------+-----+---------------+--------+
   | Mr Lahey | 54  | Supervisor    | 4500   |
   +----------+-----+---------------+--------+

   **Result (All Residents Combined):**

   +---------+-----+----------------+--------+---------------------------+---------------------------+----------+----------+----------------------+
   | name    | age | business       | income | _META_valid_from          | _META_valid_to            | _META... | _META... | _META_system_info    |
   +=========+=====+================+========+===========================+===========================+==========+==========+======================+
   | Randy   | 36  | Security       | 3000   | 2024-07-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Append"}|
   +---------+-----+----------------+--------+---------------------------+---------------------------+----------+----------+----------------------+
   | Lahey   | 54  | Supervisor     | 4500   | 2024-07-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Append"}|
   +---------+-----+----------------+--------+---------------------------+---------------------------+----------+----------+----------------------+
   | Ricky   | 31  | Get Rich Quick | 2500   | 2024-07-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Append"}|
   +---------+-----+----------------+--------+---------------------------+---------------------------+----------+----------+----------------------+
   | Julian  | 34  | Bar Business   | 5000   | 2024-07-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Append"}|
   +---------+-----+----------------+--------+---------------------------+---------------------------+----------+----------+----------------------+
   | Bubbles | 33  | Cart Business  | 1200   | 2024-07-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Append"}|
   +---------+-----+----------------+--------+---------------------------+---------------------------+----------+----------+----------------------+

   Existing residents were preserved and new residents were added to the registry.

Upsert
~~~~~~~~~~~~~
.. py:Class:: Upsert(key=[col1, col2], auto_expand=True, auto_shrink=False, metadata_config=None)

   Load data from the source entity into the target entity by using one or more keys. After the key comparison, the following happens:

    - New keys have their records inserted into the target entity
    - Existing keys will have their records updated in the target entity
    - (Optional) Nonexistent keys will have their records removed from the target entity

   All records will have metadata fields added with ``_META_active=True``. Key columns are automatically excluded from row hash calculation.

   :param key: The key(s) that will be used to upsert
   :type key: list or str
   :param bool auto_expand: Automatically add new columns to the target_entity
   :param bool auto_shrink: Automatically remove nonexistent columns from the target_entity
   :param MetadataConfig metadata_config: Optional metadata configuration. Uses default if None.
   :returns: SparkSneezeResult
   :rtype: dict

.. dropdown:: Example

   Characters are getting out of jail and updating their status in the park's character tracking system.

   **Source (Status Updates):**

   +--------------+----------+-----+---------------+--------+
   | character_id | name     | age | status        | money  |
   +==============+==========+=====+===============+========+
   | 1            | Ricky    | 32  | Out of Jail   | 150    |
   +--------------+----------+-----+---------------+--------+
   | 2            | Julian   | 35  | Running Bar   | 5500   |
   +--------------+----------+-----+---------------+--------+
   | 4            | Bubbles  | 34  | Cart Business | 1800   |
   +--------------+----------+-----+---------------+--------+
   | 5            | Corey    | 20  | Working Store | 800    |
   +--------------+----------+-----+---------------+--------+

   **Existing Target (Current Status):**

   +--------------+----------+-----+---------------+--------+
   | character_id | name     | age | status        | money  |
   +==============+==========+=====+===============+========+
   | 1            | Ricky    | 31  | In Jail       | 50     |
   +--------------+----------+-----+---------------+--------+
   | 2            | Julian   | 34  | Planning      | 3000   |
   +--------------+----------+-----+---------------+--------+
   | 3            | Randy    | 36  | Supervisor    | 2500   |
   +--------------+----------+-----+---------------+--------+

   **Result (Updated Status):**

   +-----+---------+-----+---------------+-------+---------------------------+---------------------------+----------+----------+-----------------------+
   | id  | name    | age | status        | money | _META_valid_from          | _META_valid_to            | _META... | _META... | _META_system_info     |
   +=====+=========+=====+===============+=======+===========================+===========================+==========+==========+=======================+
   | 1   | Ricky   | 32  | Out of Jail   | 150   | 2024-09-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Upsert"} |
   +-----+---------+-----+---------------+-------+---------------------------+---------------------------+----------+----------+-----------------------+
   | 2   | Julian  | 35  | Running Bar   | 5500  | 2024-09-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Upsert"} |
   +-----+---------+-----+---------------+-------+---------------------------+---------------------------+----------+----------+-----------------------+
   | 3   | Randy   | 36  | Supervisor    | 2500  | 2024-09-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Upsert"} |
   +-----+---------+-----+---------------+-------+---------------------------+---------------------------+----------+----------+-----------------------+
   | 4   | Bubbles | 34  | Cart Business | 1800  | 2024-09-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Upsert"} |
   +-----+---------+-----+---------------+-------+---------------------------+---------------------------+----------+----------+-----------------------+
   | 5   | Corey   | 20  | Working Store | 800   | 2024-09-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Upsert"} |
   +-----+---------+-----+---------------+-------+---------------------------+---------------------------+----------+----------+-----------------------+

   Ricky and Julian got updated with their new status and money, while Bubbles and Corey were inserted as new entries.

Historize
~~~~~~~~~~~~~
.. py:Class:: Historize(key=[col1, col2], auto_expand=True, auto_shrink=False, valid_from=datetime.now(), valid_to=datetime(2999, 12, 31), prefix='_META', metadata_config=None)

   Load data from the source entity into the target entity by using one or more keys and add validity time tracking attributes. The metadata columns to store a valid from date, a valid to date and active attribute will be added to the target entity, regardless of the auto_expand parameter.
   
   After the key comparison, the following happens:

    - New keys have their records inserted into the target entity, valid_from and valid_to will be set
    - Existing keys will have their records updated in the target entity, setting the valid_to and active values
    - Existing keys will have a new record inserted in the target entity, setting the valid_from and valid_to values
    - Nonexistent keys will have their records in the target_entity updated setting the valid_to and active values

   Key columns are automatically excluded from row hash calculation. Uses custom valid_from/valid_to timestamps for metadata fields.

   :param key: The key(s) that will be used to SCD2
   :type key: list or str
   :param bool auto_expand: Automatically add new columns to the target_entity
   :param bool auto_shrink: Automatically remove nonexistent columns from the target_entity
   :param datetime valid_from: The datetime value to set for the start of record validity, defaults to datetime.now()
   :param datetime valid_to: The datetime value to set for the end of the record validity, defaults to datetime(2999, 12, 31)
   :param string prefix: The prefix to use for the metadata columns, defaults to '_META'. E.g. _META_valid_from and _META_valid_to.
   :param MetadataConfig metadata_config: Optional metadata configuration. Uses default if None.
   :returns: SparkSneezeResult
   :rtype: dict

.. dropdown:: Example

   Tracking residents' rent payment status changes over time for park management records. In October 2024, residents had their initial status recorded. By December 2024, some changes occurred that needed to be tracked historically.

   **Source (Updated Rent Status):**

   +-------------+----------+-----+----------------+--------------+
   | resident_id | name     | age | trailer_number | rent_status  |
   +=============+==========+=====+================+==============+
   | 1           | Ricky    | 32  | 1              | Behind       |
   +-------------+----------+-----+----------------+--------------+
   | 2           | Julian   | 35  | 2              | Paid         |
   +-------------+----------+-----+----------------+--------------+
   | 3           | Bubbles  | 34  | 0              | Shed Owner   |
   +-------------+----------+-----+----------------+--------------+
   | 4           | Randy    | 37  | 5              | Free Housing |
   +-------------+----------+-----+----------------+--------------+

   **Existing Target (Historical Records):**

   +-------------+----------+-----+----------------+-------------+-----------------+---------------+--------------+
   | resident_id | name     | age | trailer_number | rent_status | _META_valid_from| _META_valid_to| _META_active |
   +=============+==========+=====+================+=============+=================+===============+==============+
   | 1           | Ricky    | 31  | 1              | Paid        | 2024-10-01      | 2999-12-31    | true         |
   +-------------+----------+-----+----------------+-------------+-----------------+---------------+--------------+
   | 2           | Julian   | 34  | 2              | Paid        | 2024-10-01      | 2999-12-31    | true         |
   +-------------+----------+-----+----------------+-------------+-----------------+---------------+--------------+
   | 5           | Mr Lahey | 54  | 3              | Supervisor  | 2024-10-01      | 2999-12-31    | true         |
   +-------------+----------+-----+----------------+-------------+-----------------+---------------+--------------+

   **Result (Historized Records):**

   +----+---------+-----+--------+--------------+---------------------------+---------------------------+----------+----------+--------------------------+
   | id | name    | age | trail# | rent_status  | _META_valid_from          | _META_valid_to            | _META... | _META... | _META_system_info        |
   +====+=========+=====+========+==============+===========================+===========================+==========+==========+==========================+
   | 1  | Ricky   | 31  | 1      | Paid         | 2024-10-01 00:00:00       | 2024-12-01 00:00:00       | false    | [hash]   | {"strategy":"Historize"} |
   +----+---------+-----+--------+--------------+---------------------------+---------------------------+----------+----------+--------------------------+
   | 1  | Ricky   | 32  | 1      | Behind       | 2024-12-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Historize"} |
   +----+---------+-----+--------+--------------+---------------------------+---------------------------+----------+----------+--------------------------+
   | 2  | Julian  | 34  | 2      | Paid         | 2024-10-01 00:00:00       | 2024-12-01 00:00:00       | false    | [hash]   | {"strategy":"Historize"} |
   +----+---------+-----+--------+--------------+---------------------------+---------------------------+----------+----------+--------------------------+
   | 2  | Julian  | 35  | 2      | Paid         | 2024-12-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Historize"} |
   +----+---------+-----+--------+--------------+---------------------------+---------------------------+----------+----------+--------------------------+
   | 3  | Bubbles | 34  | 0      | Shed Owner   | 2024-12-01 00:00:00       | 2999-12-31 23:59:59       | true     | [hash]   | {"strategy":"Historize"} |
   +----+---------+-----+--------+--------------+---------------------------+---------------------------+----------+----------+--------------------------+

   Changes were tracked over time: Ricky's status changed from "Paid" (Oct 2024) to "Behind" (Dec 2024), Julian's age updated, while preserving full history of all changes. Mr Lahey's record was ended since he's no longer in the source data.



.. Command Line Usage
.. ------------------

