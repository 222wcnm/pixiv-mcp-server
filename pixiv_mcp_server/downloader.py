import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

from .state import state
from .utils import (
    _generate_filename,
    _sanitize_filename,
    check_ffmpeg,
    handle_api_error,
)

logger = logging.getLogger('pixiv-mcp-server')
HAS_FFMPEG = check_ffmpeg()

def _update_task_status(task_id: str, status: str, message: str, details: Dict = None):
    """统一更新任务状态"""
    if task_id not in state.download_tasks:
        state.download_tasks[task_id] = {}
    
    state.download_tasks[task_id].update({
        "status": status,
        "message": message,
        "updated_at": time.time(),
        "details": details or state.download_tasks[task_id].get("details", {})
    })
    logger.info(f"任务 {task_id}: 状态更新为 {status} - {message}")

async def _sync_convert_ugoira(zip_path: str, frames: List[Dict], work_dir: str, output_path: str, format: str) -> str:
    """将 Ugoira 的 zip 文件同步转换为指定格式（webp/gif），并进行性能优化。"""
    temp_dir_path = Path(work_dir) / "temp_frames"
    temp_dir_path.mkdir(exist_ok=True)
    temp_dir = str(temp_dir_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        frame_list_path = os.path.join(temp_dir, "frame_list.txt")
        with open(frame_list_path, 'w', encoding='utf-8') as f:
            for frame in frames:
                duration = frame['delay'] / 1000.0
                f.write(f"file '{os.path.basename(frame['file'])}'\n")
                f.write(f"duration {duration}\n")

        absolute_output_path = str(Path(output_path).resolve())
        
        # 根据格式选择不同的 FFmpeg 参数
        if format == 'webp':
            cmd = [
                'ffmpeg',
                '-f', 'concat', '-safe', '0', '-i', "frame_list.txt",
                '-c:v', 'libwebp',       # 使用webp编码器
                '-lossless', '0',        # 0为有损，1为无损
                '-q:v', '80',            # 质量参数，0-100
                '-preset', 'default',    # 预设
                '-loop', '0',            # 循环播放
                '-threads', str(os.cpu_count() or 2),
                '-y',
                absolute_output_path
            ]
        else: # 默认为 gif
            cmd = [
                'ffmpeg',
                '-f', 'concat', '-safe', '0', '-i', "frame_list.txt",
                '-vf', "split[s0][s1];[s0]palettegen=stats_mode=single[p];[s1][p]paletteuse=new=1",
                '-preset', 'ultrafast', # 加速处理
                '-threads', str(os.cpu_count() or 2),
                '-y',
                absolute_output_path
            ]
        
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        
        async with state.cpu_bound_semaphore:
            logger.info(f"开始动图合成 (格式: {format})... CPU并发: {state.cpu_bound_semaphore._value + 1}/{os.cpu_count() or 2}")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd, cwd=temp_dir, check=True, capture_output=True, 
                text=True, encoding='utf-8', creationflags=creationflags
            )
            logger.info(f"动图合成成功: {output_path}")

        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed for {Path(output_path).stem}. Exit code: {e.returncode}")
        logger.error(f"FFmpeg stderr:\n{e.stderr}")
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred during conversion for {Path(output_path).stem}: {e}")
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if os.path.exists(zip_path):
            os.remove(zip_path)

async def _background_download_single(task_id: str, illust_id: int):
    """在背景下载单个作品，并应用智能存储和命名规则，同时更新任务状态。"""
    _update_task_status(task_id, "pending", f"任务已加入队列，等待处理。")
    
    async with state.download_semaphore:
        _update_task_status(task_id, "downloading", f"开始处理作品 ID {illust_id}。")
        try:
            detail_result = await asyncio.to_thread(state.api.illust_detail, illust_id)
            error = handle_api_error(detail_result)
            if error:
                _update_task_status(task_id, "failed", f"无法获取作品信息: {error}")
                return

            illust = detail_result['illust']
            _update_task_status(task_id, "downloading", "成功获取作品信息。", {"illust_title": illust.get('title')})

            page_count = illust.get('page_count', 1)
            illust_type = illust.get('type')
            
            save_path_base = Path(state.download_path)
            if page_count > 1 or illust_type == 'ugoira':
                sub_folder_name = _sanitize_filename(f"{illust_id} - {illust.get('title', 'Untitled')}")
                save_path_base = save_path_base / sub_folder_name
            
            save_path_base.mkdir(parents=True, exist_ok=True)
            
            if illust_type == 'ugoira':
                if not HAS_FFMPEG:
                    _update_task_status(task_id, "failed", "未找到 FFmpeg，无法处理动图。")
                    return
                
                _update_task_status(task_id, "downloading", "正在获取动图元数据...")
                metadata = await asyncio.to_thread(state.api.ugoira_metadata, illust_id)
                error = handle_api_error(metadata)
                if error:
                    _update_task_status(task_id, "failed", f"无法获取动图元数据: {error}")
                    return
                
                zip_url = metadata['ugoira_metadata']['zip_urls']['medium']
                zip_filename = os.path.basename(urlparse(zip_url).path)
                zip_path = save_path_base / zip_filename
                
                _update_task_status(task_id, "downloading", f"正在下载动图 .zip 文件...")
                await asyncio.to_thread(state.api.download, zip_url, path=str(save_path_base))
                
                output_format = state.ugoira_format
                filename_base = _generate_filename(illust)
                final_output_path = save_path_base / f"{filename_base}.{output_format}"

                _update_task_status(task_id, "processing", f"动图 .zip 下载完成，准备合成为 {output_format}...")
                await _sync_convert_ugoira(
                    str(zip_path),
                    metadata['ugoira_metadata']['frames'],
                    str(save_path_base),
                    str(final_output_path),
                    output_format
                )
                _update_task_status(task_id, "success", f"动图已成功保存至 {final_output_path}", {"final_path": str(final_output_path)})

            else:
                if page_count == 1:
                    url = illust['meta_single_page']['original_image_url']
                    file_ext = os.path.splitext(os.path.basename(urlparse(url).path))[1]
                    filename = _generate_filename(illust) + file_ext
                    final_path = save_path_base / filename
                    await asyncio.to_thread(state.api.download, url, path=str(save_path_base), name=filename)
                else:
                    for i, page in enumerate(illust['meta_pages']):
                        url = page['image_urls']['original']
                        file_ext = os.path.splitext(os.path.basename(urlparse(url).path))[1]
                        filename = _generate_filename(illust, page_num=i) + file_ext
                        await asyncio.to_thread(state.api.download, url, path=str(save_path_base), name=filename)
                
                final_path = save_path_base
                _update_task_status(task_id, "success", f"插画已成功下载至 {final_path}", {"final_path": str(final_path)})

        except Exception as e:
            logger.error(f"背景下载任务 ({task_id} - {illust_id}) 发生未预期错误: {e}", exc_info=True)
            _update_task_status(task_id, "failed", f"发生未预期错误: {str(e)}")
