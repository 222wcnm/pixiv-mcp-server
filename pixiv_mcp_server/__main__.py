import logging
import os
import urllib3
from dotenv import load_dotenv

def setup_environment():
    """
    加载并解析所有环境变量。
    这是启动过程的第一步，确保环境准备就绪。
    """
    load_dotenv()
    
    # 解决部分MCP客户端使用 `KEY=VALUE` 格式传递环境变量的问题
    # 这段逻辑必须在任何其他模块导入之前执行
    for key, value in os.environ.items():
        if '=' in value:
            try:
                k, v = value.split('=', 1)
                os.environ[k] = v
            except ValueError:
                pass # 忽略无法解析的值

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

    # 步骤 3: 初始化应用
    os.makedirs(state.download_path, exist_ok=True)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    logger.info("Pixiv MCP 服务器启动中...")
    logger.info(f"默认下载路径: {state.download_path}")
    logger.info(f"文件名模板: {state.filename_template}")
    logger.info(f"FFmpeg支持: {'是' if HAS_FFMPEG else '否'}")

    # 步骤 4: 自动认证
    if state.refresh_token:
        logger.info("正在尝试使用环境变量中的 PIXIV_REFRESH_TOKEN 自动认证...")
        try:
            state.api.auth(refresh_token=state.refresh_token)
            state.is_authenticated = True
            state.user_id = state.api.user_id
            logger.info(f"自动认证成功，用户ID: {state.user_id}")
        except Exception as e:
            logger.warning(f"自动认证失败: {e}")
            logger.warning("请检查您的 REFRESH_TOKEN 是否有效或网络连接/代理设置是否正确。")
    else:
        logger.info("未找到 PIXIV_REFRESH_TOKEN，需要手动使用 auth 工具进行认证。")

    # 步骤 5: 运行服务器
    mcp.run(transport="stdio")
    logger.info("Pixiv MCP 服务器已停止。")

if __name__ == "__main__":
    main()
