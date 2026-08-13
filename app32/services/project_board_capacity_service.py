class ProjectBoardCapacityService:
    """Calcula a saude operacional do Kanban sem acessar outro tenant."""

    SOFT_LIMIT = 500
    HARD_LIMIT = 1000

    @classmethod
    def build(cls, stage_counts):
        counts = {str(stage or "inbox"): int(value or 0) for stage, value in (stage_counts or {}).items()}
        total = sum(counts.values())
        open_count = max(total - counts.get("completed", 0), 0)

        if open_count > cls.HARD_LIMIT:
            status = "critical"
        elif open_count > cls.SOFT_LIMIT:
            status = "attention"
        else:
            status = "healthy"

        return {
            "status": status,
            "open_count": open_count,
            "soft_limit": cls.SOFT_LIMIT,
            "hard_limit": cls.HARD_LIMIT,
            "utilization_pct": round((open_count / cls.SOFT_LIMIT) * 100),
            "rollover_recommended": open_count > cls.HARD_LIMIT,
        }
