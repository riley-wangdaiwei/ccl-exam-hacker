# CCL Exam Hacker

An interactive source of truth for Contemporary Constitutional Law exam prep.
Search every lecture slide, seminar file, case and draft from one place —
every fragment traces back to its exact document, page and paragraph.

UI mimics the Sciences Po course documents.

## Quickstart

```bash
pip install pypdf
# 1. put course PDFs next to ingest.py (or edit SRC_DIR / DOCS in ingest.py)
python3 ingest.py     # builds corpus.db (351 chunks from 5 PDFs)
python3 app.py        # -> http://localhost:8000
```

## How it works

- **Step 01 — ingest**: PDFs → paragraph-aware chunks → SQLite FTS5.
  Each chunk carries filename, page and paragraph range.
- **Step 02 — search & read**: keyword search with document / lecture / tier
  filters, snippet highlights, a document-style reader, and
  highlight-to-comment. Comments are full-text indexed as `my_note` tier and
  link back to the extract they discuss.
- **Step 03 — fragment engine** (planned): paste a fuzzy thesis, get ranked
  fragments (original text + source + one-line why-relevant) across all tiers.
  AI retrieves; it never argues for you and never invents cases. Bring your
  own Gemini API key — entered in the app, stored only in your browser.

## Authority tiers

- `source` — the uploaded course materials (the only fact source)
- `my_note` — your own comments and interpretations
- `ai_suggest` — AI suggestions, always labeled unverified

`corpus.db` is generated locally and never committed.
