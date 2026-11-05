"""Paramètres modifiables depuis l'interface, enregistrés dans parametres.json."""
import json
from pathlib import Path

FICHIER_PARAMETRES = Path(__file__).resolve().parent / "parametres.json"

# Tailles de bloc possibles : elles doivent diviser l'image de 200x200 pixels
TAILLES_BLOC = (10, 5, 4, 2)

DEFAUTS = {
    # Base RGB : ce qui est considéré comme rouge ou rose
    "r_min": 80,
    "rougeur_min": 8,  # provisoire : à confirmer avec une photo de tissu non teint
    "g_moins_b_max": 30,  # au-delà : orange ou marron
    "b_moins_g_max": 130,  # au-delà : violet ou magenta
    # Analyse
    "taille_bloc": 4,  # 200 / 4 = matrice de 50x50 cases
    "intervalle_min": 70,  # intervalle proposé par défaut, en % de la référence
    "intervalle_max": 100,
    "duree_scan": 0.8,  # durée de l'animation par photo, en secondes
}

actuels = dict(DEFAUTS)


def verifier(valeurs):
    """Lève une ValueError avec un message clair si une valeur n'est pas valide."""
    limites_rgb = (
        ("r_min", "R minimum", 0),
        ("rougeur_min", "La rougeur minimum", 1),
        ("g_moins_b_max", "G - B maximum", 0),
        ("b_moins_g_max", "B - G maximum", 0),
    )
    for cle, nom, minimum in limites_rgb:
        if not minimum <= valeurs[cle] <= 255:
            raise ValueError(f"{nom} doit être entre {minimum} et 255.")

    if valeurs["taille_bloc"] not in TAILLES_BLOC:
        raise ValueError("La taille de la matrice n'est pas valide.")

    if not 0 <= valeurs["intervalle_min"] < valeurs["intervalle_max"]:
        raise ValueError("L'intervalle : le minimum doit être positif et plus petit que le maximum.")

    if not 0.1 <= valeurs["duree_scan"] <= 5:
        raise ValueError("La durée de l'animation doit être entre 0,1 et 5 secondes.")


def charger():
    """Lit le fichier. Renvoie False s'il est invalide : les défauts sont alors utilisés."""
    actuels.update(DEFAUTS)
    if not FICHIER_PARAMETRES.exists():
        return True

    try:
        with open(FICHIER_PARAMETRES, encoding="utf-8") as fichier:
            lus = json.load(fichier)
        valeurs = {cle: lus.get(cle, defaut) for cle, defaut in DEFAUTS.items()}
        verifier(valeurs)
    except (OSError, ValueError, TypeError, AttributeError):
        return False

    actuels.update(valeurs)
    return True


def enregistrer(valeurs):
    """Vérifie, applique et enregistre de nouvelles valeurs."""
    verifier(valeurs)
    with open(FICHIER_PARAMETRES, "w", encoding="utf-8") as fichier:
        json.dump(valeurs, fichier, indent=2, ensure_ascii=False)
    actuels.update(valeurs)
