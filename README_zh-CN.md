# Pixiv MCP Server

<p align="center">
  <a href="https://github.com/222wcnm/pixiv-mcp-server">
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python Version">
  </a>
  <a href="https://github.com/222wcnm/pixiv-mcp-server/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  </a>
  <a href="https://github.com/222wcnm/pixiv-mcp-server/issues">
    <img src="https://img.shields.io/github/issues/222wcnm/pixiv-mcp-server" alt="Issues">
  </a>
  <a href="https://github.com/222wcnm/pixiv-mcp-server/stargazers">
    <img src="https://img.shields.io/github/stars/222wcnm/pixiv-mcp-server" alt="Stargazers">
  </a>
</p>

<p align="center">
  一个功能强大的 Pixiv 工具集，通过模型上下文协议 (MCP) 为大语言模型（如 Claude / Cursor 等）提供浏览、搜索和下载 Pixiv 内容的能力。现在支持全新的卡片式视图，带来更直观的交互体验。
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

---

## ✨ 主要功能

### 🛠️ 通用工具
- **`next_page()`**: 获取上一条指令结果的下一页内容。
- **`update_setting(key, value)`**: 在运行时更新任意服务器配置 (例如 `download_path`)。

### 📥 下载管理
- **`download(illust_id | illust_ids, ...)`**: 异步下载指定作品。可接受额外参数 (如 `webp_quality`, `gif_preset` 等) 来控制动图转换质量。
- **`manage_download_tasks(task_id, action)`**: 管理下载任务。支持 `status` 和 `cancel` 操作。

### 🔍 搜索与发现
- **`search_illust(word, ...)`**: 根据关键词搜索插画。
- **`search_user(word, ...)`**: 搜索用户。
- **`get_illust_ranking(mode, ...)`**: 获取插画排行榜 (日榜/周榜/月榜等)。
- **`get_illust_related(illust_id, ...)`**: 获取相关推荐作品。
- **`get_illust_recommended(...)`**: 获取官方推荐插画 (需认证)。
- **`get_trending_tags()`**: 获取热门标签趋势。
- **`get_illust_detail(illust_id)`**: 获取单张插画详细信息。

### 👥 社区与用户
- **`get_follow_illusts(...)`**: 获取关注作者的最新作品 (需认证)。
- **`get_user_bookmarks(user_id_to_check, ...)`**: 获取用户收藏列表 (需认证)。
- **`get_user_following(user_id_to_check, ...)`**: 获取用户关注列表 (需认证)。

---

## ⚙️ 输出视图

为了提升在 AI 对话中的使用体验，本工具集引入了 `view` 参数来控制输出格式：

- **`view='cards'` (默认)**: 以图文并茂的 Markdown 卡片形式展示结果。这是最推荐的模式，它直观、美观，并直接内嵌了图片预览，无需额外点击链接。
- **`view='raw'`**: 返回原始的、未经处理的 JSON 数据。此模式适合需要将结果用于其他工具或进行程序化处理的场景。

默认视图已内置为 `cards`，无法通过环境变量修改。

## 🔧 环境要求

| 组件 | 版本要求 | 说明 |
|:---|:---|:---|
| **Python** | `3.10+` | 建议使用最新稳定版 |
| **FFmpeg** | 最新版 | 可选，用于下载动图 (Ugoira) |
| **MCP 客户端** | - | 如 Claude for Desktop / Cursor |

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
> 成功后会自动创建或更新 `.env` 配置文件（含 `PIXIV_REFRESH_TOKEN`）。

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
        "FILENAME_TEMPLATE": "{author} - {title}_{id}",
        "DEFAULT_LIMIT": "10",
        "UGOIRA_FORMAT": "webp"
      }
    }
  }
}
```
> 请将 `/path/to/your/pixiv-mcp-server` 替换为项目根目录的绝对路径。  

## ⚙️ 环境变量配置

| 变量名                    | 必需 | 描述                                           | 默认值                    |
|:--------------------------|:---:|:-----------------------------------------------|:--------------------------|
| `PIXIV_REFRESH_TOKEN`     | ✅  | Pixiv API 认证令牌。                           | `""`                      |
| `DOWNLOAD_PATH`           | ❌  | 下载文件的根目录。                             | `./downloads`             |
| `FILENAME_TEMPLATE`       | ❌  | 文件命名模板。                                 | `{author} - {title}_{id}` |
| `UGOIRA_FORMAT`           | ❌  | 动图（Ugoira）转换的默认格式 (`webp`/`gif`)。    | `webp`                    |
| `DEFAULT_LIMIT`           | ❌  | 卡片视图默认显示数量 (字符串会被自动转换)。    | `10`                      |
| `HTTPS_PROXY`             | ❌  | HTTPS 代理的 URL。                             | `""`                      |
| `PREVIEW_PROXY_ENABLED`   | ❌  | 是否启用本地图片预览代理 (`true`/`false`)。    | `true`                    |
| `PREVIEW_PROXY_HOST`      | ❌  | 本地预览代理的监听主机。                       | `127.0.0.1`               |
| `PREVIEW_PROXY_PORT`      | ❌  | 本地预览代理的监听端口。                       | `8643`                    |
| `DOWNLOAD_SEMAPHORE`      | ❌  | 下载任务的并发数。                             | `8`                       |
| `CPU_BOUND_SEMAPHORE`     | ❌  | CPU 密集型任务（如动图转换）的并发数。         | `2`                       |

## 🔗 相关资源
- **FastMCP**: [MCP 服务器框架](https://github.com/jlowin/fastmcp)
- **pixivpy3**: [Pixiv API Python 库](https://github.com/upbit/pixivpy)
- **MCP 协议**: [模型上下文协议文档](https://modelcontextprotocol.io/)

## ⚠️ 免责声明
本工具旨在便于用户通过现代 AI 工具访问个人 Pixiv 账号内容。使用时请遵守 Pixiv 用户协议，并尊重版权和创作者权益。开发者对任何账号相关问题不承担责任。

---

> 🤖 本项目的代码和文档内容完全由人工智能生成。虽然已通过结构分析与功能测试，但仍可能存在不完善之处。欢迎提交 Issue/PR 改进体验。
