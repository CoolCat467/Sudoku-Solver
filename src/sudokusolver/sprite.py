"""Sprite module."""

# Programmed by CoolCat467

# Copyright (C) 2023  CoolCat467
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

__title__ = "Sprite"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"
__version__ = "0.0.0"

from typing import Any, cast

from component import Component, ComponentManager, Event
from pygame import mask
from pygame.color import Color
from pygame.rect import Rect
from pygame.sprite import LayeredDirty, LayeredUpdates, WeakDirtySprite
from pygame.surface import Surface
from vector import Vector2


class Sprite(ComponentManager, WeakDirtySprite):
    """Client dirty sprite component manager."""

    __slots__ = ("rect", "update_location_on_resize")

    def __init__(self, name: str) -> None:
        """Initialize Sprite."""
        ComponentManager.__init__(self, name)
        WeakDirtySprite.__init__(self)

        self.rect = Rect(0, 0, 0, 0)

        self.update_location_on_resize = False

    def __repr__(self) -> str:
        """Return representation of self."""
        return f"<{self.__class__.__name__} Sprite>"

    def __get_location(self) -> Vector2:
        """Return rect center as new Vector2."""
        return Vector2.from_iter(self.rect.center)

    def __set_location(self, value: tuple[int, int]) -> None:
        """Set rect center from tuple of integers."""
        self.rect.center = value

    location = property(
        __get_location,
        __set_location,
        doc="Location (Center of image)",
    )

    def __get_image(self) -> Surface | None:
        """Return the surface of this sprite."""
        return self.__image

    def __set_image(self, image: Surface | None) -> None:
        """Set surface, update image dimensions, and set dirty bit.

        Automatically updates location if self.update_location_on_resize is set.
        """
        self.__image = image
        if image is not None:
            pre_loc = self.location
            self.rect.size = image.get_size()
            if self.update_location_on_resize:
                self.location = pre_loc
        if self.dirty == 0:
            self.dirty = 1

    image = cast(
        Surface,
        property(
            __get_image,
            __set_image,
            doc="Image property auto-updating dimensions and setting dirty bit.",
        ),
    )

    # Extra
    def is_selected(self, position: tuple[int, int]) -> bool:
        """Return True if visible and collision with point."""
        if not self.visible:
            return False
        return self.rect.collidepoint(position)

    def is_topmost(self, position: tuple[int, int]) -> bool:
        """Return True if topmost at point in any group this sprite is in."""
        for group in self.groups():
            assert isinstance(
                group,
                LayeredUpdates,
            ), "Group must have get_sprites_at"
            sprites_at = group.get_sprites_at(position)
            if not sprites_at:
                continue
            for top in reversed(sprites_at):
                if top != self and top.visible:
                    return False
        return True


# Monkey-patch LayeredDirty to properly support __class_getitem__
LayeredDirty.__class_getitem__ = lambda x: LayeredDirty  # type: ignore[attr-defined]


class Group(LayeredDirty[Sprite], ComponentManager):
    """Group of Layered Dirty Sprites."""

    __slots__ = ()

    def __init__(self, name: str, *sprites: Sprite, **kwargs: Any) -> None:
        """Initialize Group."""
        LayeredDirty.__init__(self, *sprites, **kwargs)
        ComponentManager.__init__(self, name)

    def group_add(self, sprite: Sprite, layer: int | None = None) -> None:
        """Only add sprite to render group, not to component."""
        super().add_internal(sprite, layer)  # type: ignore[arg-type]

    def add_internal(self, sprite: Sprite, layer: int | None = None) -> None:
        """Do not use this method directly.

        It is used by the group to add a sprite internally.
        """
        super().add_internal(sprite, layer)  # type: ignore[arg-type]
        if isinstance(sprite, Component):
            super().add_component(sprite)

    def remove_internal(self, sprite: Sprite) -> None:
        """Do not use this method directly.

        The group uses it to add a sprite.
        """
        super().remove_internal(sprite)
        if isinstance(sprite, Component):
            super().remove_component(sprite.name)


class Click(Component):
    """Raise `click` and `click_end` events on sprite when clicked."""

    __slots__ = ("selected",)

    def __init__(self) -> None:
        """Initialize Click component."""
        super().__init__("click")

        self.selected = False

        self.add_handler("MouseButtonDown", self.handle_mouse_down)
        self.add_handler("MouseButtonUp", self.handle_mouse_up)

    async def handle_mouse_down(self, event: Event[tuple[int, int]]) -> None:
        """Handle mouse down events."""
        if self.manager is None:
            return
        if self.manager.is_selected(event["pos"]) and self.manager.is_topmost(event["pos"]):
            self.selected = True
            await self.manager(Event("click", event))
        elif self.selected:
            self.selected = False
            await self.manager(Event("click_stop", event))

    async def handle_mouse_up(self, event: Event[Any]) -> None:
        """Handle mouse up events."""
        if self.selected and self.manager is not None:
            self.selected = False
            await self.manager(Event("click_stop", event))


