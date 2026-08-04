from pages.base_page import BasePage


class LoginPage(BasePage):

    USERNAME = "login-username"
    PASSWORD = "login-password"
    SUBMIT = "login-submit"
    ERROR = "login-error"
    PATH = "/login"

    def open(self):
        self.goto(self.PATH)

    def login(self, username: str, password: str):
        self.fill(self.USERNAME, username)
        self.fill(self.PASSWORD, password)
        self.click(self.SUBMIT)

    def error_message(self):
        return self.text_of(self.ERROR)
