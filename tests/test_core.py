"""Tests for the core sparksneeze functionality."""

from unittest.mock import Mock, patch
from sparksneeze.core import SparkSneezeRunner, sparksneeze
from sparksneeze.strategy import (
    DropCreate,
    Truncate,
    Upsert,
    Historize,
    SparkSneezeResult,
)


class TestSparkSneezeRunner:
    """Test cases for SparkSneezeRunner."""

    def test_initialization(self):
        """Test runner initialization."""
        strategy = DropCreate()
        runner = SparkSneezeRunner("source_entity", "target_entity", strategy)

        # Test that runner stores the provided entities and strategy
        assert runner.source_entity == "source_entity"
        assert runner.target_entity == "target_entity"
        assert runner.strategy is strategy


class TestSparksneezeFactory:
    """Test cases for sparksneeze factory function."""

    def test_sparksneeze_factory_drop_create(self):
        """Test sparksneeze factory with DropCreate strategy."""
        strategy = DropCreate()
        runner = sparksneeze("source_entity", "target_entity", strategy)

        assert isinstance(runner, SparkSneezeRunner)
        # Test that factory correctly stores entities and strategy
        assert runner.source_entity == "source_entity"
        assert runner.target_entity == "target_entity"
        assert runner.strategy is strategy

    def test_sparksneeze_factory_truncate(self):
        """Test sparksneeze factory with Truncate strategy."""
        strategy = Truncate(auto_expand=False, auto_shrink=True)
        runner = sparksneeze("source_entity", "target_entity", strategy)

        assert isinstance(runner, SparkSneezeRunner)
        assert runner.strategy.auto_expand is False
        assert runner.strategy.auto_shrink is True

    def test_sparksneeze_factory_upsert(self):
        """Test sparksneeze factory with Upsert strategy."""
        strategy = Upsert(key="user_id", auto_expand=True)
        runner = sparksneeze("source_entity", "target_entity", strategy)

        assert isinstance(runner, SparkSneezeRunner)
        assert runner.strategy.key == ["user_id"]
        assert runner.strategy.auto_expand is True

    def test_sparksneeze_factory_historize(self):
        """Test sparksneeze factory with Historize strategy."""
        from sparksneeze.metadata import MetadataConfig

        metadata_config = MetadataConfig(prefix="HIST_")
        strategy = Historize(key=["id", "version"], metadata_config=metadata_config)
        runner = sparksneeze("source_entity", "target_entity", strategy)

        assert isinstance(runner, SparkSneezeRunner)
        assert runner.strategy.key == ["id", "version"]
        assert runner.strategy.metadata_applier.config.prefix == "HIST_"

    @patch("sparksneeze.core.create_spark_session_with_delta")
    @patch("sparksneeze.core.create_data_source")
    @patch("sparksneeze.core.create_data_target")
    def test_sparksneeze_run_integration(
        self, mock_create_target, mock_create_source, mock_spark_session
    ):
        """Test full integration of sparksneeze factory and run."""
        # Mock Spark session and data abstractions
        mock_session = Mock()
        mock_spark_session.return_value = mock_session
        mock_source = Mock()
        mock_target = Mock()
        mock_create_source.return_value = mock_source
        mock_create_target.return_value = mock_target

        # Mock strategy execution to return success
        strategy = DropCreate()
        mock_result = SparkSneezeResult(success=True, message="Success")
        strategy.execute = Mock(return_value=mock_result)  # type: ignore[assignment]

        result = sparksneeze("source_entity", "target_entity", strategy).run()

        assert isinstance(result, SparkSneezeResult)
        assert result.success is True
        strategy.execute.assert_called_once_with(mock_source, mock_target)  # type: ignore[attr-defined]

    @patch("sparksneeze.core.create_spark_session_with_delta")
    @patch("sparksneeze.core.create_data_source")
    @patch("sparksneeze.core.create_data_target")
    def test_sparksneeze_chaining(
        self, mock_create_target, mock_create_source, mock_spark_session
    ):
        """Test method chaining with sparksneeze factory."""
        # Mock Spark session and data abstractions
        mock_session = Mock()
        mock_spark_session.return_value = mock_session
        mock_source = Mock()
        mock_target = Mock()
        mock_create_source.return_value = mock_source
        mock_create_target.return_value = mock_target

        # Mock strategy execution to return success
        strategy = Truncate(auto_expand=True, auto_shrink=False)
        mock_result = SparkSneezeResult(success=True, message="Success")
        strategy.execute = Mock(return_value=mock_result)  # type: ignore[assignment]

        # Test that we can chain .run() directly
        result = sparksneeze("source_entity", "target_entity", strategy).run()

        assert isinstance(result, SparkSneezeResult)
        assert result.success is True
        strategy.execute.assert_called_once_with(mock_source, mock_target)  # type: ignore[attr-defined]
