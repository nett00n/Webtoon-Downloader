from __future__ import annotations

from dataclasses import dataclass, field

from webtoon_downloader.core.webtoon.models import ChapterInfo


@dataclass
class DownloadError(Exception):
    """BaseException raised for download errors."""

    url: str
    cause: Exception
    message: str | None = field(default=None)

    def __str__(self) -> str:
        if self.message:
            return self.message
        return f'Failed to download from "{self.url}" due to: {self.cause}'


@dataclass
class ImageDownloadError(DownloadError):
    """Exception raised for image download errors"""


@dataclass
class ChapterDownloadError(DownloadError):
    """Exception raised for chapter download errors"""

    chapter_info: ChapterInfo | None = None
