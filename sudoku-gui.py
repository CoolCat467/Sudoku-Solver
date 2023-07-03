#!/usr/bin/env python3
# Sudoku-GUI - Graphical User Interface for Sudoku Solver
# -*- coding: utf-8 -*-

"Graphical User Interface for Sudoku Solver"

# Programmed by CoolCat467

from collections import deque
from collections.abc import Generator
from typing import Any, cast

import pygame
import trio
from pygame.locals import K_ESCAPE, QUIT
from pygame.rect import Rect
from pygame.surface import Surface

import crop
import sprite
from async_clock import Clock
from component import Component, ComponentManager, Event

# types: attr-defined error: Module "sudoku" has no attribute "from_grid"
# types: note: Another file has errors: /home/samuel/Desktop/Python/Projects/Sudoku-Solver/sprite.py
# types: note: Another file has errors: /home/samuel/Desktop/Python/Projects/Sudoku-Solver/sudoku.py
# types: note: Another file has errors: /home/samuel/Desktop/Python/Projects/Sudoku-Solver/location.py
from sudoku import Sudoku, from_grid
from vector import Vector2

__title__ = "Sudoku-GUI"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__ver_major__ = 0
__ver_minor__ = 0
__ver_patch__ = 0

SCREENSIZE = Vector2(800, 600)
FPS = 30
VSYNC = True

TILE_SIZE = 50
TILE_SEP = 4
FONT_FILENAME = "BookmanOldStyle.ttf"
FONT_SIZE = 60


class MrFloppy(sprite.Sprite):
    "Test sprite"
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("mr floppy")
        self.image = pygame.image.load("mr_floppy.png")
        self.location = SCREENSIZE / 2

        self.add_component(sprite.Click())
        self.add_component(sprite.Draggable())
        self.add_component(sprite.PressHoldDrag())
        self.add_component(sprite.Outline())
        self.add_component(sprite.DragOutline())


class Timer(Component):
    "Re-raise tick events but renamed to <name> every x seconds"
    __slots__ = ("times", "elapsed")

    def __init__(self) -> None:
        super().__init__("timer")

        self.times: dict[str, float] = {}
        self.elapsed: dict[str, float] = {}

        self.add_handler("tick", self.handle_tick)

    def add_event(self, event_name: str, time: float) -> None:
        "Add an event that tick should remap to every <time> seconds"
        if event_name in self.get_handled():
            raise ValueError(
                f'Remapping "{event_name}" events would cause exponential growth'
            )
        self.times[event_name] = time
        self.elapsed[event_name] = time

    def remove_event(self, event_name: str) -> None:
        "Remove an event that is being raised"
        if event_name not in self.times:
            return
        del self.times[event_name]
        del self.elapsed[event_name]

    async def handle_tick(self, tick_event: Event[float]) -> None:
        "Handle tick events and raise new events if the time is right"
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
    "FPS display"
    __slots__ = ("font",)

    def __init__(self) -> None:
        super().__init__("fps")

        self.add_handler("tick", self.handle_tick)
        self.font = pygame.font.Font(FONT_FILENAME, FONT_SIZE)
        self.location = (SCREENSIZE.x - 40, 30)
        # types: name-defined error: Name "Color" is not defined
        self.image = self.font.render("0", True, Color(0, 0, 0))

    async def handle_tick(self, event: Event[float]) -> None:
        "Tick event handler"
        fps = str(int(event["fps"]))
        # types: name-defined error: Name "Color" is not defined
        self.image = self.font.render(fps, True, Color(0, 0, 0))


class Grid(Sudoku, ComponentManager):
    "Sudoku grid Component Manager"
    __slots__ = ("solve_gen", "outline_color", "outline_size", "numbers")

    def __init__(self) -> None:
        Sudoku.__init__(self, [0 for _ in range(81)], 9)
        ComponentManager.__init__(self, "grid")

        self.solve_gen: Generator[
            tuple[tuple[int, int], int], None, None
        ] | None = None
        # types: name-defined error: Name "Color" is not defined
        self.outline_color = Color(255, 0, 0)
        self.outline_size = 2

        base = Surface((TILE_SIZE, TILE_SIZE))
        # types: name-defined error: Name "Color" is not defined
        base.fill(Color(255, 165, 0))

        self.numbers = {}
        font = pygame.font.Font(FONT_FILENAME, FONT_SIZE)
        for num in range(10):
            surf = base.copy()
            if num != 0:
                # types: name-defined error: Name "Color" is not defined
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
        "Add tiles"
        start_x = 150
        start_y = 50
        size = TILE_SIZE + TILE_SEP
        location = Vector2(start_x, start_y)
        for y in range(self.dims):
            location.x = start_x
            for x in range(self.dims):
                pos = from_grid(x, y, self.dims)
                tile = Tile(pos)
                tile.location = location
                self.add_component(tile)
                location.x += size
            location.y += size

    async def handle_init(self, event: Event[Any]) -> None:
        "Add all sprites to manager"
        for idx in range(81):
            tile = self.component(f"tile_{idx}")
            assert tile is not None, f"tile_{idx} should exist"
            # types: error: "Component" has no attribute "value"
            # types: Another file has errors: /home/samuel/Desktop/Python/Projects/Sudoku-Solver/location.py
            # types: Another file has errors: /home/samuel/Desktop/Python/Projects/Sudoku-Solver/sprite.py
            # types: attr-defined error: "Component" has no attribute "value"
            tile.value = self.grid.flat[idx]
            assert self.manager is not None, "should be bound"
            self.manager.group_add(tile)

    def set_grid(self, values: list[int]) -> None:
        "Set grid"
        for idx, value in enumerate(values):
            self.grid.flat[idx] = value

    async def trigger_solve(self, event: Event[Any]) -> None:
        "Trigger solving"
        missing = self.get_missing()
        self.solve_gen = self.solve_positions(missing)
        # types: error: "Component" has no attribute "add_event"
        # types: attr-defined error: "Component" has no attribute "add_event"
        self.component("timer").add_event("next_step", 0.4)

    # types: ^^^^^^^^^^^^^^^

    async def on_step(self, event: Event[int]) -> None:
        if event["position"] is not None:
            self.grid.flat[event["position"]] = event["value"]

    async def next_step(self, event: Event[str]) -> None:
        "Preform next step of solving"
        if self.solve_gen is None or self.manager is None:
            return None
        try:
            location, value = next(self.solve_gen)
            row, col = location
        except StopIteration:
            cast(Timer, self.component("timer")).remove_event("next_step")
            await self(Event("solve_step", position=None, value=0))
            return None
        await self(
            Event(
                "solve_step",
                position=from_grid(row, col, self.dims),
                value=value,
            )
        )

    async def text_input(self, event: Event["str"]) -> None:
        await self(Event("text_input_tile", name=event["name"]))


