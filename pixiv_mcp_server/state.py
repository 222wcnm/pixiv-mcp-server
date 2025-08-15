import asyncio
import logging
import os
from typing import Optional, TYPE_CHECKING

from pixivpy3 import AppPixivAPI

from .config import settings

if TYPE_CHECKING:
    from .api_client import PixivAPIClient

logger = logging.getLogger('pixiv-mcp-server')

class PixivState:
    """一个用于封装所有服务器状态的类。"""
    def __init__(self):
        self.api = AppPixivAPI()
        self.api_client: Optional["PixivAPIClient"] = None
        self.is_authenticated = False
        self.user_id: Optional[int] = None
        self.refresh_token: Optional[str] = settings.pixiv_refresh_token
        self.download_path = settings.download_path
        self.filename_template = settings.filename_template
        
        # 预览直链代理配置
        self.preview_proxy_enabled = settings.preview_proxy_enabled
        self.preview_proxy_host = settings.preview_proxy_host
        self.preview_proxy_port = settings.preview_proxy_port
        
        # 下载任务状态跟踪
        self.download_tasks = {}
        
        # 上一次API响应，用于分页
        self.last_response = {}
        self.last_response_key: Optional[str] = None

        # 动图输出格式 (gif, webp)
        self.ugoira_format = settings.ugoira_format

        # 并发控制器
        self.download_semaphore = asyncio.Semaphore(settings.download_semaphore)  # 网络I/O并发
        self.cpu_bound_semaphore = asyncio.Semaphore(settings.cpu_bound_semaphore) # CPU密集型任务并发

        # 代理读取
        if settings.https_proxy:
            self.api.set_proxy(settings.https_proxy)
            try:
                # 脱敏打印，仅显示协议与主机，不显示认证信息
                from urllib.parse import urlparse
                parsed = urlparse(settings.https_proxy)
                masked = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or ''}"
            except Exception:
                masked = "<masked>"
            logger.info(f"已配置代理: {masked}")

# 创建全局唯一的 state 实例
state = PixivState()
