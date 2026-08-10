# tests/test_specialized.py —— 专项测试（稳定性 / 弱网 / 性能）
import time

from playwright.sync_api import expect

from config.settings import BASE_URL, PASSWORD, USERNAME
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


def test_sse_no_connection_leak(browser):
    """稳定性：反复开关 SSE 连接，服务端连接数应回落（不泄漏）。"""
    probe = browser.new_context().new_page()

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

    ctxs = []
    for _ in range(3):
        c = browser.new_context()
        p = c.new_page()
        lp = LoginPage(p)
        lp.open()
        lp.login(USERNAME, PASSWORD)
        ctxs.append(c)

    assert wait_until(lambda: sse_count() >= baseline + 3), f"连接没建满: {sse_count()}"

    for c in ctxs:
        c.close()
    assert wait_until(
        lambda: sse_count() <= baseline
    ), f"连接泄漏！未回落: {sse_count()}"


def test_login_under_slow_network(page):
    """弱网：给所有 API 请求加 1s 延迟，验证仍能正常登录加载。"""

    def slow(route):
        time.sleep(1)
        route.continue_()

    page.route("**/api**", slow)

    login = LoginPage(page)
    login.open()
    login.login(USERNAME, PASSWORD)

    expect(page.locator('[data-testid="item-list"]')).to_be_visible()


def test_dashboard_load_performance(logged_in_page):
    """性能（体感）：看板首屏加载耗时应低于阈值。"""
    start = time.monotonic()
    logged_in_page.reload()
    dashboard = DashboardPage(logged_in_page)
    expect(dashboard.items()).to_have_count(3)

    elapsed = time.monotonic() - start
    assert elapsed < 3, f"看板首屏太慢: {elapsed:.2f}s"
