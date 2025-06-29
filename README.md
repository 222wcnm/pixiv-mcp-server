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

### 步骤 1: 获取项目文件

下载以下核心文件：
- `pixiv_mcp_server.py` - 主服务器程序
- `get_token.py` - 认证与配置向导
- `requirements.txt` - 依赖文件

### 步骤 2: 安装依赖

在项目目录下运行：

```bash
pip install -r requirements.txt
```

### 步骤 3: 获取认证 Token

运行认证向导：

```bash
python get_token.py
```

> **重要提示**：请严格按照终端提示操作。成功后会自动创建 `.env` 配置文件。

### 步骤 4: 配置 MCP 客户端

在您的 MCP 客户端（如 Claude for Desktop）中添加新服务器：

```json
{
  "mcpServers": {
    "pixiv-server": {
      "command": "python",
      "args": [
        "/path/to/your/project/pixiv_mcp_server.py"
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
> - `pixiv-server` 可自定义为任意名称
> - `environment` 部分为可选配置
> - 未配置的环境变量将从 `.env` 文件读取

## 🛠️ 工具功能详解

### 认证与配置
- `auth(token)` - 手动认证（通常不需要，`.env` 文件自动处理）
- `set_download_path(path)` - 更改下载目录

### 核心下载功能
- `download(illust_id, illust_ids)` - 异步下载单个或多个作品
- `download_random_from_recommendation(count)` - 随机下载推荐作品

### 搜索与发现
- `search_illust(word, ...)` - 插画搜索（支持 R-18 内容过滤）
- `search_user(word)` - 用户搜索
- `search_autocomplete(word)` - 标签自动补全
- `trending_tags_illust()` - 获取热门标签

### 浏览与信息获取
- `illust_detail(illust_id)` - 获取作品详细信息
- `illust_related(illust_id)` - 查找相似作品
- `illust_ranking(mode)` - 获取排行榜

### 个人化内容（需要认证）
- `illust_recommended()` - 获取个人推荐
- `illust_follow()` - 关注画师的最新作品
- `user_bookmarks(user_id)` - 查看收藏夹
- `user_following(user_id)` - 查看关注列表

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
