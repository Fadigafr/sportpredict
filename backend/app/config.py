"""
Configuration centrale de l'application.
Toutes les clés d'API et réglages se règlent ici ou via variables d'environnement.
"""
import os
from pathlib import Path

# --- Clés API (à définir comme variables d'environnement, jamais en dur dans le code) ---
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY", "")          # football + hockey (api-sports.io)
THESPORTSDB_KEY = os.getenv("THESPORTSDB_KEY", "123")     # "123" = clé de test publique gratuite

# --- URLs de base ---
API_SPORTS_FOOTBALL_URL = "https://v3.football.api-sports.io"
API_SPORTS_HOCKEY_URL = "https://v1.hockey.api-sports.io"
THESPORTSDB_URL = "https://www.thesportsdb.com/api/v1/json"

# --- Cache local (pour économiser le quota de 100 req/jour) ---
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 heures : les stats d'équipe ne bougent pas vite

# --- Paramètres du moteur de prédiction ---
NB_DERNIERS_MATCHS = 10   # nombre de matchs récents utilisés pour calculer la forme
MAX_BUTS_MATRICE = 8      # on calcule les probabilités de 0 à 8 buts par équipe

# --- Sports supportés ---
SPORTS_SUPPORTES = ["football", "tennis", "hockey"]
