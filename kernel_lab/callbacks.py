"""Validation callback recording for chainstate-backed examples."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import pbk_compat as compat


@dataclass(frozen=True)
class CallbackEvent:
    kind: str
    block_hash: str = "unavailable"
    height: int | None = None
    detail: str = ""


@dataclass
class CallbackRecorder:
    events: list[CallbackEvent] = field(default_factory=list)

    def block_checked(self, *args: Any, **kwargs: Any) -> None:
        self.events.append(self._event("block_checked", *args, **kwargs))

    def block_connected(self, *args: Any, **kwargs: Any) -> None:
        self.events.append(self._event("block_connected", *args, **kwargs))

    def block_disconnected(self, *args: Any, **kwargs: Any) -> None:
        self.events.append(self._event("block_disconnected", *args, **kwargs))

    def _event(self, kind: str, *args: Any, **kwargs: Any) -> CallbackEvent:
        block_hash = "unavailable"
        height = None
        details: list[str] = []
        for value in list(args) + list(kwargs.values()):
            try:
                block_hash = compat.block_hash(value)
                break
            except Exception:  # noqa: BLE001 - callback payloads vary by binding.
                pass
        for key, value in kwargs.items():
            if key == "height":
                try:
                    height = int(value)
                except Exception:  # noqa: BLE001
                    pass
            elif key not in {"block"}:
                details.append(f"{key}={value}")
        for value in args:
            if hasattr(value, "height") and height is None:
                try:
                    height = int(value.height)
                except Exception:  # noqa: BLE001
                    pass
            if hasattr(value, "validation_mode") and hasattr(value, "block_validation_result"):
                details.append(
                    "state="
                    f"{value.validation_mode.name}/{value.block_validation_result.name}"
                )
        return CallbackEvent(kind, block_hash, height, ", ".join(details))

    def summary_lines(self) -> list[str]:
        lines = []
        for event in self.events:
            line = f"callback: {event.kind} hash={event.block_hash}"
            if event.height is not None:
                line += f" height={event.height}"
            if event.detail:
                line += f" detail={event.detail}"
            lines.append(line)
        return lines
