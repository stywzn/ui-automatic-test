from pages.base_page import BasePage


class DashboardPage(BasePage):
    ITEM_LIST = "item-list"
    NEW_TITLE = "new-item-title"
    ADD_BTN = "add-item"

    CONFIRM_MODAL = "confirm-modal"  # 新增：弹窗
    CONFIRM_DELETE = "confirm-delete"  # 新增：弹窗-确认
    CANCEL_DELETE = "cancel-delete"  # 新增：弹窗-取消

    def items(self):
        return self.by_testid(self.ITEM_LIST).locator("li")

    def add_item(self, title: str):
        self.fill(self.NEW_TITLE, title)
        self.click(self.ADD_BTN)

    def click_delete(self, item_id: int):
        self.click(f"delete-{item_id}")

    def confirm_delete(self):
        self.click(self.CONFIRM_DELETE)

    def cancel_delete(self):
        self.click(self.CANCEL_DELETE)

    def modal(self):
        return self.by_testid(self.CONFIRM_MODAL)

    FILE_INPUT = "file-input"  # 新增
    UPLOAD_SUBMIT = "upload-submit"  # 新增
    UPLOAD_RESULT = "upload-result"  # 新增

    def upload_file(self, file_path: str):
        self.by_testid(self.FILE_INPUT).set_input_files(file_path)
        self.click(self.UPLOAD_SUBMIT)

    def upload_result(self):
        return self.by_testid(self.UPLOAD_RESULT)

    LOGOUT = "logout"

    def logout(self):
        self.click(self.LOGOUT)

    SSE_STATUS = "sse-status"

    def sse_status(self):
        return self.by_testid(self.SSE_STATUS)
