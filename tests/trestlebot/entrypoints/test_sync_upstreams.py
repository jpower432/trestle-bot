#!/usr/bin/python

#    Copyright 2024 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Test for Sync Upstreams CLI"""

import logging
from typing import Any, Dict
from unittest.mock import patch

import pytest

from tests.testutils import args_dict_to_list
from trestlebot.entrypoints.sync_upstreams import main as cli_main


@pytest.fixture
def valid_args_dict() -> Dict[str, str]:
    return {
        "branch": "main",
        "sources": "valid_source",
        "committer-name": "test",
        "committer-email": "test@email.com",
        "working-dir": ".",
        "file-patterns": ".",
    }


def test_with_no_sources(valid_args_dict: Dict[str, str], caplog: Any) -> None:
    """Test with an invalid source argument."""
    args_dict = valid_args_dict
    args_dict["sources"] = ""

    with patch("sys.argv", ["trestlebot", *args_dict_to_list(args_dict)]):
        with pytest.raises(SystemExit, match="2"):
            cli_main()

    assert any(
        record.levelno == logging.ERROR
        and "Invalid args --sources: Must set at least one source to sync from."
        in record.message
        for record in caplog.records
    )
