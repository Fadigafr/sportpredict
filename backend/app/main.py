"""
API principale de l'application de prédiction sportive.
Expose des endpoints REST consommés par l'app mobile.

Lancer en local :
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .api_client import ApiSportsClient
from .data_extraction import extraire_buts_marques_concedes, extraire_buteurs
from .poisson_engine import predire_match
from .scorer_engine import classer_buteurs_probables
from .tennis_engine import probabilite_victoire_simple, estimer_score_sets
from .config import NB_DERNIERS_MATCHS, SPORTS_SUPPORTES

app = FastAPI(title="SportPredict API", version="1.0")

# Autorise l'app mobile à appeler ce backend depuis n'importe quelle origine
# (à restreindre une fois en production, pour un usage perso ça reste simple)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def racine():
    return {"message": "SportPredict API en ligne", "sports_supportes": SPORTS_SUPPORTES}


@app.get("/equipes/recherche")
def rechercher_equipe(nom: str = Query(..., description="Nom de l'équipe à rechercher"),
                       sport: str = Query("football")):
    """Recherche une équipe par nom pour récupérer son ID (nécessaire pour les autres endpoints)."""
    if sport not in ("football", "hockey"):
        raise HTTPException(400, "Sport non supporté pour cet endpoint (football ou hockey)")
    client = ApiSportsClient(sport)
    data = client.chercher_equipe(nom)
    equipes = [
        {"id": e["team"]["id"], "nom": e["team"]["name"], "pays": e["team"].get("country")}
        for e in data.get("response", [])
    ]
    return {"equipes": equipes}


@app.get("/prediction/match")
def predire_match_endpoint(
    sport: str = Query(..., description="football ou hockey"),
    team_domicile_id: int = Query(...),
    team_exterieur_id: int = Query(...),
    league_id: int | None = Query(None, description="Nécessaire pour le pronostic buteur"),
    season: int | None = Query(None, description="Saison en cours, ex: 2025"),
):
    """
    Endpoint principal : retourne la prédiction complète d'un match
    (score exact, BTTS, nombre de buts attendu, buteurs probables).
    """
    if sport not in ("football", "hockey"):
        raise HTTPException(400, "Ce endpoint supporte football et hockey. Pour le tennis, voir /prediction/tennis")

    client = ApiSportsClient(sport)

    # 1. Récupérer les derniers matchs de chaque équipe
    fixtures_dom = client.derniers_matchs_equipe(team_domicile_id, NB_DERNIERS_MATCHS)
    fixtures_ext = client.derniers_matchs_equipe(team_exterieur_id, NB_DERNIERS_MATCHS)

    buts_marques_dom, buts_concedes_dom = extraire_buts_marques_concedes(fixtures_dom, team_domicile_id)
    buts_marques_ext, buts_concedes_ext = extraire_buts_marques_concedes(fixtures_ext, team_exterieur_id)

    if not buts_marques_dom or not buts_marques_ext:
        raise HTTPException(404, "Pas assez de données historiques pour ces équipes")

    # 2. Calculer la prédiction Poisson
    prediction = predire_match(
        buts_marques_dom, buts_concedes_dom,
        buts_marques_ext, buts_concedes_ext,
    )

    resultat = {
        "sport": sport,
        "team_domicile_id": team_domicile_id,
        "team_exterieur_id": team_exterieur_id,
        "prediction": prediction,
    }

    # 3. Pronostic buteur (uniquement si league_id et season fournis, et football uniquement
    #    car l'endpoint topscorers n'est pas structuré pareil pour le hockey)
    if league_id and season and sport == "football":
        try:
            buteurs_dom_raw = client.meilleurs_buteurs(team_domicile_id, league_id, season)
            buteurs_ext_raw = client.meilleurs_buteurs(team_exterieur_id, league_id, season)

            moyenne_dom = sum(buts_marques_dom) / len(buts_marques_dom)
            moyenne_ext = sum(buts_marques_ext) / len(buts_marques_ext)

            buteurs_dom = classer_buteurs_probables(
                extraire_buteurs(buteurs_dom_raw), prediction["lambda_domicile"], moyenne_dom
            )
            buteurs_ext = classer_buteurs_probables(
                extraire_buteurs(buteurs_ext_raw), prediction["lambda_exterieur"], moyenne_ext
            )
            resultat["buteurs_probables_domicile"] = buteurs_dom
            resultat["buteurs_probables_exterieur"] = buteurs_ext
        except Exception:
            # Si les données de buteurs ne sont pas disponibles, on continue sans bloquer
            resultat["buteurs_probables_domicile"] = []
            resultat["buteurs_probables_exterieur"] = []

    return resultat


@app.get("/matchs/du-jour")
def matchs_du_jour(
    sport: str = Query(...),
    date: str = Query(..., description="Format YYYY-MM-DD"),
    league_id: int | None = Query(None),
):
    """Liste les matchs prévus à une date donnée, pour choisir lequel prédire."""
    if sport not in ("football", "hockey"):
        raise HTTPException(400, "Sport non supporté pour cet endpoint")
    client = ApiSportsClient(sport)
    data = client.matchs_du_jour(date, league_id)

    matchs = []
    for f in data.get("response", []):
        matchs.append({
            "fixture_id": f["fixture"]["id"],
            "date": f["fixture"]["date"],
            "league": f["league"]["name"],
            "domicile": {"id": f["teams"]["home"]["id"], "nom": f["teams"]["home"]["name"]},
            "exterieur": {"id": f["teams"]["away"]["id"], "nom": f["teams"]["away"]["name"]},
        })
    return {"matchs": matchs}


@app.get("/prediction/tennis")
def predire_tennis(
    victoires_a: int = Query(..., description="Victoires récentes du joueur A"),
    matchs_a: int = Query(..., description="Matchs joués récemment par le joueur A"),
    victoires_b: int = Query(..., description="Victoires récentes du joueur B"),
    matchs_b: int = Query(..., description="Matchs joués récemment par le joueur B"),
    format_best_of: int = Query(3, description="3 ou 5 sets"),
):
    """
    Prédiction tennis V1 : à partir des taux de victoire récents des deux joueurs,
    calcule la probabilité de victoire et le score de sets le plus probable.

    Note : contrairement au football/hockey, il n'y a pas encore d'intégration
    automatique des stats joueurs ATP/WTA (l'API gratuite ne les fournit pas
    de façon fiable). En attendant, les chiffres de victoires/matchs sont à
    renseigner manuellement (ex: 10 derniers matchs ATP du joueur).
    """
    proba = probabilite_victoire_simple(victoires_a, matchs_a, victoires_b, matchs_b)
    sets = estimer_score_sets(proba["probabilite_victoire_joueur_a"] / 100, format_best_of)
    return {"probabilites": proba, "score_sets": sets}
