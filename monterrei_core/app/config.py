"""Configuración global lida do .env vía pydantic-settings."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent  # monterrei_core/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_prefix="MONTERREI_",
        case_sensitive=False,
        extra="ignore",
    )

    # Rede
    host: str = "0.0.0.0"
    host_main: Optional[str] = None
    host_main_extra: Optional[str] = None
    port_main: int = 8000           # Músicos / director
    port_public: int = 8001         # Público
    port_public_low: int = 80       # Público (estándar HTTP)
    port_admin: int = 8800          # Admin + Proxección (con contrasinal)
    bind_port_80: bool = False
    prod_ip: str = "192.168.0.2"

    # Sesións
    secret_key: str = "monterrei-dev"
    session_cookie: str = "monterrei_sid"

    # Auth admin/proxección (HTTP Basic)
    admin_user: str = "xairo"
    admin_password: str = "xairocampos"

    # MIDI
    midi_port_hint: str = "IAC"
    bpm_divider: float = 1.0
    bpm_min: float = 20.0
    bpm_max: float = 400.0
    bpm_ema_alpha: float = 0.15

    # DMX
    dmx_port_hint: str = ""
    dmx_fps: int = 30
    dmx_led_count: int = 60
    dmx_channels_per_led: int = 4

    # Recursos
    m1_video: str = "castelo_monterrei_1.mp4"
    m1_previas_dir: str = "static/assets/m1_previas"

    # Logging
    log_level: str = "INFO"

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def main_bind_host(self) -> str:
        return self.host_main or self.host

    @property
    def main_bind_hosts(self) -> list[str]:
        hosts = [self.main_bind_host]
        if self.host_main_extra and self.host_main_extra not in hosts:
            hosts.append(self.host_main_extra)
        return hosts

    @property
    def m1_previas_path(self) -> Path:
        return BASE_DIR / self.m1_previas_dir

    @property
    def video_path(self) -> Path:
        return BASE_DIR / "static" / "assets" / "videos" / self.m1_video


settings = Settings()
