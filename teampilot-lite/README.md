# teampilot-lite —— UI 自动化练习用被测系统 (SUT)

## 一、背景 / 业务场景（面试要能讲清楚）

`teampilot-lite` 是一个**精简版团队协作看板**,原型来自真实项目 team-pilot(一个内部团队工作台:管理需求 / BUG / PR，并用 SSE 做实时更新)。

为了聚焦 **UI 自动化测试**，这里把它裁剪成最小可用形态，保留了一个真实 Web 应用最典型的三段结构：

1. **认证** —— 登录 / 登出 / 未登录拦截。
2. **业务主页面（看板）** —— 工作项的增、删、查（CRUD）。
3. **实时能力（SSE）** —— 服务器主动把工作项变更推给浏览器，页面无需刷新即时更新。

> 为什么用它当 SUT：它有真实业务语义（团队看板），覆盖了 UI 自动化最常考的场景（表单、列表、CRUD、实时推送、鉴权跳转），又足够小、零外部依赖、可一键重置数据 —— 非常适合练框架、讲设计。

## 二、技术栈

- 后端：Python + FastAPI（异步，原生支持 SSE）
- 存储：纯内存（进程重启即重置；也提供 `POST /api/reset` 手动重置，方便测试隔离）
- 前端：原生 HTML/JS（无框架），**所有可交互元素都带 `data-testid`**

## 三、如何运行

```bash
cd teampilot-lite
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m uvicorn app:app --reload --port 8000
```

打开 http://localhost:8000 ，登录账号：`admin` / `admin123`

## 四、接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/login` | 登录页 |
| GET | `/dashboard` | 看板页（未登录自动跳回 `/login`） |
| POST | `/api/login` | 登录，成功后种 `tp_session` cookie |
| POST | `/api/logout` | 登出 |
| GET | `/api/items` | 工作项列表（需登录） |
| POST | `/api/items` | 新建工作项 |
| PUT | `/api/items/{id}` | 更新工作项 |
| DELETE | `/api/items/{id}` | 删除工作项 |
| POST | `/api/upload` | 上传文件（multipart），返回文件名+大小 |
| GET | `/api/uploads` | 已上传文件列表 |
| GET | `/api/stream` | **SSE** 事件流，推送 created/updated/deleted |
| POST | `/api/reset` | 重置数据到初始状态（测试隔离用） |
| GET | `/api/health` | 健康检查，含当前 SSE 连接数 |

## 五、元素定位表（写 Page Object 用）

> 原则：优先用 `data-testid`，它专为测试而设、不随样式/文案变化，比 xpath/文本稳定得多。

**登录页 `/login`**

| 元素 | data-testid |
|------|-------------|
| 用户名输入框 | `login-username` |
| 密码输入框 | `login-password` |
| 登录按钮 | `login-submit` |
| 错误提示 | `login-error` |

**看板页 `/dashboard`**

| 元素 | data-testid |
|------|-------------|
| SSE 连接状态徽标 | `sse-status` |
| 登出按钮 | `logout` |
| 新建标题输入框 | `new-item-title` |
| 添加按钮 | `add-item` |
| 工作项列表 | `item-list` |
| 单个工作项 | `item-{id}` |
| 某项的删除按钮 | `delete-{id}` |
| 选择文件输入 | `file-input` |
| 上传按钮 | `upload-submit` |
| 上传结果文案 | `upload-result` |
| 删除确认弹窗(遮罩) | `confirm-modal` |
| 弹窗提示文案 | `confirm-text` |
| 弹窗-确认删除 | `confirm-delete` |
| 弹窗-取消 | `cancel-delete` |

## 六、UI 可测试点清单（练习目标 = 逐条写成用例）

### A. 功能测试（先做这些，打通框架）
1. **登录成功** —— 正确账号密码 → 跳转 `/dashboard`。
2. **登录失败** —— 错误密码 → 停在登录页 + 显示错误提示文案。
3. **表单校验** —— 空用户名/空密码时的行为。
4. **未登录拦截** —— 直接访问 `/dashboard` → 自动跳回 `/login`（鉴权守卫）。
5. **看板加载** —— 登录后列表渲染出初始 3 个工作项。
6. **新建工作项** —— 输标题、点添加 → 新项出现在列表。
7. **删除工作项（带确认弹窗）** —— 点删除 → **弹出确认框**；点「取消」→ 弹窗关闭、项还在；点「删除」→ 弹窗关闭、项消失。（练**弹窗/模态框**交互）
8. **文件上传** —— 选文件 → 点上传 → `upload-result` 显示文件名和字节数。（练**文件上传**交互）
9. **登出** —— 点登出 → 回登录页，且再访问 `/dashboard` 被拦截。

### B. 实时 / SSE 场景
10. **SSE 连接建立** —— 进看板后状态徽标变为「实时已连接」。
11. **实时新增** —— 用 API 在后台新建一项，**不刷新页面**，该项应自动出现（验证 SSE 推送链路）。
12. **多端同步** —— 开两个浏览器上下文，A 端新建，B 端应自动收到。

### C. 专项测试（框架成型后扩展 —— 对应你学过的那几类）
13. **弱网测试** —— 用 Playwright 的网络拦截/限速，模拟慢网/丢包，验证登录、加载的超时与提示。
14. **兼容性测试** —— 同一套用例在 Chromium / Firefox / WebKit 各跑一遍。
15. **稳定性测试（SSE）** —— 长时间保持 SSE 连接 + 反复开关连接，观察 `/api/health` 里 `sse_connections` 是否回落到 0（不回落 = 连接泄漏）。
16. **性能测试（体感）** —— 测量看板首屏渲染、列表加载耗时（UI 层性能指标）。

> 从 A 一路做到 C，就是一个 UI 自动化框架从「跑通一条」到「覆盖专项」的完整成长路径，也是面试讲「我这框架能力边界」的最好素材。
```
