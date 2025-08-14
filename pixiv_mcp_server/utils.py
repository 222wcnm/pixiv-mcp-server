import functools
import logging
import re
import subprocess
import sys
import json
from typing import Callable, Optional, List, Dict, Any
from urllib.parse import quote_plus

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
            return {"ok": False, "error": "此功能需要认证。请在客户端配置 PIXIV_REFRESH_TOKEN 环境变量或确保认证成功。"}
        return await func(*args, **kwargs)
    return wrapper

def ensure_json_serializable(func: Callable) -> Callable:
    """确保工具函数返回值可被 JSON 序列化。

    - 对非可序列化对象使用 `str` 回退
    - 保持原始结构（通过 dumps/loads 往返）
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        try:
            # 使用 ensure_ascii=False 保留中文，default=str 兜底未知类型
            return json.loads(json.dumps(result, ensure_ascii=False, default=str))
        except Exception:
            return {"ok": False, "error": "结果序列化失败，请检查服务端日志。"}
    return wrapper


# --------------------------- 预览直链注入辅助 ---------------------------

def _build_proxy_base() -> Optional[str]:
    """构造代理前缀，如果代理未启用则返回 None。"""
    if not getattr(state, 'preview_proxy_enabled', False):
        return None
    host = getattr(state, 'preview_proxy_host', '127.0.0.1')
    port = getattr(state, 'preview_proxy_port', 8642)
    return f"http://{host}:{port}/pximg?url="


def inject_proxy_urls_into_illust(illust: Dict[str, Any]) -> None:
    """为单个插画对象注入 proxy_urls 字段（就地修改）。"""
    base = _build_proxy_base()
    if not base or not isinstance(illust, dict):
        return
    try:
        proxy_urls: Dict[str, Any] = {}
        imgs = illust.get('image_urls') or {}
        for key in ('square_medium', 'medium', 'large'):
            url = imgs.get(key)
            if url:
                proxy_urls[key] = base + quote_plus(url)

        # 原图（单页或多页）
        originals: List[str] = []
        single = (illust.get('meta_single_page') or {}).get('original_image_url')
        if single:
            originals = [single]
        else:
            for page in illust.get('meta_pages') or []:
                ou = (page.get('image_urls') or {}).get('original')
                if ou:
                    originals.append(ou)
        if originals:
            proxy_urls['originals'] = [base + quote_plus(u) for u in originals]

        if proxy_urls:
            illust['proxy_urls'] = proxy_urls
    except Exception:
        # 静默跳过注入失败
        pass


def inject_proxy_urls_into_illust_list(illusts: List[Dict[str, Any]]) -> None:
    if not isinstance(illusts, list):
        return
    for illust in illusts:
        if isinstance(illust, dict):
            inject_proxy_urls_into_illust(illust)


def inject_proxy_profile_urls_into_user(user: Dict[str, Any]) -> None:
    """为用户对象注入头像代理直链 proxy_profile_image_urls（就地修改）。"""
    base = _build_proxy_base()
    if not base or not isinstance(user, dict):
        return
    try:
        profile = user.get('profile_image_urls') or {}
        if not isinstance(profile, dict):
            return
        proxied: Dict[str, str] = {}
        for key, url in profile.items():
            if isinstance(url, str) and url:
                proxied[key] = base + quote_plus(url)
        if proxied:
            user['proxy_profile_image_urls'] = proxied
    except Exception:
        pass


def inject_proxy_profile_urls_into_user_previews(user_previews: List[Dict[str, Any]]) -> None:
    if not isinstance(user_previews, list):
        return
    for preview in user_previews:
        if not isinstance(preview, dict):
            continue
        user = preview.get('user')
        if isinstance(user, dict):
            inject_proxy_profile_urls_into_user(user)


def inject_proxy_into_trend_tags(trend_tags: List[Dict[str, Any]]) -> None:
    if not isinstance(trend_tags, list):
        return
    for tag in trend_tags:
        if not isinstance(tag, dict):
            continue
        illust = tag.get('illust')
        if isinstance(illust, dict):
            inject_proxy_urls_into_illust(illust)

# --------------------------- 卡片渲染与结构化输出 ---------------------------

def _is_nsfw(illust: Dict[str, Any]) -> bool:
    """判断插画是否为 R-18 内容。"""
    return (
        illust.get('x_restrict', 0) == 1 or
        any(tag.get('name') == 'R-18' for tag in illust.get('tags', []))
    )


def _get_preferred_preview(data: Dict[str, Any]) -> Optional[str]:
    """
    获取首选预览链接（优先代理直链，其次原始链接）。
    此函数现在可以处理插画对象和用户头像对象。
    """
    # 检查插画对象的标准结构
    proxy_urls = data.get('proxy_urls', {})
    if proxy_urls.get('medium'):
        return proxy_urls['medium']
    if proxy_urls.get('square_medium'):
        return proxy_urls['square_medium']
    
    image_urls = data.get('image_urls', {})
    if image_urls.get('medium'):
        return image_urls['medium']
    if image_urls.get('square_medium'):
        return image_urls['square_medium']
        
    # 检查用户头像的直接结构
    if data.get('medium'):
        return data['medium']
    if data.get('square_medium'):
        return data['square_medium']
        
    return None


def _extract_card_from_illust(illust: Dict[str, Any]) -> Dict[str, Any]:
    """从插画对象提取标准卡片信息。"""
    user = illust.get('user', {})
    tags = illust.get('tags', [])
    
    return {
        'id': illust.get('id'),
        'title': illust.get('title', ''),
        'author': {
            'id': user.get('id'),
            'name': user.get('name', ''),
            'account': user.get('account', '')
        },
        'type': illust.get('type', 'illust'),
        'page_count': illust.get('page_count', 1),
        'bookmarks': illust.get('total_bookmarks', 0),
        'views': illust.get('total_view', 0),
        'nsfw': _is_nsfw(illust),
        'preferred_preview': _get_preferred_preview(illust),
        'tags': [tag.get('name', '') for tag in tags[:5]],  # 前5个标签
        'create_date': illust.get('create_date', ''),
        'width': illust.get('width'),
        'height': illust.get('height')
    }


def _extract_card_from_user(user_preview: Dict[str, Any]) -> Dict[str, Any]:
    """从用户预览对象提取标准卡片信息。"""
    user = user_preview.get('user', {})
    
    # 用户头像数据可能在 'user' 对象内部，也可能在 'user_preview' 的顶层
    profile_images = user.get('profile_image_urls', {}) or user_preview.get('profile_image_urls', {})
    
    return {
        'id': user.get('id'),
        'name': user.get('name', ''),
        'account': user.get('account', ''),
        'is_followed': user.get('is_followed', False),
        'comment': user.get('comment', ''),
        'preferred_preview': _get_preferred_preview(profile_images),
    }


def _get_next_params(current_params: Dict[str, Any], total_count: Optional[int] = None) -> Dict[str, Any]:
    """生成下一页参数。"""
    offset = current_params.get('offset', 0)
    limit = current_params.get('limit', 30)
    
    next_params = current_params.copy()
    next_params['offset'] = offset + limit
    
    if total_count is not None:
        next_params['has_more'] = (offset + limit) < total_count
    
    return next_params


def render_cards_to_markdown(cards: List[Dict[str, Any]], title: str = "作品列表", 
                           show_nsfw: bool = False, max_items: int = 10) -> str:
    """将卡片列表渲染为 Markdown 格式。"""
    if not cards:
        return f"## {title}\n\n暂无内容。"
    
    # 过滤 NSFW 内容
    if not show_nsfw:
        cards = [card for card in cards if not card.get('nsfw', False)]
    
    # 限制显示数量
    display_cards = cards[:max_items]
    
    lines = [f"## {title}\n"]
    
    for i, card in enumerate(display_cards, 1):
        if card.get('nsfw', False):
            lines.append(f"{i}. **ID {card['id']}** | {card['title']} | 作者: {card['author']['name']} | 🔞 R-18")
        else:
            preview_link = card.get('preferred_preview')
            if preview_link:
                lines.append(f"{i}. **ID {card['id']}** | {card['title']} | 作者: {card['author']['name']} | ❤️ {card['bookmarks']}")
                lines.append(f"![{card['title']}]({preview_link})")
            else:
                lines.append(f"{i}. **ID {card['id']}** | {card['title']} | 作者: {card['author']['name']} | ❤️ {card['bookmarks']}")
    
    if len(cards) > max_items:
        lines.append(f"\n... 还有 {len(cards) - max_items} 条内容")
    
    return "\n".join(lines)


def structure_tool_response(illusts: Optional[List[Dict[str, Any]]] = None, users: Optional[List[Dict[str, Any]]] = None,
                          view: str = "cards", limit: int = 30, offset: int = 0,
                          **extra_params) -> Dict[str, Any]:
    """结构化工具响应，统一返回格式。"""
    result = {"ok": True}
    
    if view == "cards":
        # 提取卡片信息
        if illusts:
            result["cards"] = [_extract_card_from_illust(illust) for illust in illusts]
        if users:
            result["user_cards"] = [_extract_card_from_user(user) for user in users]
        
        # 生成下一页参数
        current_params = {"offset": offset, "limit": limit, **extra_params}
        result["next"] = _get_next_params(current_params)
        
        # 统计信息
        nsfw_count = sum(1 for card in result.get("cards", []) if card.get("nsfw", False))
        if nsfw_count > 0:
            result["nsfw_count"] = nsfw_count
            result["nsfw_warning"] = f"包含 {nsfw_count} 个 R-18 内容"
    
    elif view == "minimal":
        # 精简信息
        if illusts:
            result["illusts"] = [{
                "id": illust.get("id"),
                "title": illust.get("title"),
                "author": illust.get("user", {}).get("name"),
                "bookmarks": illust.get("total_bookmarks", 0),
                "nsfw": _is_nsfw(illust),
                "preview": _get_preferred_preview(illust)
            } for illust in illusts]
    
    else:  # view == "raw"
        # 原始数据
        if illusts:
            result["illusts"] = illusts
        if users:
            result["users"] = users
    
    return result
