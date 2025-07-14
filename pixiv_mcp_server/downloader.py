import asyncio
import logging
import os
import shutil
import subprocess
import sys
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

def _sync_convert_ugoira_to_gif(zip_path: str, frames: List[Dict], work_dir: str, output_gif_path: str) -> str:
    """将 Ugoira 的 zip 文件同步转换为 GIF，并增强了错误处理。"""
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

        absolute_output_gif_path = str(Path(output_gif_path).resolve())

        # 使用更先进的 palettegen/paletteuse 滤镜来提高GIF质量，避免颜色失真和黑色块
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', "frame_list.txt",
            '-vf', "split[s0][s1];[s0]palettegen=stats_mode=single[p];[s1][p]paletteuse=new=1",
            '-y',
            absolute_output_gif_path
        ]
        
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        subprocess.run(
            cmd, cwd=temp_dir, check=True, capture_output=True, 
            text=True, encoding='utf-8', creationflags=creationflags
        )
        return output_gif_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed for {Path(output_gif_path).stem}. Exit code: {e.returncode}")
        logger.error(f"FFmpeg stderr:\n{e.stderr}")
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred during GIF conversion for {Path(output_gif_path).stem}: {e}")
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        # 确保在转换完成后删除原始的zip文件
        if os.path.exists(zip_path):
            os.remove(zip_path)

async def _background_download_single(illust_id: int):
    """在背景下载单个作品，并应用智能存储和命名规则"""
    async with state.download_semaphore:
        logger.info(f"背景任务开始：处理作品 ID {illust_id}，当前并发数: {5 - state.download_semaphore._value}/{5}")
        try:
            detail_result = await asyncio.to_thread(state.api.illust_detail, illust_id)
            error = handle_api_error(detail_result)
            if error:
                logger.error(f"下载失败 ({illust_id}): 无法获取作品信息: {error}")
                return

            illust = detail_result['illust']
            page_count = illust.get('page_count', 1)
            illust_type = illust.get('type')
            
            save_path_base = Path(state.download_path)
            if page_count > 1 or illust_type == 'ugoira':
                sub_folder_name = _sanitize_filename(f"{illust_id} - {illust.get('title', 'Untitled')}")
                save_path_base = save_path_base / sub_folder_name
            
            save_path_base.mkdir(parents=True, exist_ok=True)
            
            if illust_type == 'ugoira':
                if not HAS_FFMPEG:
                    logger.warning(f"跳过动图转换 ({illust_id}): 未找到 FFmpeg。")
                    return
                
                metadata = await asyncio.to_thread(state.api.ugoira_metadata, illust_id)
                error = handle_api_error(metadata)
                if error:
                    logger.error(f"下载失败 ({illust_id}): 无法获取动图元数据: {error}")
                    return
                
                zip_url = metadata['ugoira_metadata']['zip_urls']['medium']
                zip_filename = os.path.basename(urlparse(zip_url).path)
                zip_path = save_path_base / zip_filename
                
                await asyncio.to_thread(state.api.download, zip_url, path=str(save_path_base))
                logger.info(f"动图 {illust_id} 的 .zip 文件已下载至 {zip_path}")
                
                gif_filename_base = _generate_filename(illust)
                final_gif_path = save_path_base / f"{gif_filename_base}.gif"

                await asyncio.to_thread(
                    _sync_convert_ugoira_to_gif,
                    str(zip_path),
                    metadata['ugoira_metadata']['frames'],
                    str(save_path_base),
                    str(final_gif_path)
                )
                logger.info(f"背景任务成功：动图 {illust_id} 已转换为 GIF: {final_gif_path}")

            else:
                if page_count == 1:
                    url = illust['meta_single_page']['original_image_url']
                    file_ext = os.path.splitext(os.path.basename(urlparse(url).path))[1]
                    filename = _generate_filename(illust) + file_ext
                    await asyncio.to_thread(state.api.download, url, path=str(save_path_base), name=filename)
                else:
                    for i, page in enumerate(illust['meta_pages']):
                        url = page['image_urls']['original']
                        file_ext = os.path.splitext(os.path.basename(urlparse(url).path))[1]
                        filename = _generate_filename(illust, page_num=i) + file_ext
                        await asyncio.to_thread(state.api.download, url, path=str(save_path_base), name=filename)
                
                logger.info(f"背景任务成功：插画 {illust_id} 已下载至 {save_path_base}")

        except Exception as e:
            logger.error(f"背景下载任务 ({illust_id}) 发生未预期错误: {e}", exc_info=True)
