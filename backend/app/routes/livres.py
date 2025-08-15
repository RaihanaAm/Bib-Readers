# backend/app/routes/livres.py
"""
Books endpoints:
- GET  /api/livres                : paginated list + optional title search (q)
- GET  /api/livres/random         : n random books          (declare BEFORE /{book_id})
- GET  /api/livres/top-rated      : best rated books        (declare BEFORE /{book_id})
- GET  /api/livres/{book_id}      : single book detail
- POST /api/recommander-par-description : TF-IDF cosine recommendations from free text
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.livre import Livre
from app.services import reco as reco_service

router = APIRouter(prefix="/api", tags=["livres"])


def _serialize_book(b: Livre) -> Dict[str, Any]:
    """Serialize a Livre ORM object into a plain dict (safe for JSON)."""
    return {
        "id": b.id,
        "title": b.title,
        "author": b.author,
        "description": b.description,
        "price": float(b.price or 0),
        "stock": int(b.stock or 0),
        "rating": int(b.rating or 0),
        "image_url": b.image_url,
    }


@router.get("/livres")
async def list_livres(
    q: Optional[str] = Query(default=None, description="Search by title (ILIKE)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    """
    Paginated list of books.
    Returns:
    {
      "items": [...],
      "page": 1,
      "page_size": 20,
      "total": 123
    }
    """
    offset = (page - 1) * page_size

    base_stmt = select(Livre)
    count_stmt = select(func.count(Livre.id))

    if q:
        pattern = f"%{q}%"
        base_stmt = base_stmt.where(Livre.title.ilike(pattern))
        count_stmt = count_stmt.where(Livre.title.ilike(pattern))

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = base_stmt.order_by(Livre.id).offset(offset).limit(page_size)
    res = await session.execute(stmt)
    books = res.scalars().all()

    return {
        "items": [_serialize_book(b) for b in books],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


# ----- STATIC ROUTES (must be declared BEFORE /livres/{book_id}) -----

@router.get("/livres/random")
async def random_livres(
    n: int = Query(8, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """
    Return n random books (PostgreSQL: ORDER BY random()).
    """
    stmt = select(Livre).order_by(func.random()).limit(n)
    res = await session.execute(stmt)
    books = res.scalars().all()
    return [_serialize_book(b) for b in books]


@router.get("/livres/top-rated")
async def top_rated_livres(
    limit: int = Query(8, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """
    Return best-rated books (then price asc to break ties).
    """
    stmt = select(Livre).order_by(desc(Livre.rating), Livre.price.asc()).limit(limit)
    res = await session.execute(stmt)
    books = res.scalars().all()
    return [_serialize_book(b) for b in books]


# ----- DYNAMIC ROUTE (must come AFTER the static ones) -----

@router.get("/livres/{book_id}")
async def get_livre(book_id: int, session: AsyncSession = Depends(get_session)):
    """
    Return details of a single book by ID.
    404 if not found.
    """
    res = await session.execute(select(Livre).where(Livre.id == book_id))
    book = res.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Livre non trouvé")
    return _serialize_book(book)


# ----- RECOMMENDATIONS -----

@router.post("/recommander-par-description", response_model=List[dict])
async def recommend(payload: dict):
    """
    Body: { "text": "un roman d’aventure en Afrique", "top_k": 5 }
    Returns: [{ book_id, title, score }, ...]
    """
    text = (payload.get("text") or "").strip()
    top_k = int(payload.get("top_k") or 5)
    if not text:
        return []
    return reco_service.recommend_by_text(text, top_k=top_k)
