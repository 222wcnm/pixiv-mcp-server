import asyncio
import json
import logging
import random
import uuid
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from .downloader import _background_download_single
from .state import state
from .utils import (
    format_illust_summary,
    format_user_summary,
    handle_api_error,
    require_authentication,
)

logger = logging.getLogger('pixiv-mcp-server')
mcp = FastMCP("pixiv-server")

@mcp.tool()
async def set_download_path(path: str) -> str:
    """设置图片和动图的默认本地保存位置。路径不存在时会自动创建。"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        state.download_path = path
        logger.info(f"下载路径已更新为: {state.download_path}")
        return f"下载路径已成功更新为: {path}。之后所有下载的文件都将保存于此。"
    except Exception as e:
        logger.error(f"设置下载路径失败: {e}")
        return f"错误：无法设置下载路径。请检查路径 '{path}' 是否有效且程序有写入权限。错误详情: {e}"

@mcp.tool()
async def set_ugoira_format(format: str) -> str:
    """设置动图(Ugoira)转换后的文件格式。"""
    supported_formats = ["webp", "gif"]
    if format.lower() not in supported_formats:
        return f"错误：不支持的格式 '{format}'。请选择以下格式之一: {', '.join(supported_formats)}。"
    
    state.ugoira_format = format.lower()
    logger.info(f"动图输出格式已更新为: {state.ugoira_format}")
    return f"动图输出格式已成功设置为: {format.lower()}。"

@mcp.tool()
async def download(illust_id: Optional[int] = None, illust_ids: Optional[List[int]] = None) -> str:
    """
    下载一个或多个指定ID的作品。此为异步后台操作。
    该工具会为每个作品启动一个独立的后台下载任务，并返回这些任务的ID列表。
    你可以使用 `get_download_status` 工具来查询每个任务的下载进度和结果。
    """
    if not illust_id and not illust_ids:
        return "错误：必须提供 illust_id (单个ID) 或 illust_ids (ID列表) 参数之一。"

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
    
    return json.dumps({
        "message": f"已成功为 {len(unique_ids)} 个作品创建下载任务。请使用 get_download_status 工具凭任务ID查询进度。",
        "task_ids": task_ids
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_download_status(task_id: Optional[str] = None, task_ids: Optional[List[str]] = None) -> str:
    """
    查询一个或多个下载任务的当前状态。
    如果不提供任何ID，将返回最近10个任务的摘要。
    """
    if not task_id and not task_ids:
        # 返回最近10个任务的摘要
        recent_tasks = dict(sorted(state.download_tasks.items(), key=lambda item: item[1].get('updated_at', 0), reverse=True)[:10])
        if not recent_tasks:
            return "当前没有活动的下载任务。"
        return json.dumps(recent_tasks, ensure_ascii=False, indent=2)

    id_list = []
    if task_id:
        id_list.append(task_id)
    if task_ids:
        id_list.extend(task_ids)
    
    results = {}
    for an_id in id_list:
        results[an_id] = state.download_tasks.get(an_id, {"status": "not_found", "message": "未找到指定的任务ID。"})
        
    return json.dumps(results, ensure_ascii=False, indent=2)

@mcp.tool()
@require_authentication
async def download_random_from_recommendation(count: int = 5) -> str:
    """从用户的Pixiv推荐页随机下载N张插画。此为完成此类请求的最佳方式，会自动处理下载和动图转换。"""
    try:
        json_result = await asyncio.to_thread(state.api.illust_recommended)
        error = handle_api_error(json_result)
        if error:
            return f"获取推荐列表失败: {error}"

        illusts = json_result.get('illusts', [])
        if not illusts:
            return "无法获取推荐内容，列表为空。"
        
        if len(illusts) < count:
            logger.warning(f"推荐列表数量 ({len(illusts)}) 小于要求数量 ({count})，将下载所有可用的插画。")
            count = len(illusts)

        random_illusts = random.sample(illusts, count)
        ids_to_download = [illust['id'] for illust in random_illusts]
        
        return await download(illust_ids=ids_to_download)
        
    except Exception as e:
        logger.error(f"执行随机推荐下载时出错: {e}", exc_info=True)
        return f"执行随机推荐下载时发生错误: {e}"

@mcp.tool()
async def search_illust(
    word: str, 
    search_target: str = "partial_match_for_tags", 
    sort: str = "date_desc", 
    duration: Optional[str] = None, 
    offset: int = 0,
    search_r18: bool = False
) -> str:
    """根据关键词搜索插画。可选择是否包含 R-18 内容。"""
    search_word = f"{word} R-18" if search_r18 else word
    json_result = await asyncio.to_thread(state.api.search_illust, search_word, search_target=search_target, sort=sort, duration=duration, offset=offset)
    error = handle_api_error(json_result)
    if error:
        return error
    
    illusts = json_result.get('illusts', [])
    if not illusts:
        return f"抱歉，根据您提供的关键词 '{search_word}'，未能找到相关的插画。"
        
    summary_list = [format_illust_summary(illust) for illust in illusts]
    return f"找到 {len(illusts)} 张关于 '{search_word}' 的插画:\n\n" + "\n\n".join(summary_list)

@mcp.tool()
async def illust_detail(illust_id: int) -> str:
    """获取单张插画的详细信息。"""
    json_result = await asyncio.to_thread(state.api.illust_detail, illust_id)
    error = handle_api_error(json_result)
    if error:
        return error
    return json.dumps(json_result.get('illust', {}), ensure_ascii=False, indent=2)

@mcp.tool()
async def illust_related(illust_id: int, offset: int = 0) -> str:
    """获取与指定插画相关的推荐作品。"""
    json_result = await asyncio.to_thread(state.api.illust_related, illust_id, offset=offset)
    error = handle_api_error(json_result)
    if error:
        return error
    
    illusts = json_result.get('illusts', [])
    if not illusts:
        return f"找不到与插画 {illust_id} 相关的推荐。"
        
    summary_list = [format_illust_summary(illust) for illust in illusts]
    return f"找到 {len(illusts)} 张相关推荐:\n\n" + "\n\n".join(summary_list)

@mcp.tool()
async def illust_ranking(mode: str = "day", date: Optional[str] = None, offset: int = 0) -> str:
    """获取插画排行榜。"""
    json_result = await asyncio.to_thread(state.api.illust_ranking, mode=mode, date=date, offset=offset)
    error = handle_api_error(json_result)
    if error:
        return error

    illusts = json_result.get('illusts', [])
    if not illusts:
        return f"找不到模式为 '{mode}' 的排行榜结果。"

    summary_list = [f"第 {i+1+offset} 名: {format_illust_summary(illust)}" for i, illust in enumerate(illusts)]
    return f"{mode.capitalize()} 排行榜:\n\n" + "\n\n".join(summary_list)

@mcp.tool()
async def search_user(word: str, offset: int = 0) -> str:
    """搜索用户。"""
    json_result = await asyncio.to_thread(state.api.search_user, word, offset=offset)
    error = handle_api_error(json_result)
    if error:
        return error
    
    users = json_result.get('user_previews', [])
    if not users:
        return f"抱歉，未能找到名为 '{word}' 的用户。"
        
    summary_list = [format_user_summary(user) for user in users]
    return f"找到 {len(users)} 位用户:\n\n" + "\n\n".join(summary_list)

@mcp.tool()
@require_authentication
async def illust_recommended(offset: int = 0) -> str:
    """获取官方推荐插画的文本列表。注意：此工具只返回作品信息，不执行下载。如需下载，请使用'download_random_from_recommendation'工具。"""
    json_result = await asyncio.to_thread(state.api.illust_recommended, offset=offset)
    error = handle_api_error(json_result)
    if error:
        return error
    
    illusts = json_result.get('illusts', [])
    if not illusts:
        return "暂无推荐内容。"
        
    summary_list = [format_illust_summary(illust) for illust in illusts]
    return f"为您推荐 {len(illusts)} 张插画:\n\n" + "\n\n".join(summary_list)

@mcp.tool()
async def trending_tags_illust() -> str:
    """获取当前的热门标签趋势。"""
    json_result = await asyncio.to_thread(state.api.trending_tags_illust)
    error = handle_api_error(json_result)
    if error:
        return error
    
    trend_tags = json_result.get('trend_tags', [])
    if not trend_tags:
        return "无法获取热门标签。"
        
    tag_list = [f"- {tag.get('tag')} (翻译: {tag.get('translated_name', '无')})" for tag in trend_tags]
    return "当前的热门标签:\n" + "\n".join(tag_list)

@mcp.tool()
@require_authentication
async def illust_follow(restrict: str = "public", offset: int = 0) -> str:
    """获取已关注作者的最新作品（首页动态）(需要认证)。"""
    json_result = await asyncio.to_thread(state.api.illust_follow, restrict=restrict, offset=offset)
    error = handle_api_error(json_result)
    if error:
        return error
    
    illusts = json_result.get('illusts', [])
    if not illusts:
        return "您的关注动态中暂时没有新作品。"
        
    summary_list = [format_illust_summary(illust) for illust in illusts]
    return f"找到 {len(illusts)} 篇关注动态:\n\n" + "\n\n".join(summary_list)

@mcp.tool()
@require_authentication
async def user_bookmarks(user_id_to_check: Optional[int] = None, restrict: str = "public", tag: Optional[str] = None, max_bookmark_id: Optional[int] = None) -> str:
    """获取用户的收藏列表 (需要认证)。"""
    target_user_id = user_id_to_check if user_id_to_check is not None else state.user_id
    if target_user_id is None:
         return "错误: 查询自己的收藏时，需要先认证以获取用户ID。"

    json_result = await asyncio.to_thread(state.api.user_bookmarks_illust, target_user_id, restrict=restrict, tag=tag, max_bookmark_id=max_bookmark_id)
    error = handle_api_error(json_result)
    if error:
        return error

    illusts = json_result.get('illusts', [])
    if not illusts:
        return f"找不到用户 {target_user_id} 的收藏。"
        
    summary_list = [format_illust_summary(illust) for illust in illusts]
    return f"找到用户 {target_user_id} 的 {len(illusts)} 个收藏:\n\n" + "\n\n".join(summary_list)

@mcp.tool()
@require_authentication
async def user_following(user_id_to_check: Optional[int] = None, restrict: str = "public", offset: int = 0) -> str:
    """获取用户的关注列表 (需要认证)。"""
    target_user_id = user_id_to_check if user_id_to_check is not None else state.user_id
    if target_user_id is None:
         return "错误: 查询自己的关注列表时，需要先认证以获取用户ID。"

    json_result = await asyncio.to_thread(state.api.user_following, target_user_id, restrict=restrict, offset=offset)
    error = handle_api_error(json_result)
    if error:
        return error
    
    users = json_result.get('user_previews', [])
    if not users:
        return f"用户 {target_user_id} 没有关注任何人。"
        
    summary_list = [format_user_summary(user) for user in users]
    return f"用户 {target_user_id} 关注了 {len(users)} 位用户:\n\n" + "\n\n".join(summary_list)
