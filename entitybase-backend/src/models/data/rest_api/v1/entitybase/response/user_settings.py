"""Response models for per-user UI settings."""

from pydantic import BaseModel


class UserSettingsResponse(BaseModel):
    """Arbitrary per-user UI settings (e.g. language, fallback chain)."""

    model_config = {"extra": "allow"}


class SettingsStoredResponse(BaseModel):
    """Acknowledgement that settings were stored."""

    model_config = {"populate_by_name": True}

    stored: bool = True
