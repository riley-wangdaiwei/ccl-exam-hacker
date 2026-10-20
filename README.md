# CCL Exam Hacker

An interactive source of truth for Contemporary Constitutional Law exam prep.
Search every lecture slide, seminar file, case and draft from one place —
every fragment traces back to its exact document, page and paragraph.

**Live:** https://riley-wangdaiwei.github.io/ccl-exam-hacker/

UI mimics the Sciences Po course documents. No login, no server — the whole
app runs in the browser; your comments stay in your browser's localStorage.

## How it works

- **Step 01 — ingest**: `ingest.py` reads the PDFs → paragraph-aware chunks →
  SQLite FTS5 (`corpus.db`, git-ignored). Each chunk carries filename, page
  and paragraph range.
- **Step 02 — search & read**: `build_static.py` exports `corpus.json`;
  `index.html` searches it in-browser with document / lecture / tier filters,
  snippet highlights, a document-style reader, and highlight-to-comment.
  Comments are searchable as `my_note` tier and link back to the extract.
- **Step 03 — fragment engine** (planned): paste a fuzzy thesis, get ranked
  fragments (original text + source + one-line why-relevant) across all tiers.
  AI retrieves; it never argues for you and never invents cases. Bring your
  own Gemini API key — entered in the app, stored only in your browser.

## Authority tiers

- `source` — the uploaded course materials (the only fact source)
- `my_note` — your own comments and interpretations
- `ai_suggest` — AI suggestions, always labeled unverified

## Local development

```bash
pip install pypdf
python3 ingest.py        # corpus.db from the PDFs (edit DOCS / SRC_DIR first)
python3 build_static.py  # corpus.json for the static site
python3 app.py           # optional local server -> http://localhost:8000
```
