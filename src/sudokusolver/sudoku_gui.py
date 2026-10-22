"""Sudoku-GUI - Graphical User Interface for Sudoku Solver."""

# Programmed by CoolCat467

from __future__ import annotations

# Sudoku
# Copyright (C) 2023-2026  CoolCat467
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
import contextlib
import platform
from collections import deque
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pygame
import trio
from libcomponent.async_clock import Clock
from libcomponent.component import (
    Component,
    ComponentManager,
    Event,
    ExternalRaiseManager,
)
from pygame.color import Color
from pygame.locals import K_ESCAPE, KEYUP, QUIT, WINDOWRESIZED
from pygame.rect import FRect, Rect
from pygame.surface import Surface

from sudokusolver import sprite
from sudokusolver.statemachine import AsyncState
from sudokusolver.sudoku import CSPSudoku, grid_to_flat
from sudokusolver.vector import Vector2

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Generator

__title__ = "Sudoku-GUI"
__author__ = "CoolCat467"
__version__ = "0.0.0"

SCREEN_SIZE = Vector2(800, 600)
FPS = 48
VSYNC = True

TILE_SIZE = 50
TILE_SEP = 4
DATA_FOLDER: Final = Path(__file__).parent / "data"
FONT_FILENAME = DATA_FOLDER / "BookmanOldStyle.ttf"
FONT_SIZE = 60

IS_WINDOWS: Final = platform.system() == "Windows"


class MrFloppy(sprite.Sprite):
    """Test sprite."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize Mr. Floppy."""
        super().__init__("mr floppy")
        self.image = pygame.image.load(DATA_FOLDER / "mr_floppy.png")
        self.location = SCREEN_SIZE / 2

        ##        self.add_component(sprite.Click())
        ##        self.add_component(sprite.Draggable())
        ##        self.add_component(sprite.PressHoldDrag())
        ##        self.add_component(sprite.Outline())
        ##        self.add_component(sprite.DragOutline())
        self.add_component(sprite.DragClickEventComponent())


class Timer(Component):
    """Re-raise tick events but renamed to <name> every x seconds."""

    __slots__ = ("elapsed", "times")

    def __init__(self) -> None:
        """Initialize Timer."""
        super().__init__("timer")

        self.times: dict[str, float] = {}
        self.elapsed: dict[str, float] = {}

    def bind_handlers(self) -> None:
        """Register handlers."""
        if not self.manager_exists:
            return
        self.register_handler("tick", self.handle_tick)

    def add_event(self, event_name: str, time: float) -> None:
        """Add an event that tick should remap to every <time> seconds."""
        ##        if self.has_handler(event_name):
        ##            raise ValueError(
        ##                f'Remapping "{event_name}" events would cause exponential growth',
        ##            )
        self.times[event_name] = time
        self.elapsed[event_name] = time

    def remove_event(self, event_name: str) -> None:
        """Remove an event that is being raised."""
        if event_name not in self.times:
            return
        del self.times[event_name]
        del self.elapsed[event_name]

    async def handle_tick(
        self,
        tick_event: Event[sprite.TickEventData],
    ) -> None:
        """Handle tick events and raise new events if the time is right."""
        call: deque[tuple[str, int]] = deque()
        for event, time in self.times.items():
            passed = self.elapsed[event] + tick_event.data.time_passed
            if passed >= time:
                count, passed = divmod(passed, time)
                call.append((event, int(count)))
            self.elapsed[event] = passed
        if not call or self.manager is None:
            return
        async with trio.open_nursery() as nursery:
            while call:
                event, count = call.pop()
                for _ in range(count):
                    nursery.start_soon(
                        self.manager.raise_event,
                        Event(event, (("beyond", self.elapsed[event]),)),
                    )


