"""
Moteur de prédiction V1 : modèle de Poisson.

Principe (méthode classique utilisée en analyse sportive, dite "modèle Dixon-Coles simplifié") :
1. On calcule la force d'attaque et la faiblesse de défense de chaque équipe,
   relativement à la moyenne de la ligue.
2. On en déduit le nombre de buts attendu (lambda) pour chaque équipe dans CE match.
3. La distribution de Poisson donne la probabilité d'observer 0, 1, 2... buts
   pour un lambda donné.
4. En croisant les deux distributions (équipe A x équipe B), on obtient une matrice
   de probabilités pour chaque score exact possible.

Ce modèle est volontairement simple et explicable. Il sert de V1 ; une V2 pourra
le remplacer ou le compléter par du Machine Learning (ex: gradient boosting sur
des features enrichies : forme, blessures, classement, etc.)
"""
import math
from .config import MAX_BUTS_MATRICE


def poisson_proba(lam: float, k: int) -> float:
    """Probabilité d'observer exactement k buts si la moyenne attendue est lam."""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def calculer_force_attaque_defense(buts_marques: list[float], buts_concedes: list[float],
                                     moyenne_ligue_marques: float, moyenne_ligue_concedes: float) -> tuple[float, float]:
    """
    Retourne (force_attaque, force_defense) d'une équipe.
    force_attaque > 1 => équipe qui marque plus que la moyenne
    force_defense > 1 => équipe qui concède plus que la moyenne (donc défense faible)
    """
    moyenne_marques_equipe = sum(buts_marques) / len(buts_marques) if buts_marques else moyenne_ligue_marques
    moyenne_concedes_equipe = sum(buts_concedes) / len(buts_concedes) if buts_concedes else moyenne_ligue_concedes

    force_attaque = moyenne_marques_equipe / moyenne_ligue_marques if moyenne_ligue_marques else 1.0
    force_defense = moyenne_concedes_equipe / moyenne_ligue_concedes if moyenne_ligue_concedes else 1.0
    return force_attaque, force_defense


def calculer_lambdas(
    attaque_domicile: float, defense_exterieur: float, moyenne_buts_domicile_ligue: float,
    attaque_exterieur: float, defense_domicile: float, moyenne_buts_exterieur_ligue: float,
) -> tuple[float, float]:
    """
    Calcule le nombre de buts attendu pour l'équipe à domicile et l'équipe à l'extérieur.
    """
    lambda_domicile = attaque_domicile * defense_exterieur * moyenne_buts_domicile_ligue
    lambda_exterieur = attaque_exterieur * defense_domicile * moyenne_buts_exterieur_ligue
    return lambda_domicile, lambda_exterieur


def matrice_scores(lambda_domicile: float, lambda_exterieur: float, max_buts: int = MAX_BUTS_MATRICE):
    """
    Construit la matrice de probabilités pour chaque score exact possible,
    de 0-0 jusqu'à max_buts-max_buts.
    Retourne une liste de dicts: {"domicile": i, "exterieur": j, "probabilite": p}
    """
    matrice = []
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            p = poisson_proba(lambda_domicile, i) * poisson_proba(lambda_exterieur, j)
            matrice.append({"domicile": i, "exterieur": j, "probabilite": p})
    return matrice


def analyser_matrice(matrice: list[dict]) -> dict:
    """
    À partir de la matrice de scores, calcule les statistiques utiles :
    - score exact le plus probable
    - top 5 scores les plus probables
    - probabilité BTTS (les deux marquent)
    - probabilité plus/moins de 2.5 buts
    - probabilité victoire domicile / nul / victoire extérieur
    """
    matrice_triee = sorted(matrice, key=lambda x: x["probabilite"], reverse=True)
    top5 = matrice_triee[:5]

    proba_btts = sum(m["probabilite"] for m in matrice if m["domicile"] > 0 and m["exterieur"] > 0)
    proba_plus_2_5 = sum(m["probabilite"] for m in matrice if (m["domicile"] + m["exterieur"]) > 2.5)
    proba_moins_2_5 = 1 - proba_plus_2_5

    proba_victoire_domicile = sum(m["probabilite"] for m in matrice if m["domicile"] > m["exterieur"])
    proba_nul = sum(m["probabilite"] for m in matrice if m["domicile"] == m["exterieur"])
    proba_victoire_exterieur = sum(m["probabilite"] for m in matrice if m["domicile"] < m["exterieur"])

    nb_buts_attendu = sum((m["domicile"] + m["exterieur"]) * m["probabilite"] for m in matrice)

    return {
        "score_exact_plus_probable": {
            "domicile": top5[0]["domicile"],
            "exterieur": top5[0]["exterieur"],
            "probabilite": round(top5[0]["probabilite"] * 100, 1),
        },
        "top_5_scores": [
            {"score": f"{m['domicile']}-{m['exterieur']}", "probabilite": round(m["probabilite"] * 100, 1)}
            for m in top5
        ],
        "probabilite_btts": round(proba_btts * 100, 1),
        "probabilite_plus_2_5_buts": round(proba_plus_2_5 * 100, 1),
        "probabilite_moins_2_5_buts": round(proba_moins_2_5 * 100, 1),
        "probabilite_victoire_domicile": round(proba_victoire_domicile * 100, 1),
        "probabilite_nul": round(proba_nul * 100, 1),
        "probabilite_victoire_exterieur": round(proba_victoire_exterieur * 100, 1),
        "nombre_buts_attendu_total": round(nb_buts_attendu, 2),
    }


def predire_match(
    buts_marques_domicile: list[float], buts_concedes_domicile: list[float],
    buts_marques_exterieur: list[float], buts_concedes_exterieur: list[float],
    moyenne_ligue_domicile: float = 1.5, moyenne_ligue_exterieur: float = 1.2,
) -> dict:
    """
    Fonction principale : prend les stats récentes des deux équipes et retourne
    une prédiction complète (score exact, BTTS, nombre de buts, etc.)

    Les moyennes de ligue par défaut (1.5 buts/match à domicile, 1.2 à l'extérieur)
    sont des valeurs typiques en football européen ; à ajuster selon le sport/la ligue.
    """
    attaque_dom, defense_dom = calculer_force_attaque_defense(
        buts_marques_domicile, buts_concedes_domicile, moyenne_ligue_domicile, moyenne_ligue_exterieur
    )
    attaque_ext, defense_ext = calculer_force_attaque_defense(
        buts_marques_exterieur, buts_concedes_exterieur, moyenne_ligue_exterieur, moyenne_ligue_domicile
    )

    lambda_dom, lambda_ext = calculer_lambdas(
        attaque_dom, defense_ext, moyenne_ligue_domicile,
        attaque_ext, defense_dom, moyenne_ligue_exterieur,
    )

    matrice = matrice_scores(lambda_dom, lambda_ext)
    resultats = analyser_matrice(matrice)
    resultats["lambda_domicile"] = round(lambda_dom, 2)
    resultats["lambda_exterieur"] = round(lambda_ext, 2)
    return resultats
