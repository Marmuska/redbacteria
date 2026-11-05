"""Calculs : compare l'intensité du rouge d'une photo à celle d'une référence."""
import math

import numpy as np
from PIL import Image

import parametres

# Traitement de l'image : 200x200 pixels, ensuite réduits en cases
# (les autres réglages sont dans parametres.py)
TAILLE_IMAGE = 200


def reduire_matrice(matrice, taille):
    """Calcule la moyenne de chaque bloc de pixels."""
    hauteur, largeur, canaux = matrice.shape

    nouvelle = np.zeros((hauteur // taille, largeur // taille, 3))

    for i in range(0, hauteur, taille):
        for j in range(0, largeur, taille):
            bloc = matrice[i:i + taille, j:j + taille]
            nouvelle[i // taille][j // taille] = np.mean(bloc, axis=(0, 1))

    return nouvelle


def charger_matrice(chemin):
    """Ouvre une photo et renvoie sa matrice RGB réduite en cases."""
    with Image.open(chemin) as image:
        image = image.convert("RGB").resize((TAILLE_IMAGE, TAILLE_IMAGE))

    return reduire_matrice(np.array(image, dtype=float), parametres.actuels["taille_bloc"])


def calculer_rougeur(matrice):
    """Rougeur de chaque case : R - max(G, B)."""
    return matrice[..., 0] - np.maximum(matrice[..., 1], matrice[..., 2])


def est_rouge(matrice, reglages=None):
    """Renvoie une matrice de booléens : la case est-elle rouge ou rose ?"""
    reglages = reglages or parametres.actuels
    R, G, B = matrice[..., 0], matrice[..., 1], matrice[..., 2]

    return (
        (R >= reglages["r_min"])
        & (G <= R - reglages["rougeur_min"])
        & (B <= R - reglages["rougeur_min"])
        & (G - B <= reglages["g_moins_b_max"])
        & (B - G <= reglages["b_moins_g_max"])
    )


def rougeur_reference(matrice):
    """La référence vaut 100 % : c'est la rougeur médiane de ses cases."""
    return float(np.median(calculer_rougeur(matrice)))


def part_de_rouge(matrice):
    """Pourcentage des cases considérées comme rouges ou roses."""
    return float(np.mean(est_rouge(matrice)) * 100)


def analyser_photo(matrice, rougeur_ref, minimum, maximum):
    """Compare une photo à la référence.

    La référence est le maximum : une case plus intense qu'elle compte pour 100 %.

    Renvoie :
    - intensite : intensité médiane en % de la référence ; une case rejetée compte pour 0 % ;
    - matrice_01 : le pourcentage de 1 (blanc) représente l'intensité. Les cases les plus
      intenses passent à 1 en premier. Une case rejetée reste toujours à 0 (noir).
    """
    intensites_brutes = calculer_rougeur(matrice) / rougeur_ref * 100
    intensites = np.clip(intensites_brutes, 0, 100)

    dans_intervalle = (intensites >= minimum) & (intensites <= maximum)
    acceptees = est_rouge(matrice) & dans_intervalle
    intensite = float(np.median(intensites * acceptees))

    return {
        "intensite": intensite,
        "matrice_01": construire_matrice_01(intensites_brutes, acceptees, intensite),
    }


def construire_matrice_01(intensites, acceptees, intensite):
    """Met à 1 les cases acceptées les plus intenses, autant que le demande l'intensité."""
    nombre_de_1 = min(math.ceil(intensite / 100 * intensites.size), int(acceptees.sum()))

    # Tri de la plus intense à la moins intense ; les cases rejetées passent en dernier
    classement = np.where(acceptees, intensites, -np.inf)
    ordre = np.argsort(-classement, axis=None, kind="stable")

    matrice_01 = np.zeros(intensites.shape, dtype=int)
    matrice_01.flat[ordre[:nombre_de_1]] = 1
    return matrice_01