class FPSDisplay(sprite.Sprite):
    """FPS display."""

    __slots__ = ("font",)

    def __init__(self) -> None:
        """Initialize FPS display."""
        super().__init__("fps")

        self.register_handler("tick", self.handle_tick)
        self.font = pygame.font.Font(FONT_FILENAME, FONT_SIZE)
        self.location = (SCREEN_SIZE.x - 40, 30)
        self.image = self.font.render("0", True, Color(0, 0, 0))

    async def handle_tick(self, event: Event[sprite.TickEventData]) -> None:
        """Tick event handler."""
        fps = str(int(event.data.fps))
        self.image = self.font.render(fps, True, Color(0, 0, 0))


class Grid(CSPSudoku, ComponentManager):
    """Sudoku grid Component Manager."""

    __slots__ = (
        "current_solve_gen",
        "numbers",
        "outline_color",
        "outline_size",
    )

    def __init__(self) -> None:
        """Initialize Grid."""
        CSPSudoku.__init__(self)
        ComponentManager.__init__(self, "grid")

        self.current_solve_gen: (
            Generator[tuple[int, int], None, None] | None
        ) = None
        self.outline_color = Color(255, 0, 0)
        self.outline_size = 2

        image = sprite.ImageComponent()
        self.add_component(image)

        base = Surface((TILE_SIZE, TILE_SIZE))
        base.fill(Color(255, 165, 0))

        self.numbers = {}
        font = pygame.font.Font(FONT_FILENAME, FONT_SIZE)
        for num in range(10):
            surf = base.copy()
            if num != 0:
                text = font.render(f"{num}", True, Color(0, 0, 0))
                ##                text = crop.crop_color(text, Color(0, 255, 0))
                tw, th = text.get_size()
                x, y = (TILE_SIZE - tw) / 2, (TILE_SIZE - th) / 2
                surf.blit(text, (x, y))
            self.numbers[num] = surf

        self.add_component(Timer())

        self.add_tiles()

    def add_tiles(self) -> None:
        """Add tiles."""
        start_x = 150
        start_y = 50
        size = round(TILE_SIZE + TILE_SEP)
        for y in range(self.dims):
            for x in range(self.dims):
                pos = grid_to_flat(x, y, self.dims)
                tile = Tile(pos)
                tile.location = Vector2(start_x + size * x, start_y + size * y)
                self.add_component(tile)

    def bind_handlers(self) -> None:
        """Register handlers."""
        if not self.manager_exists:
            return
        self.register_handlers(
            {
                "next_step": self.next_step,
                "init": self.handle_init,
                "solve": self.trigger_solve,
                "solve_step": self.on_step,
                "text_input": self.text_input,
            },
        )

    async def handle_init(self, event: Event[Any]) -> None:
        """Add all sprites to manager."""
        for idx in range(len(self)):
            tile = self.get_component(f"tile_{idx}")
            assert tile is not None, f"tile_{idx} should exist"
            tile.value = self.grid[idx]
            assert self.manager is not None, "should be bound"
            assert isinstance(self.manager, GroupAddComponentManager)
            self.manager.group_add(tile)

    def set_grid(self, values: list[int]) -> None:
        """Set grid."""
        for idx, value in enumerate(values):
            self.grid[idx] = value

    async def trigger_solve(self, event: Event[None]) -> None:
        """Trigger solving."""
        self.current_solve_gen = self.solve_gen()
        timer = self.get_component("timer")
        assert isinstance(timer, Timer)
        timer.add_event("next_step", 0.4)

    async def on_step(self, event: Event[tuple[int, int]]) -> None:
        """Update grid."""
        index, value = event.data
        self.grid[index] = value

    async def next_step(self, event: Event[str]) -> None:
        """Perform next step of solving."""
        if self.current_solve_gen is None or self.manager is None:
            return
        try:
            index, value = next(self.current_solve_gen)
        except StopIteration:
            timer = self.get_component("timer")
            assert isinstance(timer, Timer)
            timer.remove_event(
                "next_step",
            )
            ##            await self.raise_event(Event("solve_step", position=None, value=0))
            return
        await self.raise_event(
            Event(
                "solve_step",
                (index, value),
            ),
        )

    async def text_input(self, event: Event[dict[str, str]]) -> None:
        """Raise text_input_tile event."""
        await self.raise_event(
            Event("text_input_tile", {"name": event.data["name"]}),
        )


