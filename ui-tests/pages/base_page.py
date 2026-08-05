from playwright.sync_api import Page

from config.settings import BASE_URL


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def by_testid(self, testid: str):
        return self.page.locator(f"[data-testid='{testid}']")

    def goto(self, path: str):
        self.page.goto(f"{BASE_URL}{path}")

    def click(self, testid: str):
        self.by_testid(testid).click()

    def fill(self, testid: str, value: str):
        self.by_testid(testid).fill(value)

    def text_of(self, testid: str):
        return self.by_testid(testid).inner_text()
