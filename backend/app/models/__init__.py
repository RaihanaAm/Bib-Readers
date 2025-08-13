"""
Importer les modèles ici permet à Alembic de découvrir toutes les tables via Base.metadata.
Si tu oublies, 'alembic revision --autogenerate' risque d'être vide.
"""
from app.models.adherent import Adherent  # noqa: F401
from app.models.livre import Livre        # noqa: F401
