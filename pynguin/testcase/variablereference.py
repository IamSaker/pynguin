#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2021 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
"""Provides a base implementation of a variable in a test case."""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pynguin.utils import type_utils
from pynguin.utils.type_utils import is_type_unknown

if TYPE_CHECKING:
    import pynguin.testcase.testcase as tc


class VariableReference(metaclass=ABCMeta):
    """Represents a variable in a test case."""

    def __init__(self, test_case: tc.TestCase, variable_type: Optional[Type]) -> None:
        self._variable_type = variable_type
        self._test_case = test_case
        self._distance = 0

    @abstractmethod
    def clone(
        self, memo: Dict[VariableReference, VariableReference]
    ) -> VariableReference:
        """This method is essential for the whole variable references to work while
        cloning.

        'self' must not be cloned. Instead we have to look for the
        corresponding variable reference in the new test case.
        Actual cloning is only performed on statement level.

        Args:
            memo: A mapping from old to new variable references.

        Returns:  # noqa: DAR202
            The corresponding variable reference of this variable in the new test case.
        """

    @abstractmethod
    def get_statement_position(self) -> int:
        """Provides the position of the statement which defines this variable reference
        in the test case.

        Returns:
            The position  # noqa: DAR202
        """

    @property
    def variable_type(self) -> Optional[Type]:
        """Provides the type of this variable.

        Returns:
            The type of this variable
        """
        return self._variable_type

    @variable_type.setter
    def variable_type(self, variable_type: Optional[Type]) -> None:
        """Allows to set the type of this variable.

        Args:
            variable_type: The new type of this variable
        """
        self._variable_type = variable_type

    @property
    def test_case(self) -> tc.TestCase:
        """Provides the test case in which this variable reference is used.

        Returns:
            The containing test case
        """
        return self._test_case

    @property
    def distance(self) -> int:
        """Distance metric used to select variables for mutation based on how close
        they are to the subject under test.

        Returns:
            The distance value
        """
        return self._distance

    @distance.setter
    def distance(self, distance: int) -> None:
        """Set the distance metric.

        Args:
            distance: The new distance value
        """
        self._distance = distance

    def is_primitive(self) -> bool:
        """Does this variable reference represent a primitive type.

        Returns:
            True if the variable is a primitive
        """
        return type_utils.is_primitive_type(self._variable_type)

    def is_none_type(self) -> bool:
        """Is this variable reference of type none, i.e. it does not return anything.

        Returns:
            True if this variable is a none type
        """
        return type_utils.is_none_type(self._variable_type)

    def is_type_unknown(self) -> bool:
        """Is the type of this variable unknown?

        Returns:
            True if this variable has unknown type
        """
        return is_type_unknown(self._variable_type)

    def __repr__(self) -> str:
        return f"VariableReference({self._test_case}, {self._variable_type})"

    def __str__(self) -> str:
        return f"{self._variable_type}"

    def structural_eq(
        self, other: Any, memo: Dict[VariableReference, VariableReference]
    ) -> bool:
        """Compare if this variable reference is the same as the other and points to
        the same variable.

        Args:
            other: The variable to compare
            memo: A mapping from old to new variables.

        Returns:
            True, iff this variable is the same as the other and points to the same
            location.
        """
        if not isinstance(other, VariableReference):
            return False
        return self._variable_type == other._variable_type and memo[self] == other

    def structural_hash(self) -> int:
        """Required for structural_eq to work.

        Returns:
            A hash value.
        """
        return 31 * 17 + hash(self._variable_type)


class VariableReferenceImpl(VariableReference):
    """Basic implementation of a variable reference."""

    def clone(
        self, memo: Dict[VariableReference, VariableReference]
    ) -> VariableReference:
        return memo[self]

    def get_statement_position(self) -> int:
        for idx, stmt in enumerate(self._test_case.statements):
            if stmt.ret_val == self:
                return idx
        raise Exception(
            "Variable reference is not declared in the test case in which it is used"
        )