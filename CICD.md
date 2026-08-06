# CI/CD 详解（本项目实践：GitHub Actions + GitLab CI + Jenkins）

> 本项目提供三套等价 CI 配置，都是 **pipeline as code**（流水线写成代码、放进仓库）：
> - GitHub Actions：[.github/workflows/ui-tests.yml](.github/workflows/ui-tests.yml)
> - GitLab CI：[.gitlab-ci.yml](.gitlab-ci.yml)
> - Jenkins：[Jenkinsfile](Jenkinsfile)

---

## 一、CI/CD 是什么，为什么要（先讲清概念）

- **CI（Continuous Integration，持续集成）**：每次代码提交/合并，**自动**拉代码 → 装环境 → 构建 → 跑测试 → 出报告。目标是**尽早发现问题**，别等上线才炸。
- **CD（Continuous Delivery/Deployment，持续交付/部署）**：CI 通过后，**自动**把产物部署到测试/预发/生产环境。交付=部署到"可发布"状态；部署=直接上生产。
- **对测试的意义**：自动化测试**只有接进 CI 才有真正价值**——每次改动自动回归，而不是靠人记得手动跑。这也是"测试左移/自动化"的落地点。

**一句话**：CI/CD = 把"拉码→构建→测试→部署"这条链**自动化 + 代码化**，提交就触发。

---

## 二、本项目的通用流水线流程（三套一致）

```
触发(push / PR)
  → ① 拉代码(checkout)
  → ② 装 Python + 依赖(被测系统 + 测试)
  → ③ 装浏览器(playwright install chrome)
  → ④ 后台起被测系统(uvicorn) + 轮询 /api/health 等就绪
  → ⑤ 跑 pytest(19 用例)
  → ⑥ 生成 Allure + HTML 报告，作为产物(artifact)上传，失败也传
```

**三个关键设计点（面试必讲，体现你懂 CI 不只是抄配置）**：
1. **④ 起 SUT + 等就绪**：CI 机器上**没人手动起服务**，必须脚本后台起 uvicorn，再 `curl /api/health` **轮询等它真就绪**——否则服务没起好就跑测试，全连接失败。
2. **⑥ 失败也出报告**（`if: always()` / `post{ always }` / `when: always`）：报告**最有用的场景恰恰是失败时**，不能因为测试挂了就不出报告。
3. **产物 artifact**：CI 机器跑完就销毁，报告必须**上传成 artifact**才能下载查看，不能留在机器上。

---

## 三、GitHub Actions（详解）

**文件位置**：`.github/workflows/*.yml`（GitHub 自动发现）。

**逐段讲**：
```yaml
name: UI Tests
on:                          # 触发条件
  push: {branches: [master, main]}   # 推主分支触发
  pull_request:              # 提 PR 也触发
jobs:
  e2e:                       # 一个 job
    runs-on: ubuntu-latest   # 在 GitHub 提供的 Ubuntu 云机上跑
    steps:                   # 顺序执行的步骤
      - uses: actions/checkout@v4          # 复用官方 action：拉代码
      - uses: actions/setup-python@v5      # 复用官方 action：装 Python
        with: {python-version: "3.12"}
      - run: pip install -r ...            # run: 执行 shell 命令
      - run: python -m playwright install --with-deps chrome
      - run: |                             # 多行 shell：起 SUT + 等就绪
          cd teampilot-lite
          python -m uvicorn app:app --port 8000 &
          for i in $(seq 1 20); do curl -sf localhost:8000/api/health && break || sleep 1; done
      - run: cd ui-tests && pytest
      - uses: actions/upload-artifact@v4   # 复用官方 action：上传报告
        if: always()
        with: {name: test-reports, path: ...}
```
**核心概念**：`on`(触发)、`jobs`(任务)、`runs-on`(运行环境)、`steps`(步骤)、`uses`(复用现成 action)、`run`(跑命令)、`artifact`(产物)。
**特点**：**云托管、零运维、开箱即用**，和 GitHub 深度集成。免费额度够个人项目。

---

## 四、GitLab CI（详解）

**文件位置**：仓库根目录 `.gitlab-ci.yml`（GitLab 自动读）。

**逐段讲**：
```yaml
stages:                      # 定义阶段顺序
  - test
ui-tests:                    # 一个 job（名字随意）
  stage: test                # 属于哪个 stage
  image: python:3.12         # 用哪个 Docker 镜像当执行环境 ← GitLab CI 特色
  before_script:             # 正式跑之前的准备（装依赖）
    - pip install -r ...
    - python -m playwright install --with-deps chrome
  script:                    # 主命令（起 SUT + 跑测试）
    - cd teampilot-lite && (python -m uvicorn app:app --port 8000 &) && cd ..
    - for i in ...; do curl -sf localhost:8000/api/health && break || sleep 1; done
    - cd ui-tests && pytest
  artifacts:                 # 产物
    when: always
    paths: [ui-tests/reports/report.html, ui-tests/allure-results/]
```
**核心概念**：`stages`(阶段) → `job`(任务) → `script`(命令)；`image`(用容器镜像当环境)；`before_script`(前置)；`artifacts`(产物)。
**Runner**：GitLab CI 由 **GitLab Runner** 执行——可以用 GitLab 官方共享 Runner，也可以自己注册一台（企业内网常这么干）。
**特点**：**内置在 GitLab 里**，配置就一个文件，企业（尤其国内自建 GitLab 的）超常用。

