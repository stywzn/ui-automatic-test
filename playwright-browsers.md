# Playwright 浏览器内核 —— 手动安装位置记录

> 因本机命令行下载 Playwright 浏览器不稳定，改为**浏览器手动下载 zip + 手动解压**到 Playwright 要求的目录。
> 本文件记录每个包解压到哪里，便于日后排查或在别的机器复现。
> 对应版本：playwright 1.61.0（chromium build v1228）。

## 一、解压位置清单

所有内核放在用户目录（**不需要管理员权限**）：
`C:\Users\jhony\AppData\Local\ms-playwright\`

| 下载的 zip | 解压到的目录 | 关键可执行文件 | 用途 |
|---|---|---|---|
| `chrome-win64.zip` | `ms-playwright\chromium-1228\` | `chrome-win64\chrome.exe` | 有头模式(--headed) |
| `chrome-headless-shell-win64.zip` | `ms-playwright\chromium_headless_shell-1228\` | `chrome-headless-shell-win64\chrome-headless-shell.exe` | 无头模式(默认) |
| `ffmpeg-win64.zip` | `ms-playwright\ffmpeg-1011\` | `ffmpeg-win64.exe` | 录制视频 |
| `winldd-win64.zip` | `ms-playwright\winldd-1007\` | `PrintDeps.exe` | 依赖检查 |

> 每个目录里额外建了一个空的 `INSTALLATION_COMPLETE` 文件 —— Playwright 靠它判断"已装完"，缺了会以为没装又去重新下载。

## 二、验证状态

- ✅ **无头模式（headless）已验证可启动** Chromium 149.0.7827.55。
  - `pytest-playwright` 默认就是无头，所以**跑测试的环境已经可用**。
- ⚠️ **有头模式（--headed）在本机启动失败**（无头不受影响）。
  - 现象：启动完整 `chrome.exe` 报 `spawn UNKNOWN` / SxS 错误 14001。
  - 已排查确认**不是**文件缺失/损坏，也**不是** VC++ 缺失：
    - 4 个内核放置正确、`chrome.dll`(272MB)与 `149.0.7827.55.manifest` 均完整无损。
    - VC++ 运行库已安装且是更新版(14.51.36247)，装官方 redist 反被拒绝(不能降级)。
  - 真实原因：Windows 事件日志显示 `Activation context generation failed ... Dependent Assembly 149.0.7827.55 could not be found` ——
    系统 SxS 机制无法解析 Chrome 自己的私有组件(文件都在、manifest 有效却报找不到)。属本机 SxS 层面异常，疑与异常新的 14.51 预览版运行时有关。
  - 结论：**根治需系统层面处理(且多半要管理员)，性价比低。有头非核心功能，暂不处理。**
- ✅ **替代方案（无需有头也能"看"测试）**：ffmpeg 已装 → 录制测试视频；或用 Playwright trace viewer(时间轴+每步截图)。这也是 CI 里的标准做法。

## 三、如何重新验证

在 `ui-tests` 目录用其虚拟环境运行：

```bash
./.venv/Scripts/python.exe -c "from playwright.sync_api import sync_playwright;\
import contextlib;\
p=sync_playwright().start();\
b=p.chromium.launch();\
print('无头 OK', b.version); b.close(); p.stop()"
```

能打印版本号即说明内核放置正确、环境可用。

## 四、镜像备忘（网络慢时用）

- pip：`-i https://mirrors.aliyun.com/pypi/simple/`
- Playwright 浏览器：`PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright`
- 手动下载 4 个包的直链前缀：`https://cdn.npmmirror.com/binaries/playwright/builds/...`（具体链接见 `playwright install chromium --dry-run` 输出）。
