import functools
import logging
import re
import subprocess
import sys
from typing import Callable, Optional

from .state import state

logger = logging.getLogger('pixiv-mcp-server')

def check_ffmpeg() -> bool:
    """检测系统是否安装了FFmpeg"""
    try:
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
        
        subprocess.run(['ffmpeg', '-version'], 
                     capture_output=True, check=True, creationflags=creationflags)
        logger.info("FFmpeg 已检测 - GIF 转换功能可用")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("未找到 FFmpeg - GIF 转换功能已禁用")
        return False

def handle_api_error(response: dict) -> Optional[str]:
    """处理来自 Pixiv API 的错误响应并格式化"""
    if not response:
        return "API 响应为空。"
    if 'error' in response:
        error_details = response['error']
        msg = error_details.get('message', '未知错误')
        reason = error_details.get('reason', '')
        return f"Pixiv API 错误: {msg} - {reason}".strip()
    return None

def _sanitize_filename(name: str) -> str:
    """移除文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', '_', name)

def _generate_filename(illust: dict, page_num: int = 0) -> str:
    """根据模板生成文件名"""
    author = _sanitize_filename(illust.get('user', {}).get('name', 'UnknownAuthor'))
    title = _sanitize_filename(illust.get('title', 'Untitled'))
    illust_id = illust.get('id', 0)
    
    base_name = state.filename_template.format(
        author=author,
        title=title,
        id=illust_id
    )
    
    if illust.get('page_count', 1) > 1:
        return f"{base_name}_p{page_num}"
    return base_name

def format_illust_summary(illust: dict) -> str:
    tags = ", ".join([tag.get('name', '') for tag in illust.get('tags', [])[:5]])
    return (
        f"ID: {illust.get('id')} - \"{illust.get('title')}\"\n"
        f"  作者: {illust.get('user', {}).get('name')} (ID: {illust.get('user', {}).get('id')})\n"
        f"  类型: {illust.get('type')}\n"
        f"  标签: {tags}\n"
        f"  收藏数: {illust.get('total_bookmarks', 0)}, 浏览数: {illust.get('total_view', 0)}"
    )

def format_user_summary(user_preview: dict) -> str:
    user = user_preview.get('user', {})
    return (
        f"用户ID: {user.get('id')} - {user.get('name')} (@{user.get('account')})\n"
        f"  关注状态: {'已关注' if user.get('is_followed') else '未关注'}\n"
        f"  简介: {user.get('comment', '无')}"
    )

def require_authentication(func: Callable) -> Callable:
    """
    一个装饰器，用于保护需要认证的工具函数。
    如果用户未认证，则返回统一的错误信息。
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not state.is_authenticated:
            return "错误: 此功能需要认证。请在客户端配置 PIXIV_REFRESH_TOKEN 环境变量或确保认证成功。"
        return await func(*args, **kwargs)
    return wrapper
