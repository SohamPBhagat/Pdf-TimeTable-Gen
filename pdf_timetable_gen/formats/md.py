"""Markdown output writer."""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import date

logger = logging.getLogger(__name__)


def write(schedule, path: str | Path) -> Path:
    """Write schedule as a Markdown file.

    Args:
        schedule: GeneratedSchedule.
        path: Output file path.

    Returns:
        Path to the written file.
    """
    path = Path(path)
    lines = [
        "# Study Timetable",
        "",
        f"**Generated:** {date.today().strftime('%Y-%m-%d')}  ",
        f"**Total Days:** {len(schedule.days)}  ",
        f"**Total Topics:** {schedule.total_topics}  ",
        f"**Total Hours:** {schedule.total_hours:.1f}  ",
        f"**Constraint:** {schedule.constraints}",
        "",
        "---",
        "",
    ]

    for day in schedule.days:
        date_str = day.date.strftime("%Y-%m-%d (%a)") if day.date else f"Day {day.day_number}"
        lines.append(f"## Day {day.day_number} — {date_str}")
        lines.append("")
        lines.append("| Time | Phase | Topic | Hours |")
        lines.append("|------|-------|-------|-------|")

        hour_cursor = 9.0  # assume 9 AM start
        for slot in day.slots:
            start_h = int(hour_cursor)
            end_h = int(hour_cursor + slot.hours)
            time_str = f"{start_h:02d}:00 – {end_h:02d}:00"
            phase_emoji = {"learn": "📖", "practice": "✏️", "revise": "🔄"}.get(slot.phase, "📚")
            lines.append(
                f"| {time_str} | {phase_emoji} {slot.phase} | {slot.topic_title} | {slot.hours}h |"
            )
            hour_cursor += slot.hours

        lines.append("")
        lines.append(f"**Total:** {day.total_hours:.1f} hours")
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote MD: %s (%d lines)", path, len(lines))
    return path
