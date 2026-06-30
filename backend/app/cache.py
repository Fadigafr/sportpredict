"""
Cache disque très simple (fichiers JSON) pour limiter les appels API.
Le plan gratuit API-Sports = 100 requêtes/jour, donc chaque appel compte.
"""
import json
import time
import hashlib
from pathlib import Path
from .config import CACHE_DIR, CACHE_TTL_SECONDS


def _cache_path(key: str) -> Path:
    h = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def get_cached(key: str):
    """Retourne la donnée en cache si elle existe et n'est pas expirée, sinon None."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if time.time() - payload["timestamp"] > CACHE_TTL_SECONDS:
            return None
        return payload["data"]
    except (json.JSONDecodeError, KeyError):
        return None


def set_cached(key: str, data) -> None:
    """Enregistre la donnée en cache avec un horodatage."""
    path = _cache_path(key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "data": data}, f)
