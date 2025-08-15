我先做一次快速代码阅览来了解架构、工具定义与当前变更点，然后给出问题清单、优化建议与“目的论”设计，再据此评估与重构工具的协作方式。现在开始并行读取关键文件。
Read file: pixiv_mcp_server/__main__.py
Read file: pixiv_mcp_server/tools.py
Read file: pixiv_mcp_server/state.py
Read file: pixiv_mcp_server/api_client.py
Read file: pixiv_mcp_server/utils.py
Read file: pixiv_mcp_server/config.py
Read file: pixiv_mcp_server/downloader.py
Read file: pixiv_mcp_server/preview_proxy.py

我已完成首次通读，梳理了当前入口、配置、状态管理、API 封装、工具集与下载/预览组件。下面给出问题清单、优化建议与“目的论”设计，并基于此调整工具清单与协作方式，最后附上关键 P0 改动的代码草案。

### 项目快速画像
- 入口与环境：`__main__.py` 负责环境矫正、日志、自动认证、预览代理线程与服务器启动。
- 配置/状态：`config.py`（Pydantic 配置），`state.py`（全局状态含并发控制、下载任务、分页缓存等）。
- API 层：`api_client.py` 将 `pixivpy3` 同步方法转为异步；提供 `next_page` 的底层拼装。
- 工具层：`tools.py` 基于 `FastMCP` 注册工具，核心用 `_api_tool_handler` 统一数据拉取、代理注入、视图渲染与错误处理。
- 下载与代理：`downloader.py`（队列+并发下载、Ugoira 转码）、`preview_proxy.py`（aiohttp 直链代理）。
- 实用：`utils.py`（序列化兜底、鉴权保护、代理注入、卡片渲染等）。

### 主要问题与风险
- 认证前不可用的“无需鉴权工具”
  - 目前仅在自动认证成功后才调用 `initialize_api_client()`，导致本应“可匿名使用”的工具（如 `search_illust`）也会因为 `state.api_client` 为 None 而失败。
- 翻页脆弱性
  - `next_page` 通过 URL 字符串猜测 `response_key`（`users`/`illust`），易失效。应由状态保存上一次的 `response_key` 或返回“游标 ID”供后续翻页。
- 返回结构不完全统一
  - `ensure_json_serializable` 未覆盖所有工具；部分工具返回形态与 `_api_tool_handler` 的“cards/raw”差异较大，Agent 难以稳定消费。
- 身份认证缺失工具
  - 缺少 `auth_login/auth_logout/auth_status` 等；用户需要手动改 `auth.json` 或环境变量，使用体验不佳。
- 运行态/配置控制缺口
  - 缺少 `set_filename_template`、`set_default_limit`、`set_view_mode`、`toggle_nsfw`、`set_preview_proxy(...)` 等设置类工具；预览代理只能通过环境和启动时机控制。
- 下载任务生命周期与治理
  - `download_tasks` 会无限增长；无清理/GC、取消、重试、持久化策略。
- 代理一致性与安全性
  - API 代理取自 `settings.https_proxy`，预览代理取自环境变量；建议统一来源并提供工具化开关。预览代理缺少限流/并发限制与更细域名白名单。
- 细节改进
  - `_api_tool_handler` 本地切片 limit，但没有显式 `has_more` 标志；`search_r18` 直接拼接“R-18”可能偏执于标签检索；日志使用私有属性（`_value`）；部分工具缺少 `ensure_json_serializable`。

### 优化建议（按优先级）
- P0（稳定性/可用性）
  - 启动时无论是否认证都初始化 `state.api_client`。
  - 为 `_api_tool_handler` 和 `next_page` 引入 `state.last_response_key` 或“分页游标”模型，去除 URL 猜测。
  - 增加 `auth_login/auth_logout/auth_status`，并在登录成功后刷新 `auth.json`。
  - 统一响应骨架（ok、error/message、view、cards/raw、display_count、next/has_more/nsfw_filtered）。
  - 为下载任务增加简易 GC（如仅保留最近 N 条/超过 T 分钟的完成任务清理）。