class Tile(sprite.Sprite):
    """Tile sprite."""

    __slots__ = ("_value", "index")

    def __init__(self, index: int) -> None:
        """Initialize tile."""
        super().__init__(f"tile_{index}")

        self.index = index
        self._value = 0
        ##        self.outline = False
        self.image = Surface((0, 0))

        self.add_components(
            (
                sprite.ImageComponent(),
                sprite.DragClickEventComponent(),
            ),
        )

    @property
    def image_component(self) -> sprite.ImageComponent:
        """Image component."""
        image = self.get_component("image")
        assert isinstance(image, sprite.ImageComponent)
        return image

    def bind_handlers(self) -> None:
        """Register handlers."""
        if not self.manager_exists:
            return
        self.register_handlers(
            {
                "solve_step": self.step,
                "click": self.handle_click,
                "text_input_tile": self.check_selected,
            },
        )
        assert isinstance(self.manager, Grid)
        self.image_component.add_images(
            self.manager.numbers,  # type: ignore[arg-type]
        )

    @property
    def value(self) -> int:
        """Value of this tile."""
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        """Set tile value."""
        self._value = value
        assert self.manager is not None, "Should be bound"
        self.image_component.set_image(value)
        self.visible = True
        self.update_location_on_resize = True

    async def step(self, event: Event[tuple[int, int]]) -> None:
        """Handle solve step event."""
        assert self.manager is not None
        index, value = event.data

        outline = self.image_component.get_component("outline")
        assert isinstance(outline, sprite.OutlineComponent)

        if index != self.index:
            outline.set_color(None)
            return

        self.value = value
        assert isinstance(self.manager, Grid)
        outline.set_color(self.manager.outline_color)

    async def handle_click(self, event: Event[dict[str, int]]) -> None:
        """Handle click events."""
        if event.data["button"] == 1:
            print(f"{self.name} clicked")
            assert self.manager is not None
            await self.manager.raise_event(
                Event("text_input", {"name": self.name}),
            )

    async def check_selected(self, event: Event[dict[str, str]]) -> None:
        """Check if should be selected or not."""
        assert self.manager is not None

        outline = self.image_component.get_component("outline")
        assert isinstance(outline, sprite.OutlineComponent)

        if event.data["name"] != self.name:
            outline.set_color(None)
        elif event.data["name"] == self.name:
            assert isinstance(self.manager, Grid)
            outline.set_color(self.manager.outline_color)


class Button(sprite.Sprite):
    """Button sprite."""

    __slots__ = ()

    def __init__(self, name: str) -> None:
        """Initialize Button."""
        super().__init__(name)

        self.add_component(sprite.DragClickEventComponent())


class HaltState(AsyncState["SudokuClient"]):
    """Halt state to set state to None so running becomes False."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize Halt State."""
        super().__init__("Halt")

    async def check_conditions(self) -> None:
        """Set active state to None."""
        assert self.machine is not None
        await self.machine.set_state(None)


class InitializeState(AsyncState["SudokuClient"]):
    """Initialize Checkers."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize the Initialize State."""
        super().__init__("initialize")

    async def check_conditions(self) -> str:
        """Go to title."""
        return "play"


class GroupAddComponentManager(ComponentManager):
    """Component manager with `group_add` method."""

    __slots__ = ("group_add",)

    def __init__(
        self,
        name: object,
        group_add: Callable[[sprite.Sprite], None],
        own_name: object | None = None,
    ) -> None:
        """Initialize group add component."""
        super().__init__(name, own_name)

        self.group_add = group_add


