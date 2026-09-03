# tests/test_specialized.py —— 专项测试（稳定性 / 弱网 / 性能）
import contextlib
import time

from playwright.sync_api import expect

from config.settings import BASE_URL, PASSWORD, USERNAME
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


def test_sse_no_connection_leak(browser):
    """稳定性：反复开关 SSE 连接，服务端连接数应回落（不泄漏）。"""
    with browser.new_context() as probe_ctx:
        probe = probe_ctx.new_page()

        def sse_count():
            return probe.request.get(f"{BASE_URL}/api/health").json()["sse_connections"]

        def wait_until(pred, timeout=8):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                if pred():
                    return True
                time.sleep(0.3)
            return False

        baseline = sse_count()

        with contextlib.ExitStack() as stack:
            for _ in range(3):
                ctx = stack.enter_context(browser.new_context())
                lp = LoginPage(ctx.new_page())
                lp.open()
                lp.login(USERNAME, PASSWORD)

            assert wait_until(lambda: sse_count() >= baseline + 3), (
                f"连接没建满: {sse_count()}"
            )

            stack.close()  # 主动提前解栈全关；异常路径由 with 兜底

            assert wait_until(lambda: sse_count() <= baseline), (
                f"连接泄漏！未回落: {sse_count()}"
            )


def test_login_under_slow_network(page):
    """弱网：用 CDP 给所有网络请求加 1s 延迟，验证仍能正常登录加载。

    为什么不用 page.route + time.sleep：sleep 阻塞的是 Playwright 同步 API 的
    调度器，那 1 秒里整个浏览器交互都停了，不只是被拦的那个请求。
    CDP 的 emulateNetworkConditions 是浏览器层面的真实限速，不阻塞调度器。

    注意：CDP 是 Chromium 专有的。若将来把这条扩到 firefox/webkit，
    new_cdp_session() 会直接抛异常，需要换方案。
    """
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send(
        "Network.emulateNetworkConditions",
        {
            "offline": False,
            "latency": 1000,  # 每个请求 +1000ms
            "downloadThroughput": -1,  # -1 = 不限带宽
            "uploadThroughput": -1,
        },
    )

    login = LoginPage(page)
    login.open()
    login.login(USERNAME, PASSWORD)

    # 弱网下整个登录流程实测约 4.2s，而 expect 默认超时只有 5s —— 太贴边。
    # 显式放宽到 15s：弱网测试关心的是"最终能不能成功"，不是"多快"。
    expect(page.locator('[data-testid="item-list"]')).to_be_visible(timeout=15_000)


def test_dashboard_load_performance(logged_in_page):
    """性能：看板首屏加载耗时应低于阈值。

    断言的是浏览器自己上报的导航性能指标，不是测试脚本的墙上时间。
    原先用 time.monotonic() 会把 Playwright expect() 的轮询重试、IPC 往返
    都算进去 —— 那衡量的是 CI runner 有多忙，不是页面有多快。
    实测页面真实 load 耗时约 9ms，而原阈值是 3000ms，差 300 倍，
    等于这条断言根本没在测性能。
    """
    logged_in_page.reload(wait_until="load")

    dashboard = DashboardPage(logged_in_page)
    expect(dashboard.items()).to_have_count(3)  # 先确认内容真的渲染出来了

    nav = logged_in_page.evaluate(
        "() => performance.getEntriesByType('navigation')[0].toJSON()"
    )
    load_ms = nav["duration"]  # = loadEventEnd - startTime
    dcl_ms = nav["domContentLoadedEventEnd"]

    assert load_ms < 500, f"首屏 load {load_ms:.0f}ms（DCL {dcl_ms:.0f}ms），阈值 500ms"
