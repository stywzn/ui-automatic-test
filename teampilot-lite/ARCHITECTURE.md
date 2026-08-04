# teampilot-lite 架构文档

> 被测系统(SUT)的结构说明：每个文件做什么、有哪些模块/功能、对应哪些测试点。
> 配套文档：业务背景与测试点清单见 [README.md](README.md)。

---

## 一、这是什么 & 技术栈

一个精简的**团队协作看板**，专门作为 UI 自动化练习的被测对象。保留了真实 Web 应用最典型的三段结构：**认证 → 业务页面(看板 CRUD) → 实时能力(SSE)**，另加**文件上传**和**删除确认弹窗**两个常见交互。

| 层 | 技术 | 说明 |
|----|------|------|
| 后端 | Python + FastAPI | 异步，原生支持 SSE |
| 前端 | 原生 HTML + JavaScript | 无框架；所有可交互元素带 `data-testid` |
| 存储 | 纯内存(Python list) | 进程重启即重置；也可调 `/api/reset` 手动重置 |
| 运行 | uvicorn | `uvicorn app:app --port 8000` |

---

## 二、目录结构（每个文件做什么）

```
teampilot-lite/
├── app.py                 后端全部逻辑：路由 + 数据 + SSE（唯一的 Python 文件）
├── static/
│   ├── login.html         登录页：表单 + 提交逻辑
│   └── dashboard.html     看板页：列表渲染 + CRUD + 上传 + 删除弹窗 + SSE 订阅
├── requirements.txt       后端依赖（fastapi / uvicorn / python-multipart）
├── README.md              业务背景、接口表、元素定位表、16 个测试点
└── ARCHITECTURE.md        本文件：架构与模块说明
```

| 文件 | 职责 | 关键点 |
|------|------|--------|
| `app.py` | 提供页面 + 全部 API + SSE 推送 | 内存数据、无数据库、无外部依赖 |
| `static/login.html` | 登录界面 | 提交调 `/api/login`，成功跳 `/dashboard` |
| `static/dashboard.html` | 看板界面 | 用 `EventSource` 订阅 SSE，变更自动刷新 |

---

## 三、整体架构（分层 + 请求流）

```
浏览器 (login.html / dashboard.html)
   │  ① 页面请求 GET /login /dashboard
   │  ② 数据请求 fetch /api/*
   │  ③ 实时订阅 EventSource /api/stream  ◄─── 服务器持续单向推送
   ▼
FastAPI (app.py)
   ├─ 页面路由      返回 static/*.html
   ├─ 认证模块      /api/login /logout  + _require_login 守卫
   ├─ 工作项 CRUD   /api/items (GET/POST/PUT/DELETE)
   ├─ 文件上传      /api/upload /uploads
   ├─ SSE 推送      /api/stream + _broadcast 广播
   └─ 运维          /api/reset /health
   ▼
内存数据 (ITEMS / UPLOADS / subscribers)
```

---

## 四、后端模块与功能（app.py 逐块）

### 1. 全局状态（模块级变量）
| 变量 | 类型 | 作用 |
|------|------|------|
| `USERS` | dict | 账号表（`admin/admin123`） |
| `VALID_TOKEN` | str | 固定会话 token，登录后种到 `tp_session` cookie |
| `ITEMS` | list[dict] | 工作项数据（内存） |
| `UPLOADS` | list[dict] | 上传文件元信息（内存） |
| `subscribers` | list[Queue] | 所有 SSE 连接的消息队列 |

### 2. 工具函数
| 函数 | 作用 |
|------|------|
| `_seed()` | 生成初始 3 条工作项，供启动和 reset 复用 |
| `_require_login(request)` | 校验 cookie，未登录抛 401 —— 所有需登录的接口都调它 |
| `_broadcast(event)` | 把一条变更事件推给**所有** SSE 订阅者 |

### 3. 路由清单（14 个）
| # | 方法 | 路径 | 模块 | 功能 |
|---|------|------|------|------|
| 1 | GET | `/` | 页面 | 重定向到 `/login` |
| 2 | GET | `/login` | 页面 | 返回登录页 |
| 3 | GET | `/dashboard` | 页面 | 返回看板页；**未登录跳 `/login`**（鉴权守卫） |
| 4 | POST | `/api/login` | 认证 | 校验账号→种 cookie |
| 5 | POST | `/api/logout` | 认证 | 删除 cookie |
| 6 | GET | `/api/items` | CRUD | 列出工作项（需登录） |
| 7 | POST | `/api/items` | CRUD | 新建 → 广播 `created` |
| 8 | PUT | `/api/items/{id}` | CRUD | 更新 → 广播 `updated` |
| 9 | DELETE | `/api/items/{id}` | CRUD | 删除 → 广播 `deleted` |
| 10 | POST | `/api/upload` | 上传 | 接收 multipart 文件，记录名+大小 |
| 11 | GET | `/api/uploads` | 上传 | 列出已上传文件 |
| 12 | POST | `/api/reset` | 运维 | 重置 ITEMS/UPLOADS 到初始态（**测试隔离用**） |
| 13 | GET | `/api/stream` | SSE | 长连接，持续推送工作项变更 |
| 14 | GET | `/api/health` | 运维 | 健康检查，含当前 SSE 连接数 |

