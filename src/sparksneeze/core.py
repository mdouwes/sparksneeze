"""Core functionality for the sparksneeze library."""

from typing import Union, Optional
from pyspark.sql import DataFrame, SparkSession

from .strategy import BaseStrategy, SparkSneezeResult
from .data_sources import DataSource, create_data_source
from .data_targets import DataTarget, create_data_target
from .logging import get_logger
from .spark_utils import create_spark_session_with_delta


class SparkSneezeRunner:
    """Main runner class for sparksneeze operations.

    The SparkSneezeRunner orchestrates the execution of data warehouse transformations
    using the strategy pattern. It handles source/target abstraction, Spark session
    management, and error handling.

    Examples:
        Basic usage with DataFrame source:

        >>> from pyspark.sql import SparkSession
        >>> from sparksneeze import SparkSneezeRunner
        >>> from sparksneeze.strategy import DropCreate
        >>>
        >>> spark = SparkSession.builder.getOrCreate()
        >>> df = spark.createDataFrame([(1, "Alice"), (2, "Bob")], ["id", "name"])
        >>> runner = SparkSneezeRunner(df, "/path/to/target", DropCreate())
        >>> result = runner.run(spark)

        Using file paths:

        >>> runner = SparkSneezeRunner(
        ...     "/path/to/source.parquet",
        ...     "/path/to/target.delta",
        ...     DropCreate()
        ... )
        >>> result = runner.run()  # Auto-creates Spark session

        With custom strategy configuration:

        >>> from sparksneeze.strategy import Append
        >>> strategy = Append(auto_expand=True, auto_shrink=False)
        >>> runner = SparkSneezeRunner("source_table", "target_table", strategy)
        >>> result = runner.run()
    """

    def __init__(
        self,
        source_entity: Union[DataFrame, str, DataSource],
        target_entity: Union[str, DataTarget],
        strategy: BaseStrategy,
    ):
        """Initialize the runner with source, target, and strategy.

        Args:
            source_entity: Source data entity. Can be:
                - DataFrame: Direct Spark DataFrame
                - str: File path (e.g., "/path/to/file.parquet") or table name
                - DataSource: Custom data source implementation
            target_entity: Target data entity. Can be:
                - str: File path (e.g., "/path/to/target.delta") or table name
                - DataTarget: Custom data target implementation
            strategy: Strategy instance to execute (DropCreate, Append, Upsert, etc.)

        Raises:
            TypeError: If invalid types are provided for source_entity, target_entity, or strategy

        Examples:
            DataFrame to file:

            >>> df = spark.createDataFrame([(1, "test")], ["id", "value"])
            >>> runner = SparkSneezeRunner(df, "/output/data.delta", DropCreate())

            File to file:

            >>> runner = SparkSneezeRunner("/input/data.csv", "/output/data.parquet", Append())

            Table to table:

            >>> runner = SparkSneezeRunner("source_db.table", "target_db.table", Upsert(keys=["id"]))
        """
        self.source_entity = source_entity
        self.target_entity = target_entity
        self.strategy = strategy
        self.logger = get_logger(f"{__name__}.SparkSneezeRunner")

    def run(self, spark_session: Optional[SparkSession] = None) -> SparkSneezeResult:
        """Execute the strategy on the configured source and target.

        This method orchestrates the complete data transformation pipeline:
        1. Creates or uses provided Spark session
        2. Resolves source and target entities to concrete data abstractions
        3. Executes the configured strategy
        4. Returns detailed results with metadata

        Args:
            spark_session: Optional Spark session. If not provided, creates a local
                          session with Delta Lake support automatically.

        Returns:
            SparkSneezeResult: Comprehensive result object containing:
                - success: Boolean indicating execution success
                - records_processed: Number of records processed
                - execution_time: Time taken for execution
                - metadata: Strategy-specific metadata
                - target_schema: Final target schema after execution

        Raises:
            RuntimeError: If strategy execution fails or Spark session creation fails
            TypeError: If source/target entities cannot be resolved

        Examples:
            Basic execution:

            >>> result = runner.run()
            >>> print(f"Processed {result.records_processed} records in {result.execution_time}s")

            With existing Spark session:

            >>> spark = SparkSession.builder.appName("MyApp").getOrCreate()
            >>> result = runner.run(spark_session=spark)
            >>> if result.success:
            ...     print("Strategy executed successfully")

            Error handling:

            >>> try:
            ...     result = runner.run()
            ... except RuntimeError as e:
            ...     print(f"Execution failed: {e}")
        """
        strategy_name = self.strategy.__class__.__name__

        try:
            # Create Spark session if not provided
            if spark_session is None:
                spark_session = self._create_default_spark_session()

            # Create data source and target with spark session
            source = create_data_source(self.source_entity, spark_session)
            target = create_data_target(self.target_entity, spark_session)

            # Execute strategy with proper data source and target abstractions
            result = self.strategy.execute(source, target)

            return result

        except RuntimeError as e:
            self.logger.error(f"{strategy_name} failed: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in {strategy_name}: {str(e)}")

            # Wrap unexpected errors
            raise RuntimeError(
                f"Unexpected error during {strategy_name} execution: {str(e)}"
            ) from e

    def _create_default_spark_session(self) -> SparkSession:
        """Create a default Spark session for local execution with Delta support."""
        try:
            session = create_spark_session_with_delta(
                app_name="SparkSneeze", master="local[*]"
            )

            return session
        except Exception as e:
            self.logger.error(f"Failed to create Spark session: {str(e)}")
            raise RuntimeError(f"Failed to create Spark session: {str(e)}")


def sparksneeze(
    source_entity: Union[DataFrame, str, DataSource],
    target_entity: Union[str, DataTarget],
    strategy: BaseStrategy,
) -> SparkSneezeRunner:
    """Create a sparksneeze runner instance.

    Args:
        source_entity: Source data entity (DataFrame, path, table name, or DataSource)
        target_entity: Target data entity (path, table name, or DataTarget)
        strategy: Strategy instance to execute

    Returns:
        SparkSneezeRunner: Runner instance ready to execute

    Examples:
        >>> from sparksneeze import sparksneeze
        >>> from sparksneeze.strategy import DropCreate
        >>>
        >>> # Using DataFrame
        >>> runner = sparksneeze(my_df, "target_table", DropCreate())
        >>> result = runner.run()
        >>>
        >>> # Using file paths
        >>> runner = sparksneeze("source.parquet", "target.delta", DropCreate())
        >>> result = runner.run()
        >>>
        >>> # Using table names
        >>> runner = sparksneeze("source_table", "target_table", DropCreate())
        >>> result = runner.run()
    """
    return SparkSneezeRunner(source_entity, target_entity, strategy)
