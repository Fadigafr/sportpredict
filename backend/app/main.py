"""
API principale SportPredict V2.
Nouveautés : calendrier par ligue, ligues disponibles, buteurs top 5 systématiques.
"""
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .api_client import ApiSportsClient
from .data_extraction import extraire_buts_marques_concedes, extraire_buteurs
from .poisson_engine import predire_match
from .scorer_engine import classer_buteurs_probables
from .tennis_engine import probabilite_victoire_simple, estimer_score_sets
from .config import NB_DERNIERS_MATCHS, SPORTS_SUPPORTES, LIGUES_FOOTBALL, SAISON_COURANTE

app = FastAPI(title="SportPredict API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def racine():
    return {"message": "SportPredict API V2 en ligne", "sports_supportes": SPORTS_SUPPORTES}


# ─── LIGUES DISPONIBLES ───────────────────────────────────────────────────────

@app.get("/ligues")
def lister_ligues():
    """Retourne toutes les ligues et coupes disponibles, groupées par catégorie."""
    categories = {}
    for nom, info in LIGUES_FOOTBALL.items():
        cat = info["categorie"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "nom": nom,
            "id": info["id"],
            "pays": info["pays"],
            "logo": info["logo"],
        })
    return {"categories": categories}


# ─── CALENDRIER ───────────────────────────────────────────────────────────────

@app.get("/calendrier")
def calendrier(
    league_id: int = Query(..., description="ID de la ligue (voir /ligues)"),
    date_debut: str | None = Query(None, description="YYYY-MM-DD (défaut: aujourd'hui)"),
    nb_jours: int = Query(7, description="Nombre de jours à couvrir (1-14)"),
):
    """
    Retourne les matchs d'une ligue sur une période donnée.
    Les matchs sont triés par date et enrichis avec les noms des équipes.
    """
    debut = date.fromisoformat(date_debut) if date_debut else date.today()
    fin = debut + timedelta(days=min(nb_jours, 14) - 1)

    client = ApiSportsClient("football")
    data = client.matchs_par_ligue_semaine(league_id, str(debut), str(fin))

    matchs = []
    for f in data.get("response", []):
        statut = f["fixture"]["status"]["short"]
        matchs.append({
            "fixture_id": f["fixture"]["id"],
            "date": f["fixture"]["date"],
            "statut": statut,  # NS=à venir, FT=terminé, LIVE=en cours
            "league": {
                "nom": f["league"]["name"],
                "id": f["league"]["id"],
                "logo": f["league"].get("logo", ""),
                "round": f["league"].get("round", ""),
            },
            "domicile": {
                "id": f["teams"]["home"]["id"],
                "nom": f["teams"]["home"]["name"],
                "logo": f["teams"]["home"].get("logo", ""),
                "score": f["goals"]["home"],
            },
            "exterieur": {
                "id": f["teams"]["away"]["id"],
                "nom": f["teams"]["away"]["name"],
                "logo": f["teams"]["away"].get("logo", ""),
                "score": f["goals"]["away"],
            },
        })

    # Trier par date croissante
    matchs.sort(key=lambda x: x["date"])
    return {"league_id": league_id, "matchs": matchs, "total": len(matchs)}


# ─── CLASSEMENT ───────────────────────────────────────────────────────────────

@app.get("/classement")
def classement(league_id: int = Query(...)):
    """Retourne le classement actuel d'une ligue."""
    client = ApiSportsClient("football")
    data = client.classement_ligue(league_id, SAISON_COURANTE)

    classements = []
    for group in data.get("response", []):
        for ligue in group.get("league", {}).get("standings", []):
            for equipe in ligue:
                classements.append({
                    "position": equipe["rank"],
                    "equipe": {
                        "id": equipe["team"]["id"],
                        "nom": equipe["team"]["name"],
                    },
                    "points": equipe["points"],
                    "matchs_joues": equipe["all"]["played"],
                    "victoires": equipe["all"]["win"],
                    "nuls": equipe["all"]["draw"],
                    "defaites": equipe["all"]["lose"],
                    "buts_pour": equipe["all"]["goals"]["for"],
                    "buts_contre": equipe["all"]["goals"]["against"],
                    "difference_buts": equipe["goalsDiff"],
                    "forme": equipe.get("form", ""),
                })
    return {"league_id": league_id, "classement": classements}


# ─── RECHERCHE ÉQUIPE ─────────────────────────────────────────────────────────

