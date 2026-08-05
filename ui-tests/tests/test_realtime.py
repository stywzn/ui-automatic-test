# tests/test_realtime.py —— SSE 实时推送（连接建立 / 实时新增 / 多端同步）
from playwright.sync_api import expect

from config.settings import BASE_URL, PASSWORD, USERNAME
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


def test_sse_status(logged_in_page):
    dashboard = DashboardPage(logged_in_page)
    expect(dashboard.sse_status()).to_contain_text("实时已连接")


def test_realtime_add_via_sse(logged_in_page):
    dashboard = DashboardPage(logged_in_page)
    expect(dashboard.items()).to_have_count(3)

    # 从后台 API 直接新建（浏览器之外的变更），页面不刷新应自动收到
    logged_in_page.request.post(
        f"{BASE_URL}/api/items", data={"title": "added via sse"}
    )
    expect(dashboard.items()).to_have_count(4)


def test_multi_client_sync(browser):
    # 两个独立上下文 = 两个“设备/用户”
    ctx_a = browser.new_context()
    ctx_b = browser.new_context()
    page_a = ctx_a.new_page()
    page_b = ctx_b.new_page()

    for p in (page_a, page_b):
        login = LoginPage(p)
        login.open()
        login.login(USERNAME, PASSWORD)

    dash_a = DashboardPage(page_a)
    dash_b = DashboardPage(page_b)

    expect(dash_b.items()).to_have_count(3)
    dash_a.add_item("A端新建")
    expect(dash_b.items()).to_have_count(4)  # B 端不操作，SSE 自动收到

    ctx_a.close()
    ctx_b.close()
