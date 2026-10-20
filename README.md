# CCL Exam Hacker

An interactive source of truth for Contemporary Constitutional Law exam prep.
Search every lecture slide, seminar file, case and draft from one place —
every fragment traces back to its exact document, page and paragraph.

**Live:** https://riley-wangdaiwei.github.io/ccl-exam-hacker/

## How to use each part

- **QUESTIONS** — type a point, however rough, in Chinese or English. *Keyword search* matches exact terms; *AI semantic search* understands ideas. Narrow with the three filters first if needed.
- **DOCUMENTS** — every result is numbered, with its source (file, page, paragraph). AI results come grouped: I. supporting · II. counterarguments (steelmanned — answer these in your essay) · III. qualifications. Click any document to read the full passage.
- **MY NOTES** — while reading, select a passage, then save a note: analysis / question / counterargument. Notes stay searchable and always link back to their passage.
- **ANNEX I** — paste your Gemini API key once; set the model if you like. Both live only in your browser.
- **ANNEX II** — upload any course PDF: parsed in your browser, searchable at once, deletable any time.

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
- **Step 03 — AI semantic search**: paste a fuzzy thesis (Chinese or English)
  into the search box and hit **AI 语义检索**. Keyword matches prefilter the
  corpus, then Gemini ranks the fragments and labels each
  `supports / qualifies / counters` with a one-line note. AI retrieves; it
  never argues for you and never invents cases. Bring your own Gemini API
  key — saved in the **AI key** section, stored only in your browser.
- **Uploads**: add your own PDFs in the **Upload sources** section — parsed
  in your browser (pdf.js), chunked, searchable instantly, stored on your
  device only (localStorage), deletable any time.

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
