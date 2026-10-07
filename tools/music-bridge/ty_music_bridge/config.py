"""Configuration management for ty-music-bridge"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Spotify settings
    spotify_client_id: str = Field(..., env="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = Field(..., env="SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri: str = Field(
        default="http://localhost:9876/callback",
        env="SPOTIFY_REDIRECT_URI"
    )
    spotify_scopes: str = Field(
        default="playlist-read-private,playlist-modify-private,playlist-modify-public,user-library-read,user-library-modify",
        env="SPOTIFY_SCOPES"
    )

    # Apple Music settings
    apple_team_id: str = Field(..., env="APPLE_TEAM_ID")
    apple_key_id: str = Field(..., env="APPLE_KEY_ID")
    apple_private_key_path: str = Field(..., env="APPLE_PRIVATE_KEY_PATH")
    apple_music_user_token: str = Field(..., env="APPLE_MUSIC_USER_TOKEN")
    apple_storefront: str = Field(default="us", env="APPLE_STOREFRONT")

    # Cache and data paths
    cache_dir: Path = Field(default="data/cache", env="CACHE_DIR")
    token_dir: Path = Field(default="data/tokens", env="TOKEN_DIR")

    # Internal settings
    repo_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    batch_size: int = Field(default=50)  # API batch size
    fuzzy_match_threshold: float = Field(default=90.0)  # Fuzzy matching score threshold
    duration_tolerance_ms: int = Field(default=2000)  # ±2s tolerance

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.cache_dir = self.repo_root / self.cache_dir
        self.token_dir = self.repo_root / self.token_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.token_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment"""
        return cls()

    def get_spotify_token_path(self) -> Path:
        """Get path for Spotify token cache"""
        return self.token_dir / "spotify.json"

    def get_cache_db_path(self) -> Path:
        """Get path for SQLite cache database"""
        return self.cache_dir / "cache.sqlite"

    def get_apple_private_key_path(self) -> Path:
        """Get absolute path for Apple private key"""
        if os.path.isabs(self.apple_private_key_path):
            return Path(self.apple_private_key_path)
        return self.repo_root / self.apple_private_key_path