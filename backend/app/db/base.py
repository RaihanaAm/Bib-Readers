"""
Définit la classe Base pour tous les modèles ORM.
"""
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass  # On pourra ajouter des mixins communs plus tard
