# Pixiv MCP Server

> 一个功能强大的 Pixiv 工具集，通过模型上下文协议 (MCP) 为大语言模型（如 Claude）提供浏览、搜索和下载 Pixiv 内容的能力。

## ✨ 主要功能

### 🔍 多维度搜索
- 关键词搜索（`search_illust`）
- 用户搜索（`search_user`）
- 标签自动补全（`search_autocomplete`）
- 排行榜浏览（`illust_ranking` - 日榜/周榜/月榜等）
- 热门标签趋势（`trending_tags_illust`）
- 相关作品推荐（`illust_related`）

### 📥 智能下载
- 支持单个或批量作品下载（通过 `download` 工具）
- 异步后台下载，不阻塞 AI 操作
- 自动为多页作品（漫画）或动图创建独立子文件夹
- 动态检测 FFmpeg，自动将动图 (Ugoira) 转换为 GIF 格式
- 智能文件名清理，防止文件系统错误
- 支持随机推荐下载（`download_random_from_recommendation`）

### 👥 社区内容浏览
- 个人推荐内容（`illust_recommended`）
- 关注画师动态（`illust_follow`）
- 用户收藏夹浏览（`user_bookmarks`）
- 关注列表查看（`user_following`）
- 作品详细信息获取（`illust_detail`）

### 🔐 安全认证
- 使用官方推荐的 OAuth 2.0 (PKCE) 流程
- 提供 `get_token.py` 一次性认证向导脚本
- 自动生成和管理 `.env` 配置文件
- 支持令牌刷新功能

## 🔧 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 建议使用最新稳定版 |
| FFmpeg | 最新版 | 可选，用于 Ugoira 动图转 GIF |
| MCP 客户端 | - | 如 Claude for Desktop |

## 🚀 快速开始

### 步骤 1: 克隆或下载项目

```bash
git clone https://github.com/222wcnm/pixiv-mcp-server.git
cd pixiv-mcp-server
```

### 步骤 2: 安装依赖 (推荐使用 uv)

本项目使用 `pyproject.toml` 管理依赖。推荐使用 `uv` 进行安装，它是一个极速的 Python 包管理器。

```bash
# 安装 uv (如果尚未安装)
pip install uv

# 创建虚拟环境并安装依赖
uv venv
uv pip install -e .
```

如果您仍希望使用 `pip`：
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 步骤 3: 获取认证 Token

运行认证向导：

```bash
python get_token.py
```

> **重要提示**：请严格按照终端提示操作。成功后会自动创建 `.env` 配置文件。

### 步骤 4: 启动与配置

完成安装后，项目已经注册为一个系统命令。

#### 直接启动 (可选)
你可以在终端直接运行以下命令来启动服务器：
```bash
pixiv-mcp-server
```

#### 配置 MCP 客户端
在您的 MCP 客户端中，请使用以下配置。

