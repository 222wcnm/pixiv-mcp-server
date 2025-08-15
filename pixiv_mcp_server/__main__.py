import logging
import os
import urllib3
import json
from pathlib import Path
from dotenv import load_dotenv

def setup_environment():
    """
    加载并解析所有环境变量。
    这是启动过程的第一步，确保环境准备就绪。
    """
    load_dotenv()
    
    # 解决部分 MCP 客户端将值以 `KEY=VALUE` 形式传入的问题
    # 仅对白名单中的键进行纠正，避免误伤系统变量
    whitelist_keys = {
        'PIXIV_REFRESH_TOKEN',
        'DOWNLOAD_PATH',
        'FILENAME_TEMPLATE',
        'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
        'PREVIEW_PROXY_ENABLED', 'PREVIEW_PROXY_HOST', 'PREVIEW_PROXY_PORT',
    }
    # 快照环境，避免遍历过程中修改带来的副作用
    env_snapshot = dict(os.environ)
    for key in list(whitelist_keys):
        # 同时考虑大小写变体（部分系统区分大小写，部分不区分）
        candidates = []
        if key in env_snapshot:
            candidates.append((key, env_snapshot[key]))
        lower_key = key.lower()
        if lower_key in env_snapshot and lower_key != key:
            candidates.append((key, env_snapshot[lower_key]))

        for target_key, raw_value in candidates:
            if not isinstance(raw_value, str) or '=' not in raw_value:
                continue
            try:
                k, v = raw_value.split('=', 1)
                # 仅当左侧键名与目标键名一致（忽略大小写）时才进行修正
                if k.strip().lower() == target_key.lower():
                    os.environ[target_key] = v
            except Exception:
                # 忽略无法解析的值，保持原样
                pass

    # 额外兼容：某些客户端会将多行 KEY=VALUE 文本整体注入到任意环境变量值中
    # 这里扫描所有环境变量的值，解析其中的白名单键并写入真实环境
    for any_key, any_value in env_snapshot.items():
        if not isinstance(any_value, str) or ('=' not in any_value):
            continue
        # 仅处理包含换行的批量文本，避免误伤正常的单值配置
        if '\n' not in any_value:
            continue
        for line in any_value.splitlines():
            line = line.strip()
            if not line or '=' not in line:
                continue
            try:
                raw_k, raw_v = line.split('=', 1)
                matched = None
                for wk in whitelist_keys:
                    if wk.lower() == raw_k.strip().lower():
                        matched = wk
                        break
                if matched:
                    os.environ[matched] = raw_v
            except Exception:
                # 忽略无法解析的行
                pass

def main():
    """主函数：初始化并执行服务器"""
    # 步骤 1: 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('pixiv-mcp-server')

    # 步骤 2: 设置环境并加载模块
    # 这个函数必须在导入 state 和其他模块之前调用
    setup_environment()
    
    from .state import state
    from .downloader import HAS_FFMPEG
    from .tools import mcp
    from .api_client import initialize_api_client

    # 步骤 3: 无论认证状态如何，都先初始化API客户端以支持匿名访问
    initialize_api_client()
    
    # 启动本地预览代理（后台线程）
    if state.preview_proxy_enabled:
        try:
            from .preview_proxy import start_preview_proxy
            start_preview_proxy(state.preview_proxy_host, state.preview_proxy_port)
        except Exception as e:
            logger.warning(f"预览代理启动失败: {e}")

    # 步骤 3: 初始化应用
    os.makedirs(state.download_path, exist_ok=True)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    logger.info("Pixiv MCP 服务器启动中...")
    logger.info(f"默认下载路径: {state.download_path}")
    logger.info(f"文件名模板: {state.filename_template}")
    logger.info(f"FFmpeg支持: {'是' if HAS_FFMPEG else '否'}")
    logger.info(
        f"预览代理: {'启用' if state.preview_proxy_enabled else '禁用'}" +
        ("" if not state.preview_proxy_enabled else f" (http://{state.preview_proxy_host}:{state.preview_proxy_port}/pximg?url=...)")
    )

    # 步骤 4: 自动认证 (仅依赖环境变量或.env文件)
    if state.refresh_token:
        logger.info("检测到 refresh_token，正在尝试自动认证...")
        try:
            # 注意：这里的 state.api 是在 initialize_api_client 中创建的
            state.api.auth(refresh_token=state.refresh_token)
            state.is_authenticated = True
            state.user_id = state.api.user_id
            logger.info(f"自动认证成功！用户ID: {state.user_id}")
        except Exception as e:
            state.is_authenticated = False
            logger.warning(f"自动认证失败: {e}")
            logger.warning("将以匿名模式运行。请检查 REFRESH_TOKEN 是否有效或网络/代理设置。")
    else:
        state.is_authenticated = False
        logger.info("未在环境中找到 refresh_token，将以匿名模式运行。")

    # 步骤 5: 运行服务器
    mcp.run(transport="stdio")
    logger.info("Pixiv MCP 服务器已停止。")

if __name__ == "__main__":
    main()
