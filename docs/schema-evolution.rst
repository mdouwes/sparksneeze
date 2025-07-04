Schema Evolution
================

Introduction
------------

Schema evolution is a core feature of sparksneeze that allows automatic adaptation of target schemas as source data structure changes over time. This enables robust data pipelines that can handle evolving data sources without manual intervention.

All strategies that support schema evolution provide two key parameters:

- ``auto_expand`` (default: True) - Automatically add new columns from source to target
- ``auto_shrink`` (default: False) - Automatically remove columns from target that don't exist in source

How Schema Evolution Works
--------------------------

Schema evolution occurs during strategy execution in the following order:

1. **Source Analysis**: Compare source schema with existing target schema
2. **Type Compatibility**: Verify column types are compatible or can be safely cast
3. **Schema Expansion**: Add missing columns to target if ``auto_expand=True``
4. **Schema Shrinkage**: Remove extra columns from target if ``auto_shrink=True``
5. **Data Alignment**: Align source data with evolved target schema
6. **Metadata Application**: Apply metadata with appropriate hash calculations

Auto-Expand Behavior
--------------------

When ``auto_expand=True`` (default behavior):

.. code-block:: python

   # Day 1: Target has columns [id, name, age]
   # Day 2: Source has columns [id, name, age, email, phone]
   
   # Result: Target schema expands to [id, name, age, email, phone]
   # Existing data gets NULL values for new columns
   # New data populates all columns normally

**Key Points:**
- New columns are added to target schema
- Existing records get NULL values for new columns
- Existing metadata (including hashes) remains unchanged
- New records get metadata calculated on full expanded schema

Auto-Shrink Behavior
--------------------

When ``auto_shrink=True``:

.. code-block:: python

   # Day 1: Target has columns [id, name, age, email, phone] with 100 existing records
   # Day 2: Source has columns [id, name, age] (missing email, phone)
   
   # Result: Target schema shrinks to [id, name, age]
   # IMPORTANT: email and phone columns are physically DROPPED
   # Data in dropped columns is permanently lost
   # Existing records preserve their original hash values
   # New records get hash calculated on shrunk schema

**Critical Behavior:**

.. warning::
   
   When ``auto_shrink=True``, data in removed columns is **permanently lost**. 
   This operation cannot be undone.

Hash Calculation During Schema Evolution
-----------------------------------------

One of the most important aspects of schema evolution is maintaining data integrity through proper hash calculations:

**Existing Data Hash Preservation**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When schema evolution occurs (expand or shrink), existing target data maintains its original hash values:

.. code-block:: python

   # Example: Target evolution from [id, name, age, salary] to [id, name, age]
   
   # Existing records keep original hash: hash(id, name, age, salary)
   # Even though 'salary' column is dropped, hash remains unchanged
   # This preserves data lineage and audit trails

**New Data Hash Calculation**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

New source data gets hash values calculated based on the **final evolved schema**:

.. code-block:: python

   # After schema shrink from [id, name, age, salary] to [id, name, age]
   
   # New records get hash: hash(id, name, age)
   # Hash calculation excludes dropped columns

**Mixed Hash Scenarios**

This creates scenarios where a single target contains records with different hash calculation bases:

.. code-block:: python

   # Target after auto_shrink evolution:
   # - 100 existing records: hash(id, name, age, salary) 
   # - 50 new records: hash(id, name, age)
   
   # This is normal and expected behavior

Strategy-Specific Evolution Behavior
------------------------------------

Append Strategy
^^^^^^^^^^^^^^^

- **Existing target data**: Completely preserved, including original metadata and hashes
- **Schema changes**: Applied to target structure
- **New source data**: Aligned to evolved target schema
- **Data loss**: Only occurs with ``auto_shrink=True`` (columns dropped permanently)

.. code-block:: python

   from sparksneeze.strategy import Append
   
   # Conservative: Only expand schema, never shrink
   strategy = Append(auto_expand=True, auto_shrink=False)
   
   # Aggressive: Allow both expansion and shrinkage
   strategy = Append(auto_expand=True, auto_shrink=True)

Truncate Strategy
^^^^^^^^^^^^^^^^^

- **Existing target data**: Completely cleared before processing
- **Schema changes**: Applied to target structure
- **New source data**: All data processed uniformly with evolved schema
- **Hash consistency**: All records have same hash calculation base

.. code-block:: python

   from sparksneeze.strategy import Truncate
   
   # All data processed with consistent schema evolution
   strategy = Truncate(auto_expand=True, auto_shrink=True)

Upsert and Historize Strategies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Key preservation**: Key columns are never dropped during ``auto_shrink``
- **Existing data**: Hash calculations follow same mixed-hash patterns as Append
- **Schema evolution**: Applied before key-based operations

Data Loss Scenarios
-------------------

**When Data is Lost:**

1. **auto_shrink=True**: Columns not in source are permanently dropped
2. **Type incompatibility**: Incompatible data types may cause data loss during casting
3. **Delta Lake**: Column drops are irreversible (even with time travel)

**Prevention Strategies:**

.. code-block:: python

   # 1. Use conservative settings
   strategy = Append(auto_expand=True, auto_shrink=False)
   
   # 2. Backup before schema evolution
   target.backup("backup_table_name")
   
   # 3. Test schema evolution on sample data first
   test_result = sparksneeze(sample_df, test_target, strategy).run()

Best Practices
--------------

1. **Start Conservative**: Use ``auto_expand=True, auto_shrink=False`` initially
2. **Monitor Schema Changes**: Log and review schema evolution operations
3. **Backup Critical Data**: Always backup before enabling ``auto_shrink``
4. **Test Evolution**: Validate schema evolution on development data first
5. **Document Changes**: Track schema evolution decisions and impacts

Example: Complete Schema Evolution Workflow
-------------------------------------------

.. code-block:: python

   from sparksneeze import sparksneeze
   from sparksneeze.strategy import Append
   from sparksneeze.metadata import MetadataConfig
   
   # Setup with schema evolution enabled
   metadata_config = MetadataConfig()
   strategy = Append(
       auto_expand=True,    # Allow new columns
       auto_shrink=False,   # Prevent data loss
       metadata_config=metadata_config
   )
   
   # Execute with automatic schema adaptation
   result = sparksneeze(
       source_df, 
       "target_table", 
       strategy
   ).run()
   
   if result.success:
       print(f"Schema evolution completed: {result.message}")
       # Check for any schema changes in logs
   else:
       print(f"Schema evolution failed: {result.message}")

Troubleshooting Schema Evolution
--------------------------------

**Common Issues:**

1. **Type Mismatch**: Source and target have incompatible column types
   
   - **Solution**: Ensure compatible types or implement custom type casting

2. **Metadata Conflicts**: Existing metadata conflicts with new schema
   
   - **Solution**: Use consistent MetadataConfig across operations

3. **Hash Validation Failures**: Mixed hash calculations cause validation issues
   
   - **Solution**: Understand that mixed hashes are expected behavior after evolution

4. **Data Loss Surprise**: Unexpected data loss from auto_shrink
   
   - **Solution**: Always backup before enabling auto_shrink operations

**Debug Schema Evolution:**

.. code-block:: python

   import logging
   
   # Enable detailed schema evolution logging
   logging.getLogger("sparksneeze.schema_evolution").setLevel(logging.DEBUG)
   
   # Run operation with verbose output
   result = sparksneeze(source_df, target, strategy).run()