```json
{
  "mcpServers": {
    "pixiv-server": {
      "command": "uv",
      "args": [
        "--directory",
        ".",
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

> **配置说明**：
> - `pixiv-server` 可自定义为任意名称。
> - `command` 使用 `uv`。
> - `args` 中通过 `--directory .` 指定**当前工作目录**为项目根目录（假设您已 `cd` 进入项目文件夹），然后 `run pixiv-mcp-server` 启动服务。
> - `env` 部分为可选配置，未配置的环境变量将从 `.env` 文件读取。

## ✨ 主要功能与工具详解

### 🔍 多维度搜索
- `search_illust(word, ...)` - 根据关键词搜索插画，可选择是否包含 R-18 内容。
- `search_user(word)` - 搜索用户。
- `trending_tags_illust()` - 获取当前的热门标签趋势。
- `illust_related(illust_id)` - 获取与指定插画相关的推荐作品。

### 📥 智能下载
- `download(illust_id, illust_ids)` - 异步后台下载单个或多个作品。工具会自动判断类型并应用智能存储规则。动图(Ugoira)会自动转换为高质量GIF，并清理临时文件。
- `download_random_from_recommendation(count)` - 从用户的Pixiv推荐页随机下载N张插画。此为完成此类请求的最佳方式，会自动处理下载和动图转换。
- `set_download_path(path)` - 设置图片和动图的默认本地保存位置。路径不存在时会自动创建。

### 👥 社区内容浏览
- `illust_recommended()` - 获取官方推荐插画的文本列表。注意：此工具只返回作品信息，不执行下载。如需下载，请使用'download_random_from_recommendation'工具。
- `illust_follow()` - 获取已关注作者的最新作品（首页动态）(需要认证)。
- `user_bookmarks(user_id)` - 获取用户的收藏列表 (需要认证)。
- `user_following(user_id)` - 获取用户的关注列表 (需要认证)。
- `illust_detail(illust_id)` - 获取单张插画的详细信息。
- `illust_ranking(mode)` - 获取插画排行榜（日榜/周榜/月榜等）。

### 🔐 安全认证
- 使用官方推荐的 OAuth 2.0 (PKCE) 流程。
- 提供 `get_token.py` 一次性认证向导脚本。
- 自动生成和管理 `.env` 配置文件。
- 支持令牌刷新功能。
- **重要提示**：服务器启动时会自动尝试使用环境变量中的 `PIXIV_REFRESH_TOKEN` 进行认证。无需手动调用认证工具。

## 🚀 最新更新与改进

- **更稳定的 MCP 客户端配置**：优化了启动配置，现在无需客户端支持 `cwd` 字段，通过 `uv --directory` 参数直接指定项目路径，兼容性更强。
- **动图（Ugoira）合成质量提升**：修复了动图转换时可能出现的画面不完整或黑色块问题，现在生成的 GIF 质量更高。
- **下载任务反馈优化**：修改了 `download` 工具的返回话术，明确提示动图合成可能需要时间，避免 AI 重复调用。
- **自动清理临时文件**：修复了动图转换后遗留 `.zip` 压缩包的 Bug，现在会自动清理。
- **移除了冗余的 `auth` 工具**：简化了工具集，避免 AI 在自动认证失败时误导性地向用户索要 Token。
- **全面优化工具描述**：对所有工具的描述和返回话术进行了细致调整，提升 AI 对工具的理解和交互体验。

## ⚙️ 环境变量配置

| 变量名 | 必需 | 描述 | 默认值 |
|--------|------|------|--------|
| `PIXIV_REFRESH_TOKEN` | ✅ | Pixiv API 认证令牌 | 无 |
| `DOWNLOAD_PATH` | ❌ | 下载文件根目录 | `./downloads` |
| `FILENAME_TEMPLATE` | ❌ | 文件命名模板 | `{author} - {title}_{id}` |
| ~~`https_proxy`~~ | ❌ | ~~代理服务器地址~~ | ~~无~~ |

### 文件命名模板变量

- `{author}` - 作者名称
- `{title}` - 作品标题
- `{id}` - 作品 ID

## 🔗 相关资源

- **FastMCP**: [MCP 服务器框架](https://github.com/jlowin/fastmcp)
- **pixivpy3**: [Pixiv API Python 库](https://github.com/upbit/pixivpy)
- **MCP 协议**: [模型上下文协议文档](https://modelcontextprotocol.io/)

## ⚠️ 免责声明

本工具旨在便于用户通过现代 AI 工具访问个人 Pixiv 账号内容。使用时请：

- 遵守 Pixiv 用户协议
- 负责任地使用工具
- 尊重版权和创作者权益

开发者对任何账号相关问题不承担责任。所有操作均代表用户本人意愿。

---

> **🤖 AI 生成内容说明**  
> 本项目的代码和文档内容完全由人工智能生成。虽然经过了结构分析和功能测试，但仍可能存在不完善之处。使用前请仔细测试，如遇问题请及时反馈。

*如有问题或建议，欢迎反馈交流。*
