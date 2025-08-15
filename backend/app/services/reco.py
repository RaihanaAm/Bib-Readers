import os, pickle
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "core", "reco_model.pkl")
_model = None

def _load():
    global _model
    if _model is None:
        with open(MODEL_PATH, "rb") as f: _model = pickle.load(f)
    return _model

def recommend_by_text(text: str, top_k: int = 10) -> List[Dict]:
    m = _load(); vec, X = m["vectorizer"], m["matrix"]
    ids, titles = m["book_ids"], m["titles"]
    sims = cosine_similarity(vec.transform([text]), X).ravel()
    idxs = sims.argsort()[::-1][:top_k]
    return [{"book_id": ids[i], "title": titles[i], "score": float(sims[i])} for i in idxs]
