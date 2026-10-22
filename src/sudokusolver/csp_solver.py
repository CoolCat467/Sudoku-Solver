"""Constraint Satisfaction Problem Solver."""

# Programmed by CoolCat467

from __future__ import annotations

# Constraint Satisfaction Problem Solver
# Copyright (C) 2026  CoolCat467
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__title__ = "Constraint Satisfaction Problem Solver"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "GNU General Public License Version 3"


import operator
import re
from collections import deque
from collections.abc import Callable, Generator, Hashable, Iterable
from typing import Generic, NamedTuple, TypeAlias, TypeVar

T = TypeVar("T")
KT = TypeVar("KT", bound=Hashable)
VT = TypeVar("VT")
Constraint: TypeAlias = Callable[[T, T], bool]


def get_compare_function(op: str) -> Constraint[T]:
    """Return comparison function for a given operator."""
    return {
        "=": operator.eq,
        "!=": operator.ne,
    }[op]


CONSTRAINT = re.compile(r"(\w+)\s*(!=|=)\s*(\w+)")


def parse_constraint(
    constraint: str,
) -> tuple[tuple[str, str], Constraint[T]]:
    """Return tuple of variable name tuples and comparison function."""
    match_ = CONSTRAINT.match(constraint)
    if match_ is None:
        raise ValueError("Constraint pattern did not match")
    one, op, two = match_.groups()
    return (one, two), get_compare_function(op)


def get_constraint_dict_from_strings(
    lines: Iterable[str],
) -> dict[tuple[str, str], Constraint[T]]:
    """Return constraint dictionary from iterable of constraint strings."""
    parse_fn: Callable[[str], tuple[tuple[str, str], Constraint[T]]] = (
        parse_constraint
    )
    return dict(map(parse_fn, lines))


def get_dualway_constraints(
    constraints: dict[tuple[KT, KT], Constraint[T]],
) -> dict[tuple[KT, KT], Constraint[T]]:
    """Return new constraints after ensuring dual-way mapping."""
    dualway = {}
    for (one, two), cmp in constraints.items():
        dualway[(one, two)] = cmp
        # TODO: if ever non-unary constraint support, this will need to
        # change.
        dualway[(two, one)] = cmp
    return dualway


