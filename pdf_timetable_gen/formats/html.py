"""HTML output writer — styled, self-contained timetable page."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


# NOTE: CSS braces are escaped as {{ }} since we use .format() later


def write(schedule, path: str | Path) -> Path:
    """Write schedule as a styled HTML file.

    Args:
        schedule: GeneratedSchedule.
        path: Output file path.

    Returns:
        Path to the written file.
    """
    path = Path(path)
    phase_map = {"learn": ("📖", "learn"), "practice": ("✏️", "practice"), "revise": ("🔄", "revise")}

    days_html = ""
    for day in schedule.days:
        date_str = day.date.strftime("%Y-%m-%d (%a)") if day.date else f"Day {day.day_number}"
        slots_html = ""

        for slot in day.slots:
            icon, phase_cls = phase_map.get(slot.phase, ("📚", "learn"))
            diff_pct = int(slot.difficulty * 100)
            diff_color = "#ef4444" if slot.difficulty > 0.7 else ("#f59e0b" if slot.difficulty > 0.4 else "#10b981")
            # Escape topic_title and chapter for HTML
            safe_title = slot.topic_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_chapter = slot.chapter.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            slots_html += f"""
<div class="slot">
  <div class="phase-badge {phase_cls}">{icon} {slot.phase}</div>
  <div class="slot-info">
    <div class="slot-title">{safe_title}</div>
    <div class="slot-chapter">{safe_chapter}</div>
  </div>
  <div class="difficulty-bar">
    <div class="difficulty-fill" style="width:{diff_pct}%; background:{diff_color}"></div>
  </div>
  <div class="slot-hours">{slot.hours}h</div>
</div>"""

        days_html += f"""
<div class="day">
  <div class="day-header">
    <div class="day-title">Day {day.day_number} — {date_str}</div>
    <div class="day-total">{day.total_hours:.1f}h</div>
  </div>
  {slots_html}
</div>"""

    html = _render_html(
        generated_date=date.today().strftime("%Y-%m-%d"),
        total_days=len(schedule.days),
        total_topics=schedule.total_topics,
        total_hours=schedule.total_hours,
        days_html=days_html,
    )

    path.write_text(html, encoding="utf-8")
    logger.info("Wrote HTML: %s", path)
    return path


def _render_html(
    generated_date: str,
    total_days: int,
    total_topics: int,
    total_hours: float,
    days_html: str,
) -> str:
    """Render the full HTML page — uses string concat to avoid brace escaping issues."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Study Timetable</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0f0f1a;
    color: #e0e0e0;
    padding: 32px;
    line-height: 1.6;
  }}
  h1 {{
    color: #fff;
    text-align: center;
    margin-bottom: 8px;
    font-size: 28px;
  }}
  .meta {{
    text-align: center;
    color: #888;
    margin-bottom: 32px;
    font-size: 14px;
    display: flex;
    justify-content: center;
    gap: 24px;
    flex-wrap: wrap;
  }}
  .meta span {{ background: #1a1a2e; padding: 6px 16px; border-radius: 20px; }}
  .day {{
    background: #1a1a2e;
    border-radius: 12px;
    margin-bottom: 20px;
    overflow: hidden;
    border: 1px solid #2a2a3a;
  }}
  .day-header {{
    padding: 12px 20px;
    background: linear-gradient(135deg, #667eea22, #764ba222);
    border-bottom: 1px solid #2a2a3a;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .day-title {{ font-size: 16px; font-weight: 600; color: #fff; }}
  .day-total {{ font-size: 13px; color: #888; }}
  .slot {{
    display: flex;
    align-items: center;
    padding: 10px 20px;
    border-bottom: 1px solid #1e1e32;
    gap: 16px;
  }}
  .slot:last-child {{ border-bottom: none; }}
  .phase-badge {{
    min-width: 90px;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    text-align: center;
  }}
  .learn {{ background: #3b82f633; color: #93c5fd; }}
  .practice {{ background: #f59e0b33; color: #fcd34d; }}
  .revise {{ background: #10b98133; color: #6ee7b7; }}
  .slot-info {{ flex: 1; }}
  .slot-title {{ color: #e0e0e0; font-size: 14px; }}
  .slot-chapter {{ color: #666; font-size: 12px; }}
  .slot-hours {{
    color: #888;
    font-size: 13px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    min-width: 40px;
    text-align: right;
  }}
  .difficulty-bar {{
    width: 60px;
    height: 6px;
    background: #2a2a3a;
    border-radius: 3px;
    overflow: hidden;
  }}
  .difficulty-fill {{
    height: 100%;
    border-radius: 3px;
  }}
  .print-btn {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #667eea;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 25px;
    font-size: 14px;
    cursor: pointer;
    box-shadow: 0 4px 15px #667eea66;
    transition: transform 0.2s;
  }}
  .print-btn:hover {{ transform: scale(1.05); }}
  @media print {{
    .print-btn {{ display: none; }}
    body {{ background: white; color: black; }}
    .day {{ border: 1px solid #ccc; break-inside: avoid; }}
  }}
</style>
</head>
<body>

<h1>📚 Study Timetable</h1>

<div class="meta">
  <span>📅 Generated: {generated_date}</span>
  <span>📆 Days: {total_days}</span>
  <span>📝 Topics: {total_topics}</span>
  <span>⏱ Total: {total_hours}h</span>
</div>

{days_html}

<button class="print-btn" onclick="window.print()">🖨 Print / Save PDF</button>

</body>
</html>"""
