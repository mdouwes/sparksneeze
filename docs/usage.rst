Usage Guide
===========

Library Usage
-------------

Basic Processing
~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparksneeze import sparksneeze
   from sparksneeze.strategy import DropCreate

   source_dataframe = spark.read.csv(path)
   target_entity = "abfss://datalake@company.dfs.core.windows.net/goldcontainer/"

   sparksneeze(source_dataframe, target_entity, strategy=DropCreate).run()



Advanced Processing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparksneeze import sparksneeze
   from sparksneeze.strategy import Historize
   import datetime

   source_dataframe = spark.read.csv(path)
   target_entity = "abfss://datalake@company.dfs.core.windows.net/goldcontainer/"

   specific_strategy = Historize(key=[col1, col2], auto_expand=True, auto_shrink=False, valid_from=datetime.now(), valid_to=datetime(2999, 12, 31), prefix='META_')

   sparksneeze(source_dataframe, target_entity, strategy=).run()


Command Line Usage
------------------

See :doc:`cli` for detailed command-line usage instructions, but basically:

.. code-block:: bash

   sparksneeze "source entity" "target entity" --strategy DropCreate

   sparksneeze "source entity" "target entity" --strategy Historize --key=[col1, col2] --auto_expand=True --auto_shrink=False --valid_from=`date '+%Y-%m-%d %H:%M:%S'` --valid_to='2999-12-31' --prefix='META_'