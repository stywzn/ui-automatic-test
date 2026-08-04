"""
teampilot-lite — 一个精简的"团队看板"被测系统(SUT),专门用于 UI 自动化练习。

设计目标(为什么长这样):
- 登录 / 看板 / CRUD / SSE 实时推送 —— 覆盖 UI 自动化最常见的场景。
- 所有可交互元素带 data-testid —— 让测试用稳定定位器,而不是脆弱的 xpath/文本。
- 纯内存存储、零外部依赖 —— 一条命令就能起,方便随时重置数据做测试隔离。

运行:
    pip install -r requirements.txt
    uvicorn app:app --reload --port 8000
然后打开 http://localhost:8000
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, File, Request, Response, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

app = FastAPI(title="teampilot-lite")

STATIC = Path(__file__).parent / "static"

# --- 极简"账号"与"会话"(仅用于练习,不是真实鉴权方案) ---------------------
USERS = {"admin": "admin123"}
SESSION_COOKIE = "tp_session"
VALID_TOKEN = "demo-session-token"  # 固定 token,方便测试直接注入登录态

# --- 内存数据:工作项。用一个函数生成初始数据,方便 /api/reset 重置 ----------
def _seed():
    return [
        {"id": 1, "title": "修复登录页报错提示", "status": "open", "assignee": "alice"},
        {"id": 2, "title": "看板加载性能优化", "status": "in_progress", "assignee": "bob"},
        {"id": 3, "title": "SSE 断线自动重连", "status": "done", "assignee": "alice"},
    ]

ITEMS: list[dict] = _seed()
_next_id = 4

# 已上传文件的记录(只存元信息,不落盘 —— 练习够用)
UPLOADS: list[dict] = []

# SSE:所有已连接的浏览器订阅这个队列列表,数据变更时向每个队列推事件
subscribers: list[asyncio.Queue] = []


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


# --- 工作项 CRUD ------------------------------------------------------------
@app.get("/api/items")
def list_items(request: Request):
    _require_login(request)
    return {"items": ITEMS}


@app.post("/api/items")
async def create_item(request: Request):
    _require_login(request)
    global _next_id
    body = await request.json()
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title 不能为空")
    item = {
        "id": _next_id,
        "title": title,
        "status": body.get("status", "open"),
        "assignee": body.get("assignee", "admin"),
    }
    _next_id += 1
    ITEMS.append(item)
    await _broadcast({"type": "created", "item": item})
    return JSONResponse(item, status_code=201)


@app.put("/api/items/{item_id}")
async def update_item(item_id: int, request: Request):
    _require_login(request)
    body = await request.json()
    for it in ITEMS:
        if it["id"] == item_id:
            it.update({k: body[k] for k in ("title", "status", "assignee") if k in body})
            await _broadcast({"type": "updated", "item": it})
            return it
    raise HTTPException(status_code=404, detail="not found")


@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int, request: Request):
    _require_login(request)
    global ITEMS
    before = len(ITEMS)
    ITEMS = [it for it in ITEMS if it["id"] != item_id]
    if len(ITEMS) == before:
        raise HTTPException(status_code=404, detail="not found")
    await _broadcast({"type": "deleted", "id": item_id})
    return {"ok": True}


# --- 文件上传 ---------------------------------------------------------------
@app.post("/api/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    """接收一个上传文件,只记录文件名和大小(不落盘)。用于练习文件上传交互。"""
    _require_login(request)
    content = await file.read()
    record = {"filename": file.filename, "size": len(content)}
    UPLOADS.append(record)
    return JSONResponse(record, status_code=201)


@app.get("/api/uploads")
def list_uploads(request: Request):
    _require_login(request)
    return {"uploads": UPLOADS}


@app.post("/api/reset")
def reset():
    """把数据恢复到初始状态 —— 测试用例的 setUp/teardown 可以调它做隔离。"""
    global ITEMS, _next_id, UPLOADS
    ITEMS = _seed()
    _next_id = 4
    UPLOADS = []
    return {"ok": True}


# --- SSE:服务器持续向浏览器单向推送工作项变更 ------------------------------
@app.get("/api/stream")
async def stream(request: Request):
    _require_login(request)

    async def event_generator():
        q: asyncio.Queue = asyncio.Queue()
        subscribers.append(q)
        try:
            # 连上先推一次心跳,让前端知道连接已建立
            yield "event: hello\ndata: connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # 最多等 15s,没数据就发心跳,保持连接不被中间层掐断
                    data = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            # 关键:连接断开必须把队列摘掉,否则就是内存/连接泄漏(稳定性测试要抓的正是这个)
            if q in subscribers:
                subscribers.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/health")
def health():
    return {"status": "ok", "items": len(ITEMS), "sse_connections": len(subscribers)}