- P1（体验/可观测）
  - 设置类工具：`set_filename_template`、`set_default_limit`、`set_view_mode`、`toggle_nsfw_default`、`set_preview_proxy(enabled, host?, port?)`。
  - 预览代理增加并发限制与简单限流；API/预览代理来源统一（优先 settings，其次 env）。
  - 完善 `next_page` 输出：`next_available: bool`、`cursor_id`（可选）。
  - 将所有工具包裹 `ensure_json_serializable`，并将错误结构化。
- P2（功能扩展）
  - 用户与作品动作：收藏/取关/关注（若符合项目范围）。
  - 下载增强：`download_cancel(task_id)`、`download_from_list(illust_ids)` 支持大型批量、失败重试次数。
  - 更多浏览：`user_detail(user_id)`、`illust_comments(illust_id)`。

### 目的论（Purpose-first 设计）
- 目标
  - 让 LLM/Agent 能“浏览-筛选-预览-下载”Pixiv 内容，具备“低摩擦、可组合、可观测、安全合规”的交互能力。
- 非目标
  - 不做完整 Pixiv 客户端；不覆盖登录表单流程（保留 Refresh Token 路径）；不做重型任务调度。
- 关键质量属性
  - 稳定：无认证也可使用可匿名接口；翻页稳定；响应结构一致。
  - 可组合：所有浏览工具统一参数/返回，分页游标可互通；下载工具接受上一步输出的 ID 列表。
  - 可观测：每次响应含统计/下一步提示；下载任务可查询/可取消。
  - 安全：预览代理白名单+限流；NSFW 默认关闭可切换；代理设置一致。
  - 易用：设置类工具即可热更新运行态；错误信息清晰可操作。

### 基于目的论的工具编排与调整

- 认证与环境（新增/调整）
  - 新增：`auth_login(refresh_token: str)`、`auth_logout()`、`auth_status()`
  - 新增：`set_preview_proxy(enabled: bool, host?: str, port?: int)`（启/停线程，热切换）
  - 权衡：保留启动时自动认证，但不再依赖它作为唯一入口
- 浏览与查询（保留 + 统一）
  - 保留：`search_illust`、`search_user`、`illust_detail`、`illust_related`、`illust_ranking`、`illust_recommended`、`illust_follow`、`user_bookmarks`、`user_following`
  - 统一参数：`offset`、`view`、`limit`、`search_r18`（明确行为：作为过滤器，而非简单“拼词”）
  - 统一返回：`view`、`cards`/`raw`、`display_count`、`total_count?`、`next`（含 `has_more` 或 `cursor_id`）
- 分页（调整）
  - 保留：`next_page`，但改为基于 `state.last_response_key`/`cursor_id`，不再解析 URL 猜测类型；返回 `next_available`。
- 下载（保留 + 扩展）
  - 保留：`download(illust_id|illust_ids)`、`get_download_status(task_id|task_ids)`
  - 新增：`download_cancel(task_id)`、（可选）`download_from_recommendations(count)` 重命名为 `download_from_recommendations_random(count)`
  - 统一设置：`set_download_path(path)`、`set_ugoira_format(format)`，并新增 `set_filename_template(template)`（热更新）
  - 任务治理：新增 `tasks_gc(keep_last: int = 100)` 或配置化自动 GC
- 呈现/全局设置（新增）
  - 新增：`set_default_limit(n)`、`set_view_mode(view)`、`toggle_nsfw_default(enabled: bool)`
- 管理与健康（新增）
  - 新增：`health()`、`version()`、`config_get()`、`config_set(key, value)`（白名单）

- 协作设计要点
  - 所有“列表类”工具在响应中放入 `next` 字段（包含 `next_url`/`cursor_id` 与 `has_more`），`next_page` 只需消费此字段。
  - “下载类”工具可直接接受“列表类”响应中的 `cards -> id` 列表，避免客户端解析负担。
  - 设置类工具即时更新 `state`，并对关键项（如预览代理）执行副作用（启停线程/重建链接）。

### 关键 P0 代码级改动草案

- 启动时始终初始化 API 客户端（无论是否认证）
```100:142:pixiv_mcp_server/__main__.py
    # 步骤 2: 设置环境并加载模块
    # 这个函数必须在导入 state 和其他模块之前调用
    setup_environment()
    
    from .state import state
    from .downloader import HAS_FFMPEG
    from .tools import mcp
    from .api_client import initialize_api_client
    
    # 启动本地预览代理（后台线程）
    if state.preview_proxy_enabled:
        ...
```
建议在加载后立刻调用：
```python
# 在 setup_environment() 之后、任何 API 调用之前
initialize_api_client()
```

