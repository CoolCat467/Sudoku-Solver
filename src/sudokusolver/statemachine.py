"""State Machine module."""

# Programmed by CoolCat467

from __future__ import annotations

# Copyright (C) 2020-2024  CoolCat467
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

__title__ = "State Machine"
__author__ = "CoolCat467"
__version__ = "0.1.10"
__license__ = "GNU General Public License Version 3"


from typing import TYPE_CHECKING, Generic, TypeVar
from weakref import ref

if TYPE_CHECKING:
    from collections.abc import Iterable

    from typing_extensions import Self
import trio

__all__ = ["AsyncState", "AsyncStateMachine", "State", "StateMachine"]


class BaseState:
    """Base class for states."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        """Initialize state with a name."""
        self.name = name

    def __repr__(self) -> str:
        """Return representation of self."""
        return f"{self.__class__.__name__}({self.name!r})"

    def add_actions(self) -> None:
        """Perform actions when this state added to a State Machine."""
        return


SyncMachine = TypeVar("SyncMachine", bound="StateMachine", covariant=True)


class State(BaseState, Generic[SyncMachine]):
    """Base class for synchronous states."""

    __slots__ = ("machine_ref",)

    def __init__(self, name: str) -> None:
        """Initialize state with a name."""
        super().__init__(name)
        self.machine_ref: ref[SyncMachine]

    @property
    def machine(self) -> SyncMachine:
        """Get machine from internal weak reference."""
        if not hasattr(self, "machine_ref"):
            raise RuntimeError("State has no statemachine bound")
        machine = self.machine_ref()
        if machine is None:
            raise RuntimeError("State has no statemachine bound")
        return machine

    def entry_actions(self) -> None:
        """Perform entry actions for this State."""
        return

    def do_actions(self) -> None:
        """Perform actions for this State."""
        return

    def check_conditions(self) -> str | None:
        """Check state and return new state name or stay in current."""
        return None

    def exit_actions(self) -> None:
        """Perform exit actions for this State."""
        return


AsyncMachine = TypeVar(
    "AsyncMachine",
    bound="AsyncStateMachine",
    covariant=True,
)


class AsyncState(BaseState, Generic[AsyncMachine]):
    """Base class for asynchronous states."""

    __slots__ = ("machine_ref",)

    def __init__(self, name: str) -> None:
        """Initialize state with a name."""
        super().__init__(name)
        self.machine_ref: ref[AsyncMachine]

    @property
    def machine(self) -> AsyncMachine:
        """Get machine from internal weak reference."""
        if not hasattr(self, "machine_ref"):
            raise RuntimeError("State has no statemachine bound")
        machine = self.machine_ref()
        if machine is None:
            raise RuntimeError("State has no statemachine bound")
        return machine

    async def entry_actions(self) -> None:
        """Perform entry actions for this State."""
        await trio.lowlevel.checkpoint()

    async def do_actions(self) -> None:
        """Perform actions for this State."""
        await trio.lowlevel.checkpoint()

    async def check_conditions(self) -> str | None:
        """Check state and return new state name or stay in current."""
        await trio.lowlevel.checkpoint()
        return None

    async def exit_actions(self) -> None:
        """Perform exit actions for this State."""
        await trio.lowlevel.checkpoint()


class BaseStateMachine:
    """State Machine base class."""

    __slots__ = ("__weakref__", "active_state", "states")

    def __repr__(self) -> str:
        """Return <{class-name} {self.states}>."""
        text = f"<{self.__class__.__name__}"
        if hasattr(self, "states"):  # pragma: nocover
            text += f" {self.states}"
        return f"{text}>"

    @property
    def running(self) -> bool:
        """Boolean of if state machine is running."""
        try:
            return self.active_state is not None  # type: ignore[attr-defined]
        except AttributeError:
            return False


class StateMachine(BaseStateMachine):
    """Synchronous State Machine base class."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize synchronous state machine."""
        self.states: dict[str, State[Self]] = {}  # Stores the states
        self.active_state: State[Self] | None = (
            None  # The currently active state
        )

    def add_state(self, state: State[Self]) -> None:
        """Add a State instance to the internal dictionary."""
        if not isinstance(state, State):
            raise TypeError(
                f'"{type(state).__name__}" is not an instance of State!',
            )
        state.machine_ref = ref(self)
        self.states[state.name] = state
        state.add_actions()

    def add_states(self, states: Iterable[State[Self]]) -> None:
        """Add multiple State instances to internal dictionary."""
        for state in states:
            self.add_state(state)

    def remove_state(self, state_name: str) -> None:
        """Remove state with given name from internal dictionary."""
        if state_name not in self.states:
            raise ValueError(f"{state_name} is not a registered State.")
        if (
            self.active_state is not None
            and self.active_state.name == state_name
        ):
            self.active_state.exit_actions()
            self.active_state = None
        del self.states[state_name]

    def set_state(self, new_state_name: str | None) -> None:
        """Change states and perform any exit / entry actions."""
        if new_state_name not in self.states and new_state_name is not None:
            raise KeyError(
                f'"{new_state_name}" not found in internal states dictionary!',
            )

        if self.active_state is not None:
            self.active_state.exit_actions()

        if new_state_name is None:
            self.active_state = None
        else:
            self.active_state = self.states[new_state_name]
            self.active_state.entry_actions()

    def think(self) -> None:
        """Perform actions check conditions and potentially change states."""
        # Only continue if there is an active state
        if self.active_state is None:
            return
        # Perform the actions of the active state
        self.active_state.do_actions()
        # Check conditions and potentially change states.
        new_state_name = self.active_state.check_conditions()
        if new_state_name is not None:
            self.set_state(new_state_name)


