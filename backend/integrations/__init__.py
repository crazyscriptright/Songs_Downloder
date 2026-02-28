"""
Third-party API integration clients.

Exports the main classes used by routes and services so callers can
do either:
    from integrations import YouTubeMusicAPI, JioSaavnAPI
or the explicit form:
    from integrations.ytmusic_dynamic_tokens import YouTubeMusicAPI
"""

from integrations.ytmusic_dynamic_tokens import YouTubeMusicAPI
from integrations.ytmusic_dynamic_video_tokens import YouTubeMusicVideoAPI
from integrations.jiosaavn_search import JioSaavnAPI
from integrations import soundcloud

__all__ = [
    "YouTubeMusicAPI",
    "YouTubeMusicVideoAPI",
    "JioSaavnAPI",
    "soundcloud",
]