class GameState(AsyncState["SudokuClient"]):
    """Checkers Game Asynchronous State base class."""

    __slots__ = ("id", "manager")

    def __init__(self, name: str) -> None:
        """Initialize Game State."""
        super().__init__(name)

        self.id: int = 0
        self.manager = GroupAddComponentManager(
            self.name,
            partial(self.group_add, add_component=False),
        )

    def add_actions(self) -> None:
        """Add internal component manager to state machine's component manager."""
        assert self.machine is not None
        self.machine.manager.add_component(self.manager)

    def group_add(
        self,
        new_sprite: sprite.Sprite,
        add_component: bool = True,
    ) -> None:
        """Add new sprite to state machine's group."""
        assert self.machine is not None
        group = self.machine.get_group(self.id)
        assert group is not None, "Expected group from new group id"
        try:
            group.add(new_sprite)
        except AttributeError as exc:
            exc.add_note(f"{new_sprite = }")
            raise
        if add_component:
            self.manager.add_component(new_sprite)

    async def exit_actions(self) -> None:
        """Remove group and unbind all components."""
        assert self.machine is not None
        self.machine.remove_group(self.id)
        self.manager.unbind_components()
        self.id = 0

    def change_state(
        self,
        new_state: str | None,
    ) -> Callable[[Event[Any]], Awaitable[None]]:
        """Return an async function that will change state to `new_state`."""

        async def set_state(*args: object, **kwargs: object) -> None:
            # play_sound("button_click")
            await self.machine.set_state(new_state)

        return set_state


class TestState(GameState):
    """Test state."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize Test State."""
        super().__init__("test")

    async def entry_actions(self) -> None:
        """Add MrFloppy object and raise init event."""
        assert self.machine is not None
        self.id = self.machine.new_group("test")

        floppy = MrFloppy()
        self.group_add(floppy)

        await self.machine.raise_event(Event("init", None))


class PlayState(GameState):
    """Game Play State."""

    # __slots__ = ("exit_data",)

    def __init__(self) -> None:
        """Initialize Play State."""
        super().__init__("play")

        # (0: normal | 1: error) <error message> <? handled>
        self.exit_data: tuple[int, str, bool] | None = None

    async def entry_actions(self) -> None:
        """Add GameBoard and raise init event."""
        self.exit_data = None

        assert self.machine is not None
        if self.id == 0:
            self.id = self.machine.new_group("play")

        self.manager.add_component(Grid())

        await self.machine.raise_event(Event("init", None))


class SudokuClient(sprite.GroupProcessor):
    """Sudoku Client."""

    __slots__ = ("manager",)

    def __init__(self, manager: ExternalRaiseManager) -> None:
        """Initialize Checkers Client."""
        super().__init__()
        self.manager = manager

        self.add_states(
            (
                HaltState(),
                InitializeState(),
                ##                TitleState(),
                PlayState(),
            ),
        )

    async def raise_event(self, event: Event[Any]) -> None:
        """Raise component event in all groups."""
        await self.manager.raise_event(event)

    async def raise_event_internal(self, event: Event[Any]) -> None:
        """Raise component event in all groups."""
        await self.manager.raise_event_internal(event)