---

## 五、Jenkins（详解）

**是什么**：开源的**自动化服务器**，你**自己部署一台**，它执行流水线。老牌、插件海量、**国内公司最常见**。

**核心概念**：
| 概念 | 意思 |
|------|------|
| Pipeline | 一整条流水线 |
| Stage | 阶段（Checkout / Install / Test…） |
| Step | 阶段里的一步（`sh '...'`） |
| **Jenkinsfile** | Groovy 写的流水线，放仓库 = pipeline as code |
| Agent / Node | 真正执行的机器（master 调度、agent 干活） |
| 插件 | Allure 报告、通知、部署等（Jenkins 的灵魂） |
| Webhook | git push 事件自动触发 |

**Jenkinsfile 逐段讲**（见 [Jenkinsfile](Jenkinsfile)）：
```groovy
pipeline {
  agent any                          // 在任意可用节点上跑
  stages {
    stage('Checkout'){ steps{ checkout scm } }        // 拉代码
    stage('Install deps'){ steps{ sh 'pip install ...' } }
    stage('Start SUT'){ steps{ sh 'nohup uvicorn ... &; 轮询 health' } }
    stage('Run UI tests'){ steps{ sh 'cd ui-tests && pytest' } }
  }
  post { always {                    // 收尾：不管成败都做
    allure results: [[path: 'ui-tests/allure-results']]   // 需 Allure 插件
    archiveArtifacts 'ui-tests/reports/report.html'
    sh 'pkill -f uvicorn || true'    // 杀掉 SUT
  } }
}
```

**怎么真正跑起来（详细步骤）**：
1. **起 Jenkins**（Java 应用，用 Docker 最快）：
   ```bash
   docker run -d --name jenkins -p 8080:8080 -p 50000:50000 -v jenkins_home:/var/jenkins_home jenkins/jenkins:lts
   ```
2. **拿初始管理员密码**：
   ```bash
   docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
3. 浏览器开 **http://localhost:8080** → 粘密码解锁 → 选"安装推荐插件"。
4. **额外装 Allure 插件**：Manage Jenkins → Plugins → 搜 Allure → 装。
5. **新建任务**：New Item → 选 **Pipeline** → 配置里选 "Pipeline script from SCM" → 填你的 Git 仓库地址 → 它自动读根目录的 `Jenkinsfile`。
6. **Build Now** → 看每个 stage 跑、看 Allure 报告。

> ⚠️ **一个真实坑（要知道）**：`jenkins/jenkins:lts` 镜像里**只有 Java，没有 python/node/chrome**，所以 Jenkinsfile 里的 `pip install` 会失败。生产做法是让流水线跑在**带这些工具的 agent** 里，比如：
> ```groovy
> agent { docker { image 'python:3.12' } }   // 在 python 容器里执行
> ```
> 需要 Jenkins 装 Docker 插件 + 能访问 Docker。**这也是面试点**：Jenkins 的 agent 要自己准备好构建工具，不像 GitLab CI 直接 `image:` 指定。

**特点**：**自建、可控、插件海量、企业内网友好**，但**要运维**（你得养着这台服务器）。

---

## 六、三者对比（面试对比表）

| 维度 | GitHub Actions | GitLab CI | Jenkins |
|------|----------------|-----------|---------|
| 形态 | 云托管，零运维 | 内置 GitLab，Runner 可自建 | 完全自建，要运维 |
| 配置文件 | `.github/workflows/*.yml` | `.gitlab-ci.yml` | `Jenkinsfile`(Groovy) |
| 执行环境 | runs-on 指定 | `image:` 指定容器 | agent 自备工具 |
| 触发 | push/PR/定时/手动 | push/MR/定时/手动 | webhook/定时/手动 |
| 适合 | GitHub 项目、开源 | 自建 GitLab 的企业 | 企业内网、复杂流水线、国内多 |
| 生态 | Marketplace | 内置 + 模板 | **插件海量** |

**一句话总结**：三者**理念完全一致**（pipeline as code，拉码→构建→测试→部署）；差别在**托管 vs 自建、配置语法、生态**。**会一个，另两个照着迁移很快。**

---

## 七、面试怎么讲

- **被问"你 CI 怎么做的"**：先讲**通用流程**（第二节那 6 步 + 3 个设计点：等 SUT 就绪、失败也出报告、产物 artifact），再说"我三套都写了（Actions/GitLab CI/Jenkins），理念一致"。
- **被问"Jenkins 和 GitHub Actions 区别"**：托管 vs 自建、YAML vs Groovy、agent 自备工具 vs image 指定——见第六节表。
- **被问"CI 上怎么跑浏览器测试"**：CI 是远程机器不是本地 Chrome；装 `playwright install --with-deps chrome` 后无头跑；本地才用 `--browser-channel chrome` 绕安全软件。
- **体现深度的点**：Jenkins agent 缺 python 要用 Docker agent、GitLab Runner 概念、失败也出报告、等服务就绪——这些细节能讲，就不是"抄了个 YAML"。
