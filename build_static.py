#!/usr/bin/env python3
"""Build the static site's corpus.json from corpus.db.

Run after ingest.py. The Pages site (index.html) loads this file and
searches entirely in the browser — no server needed.
"""
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "corpus.db"
OUT = BASE / "corpus.json"


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    docs = [dict(r) for r in conn.execute(
        "SELECT id, filename, label, doc_type, lecture, page_count FROM documents ORDER BY id")]
    chunks = [dict(r) for r in conn.execute(
        "SELECT id, doc_id, page, para_start, para_end, text FROM chunks ORDER BY id")]
    conn.close()
    OUT.write_text(json.dumps({"docs": docs, "chunks": chunks}, ensure_ascii=False),
                   encoding="utf-8")
    print(f"wrote {OUT} — {len(docs)} docs, {len(chunks)} chunks, {OUT.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    raise SystemExit(main())
