Introduction
=============

The Data Warehouse Challenge
----------------------------

Organizations building data platforms face a common challenge: implementing reliable, repeatable data loading patterns for their data warehouse. Whether you're maintaining customer records, processing transaction data, or consolidating operational information from multiple systems, you need robust strategies to move data from various sources into your target tables.


The Problem with Typical Solutions
-----------------------------------

Most companies approach this challenge in one of three ways, each with significant limitations:

**Manual Processes and Spreadsheets**
Teams often resort to downloading data, manually copying and pasting between systems, and maintaining complex spreadsheets. This approach is time-consuming, error-prone, and doesn't scale. When data formats change or new sources are added, entire workflows break down.

**Custom Spark Scripts**
Data engineering teams frequently write custom Spark jobs for each data loading scenario. While this provides flexibility, these scripts typically handle only specific use cases and lack standardized error handling, schema evolution, and metadata tracking. When requirements change or team members leave, these custom solutions become maintenance burdens rather than reusable assets.

**Enterprise Data Integration Platforms**
Large organizations often purchase costly enterprise data integration platforms that support Spark and Delta Lake. While these tools can be comprehensive, they're typically complex to implement, require specialized expertise, expensive licenses, and lengthy procurement processes. For many Spark-based data teams, the cost and complexity far exceed the actual needs.

The Hidden Costs
-----------------

What makes these approaches especially problematic are the hidden costs that compound over time:

- **Schema Drift**: When source systems change their data structure, downstream processes break unpredictably
- **Data Quality Issues**: Without proper validation and metadata tracking, bad data silently corrupts analysis
- **Maintenance Overhead**: Each custom solution requires ongoing maintenance, updates, and documentation
- **Knowledge Silos**: Critical data processes become dependent on specific individuals who understand the custom implementations

A Better Approach
------------------

**sparksneeze** addresses these challenges by providing a comprehensive, professional-grade Spark and Delta Lake solution that combines the simplicity of purpose-built tools with the robustness of enterprise software - without the complexity or cost.

Unlike fragmented Spark scripts or expensive platforms, sparksneeze offers:

**Complete Data Loading Strategies**: Whether you need to completely replace Delta tables, incrementally append records, update existing data based on keys, or maintain historical change tracking, sparksneeze provides proven strategies that handle these common lakehouse patterns reliably.

**Automatic Schema Evolution**: When source DataFrames or files change their schema, sparksneeze adapts your Delta tables automatically, eliminating the schema drift problems that break traditional Spark ETL jobs.

**Professional Reliability**: Designed with enterprise-grade error handling, logging, and monitoring capabilities that ensure your Spark data operations succeed consistently, even in complex multi-source environments.

**Zero Licensing Costs**: As an open-source MIT-licensed tool, sparksneeze eliminates the budget constraints and procurement delays associated with commercial solutions.

Scope and focus
------------------

The current scope and focus is to make sparksneeze run properly and usefully on Spark workloads. The project will mainly be tested on Azure Databricks and Microsoft Fabric. 

It you encounter issues using sparksneeze in other Spark workloads, please reach out to the project via Github.


Roadmap
------------------

Short term:

- Optional column reordering after schema evolution
- Optional hash re-calculation after schema evolution

Long term:

- Support other processing engines (currently only Spark support)
    - Snowflake
- Support other targets
    - Databases
    - Iceberg
    - The common flat file formats
- More strategies (e.g. the other SCD's)
