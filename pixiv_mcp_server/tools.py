import asyncio
import json
import logging
import random
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

from .downloader import _background_download_single
from .config import settings
from .state import state
from .utils import (
    _extract_card_from_illust,
    _extract_card_from_user,
    format_illust_summary,
    format_user_summary,
    handle_api_error,
    require_authentication,
    ensure_json_serializable,
    inject_proxy_urls_into_illust,
    inject_proxy_urls_into_illust_list,
    inject_proxy_profile_urls_into_user_previews,
    inject_proxy_into_trend_tags,
    structure_tool_response,
    render_cards_to_markdown,
)

logger = logging.getLogger('pixiv-mcp-server')
mcp = FastMCP("pixiv-server")


async def _api_tool_handler(
    api_method_name: str,
    *args,
    response_key: str,
    view: str = "cards",
    limit: int = settings.default_limit,
    offset: Optional[int] = None,
    error_message: str = "未能获取数据。",
    not_found_message: str = "未找到任何内容。",
    **kwargs,
) -> dict:
    """
    一个通用的 API 工具处理器，用于简化工具函数的重复逻辑。
    - 调用指定的 API 客户端方法
    - 处理 API 错误
    - 注入代理 URL
    - 根据视图（view）参数决定是返回原始数据还是渲染后的 Markdown
    """
    if not state.api_client:
        return {"ok": False, "error": "API 客户端尚未初始化，请检查认证状态。"}
    # 调用 API
    try:
        api_method = getattr(state.api_client, api_method_name)
        if offset is not None:
            kwargs['offset'] = offset
        json_result = await api_method(*args, **kwargs)
        state.last_response = json_result  # 保存响应以供翻页
        state.last_response_key = response_key # 保存响应类型以供翻页
        if "next_url" not in json_result and "next" in json_result:
            json_result["next_url"] = json_result["next"]
    except Exception as e:
        logger.error(f"调用 API 方法 {api_method_name} 时出错: {e}", exc_info=True)
        return {"ok": False, "error": f"{error_message}: 调用 API 时发生异常: {e}"}


    # 统一错误处理
    error = handle_api_error(json_result)
    if error:
        return {"ok": False, "error": f"{error_message}: {error}"}

    # 提取数据
    items = json_result.get(response_key, [])
    if not items:
        return {"ok": True, "cards": [], "message": not_found_message}

    # 注入代理 URL
    if response_key == "illusts":
        inject_proxy_urls_into_illust_list(items)
    elif response_key == "user_previews":
        inject_proxy_profile_urls_into_user_previews(items)
    elif response_key == "trend_tags":
        inject_proxy_into_trend_tags(items)

    # 根据视图参数决定输出
    if view == "raw":
        # 保持向后兼容的 'raw' 视图
        result = {
            "ok": True,
            response_key: items,
            "next": json_result.get("next_url")
        }
        if response_key == "illusts":
            result["summary"] = [format_illust_summary(illust) for illust in items]
        elif response_key == "user_previews":
            result["summary"] = [format_user_summary(user) for user in items]
        return result
    else: # 默认为 'cards' 视图
        title = kwargs.get("title", "作品列表")
        show_nsfw = kwargs.get("search_r18", False)
        
        if response_key == "illusts":
            cards = [_extract_card_from_illust(item) for item in items]
        elif response_key == "user_previews":
            cards = [_extract_card_from_user(item) for item in items]
        else:
            cards = items

        markdown = render_cards_to_markdown(cards, title, show_nsfw, limit)
        return {
            "ok": True,
            "markdown": markdown,
            "card_count": len(items),
            "display_count": min(len(items), limit),
            "nsfw_filtered": not show_nsfw,
        }