class AsyncStateMachine(BaseStateMachine):
    """Asynchronous State Machine base class."""

    __slots__ = ()

    def __init__(self) -> None:
        """Initialize async state machine."""
        self.states: dict[str, AsyncState[Self]] = {}  # Stores the states
        self.active_state: AsyncState[Self] | None = None  # active state

    def add_state(self, state: AsyncState[Self]) -> None:
        """Add an AsyncState instance to the internal dictionary."""
        if not isinstance(state, AsyncState):
            raise TypeError(
                f'"{type(state).__name__}" is not an instance of AsyncState!',
            )
        state.machine_ref = ref(self)
        self.states[state.name] = state
        state.add_actions()

    def add_states(self, states: Iterable[AsyncState[Self]]) -> None:
        """Add multiple State instances to internal dictionary."""
        for state in states:
            self.add_state(state)

    def remove_state(self, state_name: str) -> None:
        """Remove state with given name from internal dictionary."""
        if state_name not in self.states:
            raise ValueError(f"{state_name} is not a registered AsyncState.")
        if (
            self.active_state is not None
            and self.active_state.name == state_name
        ):
            # await self.active_state.exit_actions()
            self.active_state = None
        del self.states[state_name]

    async def set_state(self, new_state_name: str | None) -> None:
        """Change states and perform any exit / entry actions."""
        if new_state_name not in self.states and new_state_name is not None:
            raise KeyError(
                f'"{new_state_name}" not found in internal states dictionary!',
            )

        if self.active_state is not None:
            await self.active_state.exit_actions()

        if new_state_name is None:
            self.active_state = None
        else:
            self.active_state = self.states[new_state_name]
            await self.active_state.entry_actions()

    async def think(self) -> None:
        """Perform actions check conditions and potentially change states."""
        # Only continue if there is an active state
        if self.active_state is None:
            return
        # Perform the actions of the active state
        await self.active_state.do_actions()
        # Check conditions and potentially change states.
        new_state_name = await self.active_state.check_conditions()
        if new_state_name is not None:
            await self.set_state(new_state_name)


if __name__ == "__main__":  # pragma: nocover
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.")
