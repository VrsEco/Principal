from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from . import db


class UiCatalog(db.Model):
    """Catalog entry for referencing UI elements by screen/object codes."""

    __tablename__ = "ui_catalog"
    __table_args__ = (
        db.UniqueConstraint("screen_code", "object_code", name="uq_ui_catalog_screen_object"),
    )

    id = db.Column(db.Integer, primary_key=True)
    screen_code = db.Column(db.Integer, nullable=False, index=True)
    object_code = db.Column(db.Integer, nullable=False, index=True)
    ui_code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    object_type = db.Column(db.String(50))
    route = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Return a serializable representation of the catalog entry."""
        return {
            "id": self.id,
            "screen_code": self.screen_code,
            "object_code": self.object_code,
            "ui_code": self.ui_code,
            "name": self.name,
            "description": self.description,
            "object_type": self.object_type,
            "route": self.route,
            "is_active": self.is_active,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<UiCatalog {self.ui_code} ({self.name})>"




















