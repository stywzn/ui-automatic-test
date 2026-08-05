# tests/test_dashboard.py —— 看板功能测试（CRUD / 上传 / 登出）
from playwright.sync_api import expect

from config.settings import BASE_URL
from pages.dashboard_page import DashboardPage


def test_dashboard_loads(logged_in_page):
    dashboard = DashboardPage(logged_in_page)
    expect(dashboard.items()).to_have_count(3)


def test_add_item(logged_in_page):
    dashboard = DashboardPage(logged_in_page)
    dashboard.add_item("write automatic test-case")
    expect(dashboard.items()).to_have_count(4)


def test_delete_cancel(logged_in_page):
    dashboard = DashboardPage(logged_in_page)
    dashboard.click_delete(1)
    expect(dashboard.modal()).to_be_visible()
    dashboard.cancel_delete()
    expect(dashboard.items()).to_have_count(3)


def test_delete_confirm(logged_in_page):
    dashboard = DashboardPage(logged_in_page)
    dashboard.click_delete(1)
    dashboard.confirm_delete()
    expect(dashboard.items()).to_have_count(2)


def test_upload_file(logged_in_page, tmp_path):
    dashboard = DashboardPage(logged_in_page)
    f = tmp_path / "sample.txt"
    f.write_text("hello upload")

    dashboard.upload_file(str(f))
    expect(dashboard.upload_result()).to_contain_text("sample.txt")


def test_logout(logged_in_page):
    dashboard = DashboardPage(logged_in_page)
    dashboard.logout()
    expect(logged_in_page).to_have_url(f"{BASE_URL}/login")
