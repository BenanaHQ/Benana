from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BENANA_", case_sensitive=False)

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "benana_user"
    db_password: str = "benana_password"
    db_name: str = "benana"

    plugins_dir: str = "plugins"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
