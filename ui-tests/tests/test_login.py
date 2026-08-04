# tests/test_login.py —— 第一条用例：登录成功

from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from config.settings import USERNAME, PASSWORD, BASE_URL


def test_login_success(page: Page):
    login = LoginPage(page)

    login.open()

    login.login(USERNAME, PASSWORD)

    expect(page).to_have_url(f"{BASE_URL}/dashboard")

    expect(page.locator('[data-testid="item-list"]')).to_be_visible()


def test_login_wrong_password(page: Page):
    login = LoginPage(page)
    login.open()

    login.login(USERNAME, "wrong-password")

    expect(page).to_have_url(f"{BASE_URL}/login")

    expect(page.locator('[data-testid="login-error"]')).to_have_text("用户名或密码错误")


def test_dashboard_requires_login(page: Page):
    page.goto(f"{BASE_URL}/dashboard")
    expect(page).to_have_url(f"{BASE_URL}/login")


def test_login_empty(page: Page):
    login = LoginPage(page)
    login.open()
    login.login("", "")
    expect(page.locator('[data-testid="login-error"]')).to_have_text("用户名或密码错误")