class CSP(NamedTuple, Generic[KT, VT]):
    """Constraint Satisfaction Problem solver."""

    domains: dict[KT, set[VT]]
    constraints: dict[tuple[KT, KT], Constraint[VT]]

    @property
    def variables(self) -> set[KT]:
        """Return set of all variable names."""
        return set(self.domains)

    def yield_arcs(self) -> Generator[tuple[KT, KT], None, None]:
        """Yield all related variables."""
        yield from self.constraints

    def yield_relative_constraints(
        self,
        variable: KT,
    ) -> Generator[tuple[KT, KT], None, None]:
        """Yield all constraint keys that involve given variable."""
        for constraint in self.constraints:
            if variable in constraint:
                yield constraint

    def get_neighbors(self, variable: KT) -> set[KT]:
        """Return set of all variables involved with given variable."""
        connected = set()
        for one, two in self.yield_relative_constraints(variable):
            connected.add(one)
            connected.add(two)
        return connected

    def domains_copy(self) -> dict[KT, set[VT]]:
        """Return a copy of current domain mapping."""
        return {k: set(v) for k, v in self.domains.items()}

    def arc_3(
        self,
        assignments: dict[KT, VT] | None = None,
    ) -> dict[KT, set[VT]] | None:
        """Return new domains after enforcing arc consistency or None on impossible problem."""
        if assignments is None:
            assignments = {}
        inferences: dict[KT, set[VT]] = self.domains_copy()

        queue = deque(self.yield_arcs())
        while queue:
            x_i, x_j = queue.popleft()
            if self.revise(x_i, x_j, inferences, assignments):
                if not inferences[x_i]:
                    return None
                # for x_k in self.get_neighbors(x_i) - {x_j}:
                # {x_i}
                for x_k in self.get_neighbors(x_i) - {x_i, x_j}:
                    queue.append((x_k, x_i))
        # if inferences != self.domains:
        #    print(f'{inferences = }')
        return inferences

    def revise(
        self,
        x_i: KT,
        x_j: KT,
        domains: dict[KT, set[VT]],
        assignments: dict[KT, VT],
    ) -> bool:
        """Return if domains were revised."""
        revised = False

        # Find the constraint for this arc.
        compare = self.constraints[(x_i, x_j)]

        values_j = {assignments[x_j]} if x_j in assignments else domains[x_j]

        for value_i in tuple(domains[x_i]):
            # if x_i in assignments and value_i != assignments[x_i]:
            if (
                assignment := assignments.get(x_i)
            ) is not None and value_i != assignment:
                continue

            supported = any(compare(value_i, value_j) for value_j in values_j)
            if not supported:
                domains[x_i].remove(value_i)
                revised = True

        return revised

    def unassigned_variables(self, assignment: dict[KT, VT]) -> set[KT]:
        """Return set of unassigned variables."""
        return self.variables - set(assignment)

    def select_unassigned_variable(self, assignment: dict[KT, VT]) -> KT:
        """Return an unassigned variable name."""
        unassigned = self.unassigned_variables(assignment)
        if not unassigned:
            raise ValueError("no unassigned variables")
        # options_per_var = {len(self.domains[var]): var for var in unassigned}
        # return options_per_var[min(options_per_var)]
        min_options = float("inf")
        equal_min: list[KT] = []
        for var in unassigned:
            options_count = len(self.domains[var])
            if options_count < min_options:
                min_options = options_count
                equal_min.clear()
            if options_count == min_options:
                equal_min.append(var)

        if len(equal_min) == 1:
            return equal_min.pop()

        return max(
            equal_min,
            # technically should do ` - {var}` but since all have var
            # included it's fine.
            key=lambda var: len(self.get_neighbors(var)),
        )

    def value_consistent_assignment(
        self,
        var: KT,
        value: VT,
    ) -> bool:
        """Return if a value is consistent with the domain of a variable."""
        return value in self.domains[var]

    def order_domain_values(
        self,
        var: KT,
        assignment: dict[KT, VT],
    ) -> set[VT]:
        """Return all domain values for a given variable."""
        return self.domains[var]

    ##def backtrace(
    ##    self,
    ##    assignment: dict[KT, VT],
    ##) -> dict[KT, VT] | None:
    ##    """Return complete assignment or None on unsolvable problem."""
    ##    if not self.unassigned_variables(assignment):
    ##        return assignment
    ##    var = self.select_unassigned_variable(assignment)
    ##    for value in self.order_domain_values(var, assignment):
    ##        if self.value_consistent_assignment(var, value):
    ##            assignment[var] = value
    ##            inference = self.arc_3(assignment)
    ##            if inference is not None:
    ##                domains_backup = self.domains_copy()
    ##                ##add inferences to csp
    ##                self.domains.update(inference)
    ##                result = self.backtrace(assignment)
    ##                if result is not None:
    ##                    return result
    ##                ##remove inferences from csp
    ##                self.domains.update(domains_backup)
    ##            del assignment[var]
    ##    return None

    def backtrace_search(self) -> dict[KT, VT] | None:
        """Return dict of solution variable assignments or None on no solution."""
        ##        return self.backtrace({})
        generator = self.backtrace_generator_search(None)
        try:
            while True:
                next(generator)
        except StopIteration as exc:
            assert exc.value is None or isinstance(exc.value, dict)  # noqa: PT017
            return exc.value

    def backtrace_generator(
        self,
        assignment: dict[KT, VT],
        unset_yield_value: T,
    ) -> Generator[tuple[KT, VT | T], None, dict[KT, VT] | None]:
        """Yield variable, value tuples or variable, unset_yield_value tuples while finding a solution.

        Returns None on unsolvable or an assignments dictionary on success.
        """
        if not self.unassigned_variables(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            if self.value_consistent_assignment(var, value):
                assignment[var] = value
                yield var, value
                inference = self.arc_3(assignment)
                if inference is not None:
                    domains_backup = self.domains_copy()
                    ##add inferences to csp
                    self.domains.update(inference)
                    generator = self.backtrace_generator(
                        assignment,
                        unset_yield_value,
                    )
                    try:
                        while True:
                            yield next(generator)
                    except StopIteration as exc:
                        if exc.value is not None:
                            assert isinstance(exc.value, dict)  # noqa: PT017
                            return exc.value
                    ##remove inferences from csp
                    self.domains.update(domains_backup)
                del assignment[var]
                yield var, unset_yield_value
        return None

    def backtrace_generator_search(
        self,
        unset_yield_value: T,
    ) -> Generator[tuple[KT, VT | T], None, dict[KT, VT] | None]:
        """Yield variable, value tuples or variable, unset_yield_value tuples while finding a solution.

        Returns None on unsolvable or an assignments dictionary on success.
        """
        generator = self.backtrace_generator({}, unset_yield_value)
        try:
            while True:
                yield next(generator)
        except StopIteration as exc:
            assert exc.value is None or isinstance(exc.value, dict)  # noqa: PT017
            return exc.value


def run() -> None:
    """Run program."""
    colors = ("red", "green", "blue")
    csp = CSP[str, str](
        {
            "C": set(colors),
            "1": set(colors),
            "2": set(colors),
            "3": set(colors),
            "4": set(colors),
            "5": set(colors),
            "6": set(colors),
        },
        get_dualway_constraints(
            get_constraint_dict_from_strings(
                (
                    "C != 1",
                    "C != 2",
                    "C != 3",
                    "C != 4",
                    "C != 5",
                    "C != 6",
                    "1 != 2",
                    "1 != 4",
                    "2 != 3",
                    "3 != 6",
                    "4 != 5",
                    "5 != 6",
                ),
            ),
        ),
    )
    print(csp)
    print()
    print(f"{csp.backtrace_search() = }")
    sudoku_csp = CSP[str, int](
        {
            "i0": {2, 4, 6, 7},
            "i1": {9, 2, 4, 7},
            "i4": {9, 4, 6},
            "i5": {2, 4},
            "i8": {4, 6},
            "i9": {2, 4, 5, 6},
            "i10": {2, 4, 5},
            "i13": {1, 4, 6},
            "i14": {1, 2, 4},
            "i17": {4, 6},
            "i19": {9, 4},
            "i20": {9, 6},
            "i22": {9, 4, 6},
            "i27": {5, 6, 7},
            "i28": {3, 5, 7},
            "i29": {5, 6, 7},
            "i31": {1, 3, 7},
            "i32": {1, 3},
            "i37": {3, 4},
            "i40": {3, 4},
            "i45": {2, 4, 7},
            "i46": {9, 2, 4, 7},
            "i47": {9, 7},
            "i49": {8, 4, 7},
            "i50": {8, 4},
            "i72": {5, 7},
            "i74": {5, 7},
            "i76": {8, 3},
            "i77": {8, 3},
        },
        get_dualway_constraints(
            get_constraint_dict_from_strings(
                (
                    "i27 != i45",
                    "i40 != i22",
                    "i5 != i8",
                    "i10 != i46",
                    "i49 != i22",
                    "i9 != i20",
                    "i74 != i72",
                    "i31 != i49",
                    "i13 != i17",
                    "i50 != i45",
                    "i4 != i5",
                    "i50 != i77",
                    "i13 != i31",
                    "i13 != i9",
                    "i32 != i77",
                    "i46 != i47",
                    "i72 != i9",
                    "i8 != i1",
                    "i10 != i37",
                    "i45 != i9",
                    "i40 != i13",
                    "i77 != i5",
                    "i77 != i74",
                    "i49 != i13",
                    "i9 != i17",
                    "i40 != i76",
                    "i49 != i32",
                    "i0 != i72",
                    "i9 != i72",
                    "i10 != i17",
                    "i27 != i9",
                    "i0 != i20",
                    "i14 != i4",
                    "i47 != i45",
                    "i49 != i76",
                    "i31 != i29",
                    "i46 != i10",
                    "i19 != i9",
                    "i19 != i37",
                    "i20 != i1",
                    "i46 != i19",
                    "i4 != i13",
                    "i13 != i40",
                    "i4 != i0",
                    "i0 != i45",
                    "i10 != i19",
                    "i28 != i37",
                    "i29 != i20",
                    "i17 != i13",
                    "i32 != i5",
                    "i1 != i9",
                    "i27 != i72",
                    "i9 != i0",
                    "i29 != i31",
                    "i47 != i49",
                    "i32 != i14",
                    "i72 != i0",
                    "i72 != i74",
                    "i47 != i27",
                    "i45 != i37",
                    "i19 != i28",
                    "i31 != i28",
                    "i0 != i19",
                    "i17 != i9",
                    "i13 != i5",
                    "i45 != i27",
                    "i45 != i0",
                    "i72 != i27",
                    "i76 != i74",
                    "i50 != i31",
                    "i32 != i31",
                    "i45 != i46",
                    "i74 != i20",
                    "i5 != i0",
                    "i8 != i0",
                    "i20 != i74",
                    "i31 != i13",
                    "i10 != i1",
                    "i45 != i29",
                    "i14 != i5",
                    "i14 != i17",
                    "i22 != i14",
                    "i1 != i4",
                    "i14 != i13",
                    "i28 != i29",
                    "i28 != i46",
                    "i28 != i32",
                    "i9 != i19",
                    "i76 != i13",
                    "i47 != i29",
                    "i74 != i76",
                    "i0 != i27",
                    "i14 != i50",
                    "i49 != i50",
                    "i22 != i49",
                    "i27 != i32",
                    "i77 != i32",
                    "i9 != i45",
                    "i4 != i31",
                    "i1 != i0",
                    "i27 != i47",
                    "i32 != i40",
                    "i31 != i76",
                    "i22 != i13",
                    "i40 != i49",
                    "i46 != i45",
                    "i74 != i77",
                    "i74 != i29",
                    "i4 != i8",
                    "i19 != i20",
                    "i32 != i27",
                    "i77 != i14",
                    "i13 != i10",
                    "i20 != i29",
                    "i50 != i5",
                    "i76 != i22",
                    "i14 != i77",
                    "i47 != i74",
                    "i37 != i45",
                    "i5 != i32",
                    "i4 != i49",
                    "i29 != i74",
                    "i10 != i20",
                    "i50 != i32",
                    "i27 != i28",
                    "i28 != i10",
                    "i31 != i40",
                    "i76 != i31",
                    "i1 != i5",
                    "i49 != i45",
                    "i46 != i27",
                    "i10 != i9",
                    "i20 != i9",
                    "i0 != i4",
                    "i32 != i29",
                    "i37 != i10",
                    "i29 != i47",
                    "i46 != i29",
                    "i8 != i5",
                    "i4 != i14",
                    "i1 != i8",
                    "i10 != i13",
                    "i29 != i28",
                    "i27 != i31",
                    "i29 != i46",
                    "i31 != i32",
                    "i45 != i28",
                    "i50 != i14",
                    "i74 != i47",
                    "i77 != i76",
                    "i29 != i37",
                    "i5 != i77",
                    "i76 != i4",
                    "i13 != i4",
                    "i37 != i27",
                    "i22 != i76",
                    "i29 != i45",
                    "i0 != i5",
                    "i27 != i29",
                    "i27 != i0",
                    "i37 != i28",
                    "i45 != i49",
                    "i45 != i72",
                    "i77 != i72",
                    "i5 != i14",
                    "i19 != i46",
                    "i49 != i4",
                    "i50 != i49",
                    "i4 != i40",
                    "i37 != i29",
                    "i17 != i10",
                    "i0 != i8",
                    "i4 != i22",
                    "i47 != i46",
                    "i40 != i4",
                    "i13 != i22",
                    "i10 != i14",
                    "i1 != i20",
                    "i31 != i4",
                    "i19 != i0",
                    "i32 != i50",
                    "i0 != i9",
                    "i22 != i5",
                    "i45 != i47",
                    "i37 != i19",
                    "i47 != i20",
                    "i14 != i22",
                    "i8 != i17",
                    "i32 != i28",
                    "i4 != i1",
                    "i17 != i8",
                    "i46 != i37",
                    "i9 != i13",
                    "i1 != i46",
                    "i10 != i0",
                    "i40 != i32",
                    "i46 != i1",
                    "i37 != i47",
                    "i47 != i28",
                    "i28 != i47",
                    "i37 != i46",
                    "i5 != i13",
                    "i28 != i27",
                    "i40 != i37",
                    "i19 != i1",
                    "i77 != i50",
                    "i1 != i10",
                    "i22 != i4",
                    "i13 != i14",
                    "i72 != i45",
                    "i40 != i50",
                    "i9 != i14",
                    "i76 != i40",
                    "i76 != i49",
                    "i20 != i22",
                    "i31 != i27",
                    "i49 != i46",
                    "i19 != i10",
                    "i14 != i9",
                    "i31 != i22",
                    "i47 != i37",
                    "i50 != i40",
                    "i50 != i46",
                    "i1 != i28",
                    "i14 != i32",
                    "i29 != i27",
                    "i9 != i1",
                    "i27 != i46",
                    "i37 != i40",
                    "i4 != i76",
                    "i19 != i22",
                    "i76 != i77",
                    "i72 != i76",
                    "i9 != i27",
                    "i46 != i50",
                    "i50 != i47",
                    "i28 != i19",
                    "i13 != i49",
                    "i5 != i50",
                    "i28 != i45",
                    "i31 != i50",
                    "i20 != i19",
                    "i49 != i31",
                    "i20 != i0",
                    "i14 != i10",
                    "i72 != i77",
                    "i1 != i37",
                    "i28 != i1",
                    "i0 != i1",
                    "i29 != i32",
                    "i47 != i50",
                    "i5 != i4",
                    "i22 != i19",
                    "i5 != i22",
                    "i22 != i40",
                    "i5 != i1",
                    "i28 != i31",
                    "i40 != i31",
                    "i10 != i28",
                    "i17 != i14",
                    "i76 != i72",
                    "i22 != i20",
                    "i9 != i10",
                    "i46 != i49",
                    "i49 != i40",
                    "i49 != i47",
                    "i1 != i19",
                    "i20 != i10",
                    "i8 != i4",
                    "i22 != i31",
                    "i0 != i10",
                    "i46 != i28",
                    "i20 != i47",
                    "i45 != i50",
                    "i37 != i1",
                    "i32 != i49",
                    "i27 != i37",
                    "i13 != i76",
                ),
            ),
        ),
    )
    print()
    print(f"{sudoku_csp.backtrace_search() = }")


if __name__ == "__main__":
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    run()
