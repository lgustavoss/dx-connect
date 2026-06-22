from datetime import date

from pydantic import BaseModel, ConfigDict


class ReleaseChangeRead(BaseModel):
    category: str
    text: str


class ReleaseRead(BaseModel):
    version: str
    version_display: str
    date: date | str
    status: str = "published"
    changes: list[ReleaseChangeRead] = []

    model_config = ConfigDict(from_attributes=True)


class SystemInfoRead(BaseModel):
    version: str | None = None
    version_display: str | None = None
    git_sha: str | None = None
    environment: str


class ReleaseNotesRead(BaseModel):
    current_version: str | None = None
    current_version_display: str | None = None
    current: ReleaseRead | None = None
    releases: list[ReleaseRead] = []
    upcoming: list[ReleaseChangeRead] = []
