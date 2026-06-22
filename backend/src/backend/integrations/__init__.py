"""
Third-party API integration clients.

Exports the main classes used by routes and services so callers can
do either:
    from integrations import YouTubeMusicAPI, JioSaavnAPI
or the explicit form:
    from integrations.ytmusic_dynamic_tokens import YouTubeMusicAPI
"""

from backend.integrations import soundcloud
from backend.integrations.jiosaavn_search import JioSaavnAPI
from backend.integrations.ytmusic_dynamic_tokens import YouTubeMusicAPI
from backend.integrations.ytmusic_dynamic_video_tokens import YouTubeMusicVideoAPI

__all__ = [
    "YouTubeMusicAPI",
    "YouTubeMusicVideoAPI",
    "JioSaavnAPI",
    "soundcloud",
]
