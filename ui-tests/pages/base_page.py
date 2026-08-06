from playwright.sync_api import Page, Locator

from config.settings import BASE_URL


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def by_testid(self, testid: str) -> Locator:
        return self.page.get_by_test_id(testid)

    def goto(self, path: str) -> None:
        self.page.goto(f"{BASE_URL}{path}")

    def click(self, testid: str) -> None:
        self.by_testid(testid).click()

    def fill(self, testid: str, value: str) -> None:
        self.by_testid(testid).fill(value)

    def text_of(self, testid: str) -> str:
        return self.by_testid(testid).inner_text()
