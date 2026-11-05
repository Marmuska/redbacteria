"""Mémoire locale : enregistre les références dans le dossier du projet."""
import json
import re
import shutil
from pathlib import Path

DOSSIER_PROJET = Path(__file__).resolve().parent
FICHIER_REFERENCES = DOSSIER_PROJET / "references.json"
DOSSIER_PHOTOS = DOSSIER_PROJET / "references"


def charger_references():
    """Renvoie le dictionnaire {nom: référence}."""
    if not FICHIER_REFERENCES.exists():
        return {}

    with open(FICHIER_REFERENCES, encoding="utf-8") as fichier:
        return json.load(fichier)


def _ecrire_references(references):
    with open(FICHIER_REFERENCES, "w", encoding="utf-8") as fichier:
        json.dump(references, fichier, indent=2, ensure_ascii=False)


def chemin_photo(reference):
    """Chemin complet de la photo d'une référence."""
    return DOSSIER_PROJET / reference["photo"]


def _nom_de_fichier(nom, extension, references):
    """Choisit un nom de fichier sûr, qui n'est pas utilisé par une autre référence."""
    base = re.sub(r"[^\w-]+", "_", nom).strip("_") or "reference"
    pris = {
        Path(reference["photo"]).name.lower()
        for autre, reference in references.items()
        if autre != nom
    }

    candidat = base + extension
    numero = 2
    while candidat.lower() in pris:
        candidat = f"{base}_{numero}{extension}"
        numero += 1

    return candidat


def enregistrer_reference(nom, photo_source, rougeur, minimum, maximum):
    """Copie la photo dans le projet et ajoute ou remplace la référence."""
    references = charger_references()
    photo_source = Path(photo_source).resolve()
    ancienne = references.get(nom)

    DOSSIER_PHOTOS.mkdir(exist_ok=True)
    extension = photo_source.suffix.lower()
    destination = DOSSIER_PHOTOS / _nom_de_fichier(nom, extension, references)

    if photo_source != destination.resolve():
        shutil.copyfile(photo_source, destination)

    # Si l'extension a changé, l'ancienne photo ne sert plus
    if ancienne and chemin_photo(ancienne).resolve() != destination.resolve():
        chemin_photo(ancienne).unlink(missing_ok=True)

    references[nom] = {
        "photo": destination.relative_to(DOSSIER_PROJET).as_posix(),
        "rougeur": rougeur,
        "min": minimum,
        "max": maximum,
    }
    _ecrire_references(references)


def modifier_intervalle(nom, minimum, maximum):
    """Enregistre un nouvel intervalle pour une référence existante."""
    references = charger_references()
    references[nom]["min"] = minimum
    references[nom]["max"] = maximum
    _ecrire_references(references)