class Draggable(Component):
    """Make Sprite Draggable."""

    __slots__ = ("active",)

    def __init__(self) -> None:
        """Initialize draggable component."""
        super().__init__("draggable")

        self.active = False

        self.add_handler("drag", self.drag_start)
        self.add_handler("drag_stop", self.drag_end)
        self.add_handler("MouseMotion", self.handle_mouse_motion)

    async def drag_start(self, event: Event[Any]) -> str:
        """Start dragging."""
        self.active = True
        return "break"

    async def drag_end(self, event: Event[Any]) -> str:
        """Start dragging."""
        self.active = False
        return "break"

    async def handle_mouse_motion(self, event: Event[tuple[int, int]]) -> None:
        """Handle mouse motion events."""
        if not self.active or self.manager is None:
            return
        assert isinstance(self.manager, Sprite)
        self.manager.location += event["rel"]
        self.manager.dirty = 1


class PressHoldDrag(Component):
    """Raise drag events when held down."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize press hold drag component."""
        super().__init__("press_hold_drag")

        self.add_handler("click", self.start_click)
        self.add_handler("click_stop", self.stop_click)

    async def start_click(self, event: Event[Any]) -> None:
        """Handle click start event."""
        if self.manager is None:
            return
        await self.manager(Event("drag"))

    async def stop_click(self, event: Event[Any]) -> None:
        """Handle click stop event."""
        if self.manager is None:
            return
        await self.manager(Event("drag_stop"))


class ToggleDrag(Component):
    """Raise drag events when held down."""

    __slots__ = ("active",)

    def __init__(self) -> None:
        """Initialize toggle drag component."""
        super().__init__("toggle_drag")

        self.active = False

        self.add_handler("click", self.handle_click)
        self.add_handler("WindowLeave", self.handle_win_leave)

    async def update(self) -> None:
        """Raise drag or drag_stop events depending on state."""
        if self.manager is None:
            return
        if self.active:
            await self.manager(Event("drag"))
        else:
            await self.manager(Event("drag_stop"))

    async def handle_click(self, event: Event[Any]) -> None:
        """Toggle active on click event."""
        self.active = not self.active
        await self.update()

    async def handle_win_leave(self, event: Event[Any]) -> None:
        """If active, stop dragging."""
        if self.active:
            self.active = False
            await self.update()


class Outline(Component):
    """Outline sprite."""

    __slots__ = ("active", "mask_threshold")

    def __init__(self) -> None:
        """Initialize outline component."""
        super().__init__("outline")

        self.active = False
        self.mask_threshold = 0x7F

        self.add_handler("outline", self.outline_handler)

    @staticmethod
    def _get_outline(surface: Surface, size: int, color: Color, mask_threshold: int) -> Surface:
        """Outline surface."""
        w, h = surface.get_size()

        diameter = size * 2
        surf = Surface((w + diameter, h + diameter)).convert_alpha()
        surf.fill(Color(0, 0, 0, 0))

        surf.lock()
        for ox, oy in mask.from_surface(surface, mask_threshold).outline():
            for x in range(diameter + 1):
                for y in range(diameter + 1):
                    surf.set_at((ox + x, oy + y), color)
        surf.unlock()
        surf.blit(surface, (size, size))
        return surf

    @staticmethod
    def _revert_outline(surface: Surface, color: Color) -> Surface:
        """Revert outline."""
        w, h = surface.get_size()

        surf = surface.copy().convert_alpha()
        surf.fill(Color(0, 0, 0, 0))

        area = Rect(0, 0, 0, 0)
        surf.lock()
        y_inter = False
        x_inter = False
        for y in range(h):
            for x in range(w):
                value = surface.get_at((x, y))
                if value == color:
                    if not y_inter:
                        area.top = y
                    else:
                        area.bottom = y
                    if not x_inter:
                        area.left = x
                    else:
                        area.right = x
                else:
                    if not y_inter:
                        y_inter = True
                    if not x_inter:
                        x_inter = True
                    surf.set_at((x, y), value)
        surf.unlock()
        final = Surface(area.size)
        final.blit(surf, (0, 0), area=area)
        return surf

    async def outline_handler(self, event: Event[bool | int | Color]) -> str:
        """Apply outline."""
        if event["enable"] != self.active and isinstance(self.manager, Sprite):
            if not self.active:
                new = self._get_outline(
                    self.manager.image,
                    event["size"],
                    event["color"],
                    self.mask_threshold,
                )
                self.manager.image = new
            else:
                new = self._revert_outline(self.manager.image, event["color"])
                self.manager.image = new
            self.active = event["enable"]
        return "break"


class DragOutline(Component):
    """Enable outline while dragging."""

    __slots__ = ("color", "size")

    def __init__(self) -> None:
        """Initialize drag outline component."""
        super().__init__("drag_outline")

        self.color = Color(255, 0, 0)
        self.size = 2

        self.add_handler("drag", self.start_drag)
        self.add_handler("drag_stop", self.stop_drag)

    async def start_drag(self, event: Event[Any]) -> None:
        """Handle drag start event."""
        if self.manager is None:
            return
        await self.manager(
            Event(
                "outline",
                {"enable": True, "color": self.color, "size": self.size},
            ),
        )

    async def stop_drag(self, event: Event[Any]) -> None:
        """Handle drag stop event."""
        if self.manager is None:
            return
        await self.manager(
            Event(
                "outline",
                {
                    "enable": False,
                    "color": self.color,
                },
            ),
        )


if __name__ == "__main__":  # pragma: nocover
    print(f"{__title__}\nProgrammed by {__author__}.\n")
