# UI 自动化测试框架（Playwright + Python）

基于 **Playwright + pytest + POM** 从 0 手搭的分层 **UI 自动化框架**。被测系统(SUT)是配套的团队协作看板 `teampilot-lite`（FastAPI + SQLite，含登录鉴权 / 看板 CRUD / 文件上传 / **SSE 实时推送**）。SUT 的业务代码由 AI 生成——本项目的重点是测试框架，SUT 只是靶子；但**靶子上的可测试性接口是按测试需求设计的**：`/api/reset`（逐用例数据隔离）、`/api/health` 暴露 SSE 连接数（连接泄漏检测）。

覆盖四个层次:**功能 · 实时(SSE) · 数据库断言 · 四大专项(弱网 / 稳定性 / 性能 / 兼容性)**,共 **24 个用例(含 7 条数据驱动负向)**,接入 **三套 CI(GitHub Actions / GitLab CI / Jenkins)** + Allure 报告。

> 重点不是"点点点",而是**框架设计 + 专项测试能力 + 工程化闭环**。

## 亮点

- **POM 分层**:用例层(只写业务意图)/ 页面对象层(定位器+动作)/ 基类(公共操作)三层解耦,页面变更只改一处。用例里零定位器。
- **数据隔离**:`autouse` fixture 每条用例前调 `/api/reset` 重置数据库,用例互不干扰、可乱序/并行的前提。
- **登录态复用**:`logged_in_page` fixture 抽掉重复登录(并修过一个"fixture 返回跳转中的半成品 page"导致的 flaky 竞态,加 `wait_for_url` 根治)。
- **实时测试(最见异步功底)**:用 `page.request` 从**浏览器之外**打接口造数据,验证页面**不刷新自动更新**(SSE 推送链路);多 context 验证多端同步。
- **数据库断言**:`db` fixture 直连 SQLite,UI 操作后查库确认真落库、字段正确——**UI + 接口 + 数据库三层校验**,防"接口成功但数据没存/存错"。
- **四大专项**:弱网(`page.route` 拦截加延迟)/ 稳定性(SSE 连接泄漏:开关连接看 `/api/health` 计数是否回落)/ 性能(首屏耗时,`time.monotonic`)/ 兼容性(`parametrize` 跑 Chrome + Edge)。
- **数据驱动**:登录负向用例(空值 / 错密码 / 类注入 / 超长…)外置到 `data/login_cases.yaml`,**加一行 = 加一个用例,不动代码**。
- **抗 flaky + 失败留证**:操作走 Locator 自动等待、断言走 `expect` 自动重试,不写 `sleep`;**失败时自动存 Playwright trace + 视频 + 截图**(`retain-on-failure`),排查像时光机回放。
- **工程化闭环**:ruff 静态检查卡口(三套 CI 均在装浏览器前拦一道) · Allure + HTML 报告 · **三套 CI** · 全 Docker 化(`docker compose up` 一条命令可复现)。

## 覆盖能力

| 层次 | 模块 | 测什么 |
|------|------|--------|
| 功能 | 登录鉴权 | 正确放行;错密码/空值 → 停留+错误提示;未登录访问 → 跳回登录(鉴权守卫) |
| 功能 | 看板 CRUD | 加载初始项;新建;删除(带确认弹窗:取消不删/确认删) |
| 功能 | 文件上传 | 选文件+上传 → 结果显示文件名和大小 |
| 功能 | 登出 | 登出 → 回登录页且被拦截 |
| 实时 | SSE 连接 | 进看板后状态徽标变"实时已连接" |
| 实时 | 实时推送 | 外部 API 建数据 → 页面不刷新自动出现 |
| 实时 | 多端同步 | A 端建 → B 端(另一 context)自动收到 |
| 数据 | 数据库断言 | UI 新建后直连 SQLite 校验落库 |
| 专项 | 弱网 | 网络拦截加延迟,慢网下仍正常 |
| 专项 | 稳定性 | SSE 连接开关后计数回落到 0(无泄漏) |
| 专项 | 性能 | 看板首屏加载耗时 < 阈值 |
| 专项 | 兼容性 | 同一流程在 Chrome + Edge 各跑一遍 |

## 快速开始（三种跑法，按需选）

