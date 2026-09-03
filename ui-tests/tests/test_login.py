# tests/test_login.py —— 登录相关用例

from pathlib import Path

import pytest
import yaml
from playwright.sync_api import Page, expect

from config.settings import BASE_URL, PASSWORD, USERNAME
from pages.login_page import LoginPage

# 数据驱动：负向登录用例外置到 data/login_cases.yaml（加一行 = 加一个用例，不动代码）
LOGIN_CASES = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "data" / "login_cases.yaml").read_text(
        encoding="utf-8"
    )
)


def test_login_success(page: Page):
    login = LoginPage(page)
    login.open()
    login.login(USERNAME, PASSWORD)
    expect(page).to_have_url(f"{BASE_URL}/dashboard")
    expect(page.locator('[data-testid="item-list"]')).to_be_visible()


@pytest.mark.parametrize("case", LOGIN_CASES, ids=[c["name"] for c in LOGIN_CASES])
def test_login_negative(page: Page, case):
    """数据驱动负向登录：各种非法输入都应停在登录页 + 显示错误提示。"""
    login = LoginPage(page)
    login.open()
    login.login(case["username"], case["password"])
    expect(page).to_have_url(f"{BASE_URL}/login")
    expect(page.locator('[data-testid="login-error"]')).to_have_text("用户名或密码错误")


def test_dashboard_requires_login(page: Page):
    page.goto(f"{BASE_URL}/dashboard")
    expect(page).to_have_url(f"{BASE_URL}/login")


@pytest.mark.parametrize("channel", ["chrome", "msedge"])
def test_login_cross_browser(playwright, channel):
    with playwright.chromium.launch(channel=channel) as browser:
        page = browser.new_page()
        lp = LoginPage(page)
        lp.open()
        lp.login(USERNAME, PASSWORD)
        expect(page).to_have_url(f"{BASE_URL}/dashboard")
