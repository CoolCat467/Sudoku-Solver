"""Sudoku-GUI - Graphical User Interface for Sudoku Solver."""

from __future__ import annotations

# Programmed by CoolCat467
import contextlib
import platform
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

import pygame
import trio
from libcomponent.component import Component, ComponentManager, Event
from pygame.color import Color
from pygame.locals import K_ESCAPE, KEYUP, QUIT, WINDOWRESIZED
from pygame.surface import Surface

from sudokusolver import sprite
from sudokusolver.async_clock import Clock
from sudokusolver.sudoku import Sudoku, grid_to_flat
from sudokusolver.vector import Vector2

if TYPE_CHECKING:
    from collections.abc import Generator

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

        self.add_component(sprite.Click())
        self.add_component(sprite.Draggable())
        self.add_component(sprite.PressHoldDrag())
        self.add_component(sprite.Outline())
        self.add_component(sprite.DragOutline())


class Timer(Component):
    """Re-raise tick events but renamed to <name> every x seconds."""

    __slots__ = ("elapsed", "times")

    def __init__(self) -> None:
        """Initialize Timer."""
        super().__init__("timer")

        self.times: dict[str, float] = {}
        self.elapsed: dict[str, float] = {}

        self.add_handler("tick", self.handle_tick)

    def add_event(self, event_name: str, time: float) -> None:
        """Add an event that tick should remap to every <time> seconds."""
        if event_name in self.get_handled():
            raise ValueError(
                f'Remapping "{event_name}" events would cause exponential growth',
            )
        self.times[event_name] = time
        self.elapsed[event_name] = time

    def remove_event(self, event_name: str) -> None:
        """Remove an event that is being raised."""
        if event_name not in self.times:
            return
        del self.times[event_name]
        del self.elapsed[event_name]

    async def handle_tick(self, tick_event: Event[float]) -> None:
        """Handle tick events and raise new events if the time is right."""
        call: deque[tuple[str, int]] = deque()
        for event, time in self.times.items():
            passed = self.elapsed[event] + tick_event["time_passed"]
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
                        self.manager,
                        Event(event, (("beyond", self.elapsed[event]),)),
                    )


class FPSDisplay(sprite.Sprite):
    """FPS display."""

    __slots__ = ("font",)

    def __init__(self) -> None:
        """Initialize FPS display."""
        super().__init__("fps")

        self.add_handler("tick", self.handle_tick)
        self.font = pygame.font.Font(FONT_FILENAME, FONT_SIZE)
        self.location = (SCREEN_SIZE.x - 40, 30)
        self.image = self.font.render("0", True, Color(0, 0, 0))

    async def handle_tick(self, event: Event[float]) -> None:
        """Tick event handler."""
        fps = str(int(event["fps"]))
        self.image = self.font.render(fps, True, Color(0, 0, 0))


class Grid(Sudoku, ComponentManager):
    """Sudoku grid Component Manager."""

    ##    __slots__ = ("solve_gen", "outline_color", "outline_size", "numbers")

    def __init__(self) -> None:
        """Initialize Grid."""
        Sudoku.__init__(self, [0 for _ in range(81)], 9)
        ComponentManager.__init__(self, "grid")

        self.solve_gen: (
            Generator[tuple[tuple[int, int], int], None, None] | None
        ) = None
        self.outline_color = Color(255, 0, 0)
        self.outline_size = 2

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

        self.add_handler("next_step", self.next_step)
        self.add_handler("__init__", self.handle_init)
        self.add_handler("solve", self.trigger_solve)
        self.add_handler("solve_step", self.on_step)
        self.add_handler("text_input", self.text_input)

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

    async def handle_init(self, event: Event[Any]) -> None:
        """Add all sprites to manager."""
        for idx in range(81):
            tile = self.component(f"tile_{idx}")
            assert tile is not None, f"tile_{idx} should exist"
            tile.value = self.grid.flat[idx]  # type: ignore[attr-defined]
            assert self.manager is not None, "should be bound"
            self.manager.group_add(tile)

    def set_grid(self, values: list[int]) -> None:
        """Set grid."""
        for idx, value in enumerate(values):
            self.grid.flat[idx] = value

    async def trigger_solve(self, event: Event[Any]) -> None:
        """Trigger solving."""
        missing = self.get_missing()
        self.solve_gen = self.solve_positions(missing)
        self.component("timer").add_event("next_step", 0.4)  # type: ignore[attr-defined]

    async def on_step(self, event: Event[int]) -> None:
        """Update grid."""
        if event["position"] is not None:
            self.grid.flat[event["position"]] = event["value"]

    async def next_step(self, event: Event[str]) -> None:
        """Perform next step of solving."""
        if self.solve_gen is None or self.manager is None:
            return
        try:
            location, value = next(self.solve_gen)
            row, col = location
        except StopIteration:
            cast(Timer, self.component("timer")).remove_event("next_step")
            await self(Event("solve_step", position=None, value=0))
            return
        await self(
            Event(
                "solve_step",
                position=grid_to_flat(row, col, self.dims),
                value=value,
            ),
        )

    async def text_input(self, event: Event[str]) -> None:
        """Raise text_input_tile event."""
        await self(Event("text_input_tile", name=event["name"]))


