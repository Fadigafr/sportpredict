"""
Configuration centrale de l'application.
"""
import os
from pathlib import Path

# --- Clés API ---
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY", "")
THESPORTSDB_KEY = os.getenv("THESPORTSDB_KEY", "123")

# --- URLs de base ---
API_SPORTS_FOOTBALL_URL = "https://v3.football.api-sports.io"
API_SPORTS_HOCKEY_URL = "https://v1.hockey.api-sports.io"
THESPORTSDB_URL = "https://www.thesportsdb.com/api/v1/json"

# --- Cache ---
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 heures

# --- Paramètres prédiction ---
NB_DERNIERS_MATCHS = 10
MAX_BUTS_MATRICE = 8

# --- Sports supportés ---
SPORTS_SUPPORTES = ["football", "tennis", "hockey"]

# --- Saison courante ---
SAISON_COURANTE = int(os.getenv("SAISON", "2024"))

# -------------------------------------------------------------------
# Ligues prioritaires avec leurs IDs API-Sports
# (ces IDs sont stables et ne changent jamais sur API-Sports)
# -------------------------------------------------------------------
LIGUES_FOOTBALL = {
    # Top 5 Europe
    "Premier League":     {"id": 39,  "pays": "Angleterre",  "logo": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "categorie": "Europe"},
    "La Liga":            {"id": 140, "pays": "Espagne",     "logo": "🇪🇸", "categorie": "Europe"},
    "Serie A":            {"id": 135, "pays": "Italie",      "logo": "🇮🇹", "categorie": "Europe"},
    "Bundesliga":         {"id": 78,  "pays": "Allemagne",   "logo": "🇩🇪", "categorie": "Europe"},
    "Ligue 1":            {"id": 61,  "pays": "France",      "logo": "🇫🇷", "categorie": "Europe"},
    # Coupes Europe
    "Champions League":   {"id": 2,   "pays": "Europe",      "logo": "🏆", "categorie": "Coupe Europe"},
    "Europa League":      {"id": 3,   "pays": "Europe",      "logo": "🏆", "categorie": "Coupe Europe"},
    "Conference League":  {"id": 848, "pays": "Europe",      "logo": "🏆", "categorie": "Coupe Europe"},
    # Coupes du monde & Nations
    "Coupe du Monde":     {"id": 1,   "pays": "Monde",       "logo": "🌍", "categorie": "Coupe Nations"},
    "CAN":                {"id": 6,   "pays": "Afrique",     "logo": "🌍", "categorie": "Coupe Nations"},
    "Copa America":       {"id": 9,   "pays": "Amériques",   "logo": "🌎", "categorie": "Coupe Nations"},
    "Euro":               {"id": 4,   "pays": "Europe",      "logo": "🇪🇺", "categorie": "Coupe Nations"},
    # Coupes nationales
    "FA Cup":             {"id": 45,  "pays": "Angleterre",  "logo": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "categorie": "Coupe Nationale"},
    "Coupe de France":    {"id": 66,  "pays": "France",      "logo": "🇫🇷", "categorie": "Coupe Nationale"},
    "Copa del Rey":       {"id": 143, "pays": "Espagne",     "logo": "🇪🇸", "categorie": "Coupe Nationale"},
    "Coppa Italia":       {"id": 137, "pays": "Italie",      "logo": "🇮🇹", "categorie": "Coupe Nationale"},
    "DFB Pokal":          {"id": 81,  "pays": "Allemagne",   "logo": "🇩🇪", "categorie": "Coupe Nationale"},
}
