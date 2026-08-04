# conftest.py —— 放在 ui-tests 根目录（pytest 会自动发现它）
#
# 作用①（现在就用到）：pytest 会把本文件所在目录加入导入路径，
#   于是 tests/ 里的用例才能 `from pages.login_page import ...` / `from config.settings import ...`
#
# 作用②（以后加）：放跨用例共享的 fixture，比如
#   - 每个用例前调 /api/reset 重置数据（测试隔离）
#   - 登录态复用（storage_state）
#
# 现在先空着即可。
import pytest

from pages.login_page import LoginPage
from config.settings import USERNAME, PASSWORD, BASE_URL


@pytest.fixture(autouse=True)
def reset_data(page):
    page.request.post(f"{BASE_URL}/api/reset")
    yield


@pytest.fixture
def logged_in_page(page):
    login = LoginPage(page)
    login.open()
    login.login(USERNAME, PASSWORD)
    return page
