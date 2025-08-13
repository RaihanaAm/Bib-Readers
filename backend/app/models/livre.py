"""
Modèle Livre = ressource du catalogue.
Champs simples + rating entier 0..5, stock entier.
"""
from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Livre(Base):
    __tablename__ = "livres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    author: Mapped[str] = mapped_column(String(180), default="Unknown", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0..5
    image_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
