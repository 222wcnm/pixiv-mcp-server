from pydantic_settings import BaseSettings, SettingsConfigDict


from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pixiv_refresh_token: str = Field(default="", validate_default=False)
    download_path: str = "./downloads"
    filename_template: str = "{author} - {title}_{id}"
    ugoira_format: str = "webp"
    preview_proxy_enabled: bool = True
    preview_proxy_host: str = "127.0.0.1"
    preview_proxy_port: int = 8643
    download_semaphore: int = 8
    cpu_bound_semaphore: int = 2
    https_proxy: str = ""
    default_limit: int = 10


settings = Settings()
