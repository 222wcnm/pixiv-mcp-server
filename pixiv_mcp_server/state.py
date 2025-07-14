import asyncio
import logging
import os
from typing import Optional

from pixivpy3 import AppPixivAPI

logger = logging.getLogger('pixiv-mcp-server')

class PixivState:
    """一个用于封装所有服务器状态的类。"""
    def __init__(self):
        self.api = AppPixivAPI()
        self.is_authenticated = False
        self.user_id: Optional[int] = None
        self.refresh_token: Optional[str] = os.getenv('PIXIV_REFRESH_TOKEN')
        self.download_path = os.getenv('DOWNLOAD_PATH', './downloads')
        self.filename_template = os.getenv('FILENAME_TEMPLATE', '{author} - {title}_{id}')
        # 新增：并发下载控制器，限制为5个并发
        self.download_semaphore = asyncio.Semaphore(5)

        proxy = os.getenv('https_proxy')
        if proxy:
            self.api.set_proxy(proxy)
            logger.info(f"已配置代理: {proxy}")

# 创建全局唯一的 state 实例
state = PixivState()
