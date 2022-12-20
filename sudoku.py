#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Sudoku Solver - Solve Sudoku puzzles with wave function collapse

"Sudoku Solver"

# Programmed by CoolCat467

__title__ = 'Sudoku Solver'
__author__ = 'CoolCat467'
__version__ = '0.0.0'
__ver_major__ = 0
__ver_minor__ = 0
__ver_patch__ = 0

from collections.abc import Container, Iterable, Generator
from collections import deque
from math import ceil, sqrt

import numpy as np

Int8 = np.dtype[np.int8]
Line = np.ndarray[int, Int8]

def get_missing(line: Container[int]) -> set[int]:
    "Return all missing numbers from line"
    return {x for x in range(1, 10) if not x in line}

def to_grid(index: int, dims: int=9) -> tuple[int, int]:
    "Return grid index of given flat index"
    col, row = divmod(index, dims)
    return row, col

def to_sector(row: int, col: int, sector_size: int=3) -> tuple[int, int]:
    "Return sector that contains given grid index"
    return (row // sector_size, col // sector_size)

def from_grid(row: int, col: int, dims: int=9) -> int:
    "Get flat index from grid index"
    return col * dims + row

##def to_sector_index(sector_row: int, sector_col: int, sector_size: int=3) -> int:
##    "Return sector index given the sector row and column"
##    return sector_row * sector_size + sector_col

def row_indexes(column: int, dims: int=9) -> list[int]:
    "Get row indexes from column"
    return [i for i in range(column*dims, (column+1)*dims)]

def column_indexes(row: int, dims: int=9) -> list[int]:
    "Get column indexes from row"
    return [i for i in range(row, dims*dims, dims)]

def show_indexes(indexes: list[int]) -> None:
    grid = Sudoku()
    for index in indexes:
        row, col = to_grid(index)
        grid.grid[col, row] = 1
    print(grid)

def sector_indexes(sector_row: int, sector_col: int, sector_size: int=3) -> list[int]:
    "Get sector indexes from sector number"
    dims = sector_size * sector_size
    
    indexes = []
    y_start = sector_col * sector_size
    x_start = sector_row * sector_size
    for y in range(y_start, y_start+sector_size):
        row = y*dims
        for x in range(x_start, x_start+sector_size):
            indexes.append(x+row)
    return indexes
## _ = 68
##to_sector(*to_grid(68)) = (1, 2)

#000 111 222
#000 111 222
#000 111 222

#333 444 555
#333 444 555
#333 444 5_5

#666 777 888
#666 777 888
#666 777 888

def get_related(index: int, sector_size: int=3) -> set[int]:
    "Get list of related indexes"
    dims = sector_size * sector_size
    row, col = to_grid(index, dims)
    sector = to_sector(row, col, sector_size)
    value =  set(
        row_indexes(col, dims)
        + column_indexes(row, dims)
        + sector_indexes(*sector, sector_size)
    )
##    print('\n\n')
##    show_indexes(value)
    return value

class Sudoku:
    "Represents Sudoku Grid"
##    __slots__ = ('grid', 'dims', 'sector')
    def __init__(self, grid: list[int] | None=None, dims: int=9) -> None:
        self.dims = dims
        self.sector = ceil(sqrt(self.dims))
        if grid is None:
            grid = [0]*(self.dims*self.dims)
        self.grid = np.array(grid, np.int8).reshape((9, 9))

    def __repr__(self) -> str:
        "Get representation of Sudoku grid"
        text = ''
        for column in range(self.dims):
            row_sect = []
            for row_add in range(self.sector):
                row_line = []
                for row in range(self.sector):
                    value = self.grid[column, row+(row_add*self.sector)]
                    row_line.append(f'{value}' if value else '_')
                row_sect.append(' '.join(row_line))
            if column and not column % self.sector:
                # Get vertical sector separation
                text = ''.join((text, ('-'*6), '+', ('-'*7), '+', ('-'*6), '\n'))
            text = ''.join((text, ' | '.join(row_sect), '\n'))
        return text[:-1]

    def get_sector(self, row: int, col: int) -> np.ndarray[tuple[int, int], Int8]:
        "Get 3x3 sector box"
        return self.grid[col*self.sector:(col+1)*3, row*self.sector:(row+1)*self.sector]

    def get_row(self, column: int) -> Line:
        "Get row"
        return self.grid[column, :]

    def get_column(self, row: int) -> Line:
        "Get column"
        return self.grid[:, row]

    def get_possible(self, row: int, col: int) -> set[int]:
        "Return a set of all possibilities for blank square given index"
        if self.grid[col, row]:# If not blank
            return set((self.grid[col, row],))
        miss_row = get_missing(self.get_row(col))
        miss_col = get_missing(self.get_column(row))
        miss_sector = get_missing(self.get_sector(*to_sector(row, col, self.sector)))
        # Return where possible in row, column, and sector all at once
        return miss_row & miss_col & miss_sector
    
    def x_wing_search(self, possible: dict[int, set[int]]) -> tuple[set[int], set[int]]:
        "Preform an X Wing search and yield indexes that cannot be possibilities"
        poss_set = set(k for k, v in possible.items() if len(v) == 2)
        part: tuple[dict[int, list[int]], dict[int, list[int]]] = (
            {i:[] for i in range(self.dims)},
            {i:[] for i in range(self.dims)}
        )
        # Populate part with possible
        for index in poss_set:
            row, col = to_grid(index, self.dims)
            for which in range(2):
                part[which][(row, col)[which]].append(index)
        candidates: dict[int, list[tuple[int, int, list[int]]]] = {0:[], 1:[]}
        for which in range(2):
            for no, poss in part[which].items():
                if len(poss) < 2:
                    continue
                num_count = {i+1:0 for i in range(self.dims)}
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
                            gridpos = to_grid(index, self.dims)
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
                        data[which]     = entry[1]
                        data[which ^ 1] = idx
                        indexes.add(from_grid(*data))
                        area_indexes.add(entry[1])
                    for idx in entry_two[2]:
                        data = [0, 0]
                        data[which]     = entry_two[1]
                        data[which ^ 1] = idx
                        indexes.add(from_grid(*data))
                        area_indexes.add(entry_two[1])
                    func = (row_indexes, column_indexes)[which ^ 1]
                    remove = set()
                    for area in area_indexes:
                        remove |= set(func(area, self.dims))
                    remove -= indexes
##                    if 72 in remove and possible[72] & {entry[0]}:
##                        print('\n')
##                        print(f'{indexes = }')
##                        print(f'num = {entry[0]}')
##    ##                    print(entry)
##    ##                    print(entry_two)
##    ##                    print(area_indexes)
##    ##                    show_indexes(indexes)
##    ##                    print(indexes)
##                        show_indexes(remove)
##                        print(self)
                    return remove, {entry[0]}
##                    showed = True
##                    
##        if showed:
##            raise ValueError
##                print(index, poss)
##                print(keep)
##            print('\n')
##        yield set(), set()
        return set(), set()
    
    def xy_wing_search(self, possible: dict[int, set[int]]) -> Generator[tuple[set[int], set[int]], None, None]:
        "Preform an XY Wing search and yield indexes that cannot be possibilities"
        # All 2 pair possible
        poss_set = set(k for k, v in possible.items() if len(v) == 2)
        for x in poss_set:# For every possible x wing
##            if not x in poss_set:
##                continue
            x_related = get_related(x, self.sector)
            # For each index related to x & also a potential wing
            for pivot in x_related & poss_set:
                y_poss = possible[x] ^ possible[pivot]
                # Only possible if X an Pivot share a possibility and have
                # different for 2nd with the condition that both x and pivot
                # only have 2 possibilities
                if len(y_poss) != 2:
                    continue
                pivot_related = get_related(pivot, self.sector) & poss_set ^ {x}
                # y is everything related to pivot but not x, pivot is connecting
                for y in pivot_related - x_related:
                    # Must match
                    if possible[y] != y_poss:
                        continue
                    # Every possibility X and Y share must be in either X or Y alone,
                    # therefore nothing connected to them both can be what
                    # one of the two must be
                    y_related = get_related(y, self.sector)
                    items, sub = x_related & y_related, possible[x] & possible[y]
                    yield items, sub
##                    # Make sure to remove local copy from 2 pairs if they existed
##                    for item in items:
##                        if item in poss_set:
##                            poss_set.remove(item)
##        return set(), set()

    def solve_positions(self,
                        # lintcheck: line-too-long (C0301): Line too long (104/100)
                        positions: Iterable[int]) -> Generator[tuple[tuple[int, int], int], None, None]:
        "Solve positions generator. Yields (row, column), value"
        missing = deque(positions)
        possibilities: dict[int, set[int]] = {}
        for index in missing:
            possibilities[index] = self.get_possible(*to_grid(index, self.dims))
        
        times_left = len(missing)
        while missing:
            # Remember if need to re-calculate later
            index = missing.popleft()
            
            # Try to eliminate more possibilities with the XY Wing strategy
##            for indexes, invalid in self.x_wing_search(possibilities):
            indexes, invalid = self.x_wing_search(possibilities)
            for related in indexes:
                if related in possibilities:
                    possibilities[related] -= invalid
##                    if related == 72:
##                        print(f'X : {invalid} {possibilities[related]}')
            
            # Try to eliminate more possibilities with the XY Wing strategy
            for indexes, invalid in self.xy_wing_search(possibilities):
                for related in indexes:
                    if related in possibilities:
                        possibilities[related] -= invalid
##                        if related == 27:
##                            print(f'XY : {possibilities[related]} - {invalid}')
            
            if len(possibilities[index]) == 1:# If only one, yield solution
                # pop = zero index if length one
                value = possibilities[index].pop()
                
                # Clear now un-required
                del possibilities[index]
                
                # Update board
                yield to_grid(index, self.dims), value
                
                # Update possibilities
                for related in get_related(index, self.sector):
                    if related in possibilities:
                        possibilities[related] &= self.get_possible(*to_grid(related, self.dims))

                times_left = 2+len(missing)# reset exhaust counter
            else:# otherwise, re-add to queue
                missing.append(index)

                times_left -= 1
                if times_left == 1:
                    for index in missing:
                        possibilities[index] = self.get_possible(*to_grid(index, self.dims))
                if not times_left:# If have already visited all without solution, not solvable
                    print(possibilities)
                    raise RuntimeError('Sudoku is impossible to solve')
    
    def get_missing(self) -> tuple[int, ...]:
        "Get indexes of zero positions, which are unsolved"
        return tuple(np.asarray(self.grid.flatten() == 0).nonzero()[0].tolist())

    def solve(self) -> None:
        "Solve puzzle *IN PLACE*"
        missing = self.get_missing()
        
        # Use generator to complete missing
        for location, value in self.solve_positions(missing):
            row, col = location
            self.grid[col, row] = value

def run() -> None:
    "Run test of module"
    _ = 0 # Easier to see known grid
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
##    puzzle = Sudoku([
##        2, _, _, _, 9, _, _, _, 8,
##        3, _, _, 2, _, 7, _, _, 6,
##        _, 6, 7, _, _, _, 5, 2, _,
##        6, _, 2, 1, _, 8, 3, _, 5,
##        _, _, _, 5, _, 4, _, _, _,
##        7, _, 5, 9, _, 3, 4, _, 1,
##        _, 2, 4, _, _, _, 8, 7, _,
##        8, _, _, 7, _, 2, _, _, 4,
##        5, _, _, _, 4, _, _, _, 2
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
    puzzle = Sudoku([
        _,_,3,  8,_,_,  5,1,_,
        _,_,8,  7,_,_,  9,3,_,
        1,_,_,  3,_,5,  7,2,8,
        #---------------------
        _,_,_,  2,_,_,  8,4,9,
        8,_,1,  9,_,6,  2,5,7,
        _,_,_,  5,_,_,  1,6,3,
        #---------------------
        9,6,4,  1,2,7,  3,8,5,
        3,8,2,  6,5,9,  4,7,1,
        _,1,_,  4,_,_,  6,9,2
    ])
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
    
    print('Original:')
    print(puzzle)
    try:
        puzzle.solve()
        print('\nSolved:')
    finally:
        print()
        print(puzzle)



if __name__ == '__main__':
    print(f'{__title__} v{__version__}\nProgrammed by {__author__}.\n')
    run()
