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

from typing import Container, Iterable, Generator

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

class Sudoku:
    "Represents Sudoku Grid"
    __slots__ = ('grid', 'dims', 'sector')
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

    def solve_positions(self,
                        positions: Iterable[int]) -> Generator[tuple[tuple[int, int], int], None, None]:
        "Solve positions generator. Yields (row, column), value"
        missing = deque(positions)
        times_left = len(missing)
        while missing:
            index = missing.popleft()# Remember if need to re-calculate later
            row, col = to_grid(index, self.dims)

            possible = self.get_possible(row, col)
            if len(possible) == 1:# If only one, yield solution
                yield (row, col), possible.pop()# pop = zero index if length one

                times_left = len(missing)# reset exhaust counter
            else:# _therwise, re-add to queue
                missing.append(index)

                times_left -= 1
                if not times_left:# If have already visited all without solution, not solvable
                    raise RuntimeError('Sudoku is impossible to solve')

    def solve(self) -> None:
        "Solve puzzle *IN PLACE*"
        # Get indexes of zero positions, which are unsolved
        missing = tuple(np.asarray(self.grid.flatten() == 0).nonzero()[0].tolist())

        # Use generator to complete missing
        for location, value in self.solve_positions(missing):
            row, col = location
            self.grid[col, row] = value

def run() -> None:
    "Run test of module"
    _ = 0 # Easier to see known grid
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
    puzzle = Sudoku([
        _,_,_,  5,_,8,  _,_,_,
        5,_,_,  1,_,3,  _,_,9,
        6,_,1,  _,2,_,  5,_,3,
        #---------------------
        4,7,9,  _,_,_,  6,5,8,
        _,_,_,  9,_,6,  _,_,_,
        1,2,6,  _,_,_,  9,3,4,
        #---------------------
        2,_,4,  _,9,_,  8,_,5,
        9,_,_,  6,_,5,  _,_,2,
        _,_,_,  2,_,4,  _,_,_
    ])
    print('Original:')
    print(puzzle)
    puzzle.solve()
    print('\nSolved:')
    print(puzzle)



if __name__ == '__main__':
    print(f'{__title__} v{__version__}\nProgrammed by {__author__}.\n')
    run()
