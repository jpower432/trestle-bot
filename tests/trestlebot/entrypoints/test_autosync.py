# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 Red Hat, Inc.


"""Test for Autosync CLI"""

import argparse
import logging
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from tests.testutils import args_dict_to_list, configure_test_logger
from trestlebot.entrypoints.autosync import AutoSyncEntrypoint
from trestlebot.entrypoints.autosync import main as cli_main
from trestlebot.entrypoints.entrypoint_base import EntrypointInvalidArgException


@pytest.fixture
def valid_args_dict() -> Dict[str, str]:
    return {
        "branch": "main",
        "markdown-path": "/my/path",
        "oscal-model": "profile",
        "committer-name": "test",
        "committer-email": "test@email.com",
        "working-dir": ".",
        "file-patterns": ".",
        "version": "0.1.0",
    }


def test_invalid_oscal_model(valid_args_dict: Dict[str, str]) -> None:
    """Test invalid oscal model"""
    args_dict = valid_args_dict
    args_dict["oscal-model"] = "fake"
    with patch("sys.argv", ["trestlebot", *args_dict_to_list(args_dict)]):
        with pytest.raises(SystemExit, match="2"):
            cli_main()


def test_validate_args_invalid_model(valid_args_dict: Dict[str, str]) -> None:
    """
    Test invalid oscal model with validate args function.
    This is a separate test from test_invalid_oscal_model because
    it args are make invalid after the args are parsed.
    """
    args_dict = valid_args_dict
    with patch("sys.argv", ["trestlebot", *args_dict_to_list(args_dict)]):
        with pytest.raises(
            EntrypointInvalidArgException,
            match="Invalid args --oscal-model: Invalid value fake. "
            "Please use one of catalog, profile, ssp, compdef",
        ):
            parser = argparse.ArgumentParser()
            auto_sync = AutoSyncEntrypoint(parser=parser)
            args = parser.parse_args()
            args.oscal_model = "fake"
            auto_sync.validate_args(args)


@patch(
    "trestlebot.entrypoints.log.configure_logger",
    Mock(side_effect=configure_test_logger),
)
def test_no_ssp_index(valid_args_dict: Dict[str, str], caplog: Any) -> None:
    """Test missing index file for ssp"""
    args_dict = valid_args_dict
    args_dict["oscal-model"] = "ssp"
    args_dict["ssp-index-path"] = ""
    with patch("sys.argv", ["trestlebot", *args_dict_to_list(args_dict)]):
        with pytest.raises(SystemExit, match="2"):
            cli_main()

    assert any(
        record.levelno == logging.ERROR
        and "Invalid args --ssp-index-path: Must set ssp index path when using SSP as "
        "oscal model." in record.message
        for record in caplog.records
    )


@patch(
    "trestlebot.entrypoints.log.configure_logger",
    Mock(side_effect=configure_test_logger),
)
def test_no_markdown_path(valid_args_dict: Dict[str, str], caplog: Any) -> None:
    """Test without a markdown file passed as a flag"""
    args_dict = valid_args_dict
    args_dict["markdown-path"] = ""
    with patch("sys.argv", ["trestlebot", *args_dict_to_list(args_dict)]):
        with pytest.raises(SystemExit, match="2"):
            cli_main()

    assert any(
        record.levelno == logging.ERROR
        and "Invalid args --markdown-path: Markdown path must be set." in record.message
        for record in caplog.records
    )


@patch(
    "trestlebot.entrypoints.log.configure_logger",
    Mock(side_effect=configure_test_logger),
)
def test_non_existent_working_dir(valid_args_dict: Dict[str, str], caplog: Any) -> None:
    """Test with a non-existent working directory"""
    args_dict = valid_args_dict
    args_dict["working-dir"] = "tmp"
    with patch("sys.argv", ["trestlebot", *args_dict_to_list(args_dict)]):
        with pytest.raises(SystemExit, match="1"):
            cli_main()

    assert any(
        record.levelno == logging.ERROR
        and "Root path tmp does not exist" in record.message
        for record in caplog.records
    )


@patch(
    "trestlebot.entrypoints.log.configure_logger",
    Mock(side_effect=configure_test_logger),
)
def test_invalid_working_dir(valid_args_dict: Dict[str, str], caplog: Any) -> None:
    """Test with directory that is not a trestle project root"""
    args_dict = valid_args_dict
    args_dict["working-dir"] = "."
    with patch("sys.argv", ["trestlebot", *args_dict_to_list(args_dict)]):
        with pytest.raises(SystemExit, match="1"):
            cli_main()

    assert any(
        record.levelno == logging.ERROR
        and "Root path . is not a valid trestle project root" in record.message
        for record in caplog.records
    )
