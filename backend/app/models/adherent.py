"""
Modèle Adherent = membre de la bibliothèque.
On stocke: identité minimale, email unique, mot de passe haché, actif, date de création.
"""

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime, func, Integer
from app.db.base import Base


class Adherent(Base):
    __tablename__ = "adherents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Email unique de l'adhérent
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Auth fields (mot de passe haché)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Statut actif/inactif
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Date de création (doit utiliser Mapped[datetime])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