```bash
# 方式一(推荐/可复现):全 Docker 化,一条命令,本机零安装
docker compose up --build          # 起 SUT + 跑测试 + 出报告

# 方式二:本机直接跑
cd teampilot-lite && python -m uvicorn app:app --port 8000   # 先起 SUT
cd ui-tests && pytest                                        # 跑测试(默认 --browser-channel chrome)
allure serve allure-results                                  # 看 Allure 报告

# 方式三:CI —— push 到 GitHub 自动触发(.github/workflows/ui-tests.yml)
```

> 详见 [Docker化指南.md](Docker化指南.md) / [CICD.md](CICD.md)。

## 分层架构

```
UI/
├─ teampilot-lite/          被测系统 SUT（FastAPI + SQLite）
│  ├─ app.py                后端:登录/CRUD/上传/SSE/reset/health
│  ├─ static/               login.html · dashboard.html（元素带 data-testid）
│  └─ README.md/ARCHITECTURE.md   业务背景 · 架构 · 16 个测试点
├─ ui-tests/                测试框架（核心）
│  ├─ config/settings.py    环境配置（URL/账号/DB 路径，切环境零改代码）
│  ├─ pages/                POM 页面对象
│  │  ├─ base_page.py       基类:by_testid(get_by_test_id)/goto/click/fill/text_of
│  │  ├─ login_page.py      登录页
│  │  └─ dashboard_page.py  看板页
│  ├─ conftest.py           fixtures:reset_data(隔离) / logged_in_page(登录态) / db(数据库断言)
│  ├─ tests/                按关注点分文件:test_login/test_dashboard/test_realtime/test_specialized/test_db
│  └─ pytest.ini            配置(用系统 Chrome 绕安全软件误杀)
├─ .github/workflows/ · .gitlab-ci.yml · Jenkinsfile   三套 CI
├─ Dockerfile.test · docker-compose.yml                全 Docker 化
└─ 面试文档（见下）
```

## 关键设计（面试可讲）

- **为什么 POM**:分离测试逻辑与定位器,页面改了只改 page object 一处(DRY、可维护)。
- **为什么按关注点拆测试文件**:功能/实时/专项/数据库分开,避免一个文件塞太多(接口测试里文件小=职责清)。
- **为什么用系统 Chrome(`--browser-channel chrome`)**:本机安全软件(火绒)会间歇误杀 Playwright 自带的无签名内核 → 报 `Executable doesn't exist`;改用系统已装的签名 Chrome 绕过。(容器/CI 里没火绒,用自带 chromium。)
- **为什么专项用 SSE 连接泄漏做稳定性**:长连接每个占服务端资源,不释放就是泄漏隐患——开关连接看计数是否回落,是"资源泄漏"这类稳定性问题的通用测法。

## 已知限制 / 风险评估（有依据）

- **不是并行安全的**:所有用例共享一个 SUT + 一个库、全局 reset;要 `pytest -n auto` 需**按 worker 隔离被测环境**(独立端口 SUT + 独立库)。**并行的前提是隔离。**
- **有头模式本机不可用**:完整 chrome.exe 在本机报 SxS 错误(14001);无头正常,用 trace/video 替代看画面。
- **兼容性依赖 branded 浏览器**:Chrome/Edge channel 需系统装好。**容器中排除**该用例(`Dockerfile.test` 里 `-k 'not cross_browser'`,镜像内只有 bundled chromium);**GitHub Actions 中并未排除**——ubuntu runner 预装了 Edge 所以能过,但这是依赖 runner 镜像的隐式前提,换 runner 可能挂。
- **未补**:视觉回归、SUT 自动起停 fixture、`ruff format` 挂 CI(会连 md 里的代码块一起改,暂不挂)。
  > 注:失败自动留 trace/video/截图**已经做了**——`pytest.ini` 里 `--tracing/--video/--screenshot retain-on-failure`。

## 面试准备文档（本目录）

