"""
teampilot-lite —— 团队看板被测系统(SUT)，用于 UI 自动化练习。

存储：SQLite（同目录 teampilot.db）。相比之前的内存版，好处是**测试可以直连数据库做断言**
（验证数据真的落库、字段正确），这是接口/端到端测试的常用技能。

接口行为与之前完全一致，只是底层存储换成了 SQLite。

运行：
    pip install -r requirements.txt
    uvicorn app:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, File, Request, HTTPException, UploadFile
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)

app = FastAPI(title="teampilot-lite")

STATIC = Path(__file__).parent / "static"
DB_PATH = Path(__file__).parent / "teampilot.db"  # 测试可直连这个文件做数据库断言

# --- 极简账号/会话（仅练习用）---
USERS = {"admin": "admin123"}
SESSION_COOKIE = "tp_session"
VALID_TOKEN = "demo-session-token"

# SSE 订阅队列
subscribers: list[asyncio.Queue] = []

# 初始数据（reset 后固定是这 3 条，id = 1/2/3）
SEED = [
    (1, "修复登录页报错提示", "open", "alice"),
    (2, "看板加载性能优化", "in_progress", "bob"),
    (3, "SSE 断线自动重连", "done", "alice"),
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让查询结果能像 dict 一样按列名取
    return conn


def _init_db():
    """建表 + 灌初始数据。drop 重建 → id 从 1 开始，保证 reset 后是固定的 1/2/3。"""
    conn = _connect()
    conn.executescript(
        """
        DROP TABLE IF EXISTS items;
        DROP TABLE IF EXISTS uploads;
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            assignee TEXT NOT NULL DEFAULT 'admin'
        );
        CREATE TABLE uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            size INTEGER NOT NULL
        );
        """
    )
    conn.executemany(
        "INSERT INTO items (id, title, status, assignee) VALUES (?, ?, ?, ?)", SEED
    )
    conn.commit()
    conn.close()


_init_db()  # 服务启动即初始化数据库


async def _broadcast(event: dict):
    data = json.dumps(event, ensure_ascii=False)
    for q in list(subscribers):
        await q.put(data)


def _require_login(request: Request):
    if request.cookies.get(SESSION_COOKIE) != VALID_TOKEN:
        raise HTTPException(status_code=401, detail="not logged in")


# --- 页面 -------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse("/login")


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return (STATIC / "login.html").read_text(encoding="utf-8")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    if request.cookies.get(SESSION_COOKIE) != VALID_TOKEN:
        return RedirectResponse("/login")
    return (STATIC / "dashboard.html").read_text(encoding="utf-8")


# --- 认证 API ---------------------------------------------------------------
@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    username, password = body.get("username"), body.get("password")
    if USERS.get(username) == password:
        resp = JSONResponse({"ok": True})
        resp.set_cookie(SESSION_COOKIE, VALID_TOKEN, httponly=True, samesite="lax")
        return resp
    return JSONResponse({"ok": False, "error": "用户名或密码错误"}, status_code=401)


@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    return resp


# --- 工作项 CRUD（SQLite）---------------------------------------------------
@app.get("/api/items")
def list_items(request: Request):
    _require_login(request)
    conn = _connect()
    rows = conn.execute(
        "SELECT id, title, status, assignee FROM items ORDER BY id"
    ).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


@app.post("/api/items")
async def create_item(request: Request):
    _require_login(request)
    body = await request.json()
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title 不能为空")
    status = body.get("status", "open")
    assignee = body.get("assignee", "admin")
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO items (title, status, assignee) VALUES (?, ?, ?)",
        (title, status, assignee),
    )
    conn.commit()
    item = {"id": cur.lastrowid, "title": title, "status": status, "assignee": assignee}
    conn.close()
    await _broadcast({"type": "created", "item": item})
    return JSONResponse(item, status_code=201)


@app.put("/api/items/{item_id}")
async def update_item(item_id: int, request: Request):
    _require_login(request)
    body = await request.json()
    conn = _connect()
    row = conn.execute(
        "SELECT id, title, status, assignee FROM items WHERE id=?", (item_id,)
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="not found")
    item = dict(row)
    for k in ("title", "status", "assignee"):
        if k in body:
            item[k] = body[k]
    conn.execute(
        "UPDATE items SET title=?, status=?, assignee=? WHERE id=?",
        (item["title"], item["status"], item["assignee"], item_id),
    )
    conn.commit()
    conn.close()
    await _broadcast({"type": "updated", "item": item})
    return item


@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int, request: Request):
    _require_login(request)
    conn = _connect()
    cur = conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="not found")
    await _broadcast({"type": "deleted", "id": item_id})
    return {"ok": True}


# --- 文件上传 ---------------------------------------------------------------
@app.post("/api/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    _require_login(request)
    content = await file.read()
    conn = _connect()
    conn.execute(
        "INSERT INTO uploads (filename, size) VALUES (?, ?)",
        (file.filename, len(content)),
    )
    conn.commit()
    conn.close()
    return JSONResponse({"filename": file.filename, "size": len(content)}, status_code=201)


@app.get("/api/uploads")
def list_uploads(request: Request):
    _require_login(request)
    conn = _connect()
    rows = conn.execute("SELECT filename, size FROM uploads ORDER BY id").fetchall()
    conn.close()
    return {"uploads": [dict(r) for r in rows]}


@app.post("/api/reset")
def reset():
    """重置数据库到初始状态 —— 测试隔离用。"""
    _init_db()
    return {"ok": True}


# --- SSE --------------------------------------------------------------------
@app.get("/api/stream")
async def stream(request: Request):
    _require_login(request)

    async def event_generator():
        q: asyncio.Queue = asyncio.Queue()
        subscribers.append(q)
        try:
            yield "event: hello\ndata: connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=1)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            if q in subscribers:
                subscribers.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/health")
def health():
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    conn.close()
    return {"status": "ok", "items": n, "sse_connections": len(subscribers)}
