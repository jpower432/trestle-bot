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

"""Trestle Validator Dataclass for loading rules with custom validation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple

from pydantic import ValidationError

from trestlebot.transformers.trestle_rule import TrestleRule
from trestlebot.transformers.base_transformer import RulesTransformer


class RuleValidationError(Exception):
    """An error during validation of a rule"""


@dataclass
class ValidationOutcome():
    validation_errors: List[RuleValidationError]
    valid: bool
    validator_id: str


class RuleValidatorBase(ABC):
    """Abstract interface for rule validators"""

    @abstractmethod
    def validate(self, data: str) -> Tuple(TrestleRule, ValidationOutcome):
        """Validate a rule"""


class PydanticRuleValidator(RuleValidatorBase):
    """
    A validator for rules using Pydantic.

    Notes: This uses the Pydantic model to validate the rule, but add custom error logic to the
    validation outcome.
    """

    name: str = 'pydantic'

    def __init__(self, RulesTransformer: RulesTransformer):
        self.transformer = RulesTransformer

    def validate(self, data: str) -> Tuple(TrestleRule, ValidationOutcome):
        """Validate a rule using Pydantic"""
        try:
            rule = self.transformer.transform(data)
        except ValidationError as e:
            return rule, ValidationOutcome(
                validation_errors=e.errors(),
                valid=False,
                validator_id=self.__class__.__name__
            )
        return rule, ValidationOutcome(
            validation_errors=[],
            valid=True,
            validator_id=self.__class__.__name__
        )
