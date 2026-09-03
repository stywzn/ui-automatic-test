# conftest.py —— 放在 ui-tests 根目录（pytest 自动发现），放跨用例共享的 fixture。
# 副作用：本文件所在目录被加入导入路径，于是用例能 `from pages... / from config...`。
import sqlite3

import pytest

from config.settings import BASE_URL, DB_PATH, PASSWORD, USERNAME
from pages.login_page import LoginPage


@pytest.fixture(scope="session")
def api_request(playwright):
    ctx = playwright.request.new_context(base_url=BASE_URL)
    yield ctx
    ctx.dispose()


@pytest.fixture(autouse=True)
def reset_data(api_request):
    """每个用例前重置 SUT 数据库到初始态 —— 测试隔离。"""
    api_request.post("/api/reset")
    yield


@pytest.fixture
def logged_in_page(page):
    login = LoginPage(page)
    login.open()
    login.login(USERNAME, PASSWORD)
    page.wait_for_url(f"{BASE_URL}/dashboard")  # 等登录跳转到看板
    return page


@pytest.fixture
def db():
    """直连 SUT 的 SQLite 数据库，用于“数据库断言”。用完自动关。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 查询结果按列名取，像 dict
    yield conn
    conn.close()
