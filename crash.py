#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Crash example - TypeError: type 'LayeredDirty' is not subscriptable

"""This is a modified excerpt from a game I am programming"""

# Programmed by CoolCat467

from typing import Any

from pygame.rect import Rect
from pygame.sprite import DirtySprite, LayeredDirty
from pygame.surface import Surface


class Component:
    "Base Component"

    def __init__(self, name: str) -> None:
        ...


class ComponentManager(Component):
    "Group of Components"

    def __init__(self, name: str) -> None:
        super().__init__(name)
        ...


class Sprite(DirtySprite, ComponentManager):
    "Both Dirty Sprite and Component Manager"

    def __init__(self, name: str) -> None:
        DirtySprite.__init__(self)
        ComponentManager.__init__(self, name)

        self.rect = Rect(0, 0, 0, 0)
        self.image = Surface((0, 0))

    ...


### Monkey-patch LayeredDirty to properly support __class_getitem__
##LayeredDirty.__class_getitem__ = lambda x: LayeredDirty  # type: ignore[attr-defined]


class Group(LayeredDirty[Sprite], ComponentManager):
    "Group of Layered Dirty Sprites"
    __slots__ = ()

    def __init__(self, name: str, *sprites: Sprite, **kwargs: Any) -> None:
        LayeredDirty.__init__(self, *sprites, **kwargs)
        ComponentManager.__init__(self, name)

    ...
