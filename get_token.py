#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pixiv Token 获取与配置向导
================================
本工具旨在提供一个安全、简单的方式来获取 Pixiv API 的 Refresh Token，
并为配套项目自动生成一份带有详细注释的完整配置文件。
"""

import json
import requests
import hashlib
import secrets
import webbrowser
import base64
import os
import sys
from urllib.parse import urlencode, parse_qs, urlparse
from pathlib import Path
from typing import Dict, Optional

# 禁用 requests 库发出的不安全请求警告
# 注意：这在连接需要自定义证书的本地代理（如抓包工具）时很方便，但在生产环境中应谨慎使用。
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 核心类定义 ---

class PixivTokenGenerator:
    """封装了获取 Pixiv Token 所有必要逻辑的类。"""
    
    def __init__(self):
        self.client_id = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
        self.client_secret = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
        self.redirect_uri = 'https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback'
        self.user_agent = 'PixivAndroidApp/5.0.234 (Android 11; Pixel 5)'

    def generate_pkce_challenge(self) -> tuple[str, str]:
        """生成并返回 PKCE 流程所需的 code_verifier 和 code_challenge。"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_sha = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_sha).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge

    def get_auth_url(self, code_challenge: str) -> str:
        """根据生成的 code_challenge 构建 Pixiv 授权 URL。"""
        params = {
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'client': 'pixiv-android',
        }
        return f"https://app-api.pixiv.net/web/v1/login?{urlencode(params)}"
    
    def _post_token_request(self, data: Dict) -> Dict:
        """发送Token请求的公共方法。"""
        headers = {'User-Agent': self.user_agent}
        response = None
        try:
            response = requests.post(
                'https://oauth.secure.pixiv.net/auth/token', 
                data=data, 
                headers=headers, 
                verify=False,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            try:
                if response is not None:
                    error_details = response.json()
                    error_message = f"API Error: {error_details.get('error', {}).get('message', str(error_details))}"
            except (ValueError, AttributeError):
                pass
            return {'error': 'NetworkError', 'message': error_message}
    
    def exchange_code_for_token(self, code: str, code_verifier: str) -> dict:
        """使用授权码(code)和校验器(verifier)换取最终的 Token。"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'code_verifier': code_verifier,
            'grant_type': 'authorization_code',
            'include_policy': 'true',
            'redirect_uri': self.redirect_uri,
        }
        return self._post_token_request(data)

    def refresh_existing_token(self, refresh_token: str) -> dict:
        """使用一个已有的 Refresh Token 来获取一个新的。"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'include_policy': 'true',
            'refresh_token': refresh_token,
        }
        return self._post_token_request(data)

# --- 辅助函数 ---

