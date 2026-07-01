"""ICS (iCalendar) output writer."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import icalendar
from icalendar import Event, Calendar

logger = logging.getLogger(__name__)


def write(schedule, path: str | Path) -> Path:
    """Write schedule as an .ics calendar file.

    Each study slot becomes a calendar event.

    Args:
        schedule: GeneratedSchedule.
        path: Output file path.

    Returns:
        Path to the written file.
    """
    path = Path(path)
    cal = Calendar()
    cal.add("prodid", "-//pdf-timetable-gen//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "Study Timetable")

    for day in schedule.days:
        if not day.date:
            continue

        hour_cursor = 9.0  # 9 AM start
        for slot in day.slots:
            evt = Event()
            start_dt = datetime.combine(
                day.date,
                _decimal_to_time(hour_cursor),
            )
            end_dt = datetime.combine(
                day.date,
                _decimal_to_time(hour_cursor + slot.hours),
            )

            evt.add("dtstart", start_dt)
            evt.add("dtend", end_dt)
            evt.add("summary", f"[{slot.phase.upper()}] {slot.topic_title}")
            evt.add("description", f"Chapter: {slot.chapter}\nPhase: {slot.phase}\nHours: {slot.hours}")
            evt.add("location", "Study Desk")
            evt.add("status", "CONFIRMED")

            # Priority based on difficulty
            priority = 5 if slot.difficulty > 0.7 else (3 if slot.difficulty > 0.4 else 1)
            evt.add("priority", priority)

            cal.add_component(evt)
            hour_cursor += slot.hours

    path.write_bytes(cal.to_ical())
    logger.info("Wrote ICS: %s (%d events)", path, len(schedule.days))
    return path


def _decimal_to_time(decimal_hours: float):
    """Convert decimal hours (9.5 = 9:30) to a time object."""
    h = int(decimal_hours)
    m = int((decimal_hours - h) * 60)
    from datetime import time
    return time(hour=h, minute=m)
