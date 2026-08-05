# tests/test_login.py —— 第一条用例：登录成功

import pytest
from playwright.sync_api import Page, expect

from config.settings import BASE_URL, PASSWORD, USERNAME
from pages.login_page import LoginPage


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


@pytest.mark.parametrize("channel", ["chrome", "msedge"])
def test_login_cross_browser(playwright, channel):
    browser = playwright.chromium.launch(channel=channel)  # 分别启动 Chrome / Edge
    page = browser.new_page()

    lp = LoginPage(page)
    lp.open()
    lp.login(USERNAME, PASSWORD)

    # TODO：断言两个浏览器里都登录成功(跳到 /dashboard)
    expect(page).to_have_url(f"{BASE_URL}/dashboard")

    browser.close()
