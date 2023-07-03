#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Component - Component System

"Component System - Original Version"

# Programmed by CoolCat467

__title__ = "Component"
__author__ = "CoolCat467"
__version__ = "0.0.0"

import weakref
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Optional, TypeVar, overload

import trio

T = TypeVar("T")


class Event(dict[str, T]):
    "Event Class"
    __slots__ = ("name",)

    @overload
    def __init__(
        self, name: str, data: dict[str, T] | None = None, /, **kwargs: None
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        name: str,
        data: Iterable[tuple[str, T]] | None = None,
        /,
        **kwargs: None,
    ) -> None:
        ...

    @overload
    def __init__(self, name: str, data: None = None, /, **kwargs: T) -> None:
        ...

    def __init__(
        self,
        name: str,
        data: dict[str, T] | Iterable[tuple[str, T]] | None = None,
        /,
        **kwargs: T | None,
    ) -> None:
        self.name: str = name
        if data is None:
            if kwargs:
                super().__init__(**kwargs)
            else:
                super().__init__()
        else:
            super().__init__(data)

    def __repr__(self) -> str:
        return f"Event({self.name!r}, {super().__repr__()})"


Handler = Callable[[Event], Awaitable[Any | None]]


class Component:
    "Base Component"
    __slots__ = ("__name", "__manager", "__handlers")

    def __init__(self, name: str) -> None:
        self.__name = name
        # weakref.CallableProxyType does not support class getitem
        self.__manager: Optional[
            "weakref.CallableProxyType[ComponentManager]"
        ] = None
        self.__handlers: dict[str, Handler] = {}

    def __repr__(self) -> str:
        "Get representation"
        return f'<"{self.name}" Component handling {self.get_handled()}>'

    def unbind(self) -> None:
        "Unbind from manager"
        self.__manager = None

    def __manager_ref_dead(self, dead_ref: "ComponentManager") -> None:
        "Called when manager reference is dead"
        # Make sure to eliminate the reference now,
        # unbind sub-classes could potentially forget to call super()
        self.__manager = None
        self.unbind()

    def bind(self, manager: "ComponentManager") -> None:
        "Bind this component to a component manager"
        if self.__manager is not None:
            raise RuntimeError(
                "Cannot bind to manager if already bound! Unbind first!"
            )
        self.__manager = weakref.proxy(manager, self.__manager_ref_dead)

    @property
    def manager(
        self,
    ) -> Optional["weakref.CallableProxyType[ComponentManager]"]:
        "Manager if bound of this Component or None if not"
        return self.__manager

    @property
    def name(self) -> str:
        "Name of this Component"
        return self.__name

    def get_handled(self) -> set[str]:
        "Return set of event names handled"
        return set(self.__handlers)

    def add_handler(self, event_name: str, handler: Handler) -> None:
        "Register event handler"
        if event_name in self.__handlers:
            raise RuntimeError(f'"{event_name}" is already being handled!')
        self.__handlers[event_name] = handler

    def remove_handler(self, event_name: str) -> Handler | None:
        "Un-register an event handler and return it if it exists, else None"
        if event_name in self.__handlers:
            old = self.__handlers[event_name]
            del self.__handlers[event_name]
            return old
        return None

    async def __call__(self, event: Event[Any]) -> Any | None:
        "Handle event if registered"
        if event.name in self.__handlers:
            return await self.__handlers[event.name](event)
        return None

    def __del__(self) -> None:
        "Free resources"
        self.__handlers.clear()


class ComponentManager(Component):
    "Group of Components"
    __slots__ = ("__weakref__", "__components", "handled_events")

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self.__components: dict[str, Component] = {}
        self.handled_events: dict[str, set[str]] = {}

    def __repr__(self) -> str:
        held = tuple(self.__components.values())
        handles = tuple(self.handled_events)
        return f'<"{self.name}" ComponentManager holding {held} handles {handles}>'

    def _replaced_handler(
        self, old_handler: Handler, new_handler: Handler
    ) -> Handler:
        "Return replaced handler. Calls old handler first, and if not break calls new one"

        async def handle(event: Event[Any]) -> Any | None:
            "Handle old event handler, and if no return handle with new handler"
            value = await old_handler(event)
            if value is not None:
                return value
            return await new_handler(event)

        return handle

    def add_component(self, component: Component) -> None:
        "Add component to this manager"
        assert isinstance(
            component, Component
        ), f"{component} is not a Component instance! ({type(component) = })"
        if component.name in self.__components:
            raise NameError(
                f"Component named {component.name!r} already exists!"
            )
        self.__components[component.name] = component
        component.bind(self)
        for name in component.get_handled():
            if name not in self.handled_events:
                self.handled_events[name] = set()
                if name not in self.get_handled():
                    self.add_handler(name, self.master_handler)
                else:
                    current = self.remove_handler(name)
                    assert (
                        current is not None
                    ), f"Impossible state where registered handler {name!r} does not exist"
                    replace = self._replaced_handler(
                        current, self.master_handler
                    )
                    self.add_handler(name, replace)
            self.handled_events[name].add(component.name)

    def component(self, name: str) -> Component:
        "Get component named name"
        return self.__components[name]

    def get_components(self) -> set[str]:
        "Get all components"
        return set(self.__components)

    def remove_component(self, name: str) -> None:
        "Remove component if it exists."
        self.__components[name].unbind()

        del self.__components[name]

        # Remove component handlers
        for event_name in tuple(self.handled_events):
            if name in self.handled_events[event_name]:
                self.handled_events[event_name].remove(name)
                if not self.handled_events[event_name]:
                    del self.handled_events[event_name]

    async def master_handler(self, event: Event[str]) -> dict[str, Any] | None:
        "Call event bound component handlers"
        if event.name in self.handled_events:
            value: dict[str, Any] = {}

            async def call_handler(component_name: str) -> None:
                "Handle component calls"
                value[component_name] = await self.component(component_name)(
                    event
                )

            async with trio.open_nursery() as nursery:
                for component_name in iter(self.handled_events[event.name]):
                    nursery.start_soon(
                        call_handler,
                        component_name,
                        name=f"{event.name} handler from {component_name}",
                    )
            return value
        return None


def run() -> None:
    "Run test of module"


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    run()
