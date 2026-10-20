#!/usr/bin/env python3
"""CCL Exam Hacker - Step 01: ingest PDFs/DOCXs into a chunked SQLite corpus.

Each chunk carries: filename, page number, paragraph range -> the acceptance
criterion is that a search for "reasonable observer" returns relevant fragments
with an accurate, jumpable source.
"""
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "corpus.db"

# Explicit source-of-truth manifest: every file Eika uploads gets an entry here.
DOCS = [
    {"path": "midterm.pdf",   "doc_type": "exam",              "lecture": None, "label": "CCL Midterm exam 2023"},
    {"path": "sunstein.pdf",  "doc_type": "preliminary_draft", "lecture": 6,    "label": "Sunstein, Presidential Immunity and Democratic Disorder (preliminary draft)"},
    {"path": "trump-v-us.pdf","doc_type": "case",              "lecture": 6,    "label": "Trump v. United States (2024)"},
    {"path": "session6.pdf",  "doc_type": "seminar",           "lecture": 6,    "label": "Session 6 seminar file"},
    {"path": "lecture6.pdf",  "doc_type": "lecture_slides",    "lecture": 6,    "label": "Lecture 6 slides"},
]

SRC_DIR = Path.home() / "workspace" / "akccl"   # where the PDFs currently live

CHUNK_TARGET = 600   # characters; fragments stay short on purpose
CHUNK_MAX = 900


def clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_page(page_text: str, max_chars: int = CHUNK_TARGET):
    """Split one page of text into paragraph-aware chunks.

    Returns list of (text, para_start, para_end) with 1-based paragraph numbers
    within the page.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", page_text) if p.strip()]
    chunks = []
    buf, start = [], None
    for i, p in enumerate(paras, start=1):
        if start is None:
            start = i
        # never split a single paragraph across chunks; start a new chunk instead
        if buf and len(" ".join(buf)) + len(p) > CHUNK_MAX:
            chunks.append((" ".join(buf), start, i - 1))
            buf, start = [], i
        buf.append(p)
        if len(" ".join(buf)) >= max_chars:
            chunks.append((" ".join(buf), start, i))
            buf, start = [], None
    if buf:
        chunks.append((" ".join(buf), start, len(paras)))
    return chunks


def read_pdf(path: Path):
    reader = PdfReader(str(path))
    pages = []
    for pageno, page in enumerate(reader.pages, start=1):
        try:
            t = clean(page.extract_text() or "")
        except Exception:
            t = ""
        pages.append(t)
    return pages


def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        DROP TABLE IF EXISTS chunks_fts;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS documents;
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            label TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            lecture INTEGER,
            page_count INTEGER NOT NULL,
            ingested_at TEXT NOT NULL
        );
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            doc_id INTEGER NOT NULL REFERENCES documents(id),
            page INTEGER NOT NULL,
            para_start INTEGER NOT NULL,
            para_end INTEGER NOT NULL,
            text TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            text, chunk_id UNINDEXED, tokenize='porter'
        );
    """)


def ingest():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    now = datetime.now(timezone.utc).isoformat()
    total_chunks = 0
    for meta in DOCS:
        src = SRC_DIR / meta["path"]
        if not src.exists():
            print(f"SKIP (missing): {src}", file=sys.stderr)
            continue
        pages = read_pdf(src)
        cur = conn.execute(
            "INSERT INTO documents (filename, label, doc_type, lecture, page_count, ingested_at)"
            " VALUES (?,?,?,?,?,?)",
            (meta["path"], meta["label"], meta["doc_type"], meta["lecture"], len(pages), now),
        )
        doc_id = cur.lastrowid
        n = 0
        for pageno, ptext in enumerate(pages, start=1):
            if not ptext:
                continue
            for text, ps, pe in chunk_page(ptext):
                cid = conn.execute(
                    "INSERT INTO chunks (doc_id, page, para_start, para_end, text)"
                    " VALUES (?,?,?,?,?)",
                    (doc_id, pageno, ps, pe, text),
                ).lastrowid
                conn.execute(
                    "INSERT INTO chunks_fts (text, chunk_id) VALUES (?,?)", (text, cid)
                )
                n += 1
        total_chunks += n
        print(f"ingested {meta['path']}: {len(pages)} pages -> {n} chunks")
    conn.commit()
    print(f"TOTAL: {total_chunks} chunks in {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    ingest()