##async def async_run() -> None:
##    """Start program."""
##    global SCREEN_SIZE
##    # Set up the screen
##    screen = pygame.display.set_mode(tuple(SCREEN_SIZE), 0, vsync=VSYNC)
##    pygame.display.set_caption(f"{__title__} v{__version__}")
##    ##    pygame.display.set_icon(pygame.image.load('icon.png'))
##
##    client = Client()
##    group_id = client.new_group()
##    group = client.get_group(group_id)
##    group.add(FPSDisplay())
##    ##    group.add(MrFloppy())
##    group.add_component(Grid())
##    _ = 0
##    # fmt: off
##    ##    group.component("grid").set_grid([
##    ##        0,0,3, 8,0,0, 5,1,0,
##    ##        0,0,8, 7,0,0, 9,3,0,
##    ##        1,0,0, 3,0,5, 7,2,8,
##    ##        #------------------
##    ##        0,0,0, 2,0,0, 8,4,9,
##    ##        8,0,1, 9,0,6, 2,5,7,
##    ##        0,0,0, 5,0,0, 1,6,3,
##    ##        #------------------
##    ##        9,6,4, 1,2,7, 3,8,5,
##    ##        3,8,2, 6,5,9, 4,7,1,
##    ##        0,1,0, 4,0,0, 6,9,2,
##    ##    ])
##    ##    group.component("grid").set_grid([
##    ##        _,7,_,  5,3,_,  1,_,6,
##    ##        _,_,2,  _,_,_,  _,_,7,
##    ##        _,_,_,  _,8,_,  _,_,_,
##    ##        #---------------------
##    ##        _,5,_,  _,_,8,  _,_,_,
##    ##        _,_,4,  6,5,_,  _,3,_,
##    ##        _,_,_,  _,_,2,  6,_,_,
##    ##        #---------------------
##    ##        _,_,_,  _,_,6,  _,_,_,
##    ##        9,_,_,  _,_,_,  _,4,_,
##    ##        _,2,_,  1,7,_,  3,_,_
##    ##    ])
##    ##    group.component("grid").set_grid([
##    ##        _,_,_, _,_,_, _,_,2,
##    ##        _,_,_, _,9,5, 4,_,_,
##    ##        _,_,6, 8,_,_, _,_,_,
##    ##        #------------------
##    ##        _,8,_, _,2,_, _,_,1,
##    ##        _,_,_, _,_,9, 7,3,_,
##    ##        1,_,_, _,_,_, _,5,_,
##    ##        #------------------
##    ##        8,9,3, _,1,_, _,_,_,
##    ##        _,_,_, _,_,_, _,_,4,
##    ##        _,_,7, 6,_,_, 3,_,_,
##    ##    ])
##    ##    group.component("grid").set_grid([
##    ##        _,_,_,  _,_,_,  _,3,_,
##    ##        _,_,6,  _,3,5,  _,_,2,
##    ##        _,7,_,  _,9,2,  _,_,_,
##    ##        #---------------------
##    ##        1,3,_,  _,_,7,  5,_,9,
##    ##        6,_,_,  _,4,_,  _,_,7,
##    ##        9,_,7,  1,_,_,  _,4,6,
##    ##        #---------------------
##    ##        _,_,_,  2,7,_,  _,5,_,
##    ##        7,_,_,  9,6,_,  2,_,_,
##    ##        _,2,_,  _,_,_,  _,_,_
##    ##    ])
##    group.component("grid").set_grid([
##        _,_,_,  5,2,6,  _,1,_,
##        _,6,7,  9,_,_,  _,_,5,
##        _,_,8,  _,3,_,  _,_,_,
##        #---------------------
##        6,5,_,  _,_,_,  _,_,3,
##        7,_,3,  _,6,_,  9,_,2,
##        9,_,_,  _,_,_,  _,7,6,
##        #---------------------
##        _,_,_,  _,4,_,  7,_,1,
##        1,_,_,  _,_,9,  2,3,_,
##        _,2,_,  8,7,1,  _,_,_,
##    ])
##    # fmt: on
##
##    await group(Event("init"))
##    await group(Event("solve"))
##
##    screen.fill((255, 255, 255))
##    client.clear(screen, screen.copy().convert())
##    client.set_timing_threshold(1000 / FPS)
##
##    running = True
##
##    # Set up the FPS clock
##    ##    clock = pygame.time.Clock()
##    clock = Clock()
##
##    # While the game is active
##    while running:
##        # Event handler
##        async with trio.open_nursery() as event_nursery:
##            for event in pygame.event.get():
##                if event.type == QUIT:
##                    running = False
##                elif event.type == KEYUP and event.key == K_ESCAPE:
##                    pygame.event.post(pygame.event.Event(QUIT))
##                elif event.type == WINDOWRESIZED:
##                    SCREEN_SIZE = Vector2(event.x, event.y)
##                sprite_event = sprite.convert_pygame_event(event)
##                # print(sprite_event)
##                event_nursery.start_soon(
##                    group,
##                    sprite_event,
##                )
##            event_nursery.start_soon(clock.tick, FPS)
##
##        # Update the display
##        rects = client.draw(screen)
##        pygame.display.update(rects)
##
##        await group(
##            Event(
##                "tick",
##                sprite.TickEventData(
##                    time_passed=clock.get_time()
##                    / 1e9,  # nanoseconds -> seconds
##                    fps=clock.get_fps(),
##                ),
##            ),
##        )


