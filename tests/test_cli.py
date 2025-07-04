"""Tests for the CLI functionality."""

import pytest
from unittest.mock import patch, Mock
from sparksneeze.cli import create_parser, main
from sparksneeze.strategy import SparkSneezeResult


class TestCLIParser:
    """Test cases for CLI argument parser."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser.prog == "sparksneeze"

    def test_version_argument(self):
        """Test version argument parsing."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_verbose_argument(self):
        """Test verbose argument parsing."""
        parser = create_parser()
        args = parser.parse_args(
            ["source_entity", "target_entity", "--strategy", "DropCreate", "--verbose"]
        )
        assert args.verbose is True

    def test_basic_command(self):
        """Test basic command parsing with source, target, and strategy."""
        parser = create_parser()
        args = parser.parse_args(
            ["source_entity", "target_entity", "--strategy", "DropCreate"]
        )
        assert args.source_entity == "source_entity"
        assert args.target_entity == "target_entity"
        assert args.strategy == "DropCreate"

    def test_truncate_strategy_with_options(self):
        """Test Truncate strategy with auto_expand and auto_shrink options."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "source_entity",
                "target_entity",
                "--strategy",
                "Truncate",
                "--auto_expand",
                "false",
                "--auto_shrink",
                "true",
            ]
        )
        assert args.strategy == "Truncate"
        assert args.auto_expand is False
        assert args.auto_shrink is True

    def test_upsert_strategy_with_key(self):
        """Test Upsert strategy with key option."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "source_entity",
                "target_entity",
                "--strategy",
                "Upsert",
                "--key",
                "col1,col2",
            ]
        )
        assert args.strategy == "Upsert"
        assert args.key == "col1,col2"

    def test_historize_strategy_with_all_options(self):
        """Test Historize strategy with all options."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "source_entity",
                "target_entity",
                "--strategy",
                "Historize",
                "--key",
                "col1,col2",
                "--auto_expand",
                "true",
                "--auto_shrink",
                "false",
                "--valid_from",
                "2023-01-01 00:00:00",
                "--valid_to",
                "2999-12-31",
                "--prefix",
                "META_",
            ]
        )
        assert args.strategy == "Historize"
        assert args.key == "col1,col2"
        assert args.auto_expand is True
        assert args.auto_shrink is False
        assert args.valid_from == "2023-01-01 00:00:00"
        assert args.valid_to == "2999-12-31"
        assert args.prefix == "META_"


class TestCLIMain:
    """Test cases for main CLI function."""

    def test_main_missing_arguments(self):
        """Test main function with missing required arguments."""
        result = main([])
        assert result == 2  # argparse returns 2 for missing required args

    @patch("sparksneeze.cli.sparksneeze")
    def test_main_drop_create_strategy(self, mock_sparksneeze):
        """Test main function with DropCreate strategy."""
        # Mock runner and its run method
        mock_runner = Mock()
        mock_result = SparkSneezeResult(success=True, message="Success")
        mock_runner.run.return_value = mock_result
        mock_sparksneeze.return_value = mock_runner

        result = main(["source_entity", "target_entity", "--strategy", "DropCreate"])

        assert result == 0
        mock_sparksneeze.assert_called_once()
        mock_runner.run.assert_called_once()

    @patch("sparksneeze.cli.sparksneeze")
    def test_main_truncate_strategy(self, mock_sparksneeze):
        """Test main function with Truncate strategy."""
        # Mock runner and its run method
        mock_runner = Mock()
        mock_result = SparkSneezeResult(success=True, message="Success")
        mock_runner.run.return_value = mock_result
        mock_sparksneeze.return_value = mock_runner

        result = main(
            [
                "source_entity",
                "target_entity",
                "--strategy",
                "Truncate",
                "--auto_expand",
                "true",
            ]
        )

        assert result == 0
        mock_sparksneeze.assert_called_once()
        mock_runner.run.assert_called_once()

    @patch("sparksneeze.cli.sparksneeze")
    def test_main_with_verbose(self, mock_sparksneeze):
        """Test main function with verbose flag."""
        # Mock runner and its run method
        mock_runner = Mock()
        mock_result = SparkSneezeResult(success=True, message="Success")
        mock_runner.run.return_value = mock_result
        mock_sparksneeze.return_value = mock_runner

        result = main(
            ["source_entity", "target_entity", "--strategy", "DropCreate", "--verbose"]
        )

        assert result == 0
        mock_sparksneeze.assert_called_once()
        mock_runner.run.assert_called_once()