@mcp.tool()
async def next_page() -> dict:
    """Fetches the next page of results from the previous command."""
    if not state.api_client:
        return {"ok": False, "error": "API 客户端尚未初始化，请检查认证状态。"}
    if not state.last_response or not state.last_response.get("next_url"):
        return {"ok": False, "error": "没有可供翻页的上一条指令。"}
    
    next_url = state.last_response["next_url"]
    
    # 从 state 中安全地获取 response_key
    response_key = state.last_response_key
    if not response_key:
        return {"ok": False, "error": "无法确定上一条指令的响应类型，无法翻页。"}

    # 调用 next_page API
    response = await state.api_client.next_page(next_url)
    json_result = response.json()
    state.last_response = json_result
    state.last_response_key = response_key # 保持 key 的传递

    # 统一错误处理
    error = handle_api_error(json_result)
    if error:
        return {"ok": False, "error": f"获取下一页失败: {error}"}

    # 提取数据
    items = json_result.get(response_key, [])
    if not items:
        return {"ok": True, "cards": [], "message": "没有更多内容了。"}

    # 注入代理 URL
    if response_key == "illusts":
        inject_proxy_urls_into_illust_list(items)
    elif response_key == "user_previews":
        inject_proxy_profile_urls_into_user_previews(items)

    # 渲染 Markdown
    title = "下一页"
    show_nsfw = False # 默认为 False
    limit = settings.default_limit
    
    if response_key == "illusts":
        cards = [_extract_card_from_illust(item) for item in items]
    elif response_key == "user_previews":
        cards = [_extract_card_from_user(item) for item in items]
    else:
        cards = items

    markdown = render_cards_to_markdown(cards, title, show_nsfw, limit)
    return {
        "ok": True,
        "markdown": markdown,
        "card_count": len(items),
        "display_count": min(len(items), limit),
        "nsfw_filtered": not show_nsfw,
    }



@mcp.tool()
async def download(illust_id: Optional[int] = None, illust_ids: Optional[List[int]] = None) -> dict:
    """
    Downloads one or more artworks by their IDs asynchronously in the background. Returns task IDs for tracking progress via `get_download_status`.
    """
    if not illust_id and not illust_ids:
        return {
            "ok": False,
            "error": "必须提供 illust_id (单个ID) 或 illust_ids (ID列表) 参数之一。"
        }

    id_list = []
    if illust_id:
        id_list.append(illust_id)
    if illust_ids:
        id_list.extend(illust_ids)
    
    unique_ids = sorted(list(set(id_list)))
    task_ids = []
    
    for an_id in unique_ids:
        task_id = f"task_{uuid.uuid4()}"
        task_ids.append(task_id)
        state.download_tasks[task_id] = {
            "illust_id": an_id,
            "status": "queued",
            "message": "任务已创建，正在等待调度。",
        }
        asyncio.create_task(_background_download_single(task_id, an_id))
    
    return {
        "ok": True,
        "message": f"已成功为 {len(unique_ids)} 个作品创建下载任务。请使用 get_download_status 工具凭任务ID查询进度。",
        "task_ids": task_ids
    }

@mcp.tool()
async def manage_download_tasks(
    task_id: Optional[str] = None, 
    task_ids: Optional[List[str]] = None,
    action: str = "status"
) -> dict:
    """
    Manages download tasks. The default action is to query the status.
    - action='status': Queries the status of one or more tasks. If no ID is provided, it displays the 10 most recent tasks.
    - action='cancel': Cancels one or more tasks that are currently queued or downloading.
    """
    id_list = []
    if task_id:
        id_list.append(task_id)
    if task_ids:
        id_list.extend(task_ids)

    if action == "status":
        if not id_list:
            # 返回最近10个任务的摘要
            recent_tasks = dict(sorted(state.download_tasks.items(), key=lambda item: item[1].get('updated_at', 0), reverse=True)[:10])
            if not recent_tasks:
                return {"ok": True, "tasks": {}, "message": "当前没有活动的下载任务。"}
            return {"ok": True, "tasks": recent_tasks}
        
        results = {}
        for an_id in id_list:
            results[an_id] = state.download_tasks.get(an_id, {"status": "not_found", "message": "未找到指定的任务ID。"})
        return {"ok": True, "tasks": results}

    elif action == "cancel":
        if not id_list:
            return {"ok": False, "error": "必须提供 task_id 或 task_ids 来取消任务。"}
        
        cancelled_count = 0
        not_found_count = 0
        results = {}
        for an_id in id_list:
            task = state.download_tasks.get(an_id)
            if not task:
                not_found_count += 1
                results[an_id] = {"status": "not_found"}
                continue
            
            if task["status"] in ["queued", "downloading"]:
                task["status"] = "cancelled"
                task["message"] = "任务已被用户取消。"
                cancelled_count += 1
                results[an_id] = {"status": "cancelled"}
            else:
                results[an_id] = {"status": task["status"], "message": "任务已完成或失败，无法取消。"}

        return {
            "ok": True, 
            "message": f"操作完成。成功取消 {cancelled_count} 个任务，{not_found_count} 个任务未找到。",
            "results": results
        }
    
    else:
        return {"ok": False, "error": f"不支持的操作: '{action}'", "supported_actions": ["status", "cancel"]}

