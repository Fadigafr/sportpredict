"""
Client pour l'API API-Sports (football + hockey).
"""
import requests
from .config import API_SPORTS_KEY, API_SPORTS_FOOTBALL_URL, API_SPORTS_HOCKEY_URL
from .cache import get_cached, set_cached


class ApiSportsClient:
    def __init__(self, sport: str):
        if sport == "football":
            self.base_url = API_SPORTS_FOOTBALL_URL
        elif sport == "hockey":
            self.base_url = API_SPORTS_HOCKEY_URL
        else:
            raise ValueError(f"Sport non supporté: {sport}")
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

    def chercher_equipe(self, nom: str) -> dict:
        return self._get("teams", {"search": nom})

    def derniers_matchs_equipe(self, team_id: int, n: int = 10) -> dict:
        return self._get("fixtures", {"team": team_id, "last": n})

    def matchs_par_ligue_date(self, league_id: int, date_str: str) -> dict:
        return self._get("fixtures", {"league": league_id, "date": date_str, "season": self._saison_courante()})

    def matchs_par_ligue_semaine(self, league_id: int, from_date: str, to_date: str) -> dict:
        return self._get("fixtures", {
            "league": league_id,
            "from": from_date,
            "to": to_date,
            "season": self._saison_courante(),
        })

    def meilleurs_buteurs_ligue(self, league_id: int, season: int) -> dict:
        return self._get("players/topscorers", {"league": league_id, "season": season})

    def buteurs_equipe_ligue(self, team_id: int, league_id: int, season: int) -> dict:
        return self._get("players", {
            "team": team_id,
            "league": league_id,
            "season": season,
        })

    def classement_ligue(self, league_id: int, season: int) -> dict:
        return self._get("standings", {"league": league_id, "season": season})

    def confrontations_directes(self, team1_id: int, team2_id: int, n: int = 10) -> dict:
        return self._get("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": n})

    def _saison_courante(self) -> int:
        from .config import SAISON_COURANTE
        return SAISON_COURANTE
