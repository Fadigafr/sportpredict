"""
Prédiction tennis (V1 simple).
Le tennis n'a pas de "buts", donc le modèle Poisson football ne s'applique pas
directement. On utilise ici un modèle de probabilité de victoire par point,
basé sur le ratio de victoires récentes (proxy simple pour démarrer).

V2 possible : modèle Elo spécifique tennis (ratings ATP/WTA) + simulation de sets.
"""
import requests
from .config import THESPORTSDB_KEY, THESPORTSDB_URL
from .cache import get_cached, set_cached


def chercher_joueur_thesportsdb(nom: str) -> dict:
    cache_key = f"tsdb_player_{nom}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    url = f"{THESPORTSDB_URL}/{THESPORTSDB_KEY}/searchplayers.php"
    resp = requests.get(url, params={"p": nom}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    set_cached(cache_key, data)
    return data


def probabilite_victoire_simple(victoires_a: int, matchs_a: int, victoires_b: int, matchs_b: int) -> dict:
    """
    Modèle simple basé sur les taux de victoire récents des deux joueurs.
    Utilise une formule de type "log5" (popularisée en sabermetrics) pour combiner
    deux taux de victoire en une probabilité de confrontation directe.
    """
    taux_a = victoires_a / matchs_a if matchs_a else 0.5
    taux_b = victoires_b / matchs_b if matchs_b else 0.5

    if taux_a == 1.0 and taux_b == 1.0:
        proba_a = 0.5
    else:
        numerateur = taux_a - taux_a * taux_b
        denominateur = taux_a + taux_b - 2 * taux_a * taux_b
        proba_a = numerateur / denominateur if denominateur != 0 else 0.5

    return {
        "probabilite_victoire_joueur_a": round(proba_a * 100, 1),
        "probabilite_victoire_joueur_b": round((1 - proba_a) * 100, 1),
    }


def estimer_score_sets(proba_victoire_a: float, format_best_of: int = 3) -> dict:
    """
    Estime le score de sets le plus probable à partir de la probabilité de victoire globale.
    Approche simplifiée : on suppose que chaque set est indépendant avec la même probabilité p.
    """
    p = proba_victoire_a
    sets_pour_gagner = (format_best_of // 2) + 1

    if format_best_of == 3:
        scores_possibles = {
            "2-0": p ** 2,
            "2-1": 2 * (p ** 2) * (1 - p),
            "1-2": 2 * p * ((1 - p) ** 2),
            "0-2": (1 - p) ** 2,
        }
    else:  # best of 5
        scores_possibles = {
            "3-0": p ** 3,
            "3-1": 3 * (p ** 3) * (1 - p),
            "3-2": 6 * (p ** 3) * ((1 - p) ** 2),
            "2-3": 6 * (p ** 2) * ((1 - p) ** 3),
            "1-3": 3 * p * ((1 - p) ** 3),
            "0-3": (1 - p) ** 3,
        }

    score_plus_probable = max(scores_possibles, key=scores_possibles.get)
    return {
        "score_sets_plus_probable": score_plus_probable,
        "detail_probabilites": {k: round(v * 100, 1) for k, v in scores_possibles.items()},
    }