async def async_run() -> None:
    """Handle main event loop."""
    # Set up globals
    global SCREEN_SIZE

    # Set up the screen
    screen = pygame.display.set_mode(SCREEN_SIZE, 0, vsync=VSYNC)
    pygame.display.set_caption(f"{__title__} v{__version__}")
    pygame.key.set_repeat(1000, 30)
    screen.fill((0xFF, 0xFF, 0xFF))

    async with trio.open_nursery() as main_nursery:
        event_manager = ExternalRaiseManager(
            "checkers",
            main_nursery,  # "client"
        )
        client = SudokuClient(event_manager)

        ##        background = pygame.image.load(
        ##            DATA_FOLDER / "background.png",
        ##        ).convert()
        ##        client.clear(screen, background)
        client.clear(screen, screen.copy().convert())
        client.set_timing_threshold(1000 / 80)

        ##        await client.set_state("initialize")
        await client.set_state("play")

        _ = 0
        # fmt: off
        event_manager.get_component("play").get_component("grid").set_grid(
            [
                _,_,_,  5,2,6,  _,1,_,
                _,6,7,  9,_,_,  _,_,5,
                _,_,8,  _,3,_,  _,_,_,
                #---------------------
                6,5,_,  _,_,_,  _,_,3,
                7,_,3,  _,6,_,  9,_,2,
                9,_,_,  _,_,_,  _,7,6,
                #---------------------
                _,_,_,  _,4,_,  7,_,1,
                1,_,_,  _,_,9,  2,3,_,
                _,2,_,  8,7,1,  _,_,_,
            ],
        )
        # fmt: on
        await event_manager.raise_event(Event("solve", None))

        # clock = pygame.time.Clock()
        clock = Clock()

        resized_window = False
        while client.running:
            async with trio.open_nursery() as event_nursery:
                for event in pygame.event.get():
                    if event.type == QUIT:
                        await client.set_state("Halt")
                    elif event.type == KEYUP and event.key == K_ESCAPE:
                        pygame.event.post(pygame.event.Event(QUIT))
                    elif event.type == WINDOWRESIZED:
                        SCREEN_SIZE = Vector2(int(event.x), int(event.y))
                        resized_window = True
                    sprite_event = sprite.convert_pygame_event(event)
                    # print(sprite_event)
                    event_nursery.start_soon(
                        event_manager.raise_event,
                        sprite_event,
                    )
                event_nursery.start_soon(client.think)
                event_nursery.start_soon(clock.tick, FPS)

            await client.raise_event(
                Event(
                    "tick",
                    sprite.TickEventData(
                        time_passed=clock.get_time()
                        / 1e9,  # nanoseconds -> seconds
                        fps=clock.get_fps(),
                    ),
                ),
            )

            rects: list[Rect | FRect]
            if resized_window:
                resized_window = False
                screen.fill((0xFF, 0xFF, 0xFF))
                rects = [Rect((0, 0), SCREEN_SIZE)]
                client.repaint_rect(rects[0])
                rects.extend(client.draw(screen))
            else:
                rects = client.draw(screen)
            pygame.display.update(rects)
    client.clear_groups()


def cli_run() -> None:
    """Start asynchronous run."""
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")

    # If we're not imported as a module, run.
    # Make sure the game will display correctly on high DPI monitors on Windows.

    if IS_WINDOWS:
        from ctypes import windll  # type: ignore

        with contextlib.suppress(AttributeError):
            windll.user32.SetProcessDPIAware()
        del windll

    try:
        pygame.init()
        trio.run(async_run)
    ##except ExceptionGroup as exc:
    ##    import traceback
    ##    traceback.print_exception(exc)
    finally:
        pygame.quit()


if __name__ == "__main__":
    cli_run()
