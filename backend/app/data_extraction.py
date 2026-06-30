"""
Transforme les réponses brutes d'API-Sports en listes de buts marqués/concédés,
prêtes à être consommées par le moteur de prédiction Poisson.
"""


def extraire_buts_marques_concedes(fixtures_response: dict, team_id: int) -> tuple[list, list]:
    """
    À partir d'une réponse de l'endpoint /fixtures (derniers matchs d'une équipe),
    retourne (liste_buts_marques, liste_buts_concedes) pour cette équipe.
    """
    buts_marques = []
    buts_concedes = []

    for fixture in fixtures_response.get("response", []):
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})

        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")
        goals_home = goals.get("home")
        goals_away = goals.get("away")

        if goals_home is None or goals_away is None:
            continue  # match pas encore joué, on l'ignore

        if home_id == team_id:
            buts_marques.append(goals_home)
            buts_concedes.append(goals_away)
        elif away_id == team_id:
            buts_marques.append(goals_away)
            buts_concedes.append(goals_home)

    return buts_marques, buts_concedes


def extraire_buteurs(topscorers_response: dict) -> list[dict]:
    """
    À partir de l'endpoint /players/topscorers, retourne une liste simplifiée
    [{"nom": ..., "buts": ..., "matchs_joues": ...}, ...]
    """
    joueurs = []
    for entry in topscorers_response.get("response", []):
        player = entry.get("player", {})
        stats_list = entry.get("statistics", [])
        if not stats_list:
            continue
        stats = stats_list[0]
        goals = stats.get("goals", {}).get("total") or 0
        appearances = stats.get("games", {}).get("appearences") or 0
        joueurs.append({
            "nom": player.get("name", "Inconnu"),
            "buts": goals,
            "matchs_joues": appearances,
        })
    return joueurs
