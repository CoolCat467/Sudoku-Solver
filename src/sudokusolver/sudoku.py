"""Sudoku Solver - Solve Sudoku puzzles with wave function collapse."""

# https://www.learn-sudoku.com/basic-techniques.html

# Programmed by CoolCat467

from __future__ import annotations

__title__ = "Sudoku Solver"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__ver_major__ = 0
__ver_minor__ = 0
__ver_patch__ = 0

import json
from collections import deque
from itertools import permutations
from math import ceil, sqrt
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Container, Generator, Iterable

Int8 = np.int8
Line = np.typing.NDArray[np.uint8]


def get_missing(line: Container[int]) -> set[int]:
    """Return all missing numbers from line."""
    return {x for x in range(1, 10) if x not in line}


def flat_to_grid(index: int, dims: int = 9) -> tuple[int, int]:
    """Return grid index of given flat index."""
    col, row = divmod(index, dims)
    return row, col


def grid_to_sector(
    row: int,
    col: int,
    sector_size: int = 3,
) -> tuple[int, int]:
    """Return sector that contains given grid index."""
    return (row // sector_size, col // sector_size)


def grid_to_flat(row: int, col: int, dims: int = 9) -> int:
    """Get flat index from grid index."""
    return col * dims + row


##def grid_to_sector_index(sector_row: int, sector_col: int, sector_size: int=3) -> int:
##    """Return sector index given the sector row and column"""
##    return sector_row * sector_size + sector_col


def row_indexes(column: int, dims: int = 9) -> set[int]:
    """Get row indexes from column."""
    return set(range(column * dims, (column + 1) * dims))


def column_indexes(row: int, dims: int = 9) -> set[int]:
    """Get column indexes from row."""
    return set(range(row, dims * dims, dims))


def show_indexes(indexes: Iterable[int]) -> None:
    """Display grid indexes."""
    grid = Sudoku()
    for index in indexes:
        row, col = flat_to_grid(index)
        grid.grid[col, row] = 1
    print(grid)


def sector_indexes(
    sector_row: int,
    sector_col: int,
    sector_size: int = 3,
) -> set[int]:
    """Get sector indexes from sector number."""
    dims = sector_size * sector_size

    indexes = set()
    y_start = sector_col * sector_size
    x_start = sector_row * sector_size
    for y in range(y_start, y_start + sector_size):
        row = y * dims
        for x in range(x_start, x_start + sector_size):
            indexes.add(x + row)
    return indexes


## _ = 68
##grid_to_sector(*flat_to_grid(68)) = (1, 2)

# 000 111 222
# 000 111 222
# 000 111 222

# 333 444 555
# 333 444 555
# 333 444 5_5

# 666 777 888
# 666 777 888
# 666 777 888


def get_related_areas(
    index: int,
    sector_size: int = 3,
) -> tuple[set[int], set[int], set[int]]:
    """Return row, column, and sector indexes related to a given position."""
    dims = sector_size * sector_size
    row, col = flat_to_grid(index, dims)
    sector = grid_to_sector(row, col, sector_size)
    return (
        row_indexes(col, dims),
        column_indexes(row, dims),
        sector_indexes(*sector, sector_size),
    )


def get_related(index: int, sector_size: int = 3) -> set[int]:
    """Get set of indexes related to a given position."""
    row, col, sec = get_related_areas(index, sector_size)
    sec.update(row, col)
    return sec


class Sudoku:
    """Represents Sudoku Grid."""

    ##    __slots__ = ("grid", "dims", "sector")

    def __init__(self, grid: list[int] | None = None, dims: int = 9) -> None:
        """Initialize sudoku grid."""
        self.dims = dims
        self.sector = ceil(sqrt(self.dims))
        if grid is None:
            self.grid = np.zeros((dims, dims), dtype=np.uint8)
        else:
            self.grid = np.array(grid, dtype=np.uint8).reshape((dims, dims))

    def __repr__(self) -> str:
        """Return representation of self."""
        text = ""
        for column in range(self.dims):
            row_sect = []
            for row_add in range(self.sector):
                row_line = []
                for row in range(self.sector):
                    value = self.grid[column, row + (row_add * self.sector)]
                    row_line.append(f"{value}")
                row_sect.append(",".join(row_line))
            if column and not column % self.sector:
                # Get vertical sector separation
                text = "".join((text, "#", ("-" * 18), "\n"))
            text = "".join((text, ", ".join(row_sect), ",\n"))
        text = "\n".join(" " * 4 + x for x in text[:-2].splitlines())
        return f"{self.__class__.__name__}([\n{text}\n])"

    def __str__(self) -> str:
        """Return text representation of Sudoku grid."""
        text = ""
        for column in range(self.dims):
            row_sect = []
            for row_add in range(self.sector):
                row_line = []
                for row in range(self.sector):
                    value = self.grid[column, row + (row_add * self.sector)]
                    row_line.append(f"{value}" if value else "_")
                row_sect.append(" ".join(row_line))
            if column and not column % self.sector:
                # Get vertical sector separation
                text = "".join(
                    (text, ("-" * 6), "+", ("-" * 7), "+", ("-" * 6), "\n"),
                )
            text = "".join((text, " | ".join(row_sect), "\n"))
        return text[:-1]

    def get_sector(
        self,
        row: int,
        col: int,
    ) -> np.typing.NDArray[np.uint8]:
        """Return 3x3 sector box."""
        return self.grid[
            col * self.sector : (col + 1) * 3,
            row * self.sector : (row + 1) * self.sector,
        ]

    def get_row(self, column: int) -> Line:
        """Return row."""
        return self.grid[column, :]

    def get_column(self, row: int) -> Line:
        """Return column."""
        return self.grid[:, row]

    def get_possible(self, row: int, col: int) -> set[int]:
        """Return a set of all possibilities for blank square given index."""
        if self.grid[col, row]:  # If not blank
            return {self.grid[col, row]}
        miss_row = get_missing(self.get_row(col))
        miss_col = get_missing(self.get_column(row))
        miss_sector = get_missing(
            self.get_sector(*grid_to_sector(row, col, self.sector)),
        )
        # Return where possible in row, column, and sector all at once
        return miss_row & miss_col & miss_sector

    def hidden_single_search(
        self,
        possible: dict[int, set[int]],
    ) -> Generator[tuple[int, set[int]], None, None]:
        """Search for hidden singles and yield indexes that cannot be possibilities."""
        for index, valid in possible.items():
            for area in get_related_areas(index, self.sector):
                mutated_valid = set(valid)
                for area_item in area:
                    if area_item == index:
                        continue
                    if area_item not in possible:
                        continue
                    mutated_valid -= possible[area_item]
                if len(mutated_valid) == 1:
                    yield index, valid - mutated_valid
                    break

    ##    def pair_search(
    ##        self,
    ##        possible: dict[int, set[int]]
    ##    ) -> Generator[tuple[int, set[int]], None, None]:
    ##        """Search for pairs and yield indexes that cannot be possibilities"""
    ##        poss_idx_by_zone: dict[int, list[int]] = {}
    ##        # Sort possibilities into zones
    ##        for index in possible:
    ##            zone = len(possible[index])
    ##            if zone not in poss_idx_by_zone:
    ##                poss_idx_by_zone[zone] = {index}
    ##            else:
    ##                poss_idx_by_zone[zone].add(index)
    ##        for zone in range(2, 5):
    ##            zone_indexes = poss_idx_by_zone.get(zone, set())
    ##            # If not enough of type, not worth continuing
    ##            if len(zone_indexes) < zone:
    ##                continue
    ##            for index in zone_indexes:
    ##                at_index = possible[index]
    ##                for area in get_related_areas(index, self.sector):
    ##                    matching = set()
    ##                    for index_in_area in area & zone_indexes:
    ##                        # See if it's possibilities match ours
    ##                        if possible[index_in_area] == at_index:
    ##                            matching.add(index_in_area)
    ##                    # We must have exactly zone number of matches
    ##                    if len(matching) != zone:
    ##                        continue
    ##                    # possibilities are mutually excusive between matches in this area
    ##                    for index_in_area in area - matching:
    ##                        if index_in_area not in possible:
    ##                            continue
    ##                        bad = possible[index_in_area] & at_index
    ##                        if not bad:
    ##                            continue
    ##                        yield index_in_area, bad

    def pair_search(
        self,
        possible: dict[int, set[int]],
    ) -> Generator[tuple[int, set[int]], None, None]:
        """Search for pairs and yield indexes that cannot be possibilities."""
        zone_indexes = {k for k, v in possible.items() if len(v) == 2}
        for index in zone_indexes:
            at_index = possible[index]
            for area in get_related_areas(index, self.sector):
                matching = set()
                for index_in_area in area & zone_indexes:
                    # See if it's possibilities match ours
                    if possible[index_in_area] == at_index:
                        matching.add(index_in_area)
                # We must have exactly zone number of matches
                if len(matching) != 2:
                    continue
                # possibilities are mutually excusive between matches in this area
                for index_in_area in area - matching:
                    if index_in_area not in possible:
                        continue
                    bad = possible[index_in_area] & at_index
                    if not bad:
                        continue
                    yield index_in_area, bad

    ##    def triplet_search(
    ##        self, possible: dict[int, set[int]]
    ##    ) -> Generator[tuple[int, set[int]], None, None]:
    ##        """Search for pairs and yield indexes that cannot be possibilities"""
    ##        # Do not use, too slow.
    ##        for zone in range(2, 5):
    ##            zone_indexes = {
    ##                k
    ##                for k, v in possible.items()
    ##                if len(v) <= zone and len(v) >= 2
    ##            }
    ##            # If not enough of type, not worth continuing
    ##            if len(zone_indexes) < zone:
    ##                continue
    ##            for index in zone_indexes:
    ##                at_index = possible[index]
    ##                for area in get_related_areas(index, self.sector):
    ##                    for permutation in permutations(area, zone):
    ##                        area_valid = set()
    ##                        area_valid_xor = set()
    ##                        for item in permutation:
    ##                            if item not in possible:
    ##                                break
    ##                            area_valid |= possible[item]
    ##                            area_valid_xor ^= possible[item]
    ##                        if item not in possible:
    ##                            continue
    ##                        if len(area_valid) != zone:
    ##                            continue
    ##                        if zone % 2:
    ##                            bad = bool(area_valid_xor)
    ##                        else:
    ##                            bad = area_valid_xor != area_valid
    ##                        if bad:
    ##                            continue
    ##                        perm_set = set(permutation)
    ##
    ##                        # possibilities are mutually excusive between
    ##                        # matches in this area
    ##                        for index_in_area in area - perm_set:
    ##                            if index_in_area not in possible:
    ##                                continue
    ##                            bad = possible[index_in_area] & area_valid
    ##                            if not bad:
    ##                                continue
    ##                            yield index_in_area, bad

    def triplet_search(
        self,
        possible: dict[int, set[int]],
    ) -> Generator[tuple[int, set[int]], None, None]:
        """Search for pairs and yield indexes that cannot be possibilities."""
        set_possible = set(possible)
        for point, need_relate in possible.items():
            # Need at least 2 possibilities to be related
            if len(need_relate) < 2:
                continue
            # For each group point is in
            for area in get_related_areas(point, self.sector):
                # Find connected points
                connected: set[int] = set()
                possible_area = area & set_possible
                # Only go through unknowns in area
                for item in possible_area:
                    # Has to have at least three
                    if len(possible[item]) < 2:
                        continue
                    related = need_relate & possible[item]
                    if not related:
                        continue
                    connected.add(item)
                if len(connected) < len(need_relate):
                    continue
                all_unknown = set()
                for item in connected:
                    all_unknown |= possible[item]
                if len(all_unknown) == len(connected):
                    for item in possible_area - connected:
                        yield item, all_unknown
                    continue
                for zone in range(3, 5):
                    for permutation in permutations(connected, zone):
                        perm_unknown = set()
                        for item in permutation:
                            perm_unknown |= possible[item]
                            if len(perm_unknown) > zone:
                                break
                        else:
                            if len(perm_unknown) == len(permutation):
                                for item in possible_area - set(permutation):
                                    ##                                    print("permut yield")
                                    yield item, perm_unknown
                                continue
                # print(f"{connected = }\t{all_unknown = }")

    ##    def omission_search(
    ##        self, possible: dict[int, set[int]]
    ##    ) -> Generator[tuple[int, set[int]], None, None]:
    ##        """Search for block omissions and yield indexes that cannot be possibilities"""
    ##        for index in possible:
    ##            valid = possible[index]
    ##            *areas, block = get_related_areas(index, self.sector)
    ##            # for each row and column connected
    ##            for area in areas:
    ##                continue
    ##                yield

    def x_wing_search(
        self,
        possible: dict[int, set[int]],
    ) -> tuple[set[int], set[int]]:
        """Perform an X Wing search and yield indexes that cannot be possibilities."""
        poss_set = {k for k, v in possible.items() if len(v) == 2}
        part: tuple[dict[int, list[int]], dict[int, list[int]]] = (
            {i: [] for i in range(self.dims)},
            {i: [] for i in range(self.dims)},
        )
        # Populate part with possible
        for index in poss_set:
            row, col = flat_to_grid(index, self.dims)
            for which in range(2):
                part[which][(row, col)[which]].append(index)
        candidates: dict[int, list[tuple[int, int, list[int]]]] = {
            0: [],
            1: [],
        }
        for which in range(2):
            for _no, poss in part[which].items():
                if len(poss) < 2:
                    continue
                num_count = {i + 1: 0 for i in range(self.dims)}
                for index in poss:
                    for idx in possible[index]:
                        num_count[idx] += 1
                for num, count in num_count.items():
                    if count < 2:
                        continue
                    where = []
                    for index in poss:
                        if index not in poss_set:
                            continue
                        if num in possible[index]:
                            gridpos = flat_to_grid(index, self.dims)
                            where.append(gridpos[which ^ 1])
                    if not where:
                        continue
                    candidates[which].append((num, gridpos[which], where))
        for which in range(2):
            for idx, entry in enumerate(candidates[which]):
                for idx_two, entry_two in enumerate(candidates[which]):
                    if idx == idx_two:
                        continue
                    if entry[0] != entry_two[0]:
                        continue
                    if entry[1] == entry_two[1]:
                        continue
                    if set(entry[2]) != set(entry_two[2]):
                        continue
                    indexes = set()
                    area_indexes = set()
                    for idx in entry[2]:
                        data = [0, 0]
                        data[which] = entry[1]
                        data[which ^ 1] = idx
                        indexes.add(grid_to_flat(*data))
                        area_indexes.add(entry[1])
                    for idx in entry_two[2]:
                        data = [0, 0]
                        data[which] = entry_two[1]
                        data[which ^ 1] = idx
                        indexes.add(grid_to_flat(*data))
                        area_indexes.add(entry_two[1])
                    func = (row_indexes, column_indexes)[which ^ 1]
                    remove = set()
                    for area in area_indexes:
                        remove |= set(func(area, self.dims))
                    remove -= indexes
                    return remove, {entry[0]}
        return set(), set()

    def xy_wing_search(
        self,
        possible: dict[int, set[int]],
    ) -> Generator[tuple[set[int], set[int]], None, None]:
        """Perform an XY Wing search and yield indexes that cannot be possibilities."""
        # All 2 pair possible
        poss_set = {k for k, v in possible.items() if len(v) == 2}
        for x in poss_set:  # For every possible x wing
            x_related = get_related(x, self.sector)
            # For each index related to x & also a potential wing
            for pivot in x_related & poss_set:
                # Y possibilities are where the pivot is related but X is not related
                y_poss = possible[x] ^ possible[pivot]
                # Only possible if X and Pivot share a possibility and have
                # different for 2nd with the condition that both x and pivot
                # only have 2 possibilities
                if len(y_poss) != 2:
                    continue
                pivot_related = (
                    get_related(pivot, self.sector) & poss_set - x_related
                )
                # y is everything related to pivot but not x, pivot is connecting
                for y in pivot_related:
                    # Must match
                    if possible[y] != y_poss:
                        continue
                    # Every possibility X and Y share must be in either X or Y alone,
                    # therefore nothing connected to them both can be what
                    # one of the two must be
                    y_related = get_related(y, self.sector)
                    items, sub = (
                        x_related & y_related,
                        possible[x] & possible[y],
                    )
                    yield items, sub

    def solve_positions(
        self,
        positions: Iterable[int],
    ) -> Generator[tuple[tuple[int, int], int], None, None]:
        """Solve positions generator. Yield (row, column), value."""
        missing = deque(positions)
        possibilities: dict[int, set[int]] = {}
        for index in missing:
            possibilities[index] = self.get_possible(
                *flat_to_grid(index, self.dims),
            )

        times_left = len(missing)
        while missing:
            # Remember if need to re-calculate later
            index = missing.popleft()

            # Try to eliminate more possibilities with the hidden single strategy
            for related, invalid in self.hidden_single_search(possibilities):
                if related in possibilities:
                    possibilities[related] -= invalid
                    if not possibilities[related]:
                        print("hidden single search")

            # Try to eliminate more possibilities with the pair strategy
            for related, invalid in self.triplet_search(possibilities):
                if related in possibilities:
                    possibilities[related] -= invalid
                    if not possibilities[related]:
                        print("pair search")

            ### Try to eliminate more possibilities with the block omission strategy
            ##for related, invalid in self.omission_search(possibilities):
            ##    if related in possibilities:
            ##        possibilities[related] -= invalid
            ##        if not possibilities[related]:
            ##            print("omission search")

            # Try to eliminate more possibilities with the XY Wing strategy
            indexes, invalid = self.x_wing_search(possibilities)
            for related in indexes:
                if related in possibilities:
                    possibilities[related] -= invalid
                    if not possibilities[related]:
                        print("x wing search")

            # Try to eliminate more possibilities with the XY Wing strategy
            for indexes, invalid in self.xy_wing_search(possibilities):
                for related in indexes:
                    if related in possibilities:
                        possibilities[related] -= invalid
                        if not possibilities[related]:
                            print("xy wing search")

            if index not in possibilities:
                copy = {k: repr(v) for k, v in possibilities.items()}
                print(json.dumps(copy, indent=2))

            if len(possibilities[index]) == 1:  # If only one, yield solution
                # pop = zero index if length one
                value = possibilities[index].pop()

                # Clear now un-required
                del possibilities[index]

                # Update board
                yield flat_to_grid(index, self.dims), value

                # Update possibilities
                for related in get_related(index, self.sector):
                    if related in possibilities:
                        ##                        possibilities[related] &= self.get_possible(
                        ##                            *flat_to_grid(related, self.dims)
                        ##                        )
                        possibilities[related] -= {value}

                times_left = 2 + len(missing)  # reset exhaust counter
            else:  # otherwise, re-add to queue
                missing.append(index)

                times_left -= 1
                if times_left == 1:
                    for index in missing:
                        possibilities[index] = self.get_possible(
                            *flat_to_grid(index, self.dims),
                        )
                if (
                    not times_left
                ):  # If have already visited all without solution, not solvable
                    copy = {k: repr(v) for k, v in possibilities.items()}
                    print(json.dumps(copy, indent=2))
                    raise RuntimeError("Sudoku is impossible to solve")
            # print(f'{times_left = }')

    def get_missing(self) -> tuple[int, ...]:
        """Get indexes of zero positions, which are unsolved."""
        return tuple(
            np.asarray(self.grid.flatten() == 0).nonzero()[0].tolist(),
        )

    def solve(self) -> None:
        """Solve puzzle *IN PLACE*."""
        missing = self.get_missing()

        # Use generator to complete missing
        for location, value in self.solve_positions(missing):
            row, col = location
            self.grid[col, row] = value


def run() -> None:
    """Run test of module."""
    _ = 0  # Easier to see known grid
    # fmt: off
    ##    puzzle = Sudoku([
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        #---------------------
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        #---------------------
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        _,_,_,  _,_,_,  _,_,_,
    ##        _,_,_,  _,_,_,  _,_,_
    ##    ])
    puzzle = Sudoku([
        2, _, _, _, 9, _, _, _, 8,
        3, _, _, 2, _, 7, _, _, 6,
        _, 6, 7, _, _, _, 5, 2, _,
        6, _, 2, 1, _, 8, 3, _, 5,
        _, _, _, 5, _, 4, _, _, _,
        7, _, 5, 9, _, 3, 4, _, 1,
        _, 2, 4, _, _, _, 8, 7, _,
        8, _, _, 7, _, 2, _, _, 4,
        5, _, _, _, 4, _, _, _, 2,
    ])
    ##    puzzle = Sudoku([
    ##        0,0,3, 8,0,0, 5,1,0,
    ##        0,0,8, 7,0,0, 9,3,0,
    ##        1,0,0, 3,0,5, 7,2,8,
    ##        #------------------
    ##        0,0,0, 2,0,0, 8,4,9,
    ##        8,0,1, 9,0,6, 2,5,7,
    ##        0,0,0, 5,0,0, 1,6,3,
    ##        #------------------
    ##        9,6,4, 1,2,7, 3,8,5,
    ##        3,8,2, 6,5,9, 4,7,1,
    ##        0,1,0, 4,0,0, 6,9,2
    ##    ])
    ##    puzzle = Sudoku([
    ##        _,_,_,  5,_,8,  _,_,_,
    ##        5,_,_,  1,_,3,  _,_,9,
    ##        6,_,1,  _,2,_,  5,_,3,
    ##        #---------------------
    ##        4,7,9,  _,_,_,  6,5,8,
    ##        _,_,_,  9,_,6,  _,_,_,
    ##        1,2,6,  _,_,_,  9,3,4,
    ##        #---------------------
    ##        2,_,4,  _,9,_,  8,_,5,
    ##        9,_,_,  6,_,5,  _,_,2,
    ##        _,_,_,  2,_,4,  _,_,_
    ##    ])
    ##    puzzle = Sudoku(
    ##        [
    ##            _,_,3,  8,_,_,  5,1,_,
    ##            _,_,8,  7,_,_,  9,3,_,
    ##            1,_,_,  3,_,5,  7,2,8,
    ##            #---------------------
    ##            _,_,_,  2,_,_,  8,4,9,
    ##            8,_,1,  9,_,6,  2,5,7,
    ##            _,_,_,  5,_,_,  1,6,3,
    ##            #---------------------
    ##            9,6,4,  1,2,7,  3,8,5,
    ##            3,8,2,  6,5,9,  4,7,1,
    ##            _,1,_,  4,_,_,  6,9,2,
    ##        ]
    ##    )
    ##    puzzle = Sudoku([
    ##        _,7,_,  5,3,_,  1,_,6,
    ##        _,_,2,  _,_,_,  _,_,7,
    ##        _,_,_,  _,8,_,  _,_,_,
    ##        #---------------------
    ##        _,5,_,  _,_,8,  _,_,_,
    ##        _,_,4,  6,5,_,  _,3,_,
    ##        _,_,_,  _,_,2,  6,_,_,
    ##        #---------------------
    ##        _,_,_,  _,_,6,  _,_,_,
    ##        9,_,_,  _,_,_,  _,4,_,
    ##        _,2,_,  1,7,_,  3,_,_
    ##    ])
    ##    puzzle = Sudoku([
    ##        _,_,_, _,_,_, _,_,2,
    ##        _,_,_, _,9,5, 4,_,_,
    ##        _,_,6, 8,_,_, _,_,_,
    ##        #------------------
    ##        _,8,_, _,2,_, _,_,1,
    ##        _,_,_, _,_,9, 7,3,_,
    ##        1,_,_, _,_,_, _,5,_,
    ##        #------------------
    ##        8,9,3, _,1,_, _,_,_,
    ##        _,_,_, _,_,_, _,_,4,
    ##        _,_,7, 6,_,_, 3,_,_,
    ##    ])
    ##    puzzle = Sudoku([
    ##        _,_,_,  _,_,_,  _,_,2,
    ##        _,_,_,  _,9,5,  4,_,_,
    ##        _,_,6,  8,_,_,  _,_,_,
    ##        #---------------------
    ##        _,8,5,  _,2,_,  9,4,1,
    ##        _,_,_,  1,_,9,  7,3,8,
    ##        1,_,_,  _,_,_,  2,5,6,
    ##        #---------------------
    ##        8,9,3,  _,1,_,  _,_,_,
    ##        _,_,_,  9,_,_,  _,_,4,
    ##        _,_,7,  6,_,_,  3,_,_
    ##    ])
    # fmt: on

    print("Original:")
    print(puzzle)
    try:
        puzzle.solve()
        print("\nSolved:")
    finally:
        print()
        print(puzzle)


if __name__ == "__main__":
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    run()
