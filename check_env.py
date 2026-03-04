#!/usr/bin/env python3
"""检查环境变量是否正确加载"""
import os
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

print("环境变量检查：")
print(f"ZHAOCAI_ADMIN_TOKEN = {os.getenv('ZHAOCAI_ADMIN_TOKEN', '未设置')}")
print(f"ZHAOCAI_PORT = {os.getenv('ZHAOCAI_PORT', '未设置')}")
