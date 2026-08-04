# config/settings.py —— 环境配置：集中放网址和账号，用例里不硬编码

BASE_URL = "http://localhost:8000"  # SUT 地址（uvicorn --port 8000，注意结尾不要 /）
USERNAME = "admin"  # 登录账号
PASSWORD = "admin123"  # 登录密码
