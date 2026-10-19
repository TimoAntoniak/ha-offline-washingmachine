"""Constants for the Offline Laundry integration."""

from enum import StrEnum
from typing import Final

DOMAIN: Final = "offline_laundry"

CONF_APPLIANCE_TYPE: Final = "appliance_type"
CONF_NOTIFY_TARGETS: Final = "notify_targets"

ATTR_DURATION: Final = "duration"
ATTR_FINISHES_AT: Final = "finishes_at"
ATTR_LOAD: Final = "load"
ATTR_REMAINING: Final = "remaining"

SERVICE_START: Final = "start"
SERVICE_PAUSE: Final = "pause"
SERVICE_RESUME: Final = "resume"
SERVICE_CANCEL: Final = "cancel"
SERVICE_EMPTY: Final = "empty"

NOTIFICATION_ACTION_EMPTIED: Final = "OFFLINE_LAUNDRY_EMPTIED_"

CARD_FILENAME: Final = "offline-laundry-card.js"
CARD_URL_PATH: Final = f"/{DOMAIN}/{CARD_FILENAME}"


class ApplianceType(StrEnum):
    """Kind of appliance; only affects icons and wording."""

    WASHER = "washer"
    DRYER = "dryer"


class LaundryState(StrEnum):
    """State of an appliance."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


class LaundryEvent(StrEnum):
    """Transitions exposed through the event entity."""

    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    CANCELLED = "cancelled"
    FINISHED = "finished"
    EMPTIED = "emptied"
