<<<<<<< HEAD
"""
Modèle Adherent = membre de la bibliothèque.
On stocke: identité minimale, email unique, mot de passe haché, actif, date de création.
"""
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

=======
# backend/app/models/adherent.py
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime, func, Integer
from app.db.base import Base


>>>>>>> main
class Adherent(Base):
    __tablename__ = "adherents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
<<<<<<< HEAD
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
=======
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Auth fields
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ✅ must use Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
>>>>>>> main
    )
