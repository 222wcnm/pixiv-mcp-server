import asyncio
import logging
from typing import Optional, Any, Dict

from pixivpy3 import PixivError

from .state import state

logger = logging.getLogger('pixiv-mcp-server')

class PixivAPIClient:
    """
    一个封装了 pixivpy3 API 调用的异步客户端。
    它将同步的 pixivpy3 方法转换为异步方法，以便在 asyncio 环境中使用。
    """

    def __init__(self, api):
        self.api = api

    async def _call_api_with_auth_refresh(self, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        一个封装了认证刷新逻辑的通用 API 调用方法。
        它同时处理异常和包含 'error' 键的返回字典。
        """
        # 首次尝试调用
        method = getattr(self.api, method_name)
        result = await asyncio.to_thread(method, *args, **kwargs)

        # 检查返回结果是否为错误
        if isinstance(result, dict) and 'error' in result:
            error_message = str(result.get('error', '')).lower()
            
            # 检查是否是认证相关的错误
            if ('token' in error_message or 'authenticate' in error_message or 'oauth' in error_message) and state.refresh_token:
                logger.info("Access token 可能已过期或无效，正在尝试刷新...")
                async with state.auth_lock:
                    try:
                        # 重新认证
                        await asyncio.to_thread(self.api.auth, refresh_token=state.refresh_token)
                        logger.info("Token 刷新成功。")
                        state.is_authenticated = True
                        # 再次调用原始方法
                        method = getattr(self.api, method_name)
                        return await asyncio.to_thread(method, *args, **kwargs)
                    except PixivError as refresh_e:
                        logger.error(f"刷新 token 失败: {refresh_e}")
                        state.is_authenticated = False
                        # 即使刷新失败，也返回原始的错误信息
                        return result
            else:
                # 如果不是认证错误，则直接返回错误信息
                return result
        
        # 如果没有错误，直接返回结果
        return result

    async def _call_api(self, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        通用 API 调用方法，使用 asyncio.to_thread 在单独的线程中运行同步方法。
        """
        return await self._call_api_with_auth_refresh(method_name, *args, **kwargs)

    async def illust_detail(self, illust_id: int) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('illust_detail', illust_id)

    async def illust_related(self, illust_id: int, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('illust_related', illust_id, **kwargs)

    async def illust_recommended(self, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('illust_recommended', **kwargs)

    async def illust_ranking(self, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('illust_ranking', **kwargs)

    async def search_illust(self, word: str, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('search_illust', word, **kwargs)

    async def search_user(self, word: str, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('search_user', word, **kwargs)

    async def trending_tags_illust(self) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('trending_tags_illust')

    async def illust_follow(self, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('illust_follow', **kwargs)

    async def user_bookmarks_illust(self, user_id: int, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('user_bookmarks_illust', user_id, **kwargs)

    async def user_following(self, user_id: int, **kwargs) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('user_following', user_id, **kwargs)
        
    async def ugoira_metadata(self, illust_id: int) -> Dict[str, Any]:
        return await self._call_api_with_auth_refresh('ugoira_metadata', illust_id)

    async def download(self, url: str, **kwargs) -> None:
        return await self._call_api_with_auth_refresh('download', url, **kwargs)

# 在 state 中初始化一个全局的 API 客户端实例
# 这将在服务器启动时完成
def initialize_api_client():
    if state.api:
        state.api_client = PixivAPIClient(state.api)
