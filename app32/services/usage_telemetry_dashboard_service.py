from datetime import date, datetime, time, timedelta

from sqlalchemy import func

from models import UsageTelemetryHourly, db


class UsageTelemetryDashboardService:
    """Leitura de agregados; nunca consulta presença ou logs brutos."""

    @staticmethod
    def period(start_raw=None, end_raw=None):
        today = date.today()
        end = date.fromisoformat(end_raw) if end_raw else today
        start = date.fromisoformat(start_raw) if start_raw else end - timedelta(days=6)
        if start > end or (end - start).days > 89:
            raise ValueError('Período inválido. O limite é 90 dias.')
        return datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)

    @classmethod
    def summary(cls, company_id, start_raw=None, end_raw=None):
        start, end = cls.period(start_raw, end_raw)
        totals = (db.session.query(
            func.coalesce(func.sum(UsageTelemetryHourly.sessions_started), 0),
            func.coalesce(func.sum(UsageTelemetryHourly.active_seconds), 0),
            func.coalesce(func.sum(UsageTelemetryHourly.request_count), 0),
            func.coalesce(func.sum(UsageTelemetryHourly.ai_request_count), 0),
            func.coalesce(func.sum(UsageTelemetryHourly.mcp_request_count), 0),
            func.coalesce(func.sum(UsageTelemetryHourly.error_count), 0),
        ).filter(UsageTelemetryHourly.company_id == company_id,
                 UsageTelemetryHourly.bucket_started_at >= start,
                 UsageTelemetryHourly.bucket_started_at < end).one())
        return {'company_id': company_id, 'start': start.date().isoformat(), 'end': (end.date() - timedelta(days=1)).isoformat(),
                'sessions_started': int(totals[0]), 'active_seconds': int(totals[1]), 'request_count': int(totals[2]),
                'ai_request_count': int(totals[3]), 'mcp_request_count': int(totals[4]), 'error_count': int(totals[5])}
