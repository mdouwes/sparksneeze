Installation
============

Requirements
------------

- Python 3.12 or higher
- uv (recommended) or pip

Using uv (Recommended)
----------------------

.. code-block:: bash

   uv add sparksneeze

For development dependencies:

.. code-block:: bash

   uv add sparksneeze[dev]

Using pip
---------

.. code-block:: bash

   pip install sparksneeze

For development dependencies:

.. code-block:: bash

   pip install sparksneeze[dev]

Development Installation
------------------------

To install for development:

.. code-block:: bash

   git clone <your-repo-url>
   cd sparksneeze
   uv sync --extra dev

This will install the package in development mode with all dependencies.