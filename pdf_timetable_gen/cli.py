"""CLI entry point — typer app with rich terminal UI."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

from .config import Settings
from .parser import parse_pdf
from .extractor import extract_structure
from .analyzer import analyze_topics
from .constraint import StudyConstraints, PhaseGrouping
from .scheduler import ScheduleGenerator
from .formats import write_all

app = typer.Typer(
    name="pdf-timetable-gen",
    help="Generate personalised study timetables from PDF syllabi.",
    add_completion=False,
)
console = Console()
settings = Settings()


@app.command()
def generate(
    pdf: str = typer.Argument(..., help="Path to the syllabus PDF"),
    output: str = typer.Option(".", "--output", "-o", help="Output directory"),
    name: str = typer.Option("timetable", "--name", "-n", help="Base filename"),
    days: int = typer.Option(39, "--days", "-d", help="Total exam prep days"),
    hours: float = typer.Option(6.0, "--hours", help="Daily study hours"),
    rest_days: str = typer.Option("", "--rest-days", help="Comma-separated rest days (0=Mon, 6=Sun)"),
    rest_per_week: int = typer.Option(1, "--rest-per-week", help="Rest days per week"),
    revision: int = typer.Option(3, "--revision", help="Revision buffer days at end"),
    phases: str = typer.Option(
        "linear",
        "--phases",
        help="Phase grouping: linear, interleaved, concentrated",
    ),
    llm: Optional[str] = typer.Option(None, "--llm", help="LLM model name"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="LLM API base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", envvar="LLM_API_KEY", help="LLM API key"),
    formats: str = typer.Option(
        "docx,md,ics,html",
        "--formats",
        "-f",
        help="Comma-separated output formats",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Generate a study timetable from a syllabus PDF.

    Examples:

        pdf-timetable-gen generate syllabus.pdf --days 30 --hours 5 --formats md,html

        pdf-timetable-gen generate syllabus.pdf --days 39 --llm gpt-4o --base-url https://api.openai.com/v1
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    rest_day_list = [int(x.strip()) for x in rest_days.split(",") if x.strip()] if rest_days else []

    # Banner
    console.print(Panel.fit(
        f"[bold cyan]Study Timetable Generator[/bold cyan]\n"
        f"[dim]pdf: {Path(pdf).name} | days: {days} | hours/day: {hours}[/dim]",
        border_style="cyan",
    ))

    # Validate PDF path
    pdf_path = Path(pdf)
    if not pdf_path.exists():
        console.print(f"[red]Error: PDF not found: {pdf}[/red]")
        raise typer.Exit(1)

    # ── Step 1: Parse ──────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Parsing PDF...", total=None)
        try:
            parsed = parse_pdf(pdf_path)
        except Exception as e:
            console.print(f"[red]Failed to parse PDF: {e}[/red]")
            raise typer.Exit(1)
        progress.update(task, completed=True)

    console.print(f"  [green]✓[/green] Parsed {parsed.total_pages} pages")

    # ── Step 2: Extract ────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Extracting topics...", total=None)
        chapters = extract_structure(parsed)
        progress.update(task, completed=True)

    total_topics = sum(len(c.topics) for c in chapters)
    console.print(f"  [green]✓[/green] Found {len(chapters)} chapters, {total_topics} topics")

    # Chapter table
    if total_topics > 0:
        table = Table(show_header=True, header_style="bold magenta", padding=(0, 2))
        table.add_column("Chapter", style="cyan")
        table.add_column("Topics", justify="right", style="green")
        for ch in chapters[:15]:
            table.add_row(ch.title, str(len(ch.topics)))
        if len(chapters) > 15:
            table.add_row("[dim]...", f"[dim]+{len(chapters)-15} more")
        console.print(table)

    # ── Step 3: Analyze ────────────────────────────────────────────────
    study_constraints_errors = StudyConstraints(
        total_days=days,
        hours_per_day=hours,
        rest_days=rest_day_list,
        rest_days_per_week=rest_per_week,
        revision_buffer_days=revision,
    ).validate()
    if study_constraints_errors:
        for err in study_constraints_errors:
            console.print(f"[red]Constraint: {err}[/red]")
        raise typer.Exit(1)

    study_days = days - (days // 7 * rest_per_week) - revision
    available_hours = study_days * hours

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Analyzing difficulty & hours...", total=None)
        all_topic_dicts = [
            {"title": t.title, "weightage": t.weightage}
            for ch in chapters for t in ch.topics
        ]
        analyzed = analyze_topics(all_topic_dicts, total_available_hours=available_hours)
        # Map analyzed data back onto topics
        idx = 0
        for ch in chapters:
            for t in ch.topics:
                if idx < len(analyzed):
                    t.difficulty = analyzed[idx].difficulty
                    t.estimated_hours = analyzed[idx].estimated_hours
                idx += 1
        progress.update(task, completed=True)

    console.print(f"  [green]✓[/green] Analyzed {total_topics} topics → {available_hours:.0f}h budget")

    # ── Step 4: Schedule ───────────────────────────────────────────────
    try:
        phase_enum = PhaseGrouping(phases.lower())
    except ValueError:
        console.print(f"[red]Unknown phase grouping: {phases} (use linear/interleaved/concentrated)[/red]")
        raise typer.Exit(1)

    constraints = StudyConstraints(
        total_days=days,
        hours_per_day=hours,
        rest_days=rest_day_list,
        rest_days_per_week=rest_per_week,
        phase_grouping=phase_enum,
        revision_buffer_days=revision,
    )

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Generating schedule...", total=None)
        generator = ScheduleGenerator(constraints)
        schedule = generator.generate(chapters)
        progress.update(task, completed=True)

    console.print(
        f"  [green]✓[/green] Generated [bold]{len(schedule.days)}[/bold] day plan, "
        f"{schedule.total_topics} slots, [cyan]{schedule.total_hours:.1f}h[/cyan] total"
    )

    # ── Step 5: Output ─────────────────────────────────────────────────
    output_dir = Path(output)
    fmt_list = [f.strip().lower() for f in formats.split(",")]

    console.print(f"\n[bold]Writing output files...[/bold]")
    try:
        paths = write_all(schedule, output_dir, name)
        for fmt in ["docx", "md", "ics", "html"]:
            if fmt in fmt_list and fmt in paths:
                console.print(f"  [green]✓[/green] {fmt.upper()}: {paths[fmt]}")
            elif fmt in fmt_list:
                console.print(f"  [red]✗[/red] {fmt.upper()}: format not available")
    except Exception as e:
        console.print(f"[red]Output error: {e}[/red]")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold green]Done![/bold green] Timetable written to [cyan]{output_dir.resolve()}[/cyan]\n"
        f"[dim]{len(schedule.days)} days | {schedule.total_topics} topics | {schedule.total_hours:.1f}h[/dim]",
        border_style="green",
    ))


@app.command()
def doctor() -> None:
    """Check system health and dependencies."""
    console.print(Panel.fit("[bold cyan]pdf-timetable-gen health check[/bold cyan]", border_style="cyan"))

    import sys
    console.print(f"  Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    deps = {
        "pypdf": "PDF parsing",
        "docx": "DOCX output",
        "typer": "CLI framework",
        "rich": "Terminal UI",
        "icalendar": "ICS calendar",
    }
    for mod, desc in deps.items():
        try:
            v = __import__(mod).__version__
            console.print(f"  [green]✓[/green] {mod} v{v} ({desc})")
        except ImportError:
            console.print(f"  [red]✗[/red] {mod} — MISSING ({desc})")

    llm = settings.llm
    if llm.is_configured:
        console.print(f"  [green]✓[/green] LLM: {llm.model} @ {llm.base_url}")
    else:
        console.print(f"  [dim]○ LLM: not configured (rule-based scoring active)[/dim]")

    console.print(f"\n[bold green]System healthy![/bold green]")


def main():
    """Entry point for console_scripts."""
    app()


if __name__ == "__main__":
    main()