### 4. SSE 推送机制（重点，也是稳定性测试对象）
- 每个浏览器连 `/api/stream` → 服务器为它建一个 `asyncio.Queue`，加入 `subscribers`。
- 任何增删改 → `_broadcast()` 往每个队列塞事件 → 各连接实时收到。
- 无数据时每 15s 发一次 keep-alive 心跳，防连接被掐。
- **连接断开时从 `subscribers` 摘除队列** —— 若不摘就是连接泄漏（稳定性测试要抓的正是这里，观察 `/health` 的 `sse_connections` 是否回落到 0）。

---

## 五、前端结构

### login.html
| 部分 | 说明 | data-testid |
|------|------|-------------|
| 用户名/密码输入 | 表单字段 | `login-username` / `login-password` |
| 登录按钮 | 点击→ fetch `/api/login` | `login-submit` |
| 错误提示 | 登录失败显示文案 | `login-error` |
| JS 逻辑 | 成功→ `location.href='/dashboard'`；失败→显示 error | — |

### dashboard.html
| 部分 | 说明 | data-testid |
|------|------|-------------|
| SSE 状态徽标 | 连上显示「实时已连接」 | `sse-status` |
| 新建区 | 输入标题 + 添加 | `new-item-title` / `add-item` |
| 上传区 | 选文件 + 上传 + 结果 | `file-input` / `upload-submit` / `upload-result` |
| 工作项列表 | 每项含标题/状态/负责人/删除 | `item-list` / `item-{id}` / `delete-{id}` |
| 删除确认弹窗 | 默认隐藏，点删除弹出 | `confirm-modal` / `confirm-delete` / `cancel-delete` |
| JS 逻辑 | `EventSource` 订阅 SSE，收到事件重新拉列表 | — |

**前端设计要点**：新建/删除后**不手动刷新列表**，而是等 SSE 把变更推回来再刷新 —— 这样能真实验证「实时推送链路是否打通」。

---

## 六、三条关键数据流（按流程理解）

**① 登录流程**
```
输账号密码 → 点登录 → POST /api/login → 校验通过 → 种 tp_session cookie
→ 前端 location 跳 /dashboard → 后端校验 cookie 通过 → 返回看板页
```

**② 实时推送流程（SSE）**
```
进看板 → EventSource 连 /api/stream → 后端建队列、推 hello
→ 徽标变「实时已连接」
→ (任意端)新建工作项 POST /api/items → _broadcast 推 created
→ 所有连接收到 → 各自重新拉 /api/items → 列表自动刷新（无需手动刷新）
```

**③ 删除确认流程**
```
点某项「删除」→ 弹出 confirm-modal（此时未删）
   ├─ 点「取消」→ 关弹窗，数据不变
   └─ 点「删除」→ DELETE /api/items/{id} → 广播 deleted → SSE 刷新，项消失
```

---

## 七、测试点 → 模块映射（16 个）

| # | 测试点 | 涉及模块/元素 |
|---|--------|--------------|
| 1 | 登录成功 | login.html + `/api/login` |
| 2 | 登录失败 | `login-error` |
| 3 | 表单校验 | 空值提交 |
| 4 | 未登录拦截 | `/dashboard` 守卫 |
| 5 | 看板加载 | `/api/items` + 列表渲染 |
| 6 | 新建工作项 | `add-item` + POST items |
| 7 | 删除(带确认弹窗) | `confirm-modal` 交互 |
| 8 | 文件上传 | `file-input` + `/api/upload` |
| 9 | 登出 | `/api/logout` |
| 10 | SSE 连接建立 | `sse-status` |
| 11 | 实时新增 | `/api/stream` 推送 |
| 12 | 多端同步 | 两个 context |
| 13 | 弱网测试 | Playwright 拦截 + 登录/加载 |
| 14 | 兼容性 | 多浏览器 |
| 15 | 稳定性(SSE) | `/api/health` 的 `sse_connections` |
| 16 | 性能(体感) | 首屏/列表加载耗时 |

> 详细的场景描述见 [README.md](README.md) 第六节。

---

## 八、如何运行

```bash
cd teampilot-lite
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m uvicorn app:app --reload --port 8000
```
打开 http://localhost:8000 ，账号 `admin` / `admin123`。
