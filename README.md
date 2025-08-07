# Pixiv MCP Server

> 一个功能强大的 Pixiv 工具集，通过模型上下文协议 (MCP) 为大语言模型（如 Claude）提供浏览、搜索和下载 Pixiv 内容的能力。

## ✨ 主要功能

### 📥 下载与任务管理
- `download(illust_id)`: 异步下载指定作品，返回任务ID用于追踪。
- `get_download_status(task_id)`: 查询下载任务的实时状态（排队、下载中、成功、失败）。
- `download_random_from_recommendation(count)`: 从个性化推荐中随机下载指定数量的作品。
- `set_download_path(path)`: 自定义作品的本地保存路径。
- `set_ugoira_format(format)`: 设定动图（Ugoira）保存的格式（`webp` 或 `gif`）。

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

---

## 🔧 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 建议使用最新稳定版 |
| FFmpeg | 最新版 | **可选**，用于下载动图 (Ugoira) |
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
