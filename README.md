# Pixiv MCP Server v2.0

> 一个功能强大的 Pixiv 工具集，通过模型上下文协议 (MCP) 为大语言模型（如 Claude）提供浏览、搜索和下载 Pixiv 内容的能力。经过全面重构，现已支持下载状态跟踪和高性能动图转换。

## ✨ v2.0 核心功能重构

本次更新对核心功能进行了彻底重构，显著提升了应用的健壮性、性能和用户体验。

### 1. 引入下载任务状态跟踪
- **解决“即发即忘”**: `download` 工具不再是简单的触发，而是会返回一个唯一的 **任务ID**。
- **实时进度查询**: 通过新增的 `get_download_status` 工具，AI 可以根据任务ID实时查询每个下载任务的状态（如排队中、下载中、处理中、成功、失败）。
- **透明的错误处理**: 下载失败时，状态查询会返回详细的错误信息，便于调试和重试。

### 2. 动图 (Ugoira) 合成性能优化
- **默认使用 WebP**: 动图默认转换为性能和质量更优的 **WebP** 格式，文件体积更小，加载速度更快。
- **性能参数调优**: 优化了 FFmpeg 的调用参数，使用 `-preset ultrafast` 等选项显著加快了合成速度。
- **并发控制**: 引入信号量（Semaphore）机制，智能控制 CPU 密集型任务（如视频转码）的并发数量，防止系统过载，保证多任务并行处理的稳定性。
- **格式可切换**: 新增 `set_ugoira_format` 工具，允许用户在 `webp` 和 `gif` 之间按需切换。

### 3. 代码质量与可维护性提升
- **认证逻辑重构**: 使用 `@require_authentication` 装饰器统一了所有需要登录的工具的认证流程，遵循了 DRY (Don't Repeat Yourself) 原则，代码更简洁、更易于维护。
- **配置加载优化**: 确认并优化了启动时的配置加载逻辑，确保环境变量的正确读取和应用。

---

## 🔧 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 建议使用最新稳定版 |
| FFmpeg | 最新版 | **必需**，用于 Ugoira 动图转 WebP/GIF |
| MCP 客户端 | - | 如 Claude for Desktop |

## 🚀 快速开始

### 步骤 1: 克隆或下载项目
```bash
git clone https://github.com/222wcnm/pixiv-mcp-server.git
cd pixiv-mcp-server
```

### 步骤 2: 安装依赖 (推荐使用 uv)
```bash
# 安装 uv (如果尚未安装)
pip install uv

# 创建虚拟环境并安装依赖
uv venv
uv pip install -e .
```

### 步骤 3: 获取认证 Token
运行认证向导：
```bash
python get_token.py
```
> **重要提示**：请严格按照终端提示操作。成功后会自动创建 `.env` 配置文件。

### 步骤 4: 启动与配置
在您的 MCP 客户端中，请使用以下配置。
```json
{
  "mcpServers": {
    "pixiv-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/pixiv-mcp-server",
        "run",
        "pixiv-mcp-server"
      ],
      "env": {
        "PIXIV_REFRESH_TOKEN": "从.env文件复制或留空自动读取",
        "DOWNLOAD_PATH": "./downloads",
        "FILENAME_TEMPLATE": "{author}_{id}_{title}"
      }
    }
  }
}
```
> **配置说明**：请务必将 `/path/to/your/pixiv-mcp-server` 替换为项目根目录的**绝对路径**。

## ✨ 主要功能与工具详解

### 📥 智能下载与状态管理
- `download(illust_id, illust_ids)`: **异步后台下载**。此工具会为每个作品创建一个后台任务，并返回一个包含**任务ID列表**的JSON对象。
- `get_download_status(task_id, task_ids)`: **查询下载状态**。使用 `download` 工具返回的任务ID来查询一个或多个任务的实时状态（如 `queued`, `downloading`, `processing`, `success`, `failed`）和详细信息。
- `download_random_from_recommendation(count)`: 从用户推荐中随机下载N张插画，并返回下载任务ID。
- `set_download_path(path)`: 设置下载文件的根目录。
- `set_ugoira_format(format)`: 设置动图转换的输出格式，支持 `webp` (默认) 和 `gif`。

### 🔍 多维度搜索
- `search_illust(word, ...)`: 根据关键词搜索插画。
- `search_user(word)`: 搜索用户。
- `trending_tags_illust()`: 获取当前的热门标签趋势。
- `illust_ranking(mode)`: 获取插画排行榜（日榜/周榜/月榜等）。
- `illust_related(illust_id)`: 获取相关推荐作品。

### 👥 社区内容浏览
- `illust_recommended()`: 获取官方推荐插画列表。
- `illust_follow()`: 获取已关注作者的最新作品（需要认证）。
- `user_bookmarks(user_id)`: 获取用户的收藏列表（需要认证）。
- `user_following(user_id)`: 获取用户的关注列表（需要认证）。
- `illust_detail(illust_id)`: 获取单张插画的详细信息。

### 🔐 安全认证
- 使用官方推荐的 OAuth 2.0 (PKCE) 流程，通过 `get_token.py` 脚本简化认证。
- 服务器启动时会自动使用 `PIXIV_REFRESH_TOKEN` 环境变量进行认证。

## ⚙️ 环境变量配置

| 变量名 | 必需 | 描述 | 默认值 |
|--------|------|------|--------|
| `PIXIV_REFRESH_TOKEN` | ✅ | Pixiv API 认证令牌 | 无 |
| `DOWNLOAD_PATH` | ❌ | 下载文件根目录 | `./downloads` |
| `FILENAME_TEMPLATE` | ❌ | 文件命名模板 | `{author} - {title}_{id}` |

## 🔗 相关资源
- **FastMCP**: [MCP 服务器框架](https://github.com/jlowin/fastmcp)
- **pixivpy3**: [Pixiv API Python 库](https://github.com/upbit/pixivpy)
- **MCP 协议**: [模型上下文协议文档](https://modelcontextprotocol.io/)

## ⚠️ 免责声明
本工具旨在便于用户通过现代 AI 工具访问个人 Pixiv 账号内容。使用时请遵守 Pixiv 用户协议，并尊重版权和创作者权益。开发者对任何账号相关问题不承担责任。

---

> **🤖 AI 生成内容说明**  
> 本项目的代码和文档内容完全由人工智能生成。虽然经过了结构分析和功能测试，但仍可能存在不完善之处。使用前请仔细测试，如遇问题请及时反馈。
