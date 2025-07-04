"""Configuration file for the Sphinx documentation builder."""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('../src'))

# Project information
project = 'sparksneeze'
copyright = '2025, Merijn Douwes'
author = 'Merijn Douwes'
release = '0.1.2'

# General configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'myst_parser',
    'sphinx_design',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output options
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Custom CSS and JS
html_css_files = [
    'custom.css',
]

html_js_files = [
    'copy-clipboard.js',
]

# Autodoc options
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
    'inherited-members': True
}

# Enhanced autodoc configuration
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'
autodoc_preserve_defaults = True

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Intersphinx configuration
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
}

# MyST parser configuration
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_image",
]

# Source file suffixes
source_suffix = {
    '.rst': None,
    '.md': 'myst_parser',
}