"""
Prédiction du buteur probable.

Approche V1 (simple et explicable) : on croise le taux de buts par match de chaque
joueur (sur ses derniers matchs / cette saison) avec le lambda d'équipe calculé par
le moteur Poisson, pour estimer la probabilité que CE joueur marque dans CE match.

formule : p(joueur marque) ≈ 1 - exp(-buts_par_match_joueur * facteur_ajustement_match)
où facteur_ajustement_match = lambda_equipe_dans_ce_match / moyenne_buts_equipe_habituelle
"""
import math


def calculer_probabilite_buteur(
    buts_par_match_joueur: float,
    lambda_equipe_ce_match: float,
    moyenne_buts_equipe_habituelle: float,
) -> float:
    """
    Retourne la probabilité (0 à 1) que ce joueur marque au moins un but dans le match.
    """
    if moyenne_buts_equipe_habituelle <= 0:
        facteur = 1.0
    else:
        facteur = lambda_equipe_ce_match / moyenne_buts_equipe_habituelle

    taux_ajuste = buts_par_match_joueur * facteur
    proba = 1 - math.exp(-taux_ajuste)
    return proba


def classer_buteurs_probables(
    joueurs: list[dict],  # [{"nom": str, "buts": int, "matchs_joues": int}, ...]
    lambda_equipe_ce_match: float,
    moyenne_buts_equipe_habituelle: float,
    top_n: int = 5,
) -> list[dict]:
    """
    Prend une liste de joueurs avec leurs stats de buts, calcule la probabilité
    de marquer pour chacun, et retourne le top N classé par probabilité décroissante.
    """
    resultats = []
    for joueur in joueurs:
        if joueur.get("matchs_joues", 0) == 0:
            continue
        buts_par_match = joueur["buts"] / joueur["matchs_joues"]
        proba = calculer_probabilite_buteur(buts_par_match, lambda_equipe_ce_match, moyenne_buts_equipe_habituelle)
        resultats.append({
            "nom": joueur["nom"],
            "buts_saison": joueur["buts"],
            "matchs_joues": joueur["matchs_joues"],
            "probabilite_buteur": round(proba * 100, 1),
        })

    resultats.sort(key=lambda x: x["probabilite_buteur"], reverse=True)
    return resultats[:top_n]