class Tile(sprite.Sprite):
    """Tile sprite."""

    __slots__ = ("_value", "outline", "position")

    def __init__(self, position: int) -> None:
        """Initialize tile."""
        super().__init__(f"tile_{position}")

        self.position = position
        self._value = 0
        self.outline = False
        self.image = Surface((0, 0))

        self.add_handler("solve_step", self.step)
        self.add_handler("click", self.handle_click)
        self.add_handler("text_input_tile", self.check_selected)

        self.add_component(sprite.Click())
        self.add_component(sprite.Outline())

    @property
    def value(self) -> int:
        """Value of this tile."""
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        """Set tile value."""
        self._value = value
        assert self.manager is not None, "Should be bound"
        self.image = self.manager.numbers[value]

    async def step(self, event: Event[int]) -> None:
        """Handle solve step event."""
        assert self.manager is not None
        if event["position"] != self.position:
            if self.outline:
                self.outline = False
                await self(
                    Event(
                        "outline",
                        {
                            "enable": False,
                            "color": self.manager.outline_color,
                            "size": self.manager.outline_size,
                        },
                    ),
                )
            return

        self.value = event["value"]
        self.outline = True
        await self(
            Event(
                "outline",
                {
                    "enable": True,
                    "color": self.manager.outline_color,
                    "size": self.manager.outline_size,
                },
            ),
        )

    async def handle_click(self, event: Event[int]) -> None:
        """Handle click events."""
        if event["button"] == 1:
            print(f"{self.name} clicked")
            assert self.manager is not None
            await self.manager(Event("text_input", name=self.name))

    async def check_selected(self, event: Event[str]) -> None:
        """Check if should be selected or not."""
        assert self.manager is not None
        if self.outline and event["name"] != self.name:
            self.outline = False
            await self(
                Event(
                    "outline",
                    {
                        "enable": False,
                        "color": self.manager.outline_color,
                        "size": self.manager.outline_size,
                    },
                ),
            )
        elif event["name"] == self.name:
            self.outline = True
            await self(
                Event(
                    "outline",
                    {
                        "enable": True,
                        "color": self.manager.outline_color,
                        "size": self.manager.outline_size,
                    },
                ),
            )


class Button(sprite.Sprite):
    """Button sprite."""

    __slots__ = ()

    def __init__(self, name: str) -> None:
        """Initialize Button."""
        super().__init__(name)

        self.add_component(sprite.Click())


class Client(sprite.GroupProcessor):
    """Main Client."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize Client."""
        super().__init__()


##        self.add_handler("KeyUp", self.handle_keyup)

##    async def handle_keyup(self, event: Event[int]) -> str | None:
##        """Post quit event when escape key stops being pressed."""
##        if event["key"] == K_ESCAPE:
##            pygame.event.post(pygame.event.Event(pygame.QUIT))
##            return "break"
##        return None
##
##    async def __call__(self, event: Event[Any]) -> None:
##        """Raise event."""
##        ##        if event.name not in self.get_handled() and event.name not in {"tick"}:
##        ##            print(event)
##        await super().raise_event(event)


def convert_pygame_event(event: pygame.event.Event) -> Event[str]:
    """Convert pygame event to component event."""
    return Event(pygame.event.event_name(event.type), event.dict)


async def async_run() -> None:
    """Start program."""
    global SCREEN_SIZE
    # Set up the screen
    screen = pygame.display.set_mode(tuple(SCREEN_SIZE), 0, 16, vsync=VSYNC)
    pygame.display.set_caption(f"{__title__} v{__version__}")
    ##    pygame.display.set_icon(pygame.image.load('icon.png'))

    group = Client()
    group.add(FPSDisplay())
    ##    group.add(MrFloppy())
    group.add_component(Grid())
    _ = 0
    # fmt: off
##    group.component("grid").set_grid([  # type: ignore[attr-defined]
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
##        0,1,0, 4,0,0, 6,9,2,
##    ])
##    group.component("grid").set_grid([  # type: ignore[attr-defined]
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
##    group.component("grid").set_grid([  # type: ignore[attr-defined]
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
##    group.component("grid").set_grid([  # type: ignore[attr-defined]
##        _,_,_,  _,_,_,  _,3,_,
##        _,_,6,  _,3,5,  _,_,2,
##        _,7,_,  _,9,2,  _,_,_,
##        #---------------------
##        1,3,_,  _,_,7,  5,_,9,
##        6,_,_,  _,4,_,  _,_,7,
##        9,_,7,  1,_,_,  _,4,6,
##        #---------------------
##        _,_,_,  2,7,_,  _,5,_,
##        7,_,_,  9,6,_,  2,_,_,
##        _,2,_,  _,_,_,  _,_,_
##    ])
    group.component("grid").set_grid([  # type: ignore[attr-defined]
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
    ])
    # fmt: on

    await group(Event("__init__"))
    await group(Event("solve"))

    screen.fill((255, 255, 255))
    group.clear(screen, screen.copy().convert())
    group.set_timing_treshold(1000 / FPS)

    running = True

    # Set up the FPS clock
    ##    clock = pygame.time.Clock()
    clock = Clock()

    # While the game is active
    while running:
        # Event handler
        async with trio.open_nursery() as event_nursery:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == KEYUP and event.key == K_ESCAPE:
                    pygame.event.post(pygame.event.Event(QUIT))
                elif event.type == WINDOWRESIZED:
                    SCREEN_SIZE = Vector2(event.x, event.y)
                sprite_event = convert_pygame_event(event)
                # print(sprite_event)
                event_nursery.start_soon(
                    group,
                    sprite_event,
                )
            event_nursery.start_soon(clock.tick, FPS)

        # Update the display
        rects = group.draw(screen)
        pygame.display.update(rects)

        await group(
            Event(
                "tick",
                time_passed=clock.get_time() / 1e9,  # nanoseconds -> seconds
                fps=clock.get_fps(),
            ),
        )


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
    finally:
        pygame.quit()


if __name__ == "__main__":
    cli_run()
