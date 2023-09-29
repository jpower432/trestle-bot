#!/usr/bin/python

#    Copyright 2023 Red Hat, Inc.
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

"""Base transformer for rules."""

from abc import abstractmethod

from trestle.transforms.transformer_factory import TransformerBase

from trestlebot.transformers.trestle_rule import TrestleRule


class RulesTransformer(TransformerBase):
    """Abstract interface for transformers for rules"""

    @abstractmethod
    def transform(self, blob: str) -> TrestleRule:
        """Transform rule data."""


class RulesTransformerException(Exception):
    """An error during transformation of a rule"""
