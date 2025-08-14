import asyncio
from typing import Optional, Any, Dict

from .state import state

class PixivAPIClient:
    """
    一个封装了 pixivpy3 API 调用的异步客户端。
    它将同步的 pixivpy3 方法转换为异步方法，以便在 asyncio 环境中使用。
    """

    def __init__(self, api):
        self.api = api

    async def _call_api(self, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        通用 API 调用方法，使用 asyncio.to_thread 在单独的线程中运行同步方法。
        """
        method = getattr(self.api, method_name)
        return await asyncio.to_thread(method, *args, **kwargs)

    async def illust_detail(self, illust_id: int) -> Dict[str, Any]:
        return await self._call_api('illust_detail', illust_id)

    async def illust_related(self, illust_id: int, **kwargs) -> Dict[str, Any]:
        return await self._call_api('illust_related', illust_id, **kwargs)

    async def illust_recommended(self, **kwargs) -> Dict[str, Any]:
        return await self._call_api('illust_recommended', **kwargs)

    async def illust_ranking(self, **kwargs) -> Dict[str, Any]:
        return await self._call_api('illust_ranking', **kwargs)

    async def search_illust(self, word: str, **kwargs) -> Dict[str, Any]:
        return await self._call_api('search_illust', word, **kwargs)

    async def search_user(self, word: str, **kwargs) -> Dict[str, Any]:
        return await self._call_api('search_user', word, **kwargs)

    async def trending_tags_illust(self) -> Dict[str, Any]:
        return await self._call_api('trending_tags_illust')

    async def illust_follow(self, **kwargs) -> Dict[str, Any]:
        return await self._call_api('illust_follow', **kwargs)

    async def user_bookmarks_illust(self, user_id: int, **kwargs) -> Dict[str, Any]:
        return await self._call_api('user_bookmarks_illust', user_id, **kwargs)

    async def user_following(self, user_id: int, **kwargs) -> Dict[str, Any]:
        return await self._call_api('user_following', user_id, **kwargs)
        
    async def ugoira_metadata(self, illust_id: int) -> Dict[str, Any]:
        return await self._call_api('ugoira_metadata', illust_id)

    async def download(self, url: str, **kwargs) -> None:
        return await self._call_api('download', url, **kwargs)

    async def next_page(self, next_url: str) -> Dict[str, Any]:
        # next_page 需要从 next_url 中提取参数，然后调用 requests_call
        # 这需要一些解析逻辑
        from urllib.parse import urlparse, parse_qs, urljoin
        
        parsed_url = urlparse(next_url)
        params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
        
        # 提取方法和路径
        method = "GET" # 默认为 GET
        
        # pixivpy 的 next_page 实际上是调用 requests_call
        # 我们需要模拟这个行为
        self.api.auth()
        headers = {
            "App-OS": "ios",
            "App-OS-Version": "14.6",
            "App-Version": "7.14.1",
            "User-Agent": "PixivIOSApp/7.14.1 (iOS 14.6; iPhone13,2)",
            "Authorization": f"Bearer {self.api.access_token}",
        }
        
        # 使用 urljoin 构造健壮的 URL
        base_url = f"https://{self.api.hosts}"
        full_url = urljoin(base_url, parsed_url.path)
        
        return await self._call_api('requests_call', method, full_url, headers=headers, params=params)

# 在 state 中初始化一个全局的 API 客户端实例
# 这将在服务器启动时完成
def initialize_api_client():
    if state.api:
        state.api_client = PixivAPIClient(state.api)