def create_or_update_env_file(refresh_token: str):
    """更新 .env 文件中的 Refresh Token，并保留其他已有配置。"""
    env_path = Path(".env")
    env_content = []
    token_line = f"PIXIV_REFRESH_TOKEN={refresh_token}"
    found = False
    config_exists = env_path.exists()

    if config_exists:
        try:
            with env_path.open('r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith("PIXIV_REFRESH_TOKEN="):
                        env_content.append(token_line + '\n')
                        found = True
                    else:
                        env_content.append(line)
        except Exception as e:
            print(f"⚠️ 读取现有配置文件失败: {e}, 将创建新文件")

    if not found:
        if not config_exists or not env_content:
            env_content = [
                "# [核心] Pixiv API 认证令牌 (必须)\n",
                f"{token_line}\n\n",
                "# [功能] 文件下载路径 (可选, 默认为 './downloads')\n",
                "DOWNLOAD_PATH=./downloads\n\n",
                "# [功能] 文件命名模板 (可选, 默认: '{author} - {title}_{id}')\n",
                "FILENAME_TEMPLATE={author} - {title}_{id}\n\n",
                "# [网络] 代理服务器设置 (可选, 默认禁用)\n",
                "# https_proxy=http://127.0.0.1:7890\n"
            ]
        else:
            env_content.insert(0, f"{token_line}\n\n")

    try:
        with env_path.open('w', encoding='utf-8') as f:
            f.writelines(env_content)
        abs_path = os.path.abspath(env_path)
        print(f"\n✅ 配置文件已成功 {'更新' if config_exists else '创建'}!")
        print(f"   📁 文件路径: {abs_path}")
        print(f"   🔑 Refresh Token 已设置。")
    except Exception as e:
        print(f"\n❌ 写入配置文件失败: {e}")

def get_existing_refresh_token() -> Optional[str]:
    """检查现有的.env文件并返回Refresh Token。"""
    env_path = Path(".env")
    if not env_path.exists():
        return None
    
    try:
        with env_path.open('r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("PIXIV_REFRESH_TOKEN="):
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return None

def print_header():
    """打印程序标题。"""
    print("=" * 60)
    print("🎨      Pixiv Token 获取与配置向导      🎨")
    print("=" * 60)
    print("本工具将引导您完成认证，并为您的 Pixiv MCP 服务器生成配置文件。")
    
    existing_token = get_existing_refresh_token()
    if existing_token:
        print(f"\nℹ️ 检测到现有配置文件 (.env)。")
    else:
        print("\nℹ️ 未检测到现有配置文件 (.env)。")

# --- 主流程函数 ---

def get_new_token_flow(generator: PixivTokenGenerator) -> bool:
    """处理获取新 Token 的完整流程。"""
    attempt_count = 0
    max_attempts = 3
    
    while attempt_count < max_attempts:
        attempt_count += 1
        code_verifier, code_challenge = generator.generate_pkce_challenge()
        auth_url = generator.get_auth_url(code_challenge)
        
        print(f"\n{'='*20} 尝试 #{attempt_count}/{max_attempts} {'='*20}")
        print("📝 请严格按照以下步骤操作：")
        print("-" * 50)
        print("1. 在你的浏览器中，先按 F12 打开【开发者工具】。")
        print("2. 在开发者工具中，切换到【网络(Network)】标签页。")
        print("3. ✨【重要】确保【Preserve log】或【保留日志】选项是勾选状态！")
        print("4. 我们将为您自动打开一个登录链接，请在页面中【完成登录】。")
        print("5. 登录后，回到【开发者工具】找到 `callback?...` 请求，并【完整复制】它的URL。")
        print("-" * 50)
        
        input("👉 请仔细阅读以上步骤。准备好后，请按【回车键】，我们将为您打开浏览器...")
        
        try:
            webbrowser.open(auth_url)
            print("\n✅ 已在您的默认浏览器中打开登录链接。现在请在浏览器中完成操作。")
            print(f"   🔗 如果浏览器没有自动打开，请手动访问: {auth_url}")
        except Exception as e:
            print(f"❌ 自动打开浏览器失败: {e}。请手动复制下面的链接访问：")
            print(f"   🔗 {auth_url}")
        
        code = None
        while True:
            callback_url = input("\n👉 请将您在浏览器中复制的完整 `callback` URL 粘贴到此处 (输入 'q' 退出): ").strip()
            if callback_url.lower() == 'q':
                print("❌ 操作已由用户手动取消。")
                return False

            if not callback_url:
                print("❗ 您没有输入任何内容，请重新粘贴。")
                continue

            try:
                query_params = parse_qs(urlparse(callback_url).query)
                extracted_code = query_params.get('code', [None])[0]
                
                if extracted_code:
                    print(f"\n✅ 成功提取授权码(code)！")
                    code = extracted_code
                    break
                else:
                    print("❌ 错误：您粘贴的URL中未能找到`code`参数。请重试。")
            except Exception:
                print("❌ 解析URL时发生错误，请确认您粘贴的是一个有效的URL。请重试。")

        print("⏳ 正在用授权码换取最终的 Refresh Token...")
        token_response = generator.exchange_code_for_token(code, code_verifier)
        
        if 'refresh_token' in token_response:
            refresh_token = token_response['refresh_token']
            print(f"\n🎉 恭喜！成功获取 Refresh Token!")
            create_or_update_env_file(refresh_token)
            return True
        else:
            print("\n❌ 获取 Token 失败:")
            print(json.dumps(token_response, indent=2, ensure_ascii=False))
            print("\n" + "!"*20)
            print("❗ 失败原因通常是授权码已过期(操作太慢)、已被使用或网络连接问题。")
            
            if attempt_count < max_attempts:
                print(f"\n💡 我们将进行第 {attempt_count+1}/{max_attempts} 次尝试...")
            else:
                print("\n❌ 已达到最大尝试次数，请检查网络后重试程序。")
                return False

    return False


def refresh_token_flow(generator: PixivTokenGenerator):
    """处理刷新已有 Token 的流程。"""
    print("\n🔄 刷新已有 Token")
    print("   如果您觉得当前的 Token 可能快要过期，可以使用此功能获取一个新的。")
    
    existing_token = get_existing_refresh_token()
    current_token = None
    
    if existing_token:
        use_existing = input("👉 检测到已有 Token，是否直接用它刷新? (y/n): ").strip().lower()
        if use_existing == 'y':
            current_token = existing_token
            print("✅ 将使用现有Token进行刷新。")
    
    if not current_token:
        while True:
            current_token = input("\n👉 请输入您要刷新的 Refresh Token (输入 'q' 退出): ").strip()
            if current_token.lower() == 'q':
                print("❌ 操作已由用户手动取消。")
                return
            if not current_token:
                print("❗ Token 不能为空，请重新输入。")
                continue
            break
    
    print("\n⏳ 正在刷新 Token...")
    try:
        token_response = generator.refresh_existing_token(current_token)
        if 'refresh_token' in token_response:
            new_refresh_token = token_response['refresh_token']
            print(f"\n🎉 成功刷新！这是您的新 Refresh Token:")
            print(f"🔑 {new_refresh_token}")
            create_or_update_env_file(new_refresh_token)
        else:
            print("\n❌ 刷新 Token 失败:")
            print(json.dumps(token_response, indent=2, ensure_ascii=False))
            print("\n可能的原因: Token已过期或无效、网络问题。")
    except Exception as e:
        print(f"\n❌ 刷新过程中发生意外错误: {e}")

def main():
    """程序主入口。"""
    print_header()
    generator = PixivTokenGenerator()
    
    while True:
        print("\n" + "-" * 25 + " 主菜单 " + "-" * 26)
        print("1. 获取新 Token / 重新登录")
        print("2. 刷新已有的 Token")
        print("3. 退出")
        print("-" * 60)
        
        choice = input("请输入您的选择 (1-3): ").strip()
        
        if choice == "1":
            if get_new_token_flow(generator):
                break
        elif choice == "2":
            refresh_token_flow(generator)
            break
        elif choice == "3":
            break
        else:
            print("\n❌ 无效选择，请输入 1, 2 或 3。")
    
    print("\n👋 感谢使用，再见！")
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 程序已被用户中断。")
        sys.exit(1)
