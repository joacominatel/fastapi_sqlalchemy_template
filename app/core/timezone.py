from __future__ import annotations

import logging
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_TIMEZONE = "UTC" # Americas/Argentina/Buenos_Aires 🧉 , just for remember the timezone

@lru_cache(maxsize=1)
def get_timezone() -> ZoneInfo:
    tz_name = settings.TIMEZONE or _DEFAULT_TIMEZONE
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning("Timezone '%s' not found, falling back to '%s'", tz_name, _DEFAULT_TIMEZONE)
        return ZoneInfo(_DEFAULT_TIMEZONE)


def aware_now() -> datetime:
    return datetime.now(get_timezone())
