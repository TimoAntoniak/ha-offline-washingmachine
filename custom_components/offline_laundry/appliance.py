"""State machine for a single offline laundry appliance."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, TypedDict

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DURATION,
    ATTR_FINISHES_AT,
    ATTR_LOAD,
    ATTR_REMAINING,
    DOMAIN,
    LaundryEvent,
    LaundryState,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1

type LaundryListener = Callable[[LaundryEvent], None]


class StoredCycle(TypedDict):
    """Persisted representation of a cycle."""

    state: str
    load: str | None
    duration: float | None
    finishes_at: str | None
    remaining: float | None


@dataclass(frozen=True, slots=True)
class Cycle:
    """Snapshot of the current cycle.

    ``finishes_at`` is only set while running, ``remaining`` only while paused,
    mirroring the built-in timer helper.
    """

    state: LaundryState = LaundryState.IDLE
    load: str | None = None
    duration: timedelta | None = None
    finishes_at: datetime | None = None
    remaining: timedelta | None = None

    def as_dict(self) -> StoredCycle:
        """Serialize for storage."""
        return {
            "state": self.state,
            "load": self.load,
            "duration": self.duration.total_seconds() if self.duration else None,
            "finishes_at": self.finishes_at.isoformat() if self.finishes_at else None,
            "remaining": self.remaining.total_seconds() if self.remaining else None,
        }

    @classmethod
    def from_dict(cls, data: StoredCycle) -> Cycle:
        """Deserialize from storage."""
        return cls(
            state=LaundryState(data["state"]),
            load=data["load"],
            duration=_seconds(data["duration"]),
            finishes_at=dt_util.parse_datetime(data["finishes_at"])
            if data["finishes_at"]
            else None,
            remaining=_seconds(data["remaining"]),
        )


def _seconds(value: float | None) -> timedelta | None:
    return timedelta(seconds=value) if value is not None else None


class LaundryAppliance:
    """Timer-like state machine with persistence across restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str) -> None:
        """Initialize the appliance."""
        self._hass = hass
        self._name = name
        self._store: Store[StoredCycle] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}"
        )
        self._cycle = Cycle()
        self._listeners: list[LaundryListener] = []
        self._unsub_finish: CALLBACK_TYPE | None = None

    @property
    def cycle(self) -> Cycle:
        """Return the current cycle."""
        return self._cycle

    @property
    def name(self) -> str:
        """Return the appliance name."""
        return self._name

    async def async_load(self) -> None:
        """Restore the last cycle; finish it if it ended while HA was down."""
        if (data := await self._store.async_load()) is None:
            return
        try:
            self._cycle = Cycle.from_dict(data)
        except KeyError, ValueError, TypeError:
            _LOGGER.warning("Discarding invalid stored cycle for %s", self._name)
            return
        if self._cycle.state is LaundryState.RUNNING:
            self._schedule_finish()

    @callback
    def async_shutdown(self) -> None:
        """Cancel the pending finish callback."""
        self._cancel_finish()

    @callback
    def async_add_listener(self, listener: LaundryListener) -> CALLBACK_TYPE:
        """Listen for transitions."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def start(self, duration: timedelta, load: str | None = None) -> None:
        """Start a new cycle."""
        self._require(LaundryState.IDLE, "not_idle")
        if duration <= timedelta(0):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_duration"
            )
        self._set(
            Cycle(
                state=LaundryState.RUNNING,
                load=(load or "").strip() or None,
                duration=duration,
                finishes_at=dt_util.utcnow() + duration,
            ),
            LaundryEvent.STARTED,
        )

    @callback
    def pause(self) -> None:
        """Pause the running cycle."""
        self._require(LaundryState.RUNNING, "not_running")
        assert self._cycle.finishes_at is not None
        remaining = max(self._cycle.finishes_at - dt_util.utcnow(), timedelta(0))
        self._set(
            Cycle(
                state=LaundryState.PAUSED,
                load=self._cycle.load,
                duration=self._cycle.duration,
                remaining=remaining,
            ),
            LaundryEvent.PAUSED,
        )

    @callback
    def resume(self) -> None:
        """Resume the paused cycle."""
        self._require(LaundryState.PAUSED, "not_paused")
        assert self._cycle.remaining is not None
        self._set(
            Cycle(
                state=LaundryState.RUNNING,
                load=self._cycle.load,
                duration=self._cycle.duration,
                finishes_at=dt_util.utcnow() + self._cycle.remaining,
            ),
            LaundryEvent.RESUMED,
        )

    @callback
    def cancel(self) -> None:
        """Cancel a running or paused cycle."""
        if self._cycle.state not in (LaundryState.RUNNING, LaundryState.PAUSED):
            raise self._invalid("not_active")
        self._set(Cycle(), LaundryEvent.CANCELLED)

    @callback
    def empty(self) -> None:
        """Mark the finished cycle as emptied."""
        self._require(LaundryState.FINISHED, "not_finished")
        self._set(Cycle(), LaundryEvent.EMPTIED)

    @callback
    def _finish(self, _now: datetime | None = None) -> None:
        self._unsub_finish = None
        self._set(
            Cycle(
                state=LaundryState.FINISHED,
                load=self._cycle.load,
                duration=self._cycle.duration,
            ),
            LaundryEvent.FINISHED,
        )

    def _require(self, state: LaundryState, translation_key: str) -> None:
        if self._cycle.state is not state:
            raise self._invalid(translation_key)

    def _invalid(self, translation_key: str) -> ServiceValidationError:
        return ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key=translation_key,
            translation_placeholders={"name": self._name},
        )

    @callback
    def _set(self, cycle: Cycle, event: LaundryEvent) -> None:
        self._cancel_finish()
        self._cycle = cycle
        if cycle.state is LaundryState.RUNNING:
            self._schedule_finish()
        self._store.async_delay_save(self._cycle.as_dict)
        for listener in list(self._listeners):
            listener(event)

    @callback
    def _schedule_finish(self) -> None:
        assert self._cycle.finishes_at is not None
        if self._cycle.finishes_at <= dt_util.utcnow():
            self._finish()
            return
        self._unsub_finish = async_track_point_in_utc_time(
            self._hass, self._finish, self._cycle.finishes_at
        )

    @callback
    def _cancel_finish(self) -> None:
        if self._unsub_finish is not None:
            self._unsub_finish()
            self._unsub_finish = None

    async def async_remove(self) -> None:
        """Delete persisted data."""
        await self._store.async_remove()


def cycle_attributes(cycle: Cycle) -> dict[str, Any]:
    """State attributes shared by entities, formatted like the timer helper."""
    return {
        ATTR_LOAD: cycle.load,
        ATTR_DURATION: _format(cycle.duration),
        ATTR_FINISHES_AT: cycle.finishes_at.isoformat() if cycle.finishes_at else None,
        ATTR_REMAINING: _format(cycle.remaining),
    }


def _format(value: timedelta | None) -> str | None:
    if value is None:
        return None
    total = round(value.total_seconds())
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{seconds:02}"
