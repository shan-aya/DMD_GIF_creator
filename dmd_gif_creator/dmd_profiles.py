# ============================================
# safe-modify — Historique des modifications
# ============================================
# Version actuelle : v4
#
# v4 — 2026-09-26 — safe-modify — Profil Logos Recalbox : cadence 15 i/s
#      (choix utilisateur après essais sur la dalle, variante G jugée plus
#      fluide que B à 10 i/s ; plafond 30 s inchangé).
#
# v3 — 2026-09-26 — safe-modify — Décisions utilisateur après essais sur la
#      dalle : DMD playlist 20 i/s validé ; plafond 30 s du profil Logos
#      Recalbox confirmé comme maximum (n'est plus provisoire). Commentaires
#      seuls, valeurs inchangées.
#
# v2 — 2026-09-26 — safe-modify — Demande utilisateur : profil "DMD playlist"
#      (réglages DMD + cadence plus élevée pour la fluidité) et profils
#      personnels avec toutes les variables accessibles. Un profil porte
#      désormais aussi les paramètres globaux (fps, duration, scroll_speed,
#      contrast, saturation, color_count, pixel_perfect ; None = inchangé).
#      delete_profile() (profil personnel supprimé, profil intégré remis à ses
#      valeurs d'origine), new_profile_key().
# v1 — 2026-09-26 — safe-modify — Création : profils "Générique" et "Logos
#      Recalbox (navigation)", options neutres du moteur (dmd_pipeline_quality
#      v27, dmd_engine v18), surcharge par profiles.json.
# ============================================
"""Profils de génération DMD GIF Creator (sans dépendance Tk).

Options de profil (toujours appliquées ; None = désactivée) :
  fill_min_ratio      défilement imposé dès ce rapport L/H
  invert_dark         inversion des logos sombres monochromes (booléen)
  max_scroll_cycle_s  plafond d'un aller-retour de défilement (s)
Paramètres globaux (None = ne pas modifier la valeur courante) :
  fps, duration, scroll_speed, contrast, saturation, color_count, pixel_perfect
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROFILES_FILE = "profiles.json"

_TYPES = {
    "fill_min_ratio": float, "invert_dark": bool, "max_scroll_cycle_s": float,
    "fps": int, "duration": float, "scroll_speed": float, "contrast": float,
    "saturation": float, "color_count": int, "pixel_perfect": bool,
}
OPTION_KEYS = tuple(_TYPES)
_OFF_WHEN_ZERO = ("fill_min_ratio", "max_scroll_cycle_s")

_BASE = {"duration": 2.0, "scroll_speed": 1.0, "contrast": 1.5, "saturation": 1.3,
         "color_count": 256, "pixel_perfect": None}

BUILTIN_PROFILES = {
    # Moteur neutre : aucune limite, pour tout usage.
    "generic": {"label": "Générique", "fill_min_ratio": None, "invert_dark": True,
                "max_scroll_cycle_s": None, "fps": 10, **_BASE},
    # Logos de jeux affichés par la dalle en navigation Recalbox (raw565pack).
    "recalbox_logos": {"label": "Logos Recalbox (navigation)", "fill_min_ratio": 2.0,
                       "invert_dark": True,
                       # 30 s = maximum pour un logo (décision utilisateur 2026-09-26,
                       # au-delà c'est trop long) ; 15 i/s retenu après essais sur la
                       # dalle (variante G : plus fluide que 10 i/s)
                       "max_scroll_cycle_s": 30.0,
                       "fps": 15, **_BASE},
    # GIF joués en playlist sur la dalle : mêmes réglages DMD, sans plafond,
    # cadence doublée pour plus de fluidité (20 i/s validé sur la dalle).
    "dmd_playlist": {"label": "DMD playlist", "fill_min_ratio": 2.0, "invert_dark": True,
                     "max_scroll_cycle_s": None, "fps": 20, **_BASE},
}


def _clean(values: dict) -> dict:
    out = {}
    for k, typ in _TYPES.items():
        v = values.get(k)
        if v is None or v == "":
            out[k] = True if k == "invert_dark" else None
            continue
        try:
            v = typ(v)
        except (TypeError, ValueError):
            out[k] = True if k == "invert_dark" else None
            continue
        if k in _OFF_WHEN_ZERO and not v:
            v = None
        out[k] = v
    return out


def load_profiles(user_dir) -> dict:
    """Profils intégrés, surchargés/complétés par profiles.json s'il existe.
    Retourne {clé: {"label", "builtin", options...}} ; fichier illisible ignoré."""
    profiles = {k: {**v, "builtin": True} for k, v in BUILTIN_PROFILES.items()}
    try:
        data = json.loads((Path(user_dir) / PROFILES_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return profiles
    if isinstance(data, dict):
        for key, values in data.items():
            if not isinstance(values, dict):
                continue
            base = profiles.get(key, {"label": str(values.get("label", key)), "builtin": False})
            merged = {**base, **values}
            base.update(_clean(merged))
            base["label"] = str(values.get("label", base["label"]))
            profiles[key] = base
    return profiles


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def save_profile(user_dir, key: str, values: dict, label: str | None = None) -> Path:
    """Enregistre les valeurs d'un profil dans profiles.json (les autres
    entrées du fichier sont conservées)."""
    path = Path(user_dir) / PROFILES_FILE
    data = _read(path)
    entry = _clean(values)
    if label:
        entry["label"] = label
    elif key in data and "label" in data[key]:
        entry["label"] = data[key]["label"]
    data[key] = entry
    _write(path, data)
    return path


def delete_profile(user_dir, key: str) -> None:
    """Retire le profil de profiles.json : un profil personnel disparaît, un
    profil intégré retrouve ses valeurs d'origine."""
    path = Path(user_dir) / PROFILES_FILE
    data = _read(path)
    if key in data:
        del data[key]
        _write(path, data)


def new_profile_key(label: str, existing) -> str:
    """Clé unique dérivée du nom saisi (ex. "Ma borne" -> "user_ma_borne")."""
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "profil"
    key, n = f"user_{slug}", 2
    while key in existing:
        key, n = f"user_{slug}_{n}", n + 1
    return key
