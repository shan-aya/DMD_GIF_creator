"""dmd_autofix -- propositions de correction automatique des GIF faibles
(fenêtre Revoir de DMD GIF Creator).

Principe : pour un GIF mal noté, on prépare des variantes de l'image SOURCE
(copies temporaires, la source n'est jamais modifiée), on les repasse dans le
traitement par lot normal (mêmes réglages que le lot d'origine) et on note le
rendu. Les meilleures versions sont PROPOSÉES ; rien ne change sans
validation de l'utilisateur, et l'original accepté est mis de côté, jamais
supprimé.

Calibré le 2026-09-27 sur les 54 GIF faibles d'un lot de 54 765 logos
Recalbox : 53 sortis de Faible/Mauvais en gardant les couleurs (surtout
"sombres éclaircis" : texte/contours noirs, invisibles sur un DMD noir,
passés en clair, couleurs vives gardées) ; l'inversion totale reste utile aux
logos sombres d'une seule couleur mais change les couleurs d'un logo coloré,
d'où deux propositions distinctes. Fond opaque clair : pas de proposition
(les corrections éclaircissent aussi le fond).

safe-modify — Historique des modifications
============================================
Version actuelle : v1

v1 — 2026-09-27 — création (variantes, règles de choix, dmd_batch.json).
"""
from __future__ import annotations

import json
import os

import numpy as np
from PIL import Image

BLACK = 10              # niveau "éteint", identique à dmd_quality.BLACK_THRESHOLD
FIX_MIN_GAIN = 10       # une proposition doit gagner au moins 10 points
INVERT_EXTRA = 5        # l'inversion n'est proposée que si elle fait nettement mieux
LIT_BORDER = 24         # bord opaque plus clair que ça = fond plein, pas de proposition
LIT_FILL_MAX = 0.90     # ... ou plus de 90 % de pixels allumés une fois le vide retiré
BATCH_FILE = "dmd_batch.json"
BEFORE_DIR = "_avant_correction"   # sous _a_revoir : originaux remplacés
SOURCE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".raw565", ".webp")


# --- variantes de la source ---------------------------------------------------
def _rgba(img):
    return np.asarray(img.convert("RGBA")).astype(np.float32)


def _luma_on_black(rgba):
    a = rgba[..., 3] / 255.0
    return (0.299 * rgba[..., 0] + 0.587 * rgba[..., 1] + 0.114 * rgba[..., 2]) * a


def _to_img(rgba):
    return Image.fromarray(rgba.clip(0, 255).astype(np.uint8), "RGBA")


def has_lit_background(img):
    """True si l'image a un fond plein : les corrections éclairciraient aussi
    le fond, on ne propose rien. Deux cas : bord opaque allumé, ou, une fois
    le vide retiré, plus de LIT_FILL_MAX des pixels allumés (plaque colorée
    entourée de noir ou de transparence, ex. Railroad Empire à 99 % ; les
    logos corrigés avec succès de l'essai du 2026-09-27 sont au plus à 76 %)."""
    lum = _luma_on_black(_rgba(img))
    if lum.shape[0] >= 5 and lum.shape[1] >= 5:
        ring = np.concatenate([lum[:2].ravel(), lum[-2:].ravel(), lum[:, :2].ravel(), lum[:, -2:].ravel()])
        if float(np.median(ring)) > LIT_BORDER:
            return True
    t = trim_empty(img)
    lum_t = lum if t is None else _luma_on_black(_rgba(t))
    return float((lum_t > BLACK).mean()) > LIT_FILL_MAX


def trim_empty(img):
    """Retire le vide : bords transparents ou noirs (éteints sur le DMD).
    Aucun contenu n'est coupé ; None si rien à retirer."""
    lit = _luma_on_black(_rgba(img)) > BLACK
    if not lit.any():
        return None
    ys, xs = np.nonzero(lit)
    box = (max(0, int(xs.min()) - 1), max(0, int(ys.min()) - 1),
           min(img.width, int(xs.max()) + 2), min(img.height, int(ys.max()) + 2))
    if box == (0, 0, img.width, img.height):
        return None
    return img.convert("RGBA").crop(box)


def gamma(img, g=0.55):
    rgba = _rgba(img)
    rgba[..., :3] = 255.0 * (rgba[..., :3] / 255.0) ** g
    return _to_img(rgba)


