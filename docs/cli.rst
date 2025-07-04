Command Line Interface
======================

The sparksneeze CLI provides a convenient way to use sparksneeze functionality from the command line. This is not the recommended usage, as you're not using your spark cluster. It is useful for debugging or running something one-off.

Basic Usage
-----------

.. code-block:: bash

   sparksneeze --help

The CLI requires a source entity, target entity, and strategy for data processing.

.. code-block:: bash

   sparksneeze SOURCE_ENTITY TARGET_ENTITY ``--strategy`` STRATEGY_NAME

Required Arguments
------------------

source_entity
~~~~~~~~~~~~~

Source data entity (DataFrame or path):

.. code-block:: bash

   sparksneeze /path/to/source.parquet /path/to/target ``--strategy`` DropCreate

target_entity
~~~~~~~~~~~~~

Target data entity (path):

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Truncate

``--strategy``
~~~~~~~~~~~~~~

Strategy to use for data processing. Available strategies:

* ``DropCreate`` - Remove target and recreate with source schema
* ``Truncate`` - Clear target and load source data
* ``Append`` - Add source data to target
* ``Upsert`` - Insert/update based on keys
* ``Historize`` - Upsert with validity time tracking metadata

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Append

Strategy Options
----------------

``--auto_expand``
~~~~~~~~~~~~~~~~~

Automatically add new columns to the target entity (for Truncate, Append, Upsert, Historize):

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Append ``--auto_expand`` true

``--auto_shrink``
~~~~~~~~~~~~~~~~~

Automatically remove nonexistent columns from the target entity (for Truncate, Append, Upsert, Historize):

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Append ``--auto_shrink`` true

``--key``
~~~~~~~~~

The key(s) used for Upsert/Historize strategies. Use comma-separated values for multiple keys:

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Upsert ``--key`` user_id
   sparksneeze source.csv target ``--strategy`` Upsert ``--key`` user_id,version

``--valid_from``
~~~~~~~~~~~~~~~~

The datetime value for the start of record validity (for Historize strategy):

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Historize ``--key`` user_id ``--valid_from`` "2024-01-01"
   sparksneeze source.csv target ``--strategy`` Historize ``--key`` user_id ``--valid_from`` "2024-01-01 10:30:00"

``--valid_to``
~~~~~~~~~~~~~~

The datetime value for the end of record validity (for Historize strategy):

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Historize ``--key`` user_id ``--valid_to`` "2024-12-31 23:59:59"

``--prefix``
~~~~~~~~~~~~

The prefix to use for metadata columns (for Historize strategy):

.. code-block:: bash

   sparksneeze source.csv target ``--strategy`` Historize ``--key`` user_id ``--prefix`` "hist_"

Logging Options
---------------

``--quiet, -q``
~~~~~~~~~~~~~~~

Suppress all output except errors:

.. code-block:: bash

   sparksneeze --quiet source.csv target ``--strategy`` DropCreate

``--verbose, -v``
~~~~~~~~~~~~~~~~~

Enable verbose output (INFO level):

.. code-block:: bash

   sparksneeze --verbose source.csv target ``--strategy`` DropCreate

``--debug``
~~~~~~~~~~~

Enable debug output (DEBUG level):

.. code-block:: bash

   sparksneeze ``--debug`` source.csv target ``--strategy`` DropCreate

``--log-file``
~~~~~~~~~~~~~~

Path to log file for persistent logging:

.. code-block:: bash

   sparksneeze ``--log-file`` /path/to/logfile.log source.csv target ``--strategy`` DropCreate

Global Options
--------------

``--version``
~~~~~~~~~~~~~

Show version information:

.. code-block:: bash

   sparksneeze ``--version``

Examples
--------

.. code-block:: bash

   # Basic drop and create
   sparksneeze source.csv target ``--strategy`` DropCreate

   # Truncate with schema evolution
   sparksneeze source.csv target ``--strategy`` Truncate ``--auto_expand`` true ``--auto_shrink`` true

   # Append with verbose logging
   sparksneeze --verbose source.csv target ``--strategy`` Append

   # Upsert with single key
   sparksneeze source.csv target ``--strategy`` Upsert ``--key`` user_id

   # Upsert with multiple keys
   sparksneeze source.csv target ``--strategy`` Upsert ``--key`` user_id,version

   # Historize with custom metadata prefix
   sparksneeze source.csv target ``--strategy`` Historize ``--key`` user_id ``--prefix`` "audit_"

   # Historize with validity period
   sparksneeze source.csv target ``--strategy`` Historize ``--key`` user_id ``--valid_from`` "2024-01-01" ``--valid_to`` "2024-12-31"

   # Debug mode with log file
   sparksneeze ``--debug`` ``--log-file`` debug.log source.csv target ``--strategy`` DropCreate