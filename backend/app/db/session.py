"""
Crée le moteur async SQLAlchemy et la fabrique de sessions.
Expose une dépendance FastAPI get_session() pour obtenir une AsyncSession par requête.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Moteur de connexion asynchrone à PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,   # passe à True en debug pour voir les requêtes SQL
    future=True
)

# Fabrique de sessions
SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,  # évite l'expiration automatique après commit (plus simple au début)
    class_=AsyncSession
)

async def get_session() -> AsyncSession:
    """
    Dépendance FastAPI: fournit une session par requête et la ferme proprement ensuite.
    """
    async with SessionLocal() as session:
        yield session
