# config/settings.py —— 环境配置：集中放网址、账号、数据库路径，用例里不硬编码
from pathlib import Path

BASE_URL = "http://localhost:8000"  # SUT 地址（uvicorn --port 8000，结尾不要 /）
USERNAME = "admin"  # 登录账号
PASSWORD = "admin123"  # 登录密码

# SUT 的 SQLite 数据库文件（UI/teampilot-lite/teampilot.db）——测试直连它做“数据库断言”
DB_PATH = Path(__file__).resolve().parents[2] / "teampilot-lite" / "teampilot.db"
