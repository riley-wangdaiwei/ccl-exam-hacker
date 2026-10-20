#!/usr/bin/env python3
"""CCL Exam Hacker - Step 02: search + reader + highlight-to-comment web app.

Stdlib only, no login. Run: python3 app.py  ->  http://localhost:8000
"""
import html
import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "corpus.db"
PORT = 8000


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL REFERENCES chunks(id),
            text TEXT NOT NULL,
            tag TEXT NOT NULL DEFAULT 'note',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS comments_fts
            USING fts5(text, comment_id UNINDEXED, tokenize='porter');
    """)
    conn.commit()


def fts_query(q: str) -> str:
    terms = [t for t in re.split(r"\s+", q.strip().strip('"')) if t]
    return " ".join('"' + t.replace('"', '""') + '"' for t in terms)


def search_chunks(conn, q, doc_type=None, lecture=None):
    fq = fts_query(q)
    sql = """
        SELECT c.id, c.page, c.para_start, c.para_end,
               d.label AS doc_label, d.doc_type, d.lecture, d.filename,
               snippet(chunks_fts, 0, '<mark>', '</mark>', '…', 24) AS snippet
        FROM chunks_fts f
        JOIN chunks c ON c.id = f.chunk_id
        JOIN documents d ON d.id = c.doc_id
        WHERE chunks_fts MATCH ?
    """
    params = [fq]
    if doc_type:
        sql += " AND d.doc_type = ?"; params.append(doc_type)
    if lecture:
        sql += " AND d.lecture = ?"; params.append(int(lecture))
    sql += " LIMIT 40"
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        return []
    return [dict(r, tier="source", kind="chunk") for r in rows]


def search_comments(conn, q):
    fq = fts_query(q)
    try:
        rows = conn.execute("""
            SELECT cm.id, cm.text, cm.tag, cm.created_at, cm.chunk_id,
                   snippet(comments_fts, 0, '<mark>', '</mark>', '…', 24) AS snippet,
                   d.label AS doc_label, d.doc_type, c.page
            FROM comments_fts f
            JOIN comments cm ON cm.id = f.comment_id
            JOIN chunks c ON c.id = cm.chunk_id
            JOIN documents d ON d.id = c.doc_id
            WHERE comments_fts MATCH ?
            LIMIT 20
        """, (fq,)).fetchall()
    except Exception:
        return []
    return [dict(r, tier="my_note", kind="comment") for r in rows]


class Handler(BaseHTTPRequestHandler):
    server_version = "CCLExamHacker/0.2"

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, ctype: str):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        conn = db()
        try:
            if u.path in ("/", "/index.html"):
                return self._file(BASE / "index.html", "text/html; charset=utf-8")
            if u.path == "/api/docs":
                rows = conn.execute(
                    "SELECT id, filename, label, doc_type, lecture, page_count FROM documents ORDER BY lecture, id"
                ).fetchall()
                return self._json([dict(r) for r in rows])
            if u.path == "/api/search":
                qs = parse_qs(u.query)
                q = qs.get("q", [""])[0].strip()
                if not q:
                    return self._json([])
                doc_type = qs.get("doc_type", [""])[0] or None
                lecture = qs.get("lecture", [""])[0] or None
                tier = qs.get("tier", [""])[0] or None
                out = []
                if tier in (None, "", "source"):
                    out += search_chunks(conn, q, doc_type, lecture)
                if tier in (None, "", "my_note") and not doc_type:
                    out += search_comments(conn, q)
                return self._json(out)
            if u.path.startswith("/api/chunk/"):
                cid = int(u.path.rsplit("/", 1)[1])
                c = conn.execute("""
                    SELECT c.*, d.label AS doc_label, d.doc_type, d.filename, d.lecture
                    FROM chunks c JOIN documents d ON d.id = c.doc_id WHERE c.id = ?
                """, (cid,)).fetchone()
                if not c:
                    return self._json({"error": "not found"}, 404)
                comments = conn.execute(
                    "SELECT id, text, tag, created_at FROM comments WHERE chunk_id = ? ORDER BY id",
                    (cid,)).fetchall()
                return self._json({**dict(c), "comments": [dict(x) for x in comments]})
            if u.path == "/api/comments":
                qs = parse_qs(u.query)
                cid = qs.get("chunk_id", [None])[0]
                if cid:
                    rows = conn.execute(
                        "SELECT id, text, tag, created_at FROM comments WHERE chunk_id = ? ORDER BY id",
                        (int(cid),)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT cm.id, cm.text, cm.tag, cm.created_at, cm.chunk_id,
                               d.label AS doc_label, c.page
                        FROM comments cm
                        JOIN chunks c ON c.id = cm.chunk_id
                        JOIN documents d ON d.id = c.doc_id
                        ORDER BY cm.id DESC LIMIT 50""").fetchall()
                return self._json([dict(r) for r in rows])
            return self._json({"error": "not found"}, 404)
        finally:
            conn.close()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/comments":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            text = (data.get("text") or "").strip()
            chunk_id = data.get("chunk_id")
            tag = (data.get("tag") or "note").strip() or "note"
            if not text or not chunk_id:
                return self._json({"error": "text and chunk_id required"}, 400)
            if tag not in ("note", "question", "counterargument"):
                tag = "note"
            conn = db()
            try:
                exists = conn.execute("SELECT 1 FROM chunks WHERE id = ?", (int(chunk_id),)).fetchone()
                if not exists:
                    return self._json({"error": "chunk not found"}, 404)
                cur = conn.execute(
                    "INSERT INTO comments (chunk_id, text, tag) VALUES (?,?,?)",
                    (int(chunk_id), text, tag))
                conn.execute("INSERT INTO comments_fts (text, comment_id) VALUES (?,?)",
                             (text, cur.lastrowid))
                conn.commit()
                row = conn.execute(
                    "SELECT id, text, tag, created_at FROM comments WHERE id = ?",
                    (cur.lastrowid,)).fetchone()
                return self._json(dict(row), 201)
            finally:
                conn.close()
        return self._json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    conn = db()
    ensure_schema(conn)
    conn.close()
    print(f"CCL Exam Hacker on http://localhost:{PORT}  (corpus: {DB_PATH.name})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