@app.get("/equipes/recherche")
def rechercher_equipe(nom: str = Query(...), sport: str = Query("football")):
    if sport not in ("football", "hockey"):
        raise HTTPException(400, "Sport non supporté")
    client = ApiSportsClient(sport)
    data = client.chercher_equipe(nom)
    equipes = [
        {"id": e["team"]["id"], "nom": e["team"]["name"], "pays": e["team"].get("country")}
        for e in data.get("response", [])
    ]
    return {"equipes": equipes}


# ─── PRÉDICTION MATCH (avec buteurs systématiques) ────────────────────────────

@app.get("/prediction/match")
def predire_match_endpoint(
    sport: str = Query(...),
    team_domicile_id: int = Query(...),
    team_exterieur_id: int = Query(...),
    league_id: int | None = Query(None),
    season: int | None = Query(None),
):
    """
    Prédiction complète d'un match.
    Si league_id est fourni, les buteurs top 5 sont inclus systématiquement.
    """
    if sport not in ("football", "hockey"):
        raise HTTPException(400, "Sport non supporté ici")

    client = ApiSportsClient(sport)
    saison = season or SAISON_COURANTE

    # 1. Stats récentes des équipes
    fixtures_dom = client.derniers_matchs_equipe(team_domicile_id, NB_DERNIERS_MATCHS)
    fixtures_ext = client.derniers_matchs_equipe(team_exterieur_id, NB_DERNIERS_MATCHS)

    buts_marques_dom, buts_concedes_dom = extraire_buts_marques_concedes(fixtures_dom, team_domicile_id)
    buts_marques_ext, buts_concedes_ext = extraire_buts_marques_concedes(fixtures_ext, team_exterieur_id)

    if not buts_marques_dom or not buts_marques_ext:
        raise HTTPException(404, "Pas assez de données historiques")

    # 2. Prédiction Poisson
    prediction = predire_match(
        buts_marques_dom, buts_concedes_dom,
        buts_marques_ext, buts_concedes_ext,
    )

    resultat = {
        "sport": sport,
        "team_domicile_id": team_domicile_id,
        "team_exterieur_id": team_exterieur_id,
        "prediction": prediction,
        "buteurs_probables_domicile": [],
        "buteurs_probables_exterieur": [],
    }

    # 3. Buteurs top 5 — systématiques si league_id fourni
    if league_id and sport == "football":
        try:
            moyenne_dom = sum(buts_marques_dom) / len(buts_marques_dom)
            moyenne_ext = sum(buts_marques_ext) / len(buts_marques_ext)

            # Récupérer les joueurs de chaque équipe avec leurs stats
            joueurs_dom_raw = client.buteurs_equipe_ligue(team_domicile_id, league_id, saison)
            joueurs_ext_raw = client.buteurs_equipe_ligue(team_exterieur_id, league_id, saison)

            joueurs_dom = _extraire_joueurs_avec_stats(joueurs_dom_raw)
            joueurs_ext = _extraire_joueurs_avec_stats(joueurs_ext_raw)

            resultat["buteurs_probables_domicile"] = classer_buteurs_probables(
                joueurs_dom, prediction["lambda_domicile"], moyenne_dom, top_n=5
            )
            resultat["buteurs_probables_exterieur"] = classer_buteurs_probables(
                joueurs_ext, prediction["lambda_exterieur"], moyenne_ext, top_n=5
            )
        except Exception:
            pass  # On continue sans les buteurs si erreur

    return resultat


def _extraire_joueurs_avec_stats(response: dict) -> list[dict]:
    """Extrait les joueurs avec buts et matchs joués depuis l'endpoint /players."""
    joueurs = []
    for entry in response.get("response", []):
        player = entry.get("player", {})
        stats_list = entry.get("statistics", [])
        if not stats_list:
            continue
        stats = stats_list[0]
        buts = stats.get("goals", {}).get("total") or 0
        matchs = stats.get("games", {}).get("appearences") or 0
        if buts > 0:  # On ne garde que les joueurs qui ont marqué
            joueurs.append({
                "nom": player.get("name", "Inconnu"),
                "buts": buts,
                "matchs_joues": matchs,
            })
    return joueurs


# ─── PRÉDICTION TENNIS ────────────────────────────────────────────────────────

@app.get("/prediction/tennis")
def predire_tennis(
    victoires_a: int = Query(...),
    matchs_a: int = Query(...),
    victoires_b: int = Query(...),
    matchs_b: int = Query(...),
    format_best_of: int = Query(3),
):
    proba = probabilite_victoire_simple(victoires_a, matchs_a, victoires_b, matchs_b)
    sets = estimer_score_sets(proba["probabilite_victoire_joueur_a"] / 100, format_best_of)
    return {"probabilites": proba, "score_sets": sets}
