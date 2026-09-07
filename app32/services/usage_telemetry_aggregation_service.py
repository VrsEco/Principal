from collections import defaultdict
from datetime import datetime, timedelta

from models import UserPresenceSession, UsageTelemetryHourly, db


class UsageTelemetryAggregationService:
    """Consolida somente buckets fechados; não roda no request web."""

    @classmethod
    def aggregate_hour(cls, bucket_started_at):
        start = bucket_started_at.replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        sessions = UserPresenceSession.query.filter(
            UserPresenceSession.last_seen_at >= start,
            UserPresenceSession.last_seen_at < end,
        ).all()
        totals = defaultdict(lambda: {'sessions_started': 0, 'active_seconds': 0})
        for session in sessions:
            key = (session.company_id, session.user_id)
            totals[key]['sessions_started'] += int(start <= session.login_at < end)
            seen_start = max(session.login_at, start)
            seen_end = min(session.last_seen_at, end)
            totals[key]['active_seconds'] += max(0, int((seen_end - seen_start).total_seconds()))
        for (company_id, user_id), values in totals.items():
            row = UsageTelemetryHourly.query.filter_by(company_id=company_id, user_id=user_id,
                bucket_started_at=start, channel='web', usage_kind='presence').first()
            if row is None:
                row = UsageTelemetryHourly(company_id=company_id, user_id=user_id, bucket_started_at=start,
                    channel='web', usage_kind='presence')
                db.session.add(row)
            row.sessions_started = values['sessions_started']
            row.active_seconds = values['active_seconds']
        db.session.commit()
        return {'bucket_started_at': start.isoformat(), 'users': len(totals)}

    @classmethod
    def aggregate_previous_closed_hour(cls):
        return cls.aggregate_hour(datetime.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1))
