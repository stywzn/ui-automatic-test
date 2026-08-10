# tests/test_db.py —— 数据库断言（直连 SQLite 验证数据真的落库）
from playwright.sync_api import expect

from pages.dashboard_page import DashboardPage


def test_add_item_persisted(logged_in_page, db):
    dashboard = DashboardPage(logged_in_page)

    dashboard.add_item("落库检查项目")
    expect(dashboard.items()).to_have_count(4)  # 先等 UI 更新，确保写入已提交

    # 直连数据库确认这条记录真的存在、字段正确
    row = db.execute("SELECT * FROM items WHERE title=?", ("落库检查项目",)).fetchone()
    assert row is not None
    assert row["status"] == "open"
