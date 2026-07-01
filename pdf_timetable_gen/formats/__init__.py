"""Output formatters — .docx, .md, .ics, .html."""

from __future__ import annotations

from pathlib import Path


def write_all(
    schedule,
    output_dir: str | Path,
    base_name: str = "timetable",
) -> dict[str, Path]:
    """Write all output formats and return paths.

    Args:
        schedule: GeneratedSchedule from scheduler.
        output_dir: Directory to write files.
        base_name: Base filename (no extension).

    Returns:
        Dict mapping format name to output Path.
    """
    from . import docx, md, ics, html  # lazy import to avoid circular deps

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    paths["docx"] = docx.write(schedule, output_dir / f"{base_name}.docx")
    paths["md"] = md.write(schedule, output_dir / f"{base_name}.md")
    paths["ics"] = ics.write(schedule, output_dir / f"{base_name}.ics")
    paths["html"] = html.write(schedule, output_dir / f"{base_name}.html")

    return paths
