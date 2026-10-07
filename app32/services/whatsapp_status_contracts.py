"""Pure, strict Status contracts shared by import, MCP and scheduler."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hashlib
import io
import json
import re
import warnings
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, StrictInt

BAHIA = ZoneInfo('America/Bahia')
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class WeeklyStatusPlan(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(min_length=1, max_length=80, pattern=r'^[\w -]+$')
    hour: StrictInt = Field(default=8, ge=0, le=23)
    minute: StrictInt = Field(default=30, ge=0, le=59)
    timezone: str = Field(default='America/Bahia', pattern=r'^America/Bahia$')
    weekly_arts: dict[str, list[StrictInt]]

    def checked(self):
        if set(self.weekly_arts) != set('0123456'):
            raise ValueError('weekly_plan_requires_seven_days')
        for ids in self.weekly_arts.values():
            if len(ids) > 12 or len(ids) != len(set(ids)) or any(i <= 0 for i in ids):
                raise ValueError('weekly_plan_invalid_arts')
        return self


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', value):
        raise ValueError('invalid_status_identifier')
    return value


def command_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{8,100}', value):
        raise ValueError('invalid_command_key')
    return value


def digest(ids):
    return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()


def inspect_image(data):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_IMAGE_BYTES:
        raise ValueError('invalid_image_size')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                if im.format not in ('PNG', 'JPEG') or im.width * im.height > 20_000_000:
                    raise ValueError('invalid_image_format')
                mime = 'image/png' if im.format == 'PNG' else 'image/jpeg'
                im.verify()
    except Exception:
        raise ValueError('invalid_image') from None
    return hashlib.sha256(data).hexdigest(), mime


def due_today(plan, now, last_run_date):
    if now.tzinfo is None:
        raise ValueError('timezone_required')
    local = now.astimezone(BAHIA)
    target = local.replace(hour=plan.hour, minute=plan.minute, second=0, microsecond=0)
    return (last_run_date != local.date() and target <= local < target + timedelta(minutes=5)
            and bool(plan.weekly_arts.get(str(local.weekday()))))


def next_month(now):
    import calendar
    month = now.month % 12 + 1
    year = now.year + (now.month == 12)
    return now.replace(year=year, month=month, day=min(now.day, calendar.monthrange(year, month)[1]))
