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
  A powerful Pixiv toolkit that empowers Large Language Models (like Claude / Cursor) to browse, search, and download content from Pixiv via the Model Context Protocol (MCP). Now featuring a brand-new card-based view for a more intuitive interactive experience.
</p>

<p align="center">
  <a href="README_zh-CN.md">简体中文</a>
</p>

---

## ✨ Key Features

### 🛠️ General Tools
- **`next_page()`**: Fetches the next page of results from the previous command.
- **`set_download_path(path)`**: Customizes the local save path for artworks.
- **`set_ugoira_format(format)`**: Sets the file format for animated works (Ugoira) (`webp` or `gif`).

### 📥 Download Management
- **`download(illust_id | illust_ids)`**: Asynchronously downloads specified artworks, returning task IDs for tracking.
- **`get_download_status(task_id | task_ids)`**: Queries the real-time status of download tasks.
- **`download_random_from_recommendation(count)`**: Randomly downloads artworks from personalized recommendations (Authentication required).

### 🔍 Search & Discovery
- **`search_illust(word, ...)`**: Searches for illustrations by keyword.
- **`search_user(word, ...)`**: Searches for users.
- **`illust_ranking(mode, ...)`**: Retrieves illustration rankings (daily/weekly/monthly, etc.).
- **`illust_related(illust_id, ...)`**: Gets recommended works related to a specific illustration.
- **`illust_recommended(...)`**: Fetches official recommended illustrations (Authentication required).
- **`trending_tags_illust()`**: Gets trending tags.
- **`illust_detail(illust_id)`**: Retrieves detailed information for a single illustration.

### 👥 Community & User
- **`illust_follow(...)`**: Fetches the latest works from followed artists (Authentication required).
- **`user_bookmarks(user_id_to_check, ...)`**: Retrieves a user's bookmark list (Authentication required).
- **`user_following(user_id_to_check, ...)`**: Retrieves a user's following list (Authentication required).

> **Note**: All search and browsing tools support `view` and `limit` parameters to control the output format and quantity. See the [Output Views](#-output-views) section for details.

---

## ⚙️ Output Views

To enhance the user experience in AI conversations, this toolkit introduces a `view` parameter to control the output format:

- **`view='cards'` (Default)**: Displays results as rich Markdown cards with embedded image previews. This is the recommended mode for its intuitive and visually appealing presentation.
- **`view='raw'`**: Returns the raw, unprocessed JSON data. This mode is suitable for programmatic use or when results need to be piped into other tools.

You can change the default view mode via the `DEFAULT_VIEW` environment variable.

## 🔧 Requirements

| Component      | Version | Notes                               |
|----------------|---------|-------------------------------------|
| **Python**     | `3.10+` | Latest stable version is recommended. |
| **FFmpeg**     | Latest  | Optional, for downloading Ugoira.   |
| **MCP Client** | -       | e.g., Claude for Desktop / Cursor.  |

## 🚀 Quick Start

### Step 1: Clone or Download the Project
```bash
git clone https://github.com/222wcnm/pixiv-mcp-server.git
cd pixiv-mcp-server
```

### Step 2: Install Dependencies (uv recommended)
```bash
# Install uv (if not already installed)
pip install uv

# Create a virtual environment and install dependencies
uv venv
uv pip install -e .
```

### Step 3: Obtain Authentication Token
Run the authentication wizard:
```bash
python get_token.py
```
> A `.env` file containing `PIXIV_REFRESH_TOKEN` will be created automatically upon success.

### Step 4: Launch and Configure
In your MCP client, use the following configuration:
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
        "PIXIV_REFRESH_TOKEN": "Copy from .env file or leave empty to read automatically",
        "DOWNLOAD_PATH": "./downloads",
        "FILENAME_TEMPLATE": "{author} - {title}_{id}",
        "DEFAULT_VIEW": "cards",
        "DEFAULT_LIMIT": 10
      }
    }
  }
}
```
> Please replace `/path/to/your/pixiv-mcp-server` with the absolute path to the project's root directory.

## ⚙️ Environment Variables

| Variable Name         | Required | Description                                     | Default Value             |
|-----------------------|:--------:|-------------------------------------------------|---------------------------|
| `PIXIV_REFRESH_TOKEN` | ✅       | Pixiv API authentication token.                 | `None`                    |
| `DOWNLOAD_PATH`       | ❌       | Root directory for downloaded files.            | `./downloads`             |
| `FILENAME_TEMPLATE`   | ❌       | File naming template.                           | `{author} - {title}_{id}` |
| `DEFAULT_VIEW`        | ❌       | Default output view (`cards`/`raw`).            | `cards`                   |
| `DEFAULT_LIMIT`       | ❌       | Default number of items for `cards` view.       | `10`                      |
| `WEBP_QUALITY`        | ❌       | Ugoira to webp conversion quality (0-100).      | `80`                      |
| `WEBP_PRESET`         | ❌       | Webp preset (`default`/`picture`/`photo`...).   | `default`                 |
| `WEBP_LOSSLESS`       | ❌       | Webp lossless mode (`0`/`1`).                   | `0`                       |
| `GIF_PRESET`          | ❌       | Ugoira to gif conversion preset.                | `ultrafast`               |
| `GIF_FPS`             | ❌       | Target FPS for gif conversion.                  | `None`                    |
| `HTTP_PROXY`, etc.    | ❌       | Proxy settings.                                 | System default            |

## 🔗 Related Resources
- **FastMCP**: [MCP Server Framework](https://github.com/jlowin/fastmcp)
- **pixivpy3**: [Pixiv API Python Library](https://github.com/upbit/pixivpy)
- **MCP Protocol**: [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

## ⚠️ Disclaimer
This tool is intended to facilitate access to your personal Pixiv account content through modern AI tools. Please adhere to the Pixiv user agreement and respect copyright and creator rights. The developer assumes no responsibility for any account-related issues.

---

> 🤖 The code and documentation for this project were entirely generated by AI. While it has undergone structural analysis and functional testing, imperfections may still exist. Contributions via Issues/PRs to improve the experience are welcome.