- 在状态里显式保存 `last_response_key`，并由 `_api_tool_handler` 维护
```1:58:pixiv_mcp_server/state.py
class PixivState:
    def __init__(self):
        ...
        self.last_response = {}
        self.last_response_key: Optional[str] = None
```

- 统一由 `_api_tool_handler` 设置 `last_response_key`，`next_page` 不再猜测
```python
# tools.py 内 _api_tool_handler 成功拿到 json_result 后
state.last_response = json_result
state.last_response_key = response_key
```

- 修正 `next_page`，按状态读取键并生成输出
```python
# 简化：优先用 state.last_response_key
response_key = state.last_response_key or "illusts"
```

- 新增认证工具（示例）
```python
# 新增到 tools.py
@mcp.tool()
async def auth_login(refresh_token: str) -> dict:
    from .api_client import initialize_api_client
    try:
        state.api.auth(refresh_token=refresh_token)
        state.is_authenticated = True
        state.user_id = state.api.user_id
        state.refresh_token = state.api.refresh_token
        initialize_api_client()
        Path("auth.json").write_text(json.dumps({"refresh_token": state.refresh_token}, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "user_id": state.user_id}
    except Exception as e:
        return {"ok": False, "error": f"认证失败: {e}"}

@mcp.tool()
async def auth_status() -> dict:
    return {"ok": True, "is_authenticated": state.is_authenticated, "user_id": state.user_id}

@mcp.tool()
async def auth_logout() -> dict:
    state.is_authenticated = False
    state.user_id = None
    state.refresh_token = ""
    return {"ok": True, "message": "已登出（令牌未自动删除，可手动清理 auth.json）"}
```

- 新增预览代理设置（示例）
```python
# 新增到 tools.py
@mcp.tool()
async def set_preview_proxy(enabled: bool, host: Optional[str] = None, port: Optional[int] = None) -> dict:
    try:
        state.preview_proxy_enabled = enabled
        if host: state.preview_proxy_host = host
        if port: state.preview_proxy_port = port
        if enabled:
            from .preview_proxy import start_preview_proxy
            start_preview_proxy(state.preview_proxy_host, state.preview_proxy_port)
        return {"ok": True, "enabled": enabled, "host": state.preview_proxy_host, "port": state.preview_proxy_port}
    except Exception as e:
        return {"ok": False, "error": f"设置预览代理失败: {e}"}
```

- 统一工具返回（建议把尚未包裹的工具也加上 `@ensure_json_serializable`，并返回含 `view/display_count/next_available` 等字段）

### 最简实施顺序（建议）
- P0 一次性完成：初始化顺序修正、`last_response_key` 引入、`auth_*` 工具、`next_page` 修正、返回统一化、下载任务 GC。
- P1 设置类与预览代理工具；限流与观测细节。
- P2 功能扩展视资源安排推进。

- 工具去留建议
  - 保留：现有浏览与下载类工具（均统一返回与分页）
  - 重命名：`download_random_from_recommendation` -> `download_from_recommendations_random`
  - 新增：`auth_*`、`set_preview_proxy`、`set_filename_template`、`set_default_limit`、`set_view_mode`、`toggle_nsfw_default`、`download_cancel`、`tasks_gc`、`health`、`version`
  - 可删除：`structure_tool_response` 若全量改用 `_api_tool_handler` 的统一返回；或反向采用它做唯一统一出口（二选一，避免并存）

### 状态更新
- 我已阅读 `__main__.py`、`tools.py`、`state.py`、`api_client.py`、`utils.py`、`downloader.py`、`preview_proxy.py`，梳理出架构与问题点，并给出按优先级的优化与工具编排方案，附关键 P0 改动草案代码。

- 关键影响
  - 解决“未认证时无法调用匿名接口”的可用性问题。
  - 令翻页稳定、响应统一，Agent 更易消费与编排。
  - 增加认证/设置类工具，减少环境手工操作。
  - 改善下载任务治理与预览代理安全性。

- 后续如需，我可以基于上述建议直接提交具体edits（分 P0→P1→P2 批次），并补充简单集成测试脚本。