@mcp.tool()
async def update_setting(key: str, value: Any) -> dict:
    """
    Updates the server configuration at runtime.
    Supported 'key' values include: 'download_path', 'ugoira_format', 'filename_template'.
    """
    supported_keys = {
        "download_path": str,
        "ugoira_format": str,
        "filename_template": str,
    }

    if key not in supported_keys:
        return {"ok": False, "error": f"不支持的配置项: '{key}'", "supported_keys": list(supported_keys.keys())}

    # 类型校验
    expected_type = supported_keys[key]
    if not isinstance(value, expected_type):
        return {"ok": False, "error": f"配置项 '{key}' 的值类型错误。期望类型: {expected_type.__name__}, 实际类型: {type(value).__name__}"}

    # 特定值的合法性校验
    if key == "ugoira_format":
        supported_formats = ["webp", "gif"]
        if value.lower() not in supported_formats:
            return {"ok": False, "error": f"不支持的动图格式 '{value}'", "supported_formats": supported_formats}
        value = value.lower()
    
    if key == "download_path":
        try:
            Path(value).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建下载路径 '{value}' 失败: {e}")
            return {"ok": False, "error": f"无法创建或访问指定的下载路径: {e}"}

    try:
        setattr(state, key, value)
        logger.info(f"配置项 '{key}' 已更新为: {value}")
        return {"ok": True, "message": f"配置 '{key}' 已成功更新。", "new_value": value}
    except Exception as e:
        logger.error(f"更新配置项 '{key}' 失败: {e}")
        return {"ok": False, "error": f"更新配置时发生未知错误: {e}"}

@mcp.tool()
@ensure_json_serializable
async def search_illust(
    word: str, 
    search_target: str = "partial_match_for_tags", 
    sort: str = "date_desc", 
    duration: Optional[str] = None, 
    offset: int = 0,
    search_r18: bool = False,
    view: str = "cards",
    limit: int = settings.default_limit
) -> dict:
    """Searches for illustrations by keyword. You can choose whether to include R-18 content."""
    search_word = f"{word} R-18" if search_r18 else word
    return await _api_tool_handler(
        "search_illust",
        search_word,
        search_target=search_target,
        sort=sort,
        duration=duration,
        offset=offset,
        response_key="illusts",
        view=view,
        limit=limit,
        error_message=f"搜索 '{search_word}' 失败",
        not_found_message=f"未能找到与 '{search_word}' 相关的插画。",
    )

@mcp.tool()
@ensure_json_serializable
async def illust_detail(illust_id: int) -> dict:
    """Retrieves detailed information for a single illustration."""
    json_result = await state.api_client.illust_detail(illust_id)
    error = handle_api_error(json_result)
    if error:
        return {"ok": False, "error": error}
    illust = json_result.get('illust', {})
    inject_proxy_urls_into_illust(illust)
    return {"ok": True, "illust": illust}

@mcp.tool()
@ensure_json_serializable
async def illust_related(illust_id: int, offset: int = 0, view: str = "cards", limit: int = settings.default_limit) -> dict:
    """Gets recommended artworks related to the specified illustration."""
    return await _api_tool_handler(
        "illust_related",
        illust_id,
        offset=offset,
        response_key="illusts",
        view=view,
        limit=limit,
        error_message=f"获取插画 {illust_id} 的相关推荐失败",
        not_found_message=f"找不到与插画 {illust_id} 相关的推荐。",
    )

@mcp.tool()
@ensure_json_serializable
async def illust_ranking(mode: str = "day", date: Optional[str] = None, offset: int = 0, view: str = "cards", limit: int = settings.default_limit) -> dict:
    """Retrieves the illustration rankings."""
    return await _api_tool_handler(
        "illust_ranking",
        mode=mode,
        date=date,
        offset=offset,
        response_key="illusts",
        view=view,
        limit=limit,
        error_message=f"获取 '{mode}' 排行榜失败",
        not_found_message=f"找不到模式为 '{mode}' 的排行榜结果。",
    )