| 文档 | 内容 |
|------|------|
| [项目讲解.md](项目讲解.md) | 怎么从头讲这个项目(30 秒电梯版 + 详细 + 选型 + STAR + 局限) |
| [面试问答.md](面试问答.md) | 33 个详细问答(项目/选型/POM/fixture/flaky/断言/SSE/专项/CI/职业) |
| [OPTIMIZATION-QA.md](OPTIMIZATION-QA.md) | **"项目还能怎么优化"**:已做的 + 下一步(为什么/怎么/效果) |
| [DB-ASSERTION-QA.md](DB-ASSERTION-QA.md) | 数据库断言:为什么/实现/坑/何时没有 |
| [PERFORMANCE-QA.md](PERFORMANCE-QA.md) | 性能:UI 体感 vs 后端压测/完整体系/话术 |
| [MOCK-INTERVIEW-PROMPT.md](MOCK-INTERVIEW-PROMPT.md) | 模拟面试 prompt(贴给 AI 或让我扮演) |
| [简历项目介绍.md](简历项目介绍.md) | 简历 bullet + STAR 详细版 + 一句话版 |
| [面试笔记.md](面试笔记.md) | 36 条技术点 + 调试经验 + 职业发展话术 |
| [CICD.md](CICD.md) | CI/CD 详解:GitHub Actions + GitLab CI + Jenkins 三套 |
| [Docker化指南.md](Docker化指南.md) | 全 Docker 化:一条命令跑测试 + Jenkins docker agent |
| [ui-tests/prerequisites.md](ui-tests/prerequisites.md) | 前置知识:无头/有头 · SxS |
| [teampilot-lite/ARCHITECTURE.md](teampilot-lite/ARCHITECTURE.md) | SUT 架构 · 16 个测试点 |

## 简历写法（可直接改）

**UI 自动化测试框架(个人项目)** — Playwright / Python / pytest / POM / Docker / CI

- 从 0 设计分层(POM)UI 自动化框架,配套 FastAPI+SQLite 被测系统并按测试需求设计其可测试性接口,**24 个用例(含数据驱动负向)**覆盖功能/实时(SSE)/数据库断言/四大专项(弱网·稳定性·性能·兼容性)。
- fixture 做数据隔离 + 登录态复用;断言全走 `expect` 自动等待,基本消除 flaky;修过 fixture 竞态、浏览器被安全软件误杀等疑难。
- **测试资源生命周期治理**:手动管理 browser/context 的用例把 `close()` 写在断言之后,断言一失败清理即被跳过;改用 context manager 与 `contextlib.ExitStack` 接管,异常路径也保证释放。其中连接泄漏检测用例原本会**污染它自己要断言的指标**。
- **修正错误的测量对象**:首屏性能断言原先量的是脚本挂钟时间(含框架轮询开销,受 runner 负载影响),改为读浏览器上报的导航性能指标后,阈值从 3000ms **收紧**到 500ms(实测真实耗时 9ms)。
- 实时测试:从浏览器之外造数据验证 SSE 自动同步;稳定性测试:检测 SSE 长连接泄漏。
- 工程化:ruff 质量卡口(规则集锁在 `ruff.toml`)、Allure 报告、**三套 CI(Actions/GitLab/Jenkins)** + 全 Docker 化一键复现。

## STAR 口述

- **S**:想做能体现测试工程能力的项目,不停在点点点。
- **T**:从 0 搭一套可维护、抗 flaky、覆盖专项的 UI 自动化框架并接入 CI。
- **A**:POM 分层隔离变化;fixture 做隔离+登录态;断言走自动等待;专项覆盖弱网/稳定性/性能/兼容;数据库三层校验;ruff 卡口+Allure+三套 CI+Docker 化。
- **R**:24 用例本地+CI 双绿,flaky 基本消除,能讲透每个设计;踩过的坑(火绒误杀、竞态)都定位到根因。

## 面试可能追问（预演，详见面试问答.md）

- **怎么测实时功能?** 造浏览器之外的变更(API),验证页面不刷新自动更新(SSE)。
- **flaky 怎么排?** "单独过、全量挂"=竞态/状态没 settle;修法是等到确定状态(`wait_for_url`/`expect`),不是 sleep。
- **框架能并行吗?** 当前共享 SUT+全局 reset 不安全;要并行需按 worker 隔离环境——并行的前提是隔离。
- **踩过最大的坑?** 浏览器被火绒间歇误杀,逐层排查(文件在→Defender 关着→查进程发现火绒),改用系统签名 Chrome 绕过——排查到系统层。
