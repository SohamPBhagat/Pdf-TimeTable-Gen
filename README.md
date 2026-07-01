# pdf-timetable-gen

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Status: Beta](https://img.shields.io/badge/status-beta-yellow)

**Generate personalised study timetables from PDF syllabi — rule-based scoring + optional AI analysis via any LLM.**

---

## Features

- **PDF Parsing** — raw page text extraction via pypdf, preserving structure
- **Topic Extraction** — regex-driven chapter and topic identification from parsed text
- **Dual-Mode Difficulty Scoring** — rule-based heuristics so it works fully offline; optional LLM analysis for finer estimation
- **Constraint Engine** — total days, daily hours, rest days, phase grouping (Learn → Practice → Revise), max consecutive difficult topics, revision buffer days
- **Schedule Generator** — balanced load across study days with topic priority baked in
- **Multiple Output Formats** — `.docx` (Word), `.md` (Markdown), `.ics` (calendar), `.html` (styled, printable)
- **Rich Terminal UI** — progress spinners, colored summary tables, and a `doctor` command for system health checks
- **Model-Agnostic** — plug in any OpenAI-compatible endpoint (OpenAI, Gemini, Ollama, Together AI, Groq)

---

## Install

```bash
# From PyPI (when published)
pip install pdf-timetable-gen

# From source
git clone https://github.com/SohamPBhagat/pdf-timetable-gen
cd pdf-timetable-gen
pip install -e ".[dev]"
```

Requires Python 3.10 or later.

---

## Quick Start

### Basic (no LLM)

Rule-based scoring only. No API key needed.

```bash
pdf-timetable-gen generate syllabus.pdf \
  --days 39 \
  --hours 6 \
  --rest-days 6 \
  --rest-per-week 1 \
  --phases linear \
  --formats md,html
```

### With LLM analysis

Point any OpenAI-compatible endpoint at a model you already have access to.

```bash
export LLM_API_KEY=sk-...
export LLM_MODEL=gpt-4o
export LLM_BASE_URL=https://api.openai.com/v1

pdf-timetable-gen generate syllabus.pdf \
  --days 30 \
  --hours 5 \
  --revision 3 \
  --llm gpt-4o \
  --base-url https://api.openai.com/v1 \
  --formats docx,md,ics
```

For local or alternative providers, swap the base URL and model name:

```bash
# Ollama (local)
export LLM_API_KEY=ollama
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=llama3

# Groq
export LLM_API_KEY=gsk_...
export LLM_BASE_URL=https://api.groq.com/openai/v1
export LLM_MODEL=llama-3.3-70b-versatile
```

---

## LLM Configuration

Settings are read from environment variables or CLI flags. The `--api-key` flag supports the `LLM_API_KEY` environment variable as a fallback.

| Env Var | CLI Flag | Default | Description |
|---------|----------|---------|-------------|
| `LLM_API_KEY` | `--api-key` | _(empty)_ | API key for the LLM provider |
| `LLM_BASE_URL` | `--base-url` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `--llm` | `gpt-4o` | Model identifier |
| `LLM_MAX_TOKENS` | _(none)_ | `1024` | Max tokens per LLM request |
| `LLM_TEMPERATURE` | _(none)_ | `0.3` | Sampling temperature |

### Supported Providers

| Provider | Base URL |
|----------|----------|
| OpenAI | `https://api.openai.com/v1` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta` |
| Ollama (local) | `http://localhost:11434/v1` |
| Together AI | `https://api.together.xyz/v1` |
| Groq | `https://api.groq.com/openai/v1` |

---

## Constraints

| Flag / Env | Type | Default | Description |
|------------|------|---------|-------------|
| `--days` / `-d` | int | `39` | Total exam preparation days |
| `--hours` | float | `6.0` | Study hours per day |
| `--rest-days` | int list | _(none)_ | Comma-separated weekday indices (0 = Mon, 6 = Sun) |
| `--rest-per-week` | int | `1` | Automatic rest days per week |
| `--phases` | str | `linear` | Phase grouping: `linear`, `interleaved`, `concentrated` |
| `--revision` | int | `3` | Revision buffer days reserved at end |
| `--llm` | str | _(none)_ | LLM model identifier to enable AI scoring |
| `--formats` / `-f` | str | `docx,md,ics,html` | Comma-separated output formats |

### Phase Grouping

- **linear** — learn all subtopics of a chapter, then practice, then revise (top-down)
- **interleaved** — learn → practice → revise within each topic, cycling through chapters
- **concentrated** — complete an entire chapter (all phases) before moving to the next

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PDF INPUT  │────▶│  PDF PARSER  │────▶│ CONTENT       │
│  Syllabus    │     │  pypdf        │     │ EXTRACTOR     │
│  PDF(s)      │     │ per-page text │     │ Chaps,Topics  │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                           ┌──────────────┐
                                           │ AI ANALYZER   │
                                           │ Rule-based +  │
                                           │ Optional LLM  │
                                           │ Difficulty &  │
                                           │ Hours         │
                                           └──────┬───────┘
                                                  │
                                                  ▼
                                           ┌──────────────┐
                                           │ CONSTRAINT    │
                                           │ ENGINE        │
                                           │ Days, Hours,  │
                                           │ Rest, Phases  │
                                           └──────┬───────┘
                                                  │
                                                  ▼
                                           ┌──────────────┐
                                           │ SCHEDULE      │
                                           │ GENERATOR     │
                                           │ Day mapping,  │
                                           │ Balance,      │
                                           │ Revision buf  │
                                           └──────┬───────┘
                                                  │
                                ┌──────────────────┼──────────────────┐
                                ▼                  ▼                  ▼
                          ┌──────────┐    ┌──────────┐    ┌──────────┐
                          │  .docx   │    │   .md    │    │  .ics    │
                          │  Word    │    │ Markdown │    │ Calendar │
                          └──────────┘    └──────────┘    └──────────┘
                                │                  │
                                ▼                  ▼
                          ┌──────────┐    ┌──────────┐
                          │  .html   │    │  rich    │
                          │ Styled   │    │  CLI     │
                          │ Printable│    │  Output  │
                          └──────────┘    └──────────┘
```

---

## Development

```bash
# Clone and install in editable mode with dev deps
git clone https://github.com/SohamPBhagat/pdf-timetable-gen
cd pdf-timetable-gen
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check pdf_timetable_gen/

# Type check
mypy pdf_timetable_gen/
```

---

## Roadmap

- [x] v0.1 — Core pipeline: PDF → schedule → outputs (docx, md, ics, html)
- [x] v0.1 — Rule-based scoring + optional LLM integration
- [x] v0.1 — Constraint engine with phase grouping and revision buffer
- [x] v0.1 — Rich terminal UI (`doctor` command, progress bars, tables)
- [ ] v0.2 — True Learn/Practice/Revise phase separation in schedule output
- [ ] v0.3 — AI-powered chapter detection for messy or image-heavy PDFs
- [ ] v0.4 — Spaced repetition integration for revision days
- [ ] v0.5 — Web UI (Streamlit)

---

## License

MIT — see [LICENSE](LICENSE) for details.