@mcp.tool()
@ensure_json_serializable
async def search_user(word: str, offset: int = 0, view: str = "cards", limit: int = settings.default_limit) -> dict:
    """Searches for users."""
    return await _api_tool_handler(
        "search_user",
        word,
        offset=offset,
        response_key="user_previews",
        view=view,
        limit=limit,
        error_message=f"搜索用户 '{word}' 失败",
        not_found_message=f"未能找到名为 '{word}' 的用户。",
    )

@mcp.tool()
@ensure_json_serializable
@require_authentication
async def illust_recommended(offset: int = 0, view: str = "cards", limit: int = settings.default_limit) -> dict:
    """Fetches a list of official recommended illustrations (Authentication required)."""
    return await _api_tool_handler(
        "illust_recommended",
        offset=offset,
        response_key="illusts",
        view=view,
        limit=limit,
        error_message="获取官方推荐失败",
        not_found_message="暂无推荐内容。",
    )

@mcp.tool()
@ensure_json_serializable
async def trending_tags_illust() -> dict:
    """Gets the current trending tag trends."""
    json_result = await state.api_client.trending_tags_illust()
    error = handle_api_error(json_result)
    if error:
        return {"ok": False, "error": error}
    
    trend_tags = json_result.get('trend_tags', [])
    inject_proxy_into_trend_tags(trend_tags)
    if not trend_tags:
        return {"ok": True, "trend_tags": [], "message": "无法获取热门标签。"}
        
    tag_list = [f"- {tag.get('tag')} (翻译: {tag.get('translated_name', '无')})" for tag in trend_tags]
    return {"ok": True, "trend_tags": trend_tags, "summary": tag_list}

@mcp.tool()
@ensure_json_serializable
@require_authentication
async def illust_follow(restrict: str = "public", offset: int = 0, view: str = "cards", limit: int = settings.default_limit) -> dict:
    """Fetches the latest works from followed artists (home feed) (Authentication required)."""
    return await _api_tool_handler(
        "illust_follow",
        restrict=restrict,
        offset=offset,
        response_key="illusts",
        view=view,
        limit=limit,
        error_message="获取关注动态失败",
        not_found_message="您的关注动态中暂时没有新作品。",
    )

@mcp.tool()
@ensure_json_serializable
@require_authentication
async def user_bookmarks(user_id_to_check: Optional[int] = None, restrict: str = "public", tag: Optional[str] = None, max_bookmark_id: Optional[int] = None, view: str = "cards", limit: int = settings.default_limit) -> dict:
    """Retrieves a user's bookmark list (Authentication required)."""
    target_user_id = user_id_to_check if user_id_to_check is not None else state.user_id
    if target_user_id is None:
        return {"ok": False, "error": "查询自己的收藏时，需要先认证以获取用户ID。"}

    return await _api_tool_handler(
        "user_bookmarks_illust",
        target_user_id,
        restrict=restrict,
        tag=tag,
        max_bookmark_id=max_bookmark_id,
        response_key="illusts",
        view=view,
        limit=limit,
        error_message=f"获取用户 {target_user_id} 的收藏失败",
        not_found_message=f"找不到用户 {target_user_id} 的收藏。",
    )

@mcp.tool()
@ensure_json_serializable
@require_authentication
async def user_following(user_id_to_check: Optional[int] = None, restrict: str = "public", offset: int = 0, view: str = "cards", limit: int = settings.default_limit) -> dict:
    """Retrieves a user's following list (Authentication required)."""
    target_user_id = user_id_to_check if user_id_to_check is not None else state.user_id
    if target_user_id is None:
        return {"ok": False, "error": "查询自己的关注列表时，需要先认证以获取用户ID。"}

    return await _api_tool_handler(
        "user_following",
        target_user_id,
        restrict=restrict,
        offset=offset,
        response_key="user_previews",
        view=view,
        limit=limit,
        error_message=f"获取用户 {target_user_id} 的关注列表失败",
        not_found_message=f"用户 {target_user_id} 没有关注任何人。",
    )