class Tile(sprite.Sprite):
    "Tile sprite"
    __slots__ = ("position", "_value", "outline")

    def __init__(self, position: int) -> None:
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
        "Value of this tile"
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        self._value = value
        assert self.manager is not None, "Should be bound"
        self.image = self.manager.numbers[value]

    async def step(self, event: Event[int]) -> None:
        "Handle solve step event"
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
                    )
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
            )
        )

    async def handle_click(self, event: Event[int]) -> None:
        "Handle click events"
        if event["button"] == 1:
            print(f"{self.name} clicked")
            # types: error: "None" not callable
            # types: misc error: "None" not callable
            await self.manager(Event("text_input", name=self.name))

    # types: ^^^^^^^^^^^^^^^^^^^^^^^^^^^

    async def check_selected(self, event: Event[str]) -> None:
        "Check if should be selected or not"
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
                )
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
                )
            )


class Button(sprite.Sprite):
    "Button sprite"
    __slots__ = ()

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # types: error: Argument 1 to "add_component" of "ComponentManager" has incompatible type "Type[Click]"; expected "Component"
        # types: arg-type error: Argument 1 to "add_component" of "ComponentManager" has incompatible type "type[Click]"; expected "Component"
        self.add_component(sprite.Click)


# types:                   ^


class Client(sprite.Group):
    "Client"
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("Client")
        self.add_handler("KeyUp", self.handle_keyup)

    async def handle_keyup(self, event: Event[int]) -> str | None:
        "If escape key let go, post quit event"
        # types: name-defined error: Name "K_ESCAPE" is not defined
        if event["key"] == K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return "break"
        return None

    async def __call__(self, event: Event[str]) -> None:
        if event.name not in self.get_handled() and event.name not in {"tick"}:
            print(event)
        await super().__call__(event)


def as_component_event(event: pygame.event.Event) -> Event[str]:
    "Convert pygame event to component event"
    return Event(pygame.event.event_name(event.type), event.dict)


async def async_run() -> None:
    "Start program"
    # Set up the screen
    screen = pygame.display.set_mode(tuple(SCREENSIZE), 0, 16, vsync=VSYNC)
    pygame.display.set_caption(f"{__title__} v{__version__}")
    ##    pygame.display.set_icon(pygame.image.load('icon.png'))

    group = Client()
    group.add(FPSDisplay())
    ##    group.add(MrFloppy())
    group.add_component(Grid())
    _ = 0
    # types: error: "Component" has no attribute "set_grid"
    # types: attr-defined error: "Component" has no attribute "set_grid"
    group.component("grid").set_grid(
        # types: ^^^^^^^^^^^^^^^^^^
        [
            _,
            _,
            3,
            8,
            _,
            _,
            5,
            1,
            _,
            _,
            _,
            8,
            7,
            _,
            _,
            9,
            3,
            _,
            1,
            _,
            _,
            3,
            _,
            5,
            7,
            2,
            8,
            # ---------------------
            _,
            _,
            _,
            2,
            _,
            _,
            8,
            4,
            9,
            8,
            _,
            1,
            9,
            _,
            6,
            2,
            5,
            7,
            _,
            _,
            _,
            5,
            _,
            _,
            1,
            6,
            3,
            # ---------------------
            9,
            6,
            4,
            1,
            2,
            7,
            3,
            8,
            5,
            3,
            8,
            2,
            6,
            5,
            9,
            4,
            7,
            1,
            _,
            1,
            _,
            4,
            _,
            _,
            6,
            9,
            2,
        ]
    )

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
        async with trio.open_nursery() as nursery:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                nursery.start_soon(group, as_component_event(event))

        # Get the time passed from the FPS clock
        time_passed = await clock.tick(FPS)

        # Update the display
        rects = group.draw(screen)
        pygame.display.update(rects)

        await group(
            Event(
                "tick",
                # types: error: Argument "time_passed" to "Event" has incompatible type "float"; expected "str"
                # types: arg-type error: Argument "time_passed" to "Event" has incompatible type "float"; expected "str"
                time_passed=time_passed / 1000,
                # types:      ^
                # types: error: Argument "fps" to "Event" has incompatible type "float"; expected "str"
                # types: arg-type error: Argument "fps" to "Event" has incompatible type "float"; expected "str"
                fps=clock.get_fps(),
                # types:  ^
            )
        )


def run() -> None:
    "Synchronous entry point"
    trio.run(async_run)


if __name__ == "__main__":
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    try:
        pygame.init()
        run()
    finally:
        pygame.quit()
