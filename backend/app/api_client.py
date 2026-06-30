"""
Client pour l'API API-Sports (football + hockey).
Toutes les requêtes passent par le cache pour économiser le quota gratuit.
"""
import requests
from .config import API_SPORTS_KEY, API_SPORTS_FOOTBALL_URL, API_SPORTS_HOCKEY_URL
from .cache import get_cached, set_cached


class ApiSportsClient:
    def __init__(self, sport: str):
        """sport: 'football' ou 'hockey'"""
        if sport == "football":
            self.base_url = API_SPORTS_FOOTBALL_URL
        elif sport == "hockey":
            self.base_url = API_SPORTS_HOCKEY_URL
        else:
            raise ValueError(f"Sport non supporté par API-Sports: {sport}")
        self.headers = {"x-apisports-key": API_SPORTS_KEY}

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        params = params or {}
        cache_key = f"{self.base_url}/{endpoint}?{sorted(params.items())}"

        cached = get_cached(cache_key)
        if cached is not None:
            return cached

        resp = requests.get(
            f"{self.base_url}/{endpoint}",
            headers=self.headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        set_cached(cache_key, data)
        return data

    def chercher_equipe(self, nom: str, league_id: int | None = None) -> dict:
        params = {"search": nom}
        return self._get("teams", params)

    def derniers_matchs_equipe(self, team_id: int, n: int = 10) -> dict:
        params = {"team": team_id, "last": n}
        return self._get("fixtures", params)

    def confrontations_directes(self, team1_id: int, team2_id: int, n: int = 10) -> dict:
        params = {"h2h": f"{team1_id}-{team2_id}", "last": n}
        return self._get("fixtures/headtohead", params)

    def meilleurs_buteurs(self, team_id: int, league_id: int, season: int) -> dict:
        params = {"team": team_id, "league": league_id, "season": season}
        return self._get("players/topscorers", params)

    def matchs_du_jour(self, date_str: str, league_id: int | None = None) -> dict:
        params = {"date": date_str}
        if league_id:
            params["league"] = league_id
        return self._get("fixtures", params)
