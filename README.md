# UI 自动化测试框架（Playwright + Python）

一套基于 **Playwright + pytest + POM** 的 UI 自动化测试框架，被测系统是自建的团队看板 `teampilot-lite`。
覆盖**功能 / 实时(SSE) / 数据库断言 / 专项(弱网·稳定性·性能·兼容性)**，共 19 个用例，接入 CI。

## 技术栈

| 层 | 技术 |
|----|------|
| 自动化 | Playwright（sync API）+ pytest + pytest-playwright |
| 设计 | POM（Page Object Model）分层 |
| 被测系统(SUT) | Python + FastAPI + SQLite（登录 / 看板 CRUD / SSE 实时推送 / 上传） |
| 工程化 | black（格式化）· ruff（linter）· pytest-html（报告）· GitHub Actions（CI）· git |

## 项目结构

```
.
├── teampilot-lite/            被测系统 SUT（FastAPI + SQLite）
│   ├── app.py                 后端：登录/CRUD/上传/SSE/reset/health
│   ├── static/                登录页、看板页（元素带 data-testid）
│   ├── README.md              业务背景 + 接口 + 定位表 + 测试点
│   └── ARCHITECTURE.md        架构与模块说明
├── ui-tests/                  测试框架（本项目核心）
│   ├── config/settings.py     配置：URL / 账号 / 数据库路径
│   ├── conftest.py            fixture：reset_data(隔离) / logged_in_page / db(数据库断言)
│   ├── pages/                 POM 页面对象
│   │   ├── base_page.py        公共操作基类
│   │   ├── login_page.py
│   │   └── dashboard_page.py
│   ├── tests/                 用例（按关注点拆分）
│   │   ├── test_login.py       登录 + 跨浏览器兼容
│   │   ├── test_dashboard.py   看板功能：CRUD / 上传 / 登出
│   │   ├── test_realtime.py    SSE：连接 / 实时新增 / 多端同步
│   │   ├── test_specialized.py 专项：稳定性 / 弱网 / 性能
│   │   └── test_db.py          数据库断言
│   ├── pytest.ini             配置（系统 Chrome + HTML 报告）
│   └── requirements.txt
├── .github/workflows/ui-tests.yml   CI：自动装环境、起 SUT、跑测试、传报告
└── README.md
```

## 如何运行

```bash
# 1) 起被测系统
cd teampilot-lite
python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m uvicorn app:app --port 8000

# 2) 另开一个终端，跑测试
cd ui-tests
python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m playwright install chromium
./.venv/Scripts/python.exe -m pytest          # 报告生成在 reports/report.html
```

## 测试覆盖度（16 个测试点 / 19 个用例）

| 类别 | 测试点 | 文件 |
|------|--------|------|
| **功能** | 登录成功/失败/空值/未登录拦截、看板加载、新建、删除(带弹窗)、上传、登出 | test_login.py / test_dashboard.py |
| **实时(SSE)** | SSE 连接建立、实时新增(外部变更自动同步)、多端同步 | test_realtime.py |
| **数据库** | 数据库断言（直连 SQLite 验证数据落库） | test_db.py |
| **专项 ★** | **弱网**(网络限速) · **稳定性**(SSE 连接泄漏) · **性能**(首屏耗时) · **兼容性**(Chrome + Edge) | test_specialized.py / test_login.py |

## 亮点

- **不止点点点**：覆盖 SSE 实时推送、多端同步等**异步场景**，以及弱网/稳定性/性能/兼容**四类专项**。
- **三层校验**：UI（`expect` 自动等待）+ 接口（`page.request`）+ **数据库**（直连 SQLite 断言）。
- **抗 flaky**：Playwright 自动等待 + 数据隔离 fixture + 竞态修复（`wait_for_url` 等确定状态）。
- **工程化闭环**：POM 分层 · black/ruff · HTML 报告 · GitHub Actions CI。
