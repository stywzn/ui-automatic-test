# CI/CD 怎么做（本项目实践）

> 本项目同时提供两套 CI：**GitHub Actions**（[.github/workflows/ui-tests.yml](.github/workflows/ui-tests.yml)）和 **Jenkins**（[Jenkinsfile](Jenkinsfile)）。

## 一、CI/CD 是什么，为什么要

- **CI（持续集成）**：每次提交/PR，自动**拉代码 → 装环境 → 跑测试 → 出报告**。目的：**早发现问题**，别等上线才炸。
- **CD（持续交付/部署）**：CI 通过后，自动把产物**部署**到测试/生产环境。
- 对测试的意义：**自动化测试只有接进 CI 才有真正价值**——每次改动自动回归，而不是靠人记得手动跑。

## 二、本项目的 CI 流程（GitHub Actions 和 Jenkins 一致）

```
触发(push/PR)
  → 拉代码
  → 装 Python + 依赖(SUT + 测试)
  → 装浏览器(playwright install chrome)
  → 起被测系统(后台 uvicorn) + 轮询 health 等就绪   ← 关键：CI 上没人手动起服务
  → 跑 pytest(19 用例)
  → 生成 Allure + HTML 报告，作为产物上传(失败也传)
```

**几个设计要点（面试可讲）**：
- **起 SUT + 等就绪**：`curl health` 轮询，服务没起好就跑测试会连接失败。
- **失败也出报告**（`if: always()` / `post{ always }`）：报告最有用的场景恰恰是失败时。
- **产物 artifact**：报告不留在跑完就销毁的机器上，而是上传下载。

## 三、GitHub Actions 版

见 [.github/workflows/ui-tests.yml](.github/workflows/ui-tests.yml)。核心：`on: [push, pull_request]` 触发，`runs-on: ubuntu-latest`，`steps` 逐步执行，`actions/upload-artifact` 传报告。**云托管、零运维、开箱即用**，适合 GitHub 项目。

## 四、Jenkins 版（国内公司常用，值得会）

见 [Jenkinsfile](Jenkinsfile)。**声明式流水线**：`pipeline { stages { stage('...') { steps { sh '...' } } } }`，`post { always { ... } }` 做收尾（出报告、杀 SUT）。

**怎么真正跑起来**（需要一个 Jenkins 服务器）：
1. 装 Jenkins（Java 应用）：本地可用 Docker 一条命令起——
   ```bash
   docker run -d -p 8080:8080 -v jenkins_home:/var/jenkins/home jenkins/jenkins:lts
   ```
   打开 http://localhost:8080，按提示解锁、装推荐插件。
2. 插件里额外装 **Allure**（Manage Jenkins → Plugins）。
3. 新建 **Pipeline** 任务 → 指定 "Pipeline script from SCM" → 填你的 Git 仓库 → 它会读根目录的 `Jenkinsfile`。
4. 节点上要有 python3/pip/node/curl（或用带这些的 agent 镜像）。
5. Build → 看流水线各 stage 跑、看 Allure 报告。

> 我暂时没起真实 Jenkins 服务（需要单独一台/一个容器长期跑），但 **Jenkinsfile 已写好（pipeline as code）**，有 Jenkins 环境时直接可用。

## 五、GitHub Actions vs Jenkins（面试对比）

| | GitHub Actions | Jenkins |
|---|---|---|
| 形态 | GitHub 云托管，零运维 | 自建服务器，要维护 |
| 配置 | YAML（`.github/workflows`） | Jenkinsfile（Groovy） |
| 适合 | GitHub 项目、开源、中小团队 | 企业内网、复杂流水线、国内公司多 |
| 插件生态 | Marketplace | 海量插件（Allure、通知、部署等） |

**一句话**：两者都是"pipeline as code"，理念一致（拉码→构建→测试→部署）；GitHub Actions 更省心，Jenkins 更可控/企业内网友好。**会一个，另一个照着迁移很快。**