def levels(img):
    """Étire les niveaux : le plus clair des pixels allumés (99e centile)
    passe à 255, le noir reste noir. None si déjà lumineux."""
    rgba = _rgba(img)
    lum = _luma_on_black(rgba)
    lit = (rgba[..., 3] > 16) & (lum > BLACK)
    if lit.sum() < 16:
        return None
    hi = float(np.percentile(lum[lit], 99))
    k = 255.0 / max(1.0, hi)
    if k <= 1.05:
        return None
    rgba[..., :3] *= k
    return _to_img(rgba)


def dark_lift(img):
    """Éclaircit seulement les parties sombres et peu colorées (texte ou
    contours noirs, invisibles sur un DMD noir) ; les couleurs vives sont
    gardées. None si rien de sombre, ou si c'est un fond opaque sombre."""
    rgba = _rgba(img)
    vis = rgba[..., 3] > 16
    rgb = rgba[..., :3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1.0), 0.0) * 255.0
    mask = vis & (lum < 90) & (sat < 80)
    if mask.sum() < 16 or (vis.all() and mask.mean() > 0.4):
        return None
    rgb[mask] = 255.0 - rgb[mask]
    return _to_img(rgba)


def invert(img):
    """Inversion totale, transparence gardée ; None si l'image est opaque
    (on inverserait aussi le fond)."""
    rgba = _rgba(img)
    if (rgba[..., 3] > 16).all():
        return None
    rgba[..., :3] = 255.0 - rgba[..., :3]
    return _to_img(rgba)


# codes -> fonction, dans l'ordre d'essai ; un code composé = enchaînement
_STEPS = {"gamma": gamma, "levels": levels, "dark_lift": dark_lift, "invert": invert}
_CHAINS = (("gamma",), ("levels",), ("dark_lift",), ("dark_lift", "gamma"), ("invert",))


def build_variants(img):
    """{code: image} ; code = étapes jointes par "+" (ex. "trim+dark_lift")."""
    out = {}
    bases = {"": img}
    t = trim_empty(img)
    if t is not None:
        bases["trim"] = t
        out["trim"] = t
    for prefix, base in bases.items():
        for chain in _CHAINS:
            v = base
            for step in chain:
                v = _STEPS[step](v)
                if v is None:
                    break
            if v is not None:
                out["+".join(([prefix] if prefix else []) + list(chain))] = v
    return out


def keeps_colors(code):
    return "invert" not in code.split("+")


def choose(base_score, scored):
    """scored : {code: score}. Renvoie les codes à proposer (0 à 2) : la
    meilleure version qui garde les couleurs, puis l'inversion si elle fait
    nettement mieux. Chacune doit gagner au moins FIX_MIN_GAIN points."""
    def best(pred):
        c = [k for k in scored if pred(k)]
        return max(c, key=lambda k: scored[k]) if c else None

    out = []
    keep = best(keeps_colors)
    if keep is not None and scored[keep] >= base_score + FIX_MIN_GAIN:
        out.append(keep)
    inv = best(lambda k: not keeps_colors(k))
    if inv is not None and scored[inv] >= base_score + FIX_MIN_GAIN:
        if not out or scored[inv] >= scored[out[0]] + INVERT_EXTRA:
            out.append(inv)
    return out


# --- réglages des lots (dmd_batch.json, à côté de dmd_scores.json) -------------
def batch_path(folder):
    return os.path.join(folder, BATCH_FILE)


def load_batches(folder):
    try:
        with open(batch_path(folder), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_batches(folder, data):
    tmp = batch_path(folder) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, batch_path(folder))


def add_batch(folder, record):
    """Ajoute les réglages d'un lot ; renvoie son numéro (clé "b" des lignes
    de dmd_scores.json)."""
    data = load_batches(folder)
    batches = data.setdefault("batches", [])
    batches.append(record)
    save_batches(folder, data)
    return len(batches) - 1


def find_source(root, rel):
    """Source d'un GIF d'un dossier produit avant dmd_batch.json : même
    chemin relatif sous `root`, extension d'image quelconque (et sans le
    suffixe _sens ajouté par l'option "sens dans le nom" en repli)."""
    stem = os.path.join(root, *os.path.splitext(rel)[0].split("/"))
    cands = [stem]
    base = os.path.basename(stem)
    if "_" in base:
        cands.append(os.path.join(os.path.dirname(stem), base.rsplit("_", 1)[0]))
    for s in cands:
        for e in SOURCE_EXTS:
            for ext in (e, e.upper()):
                if os.path.isfile(s + ext):
                    return s + ext
    return None
