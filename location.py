#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Location - Vector2 bound to a rect

"Location"

# Programmed by CoolCat467

__title__ = "Location"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__ver_major__ = 0
__ver_minor__ = 0
__ver_patch__ = 0

from typing import TypeVar, Union, cast, overload

from pygame.rect import Rect

from vector import Vector, Vector2

T = TypeVar("T")
##L = TypeVar('L', bound = int | float)


class Location(Vector2[int]):
    "Location bound to the center of a given rectangle"
    __slots__ = ("_rect",)

    @overload
    def __new__(cls, *args: int, dtype: type) -> Vector2[int]:
        ...  # type: ignore[misc]

    @overload
    def __new__(cls, *args: int, dtype: None = None) -> "Location":
        ...

    def __new__(
        cls, *args: int, dtype: type | None = None  # type: ignore[misc]
    ) -> "Location | Vector2[int]":
        "Super hack to return Vector2 if data type is not None, otherwise new Location."
        if dtype is not None:
            new_vec = super().__new__(Vector2)
            new_vec.__init__(*args, dtype=dtype)  # type: ignore
            return new_vec
        return super().__new__(cls)

    def __init__(self, rect: Rect) -> None:
        "Initialize Location with rectangle."
        self._rect = rect
        super().__init__(*self._rect.center, dtype=list)

    def __setitem__(
        self, index: int, value: int | float | complex, normal: bool = False
    ) -> None:
        "Set item, but if not normal, updates rectangle as well."
        if isinstance(value, complex):
            raise ValueError("No complex for Locations")
        super().__setitem__(index, int(value))
        if normal:
            return
        new_x, new_y = tuple(self)
        self._rect.center = new_x, new_y

    def __getitem__(self, index: int) -> int:
        "Get item, but sets internal data at index to data from rectangle center first."
        self.__setitem__(index, self._rect.center[index], normal=True)  # type: ignore[call-arg]
        return super().__getitem__(index)

    def normalize(self) -> Vector[float]:
        "Raise NotImplemented, original is in place."
        raise NotImplementedError

    def set_length(self, new_length: T) -> Vector[T]:
        "Raise NotImplemented, original is in place."
        raise NotImplementedError


def run() -> None:
    "Run program"


if __name__ == "__main__":
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    run()
