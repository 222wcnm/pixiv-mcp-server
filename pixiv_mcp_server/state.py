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
        
        # 下载任务状态跟踪
        self.download_tasks = {}
        
        # 动图输出格式 (gif, webp)
        self.ugoira_format = "webp"

        # 并发控制器
        self.download_semaphore = asyncio.Semaphore(8)  # 网络I/O并发
        self.cpu_bound_semaphore = asyncio.Semaphore(os.cpu_count() or 2) # CPU密集型任务并发

        # 代理读取：同时支持大小写与 ALL_PROXY/NO_PROXY
        proxy = (
            os.getenv('HTTPS_PROXY') or
            os.getenv('https_proxy') or
            os.getenv('HTTP_PROXY') or
            os.getenv('http_proxy') or
            os.getenv('ALL_PROXY') or
            os.getenv('all_proxy')
        )
        if proxy:
            self.api.set_proxy(proxy)
            try:
                # 脱敏打印，仅显示协议与主机，不显示认证信息
                from urllib.parse import urlparse
                parsed = urlparse(proxy)
                masked = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or ''}"
            except Exception:
                masked = "<masked>"
            logger.info(f"已配置代理: {masked}")

# 创建全局唯一的 state 实例
state = PixivState()
