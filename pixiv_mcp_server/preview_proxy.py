import asyncio
import logging
import os
from urllib.parse import urlparse

from aiohttp import web, ClientSession, ClientTimeout

logger = logging.getLogger('pixiv-mcp-server')


async def _handle_pximg(request: web.Request, proxy: str | None) -> web.StreamResponse:
    url = request.query.get('url', '').strip()
    if not url:
        return web.json_response({'ok': False, 'error': 'missing url'}, status=400)

    try:
        p = urlparse(url)
    except Exception:
        return web.json_response({'ok': False, 'error': 'invalid url'}, status=400)

    # 仅允许 Pixiv 图片域名，避免滥用
    host = (p.hostname or '').lower()
    if not (host.endswith('pximg.net') or host.endswith('pixiv.net')):
        return web.json_response({'ok': False, 'error': 'host not allowed'}, status=403)

    headers = {
        'Referer': 'https://www.pixiv.net/',
        'User-Agent': 'Mozilla/5.0 (PixivPreviewProxy)',
    }
    timeout = ClientTimeout(total=30)

    async with ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers, proxy=proxy) as resp:
                content = await resp.read()
                ctype = resp.headers.get('Content-Type', 'application/octet-stream')
                return web.Response(body=content, content_type=ctype, status=resp.status)
        except Exception as e:
            logger.warning(f'Fetch failed: {e}')
            return web.json_response({'ok': False, 'error': str(e)}, status=502)


def start_preview_proxy(host: str, port: int, proxy: str | None) -> None:
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def handler_wrapper(request):
            return await _handle_pximg(request, proxy)

        app = web.Application()
        app.add_routes([web.get('/pximg', handler_wrapper)])
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, host=host, port=port)
        loop.run_until_complete(site.start())
        logger.info(f'预览代理已监听 http://{host}:{port}/pximg?url=...')
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(runner.cleanup())
            loop.close()

    import threading
    th = threading.Thread(target=_run, name='pximg-proxy', daemon=True)
    th.start()
