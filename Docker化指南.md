# 全 Docker 化指南：测试 + Jenkins 都跑在容器里

> 目标：**一条命令跑全套测试，不在本机装任何东西**，且和 CI 环境一致、可复现。

## 0. Jenkinsfile 是什么语言？
**Groovy**。Jenkins 声明式流水线（Declarative Pipeline）是基于 Groovy 的 DSL——`pipeline{} / stages{} / steps{} / sh '...'` 都是 Jenkins 定义的语法。**你不用会 Groovy 编程，照结构填即可。**

## 1. 为什么"全用 docker"（面试也能讲）
- **可复现**：依赖全写进镜像，换台机器 `docker compose up` 就能跑，不用手装 python/浏览器。
- **不污染本机**：不在你电脑上堆一堆东西。
- **免下载**：用官方 **Playwright 镜像**（`mcr.microsoft.com/playwright/python`），**自带 python + 浏览器 + 系统依赖**——直接绕开你这几天踩的所有"下载失败/SSL 被掐"的坑。
- **本地=CI**：本地跑的容器和 CI 跑的容器一致，消除"本地能跑、CI 挂"。

## 2. 一条命令跑全套测试（推荐日常这么用）

**涉及文件**（都在 UI 根目录）：`Dockerfile.test`、`docker-compose.yml`、`.dockerignore`

**命令**：
```bash
docker compose up --build
```
它做的事：构建镜像（装依赖）→ 起容器 → 容器内**起 SUT + 跑 24 条测试** → 报告输出到本机 `ui-tests/reports`、`ui-tests/allure-results`。
> 第一次要拉 ~2GB 的 Playwright 镜像，慢；之后有缓存很快。改了代码重跑：`docker compose up --build`。

跑完清理：`docker compose down`。

## 3. Dockerfile.test 逐段讲
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.61.0-noble  # 官方镜像，自带 python+浏览器
WORKDIR /app
RUN apt-get install curl                                # 等 SUT 就绪用
COPY 两个 requirements.txt → RUN pip install            # 先装依赖（层缓存，requirements 不变不重装）
COPY . /app                                             # 再拷代码
CMD 起 uvicorn(后台) → 轮询 health → pytest             # 用自带 chromium，排除兼容性用例
```
**关键点**：先 COPY requirements 再 COPY 代码——这样只改代码时，pip 那层走缓存不重装，构建快。这是 Docker 层缓存的常见优化，面试可讲。

## 4. Jenkins 也用 docker（可复现版，解决之前 ad-hoc 装依赖的坑）

之前往运行中的 Jenkins 容器手动 `docker exec` 装 python/浏览器 → **不可复现**。正解是让流水线跑在 **docker agent** 里：
```groovy
pipeline {
    agent { docker { image 'mcr.microsoft.com/playwright/python:v1.61.0-noble'; args '-u root' } }
    stages {
        stage('Test') {
            steps {
                sh '''
                    pip install -r teampilot-lite/requirements.txt -r ui-tests/requirements.txt
                    cd teampilot-lite && python -m uvicorn app:app --port 8000 &
                    for i in $(seq 1 20); do curl -sf http://localhost:8000/api/health && break || sleep 1; done
                    cd ../ui-tests && python -m pytest -o "addopts=-v" -k "not cross_browser"
                '''
            }
        }
    }
}
```
**每次构建自动起一个自带浏览器的新容器跑**，零手动安装、完全可复现。
> ⚠️ 前提：Jenkins 要能用 docker（装 Docker Pipeline 插件 + 挂 `docker.sock` + Jenkins 容器里有 docker CLI）。在 **Docker Desktop / Windows 上要额外配，较折腾**；在真实 Linux CI 服务器上很顺。所以：**本地图省事直接用第 2 节的 `docker compose`；docker agent 留给真实 CI 服务器。**

## 5. 三种"跑测试"方式对比（面试可讲）
| 方式 | 命令 | 优点 | 何时用 |
|------|------|------|--------|
| 本机直接跑 | `pytest` | 快 | 本机装好了、快速调试（但踩过火绒/下载坑） |
| **docker compose** | `docker compose up --build` | 可复现、免装、免下载 | **日常 / 换机 / 演示（推荐）** |
| Jenkins/CI | push 触发 | 自动、团队共享、看板 | 团队 / 服务器 |

**一句话**：能力从小到大是"本机 → 容器 → CI"；`docker compose` 是性价比最高的那档——**一条命令、可复现、还免了你这几天所有下载的罪**。
