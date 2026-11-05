#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dmd_gif_convert -- conversion d'un GIF animé EXISTANT vers le format DMD 128×32.

Module cœur SANS Tkinter (Pillow + NumPy uniquement) : utilisé par l'onglet GIF de DMD GIF Creator, par la
ligne de commande ci-dessous et par le bot Discord (qui l'appelle en sous-processus).

Principe (le moteur de rendu de l'appli traite des images FIXES : on réutilise ses briques image par image) :
  1. load_gif      : images RGB composées sur noir, durées d'origine, garde-fous (taille, nb d'images, pixels).
  2. analyze_gif   : verdict « à convertir ? » (dimensions, fond non noir, contraste faible, couleurs, poids) ;
                     un GIF déjà produit par l'appli (filigrane DGC) et aux bonnes dimensions est « déjà OK ».
  3. plan_conversion : UN SEUL recadrage pour tout le GIF (sinon l'animation tremble) et des réglages choisis
                     UNE fois (3 images à 25/50/75 %), appliqués à toutes les images. Recadrage « remplir » ou
                     bandes noires choisi automatiquement selon le contenu perdu.
  4. render_frames : par image  clé du fond -> recadrage -> optimize_for_dmd -> adaptive_resize(pixel_perfect)
                     -> canevas noir 128×32 -> cleanup_dmd_frame (même chaîne que _video_render_frame, VIDEO).
  5. encodage      : dmd_gif_exporter avec les durées d'origine, filigrane DGC.

Ligne de commande (JSON sur stdout avec --json) :
    python dmd_gif_convert.py in.gif -o out.gif [--check] [--letterbox] [--force] [--json]
Codes de sortie : 0 = traité (voir le JSON : "converted" vrai/faux), 3 = GIF refusé/illisible, 4 = erreur interne.

safe-modify — Historique des modifications
============================================
Version actuelle : v1

v1 — 2026-11-05 — création (onglet GIF + bot Discord).
"""
from __future__ import annotations

import argparse
import dataclasses
import io
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

try:  # même schéma d'import que les autres modules de l'appli (paquet ou dossier à plat)
    from .dmd_engine import DMDEngine
    from .dmd_video_engine import VideoEngine
    from .dmd_gif_exporter import _encode_gif_bytes
    from . import dmd_quality as dq
    from . import dgc_mark
except ImportError:  # exécution en script / copie à plat (bot), y compris `python -I` (sans dossier du script)
    import os as _os
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from dmd_engine import DMDEngine
    from dmd_video_engine import VideoEngine
    from dmd_gif_exporter import _encode_gif_bytes
    import dmd_quality as dq
    import dgc_mark

TARGET_W, TARGET_H = 128, 32
APP_URL = "https://github.com/shan-aya/DMD_GIF_creator/releases/latest"
APP_PAGE = "https://shan-aya.github.io/DMD_GIF_creator/"
REPORT_VERSION = 1

# --- Seuils (à calibrer sur un lot réel de GIF) ---------------------------------------------------------
CONTENT_LEVEL = 24          # canal max au-dessus duquel un pixel est du « contenu » (sous : fond noir)
THUMB_SIDE = 192            # côté max des vignettes d'analyse (recadrage, énergie)
CROP_PAD = 2                # marge de recadrage (px, comme crop_to_visible_content)
FULL_FRAME_RATIO = 0.96     # zone de contenu couvrant >= 96 % de l'image sur les 2 axes : pas de recadrage
FILL_LOSS_TINY = 0.06       # « remplir » accepté si on perd <= 6 % de la surface de contenu ET <= 8 % de lumière
FILL_ENERGY_TINY = 0.08
FILL_LOSS_MAX = 0.35        # ... ou jusqu'à 35 % si la perte ne touche (presque) rien d'allumé
FILL_ENERGY_MAX = 0.03      # part max de « lumière » du contenu perdue par le recadrage
BG_UNIFORM_STD = 14.0       # écart-type max du bord pour parler de fond uni
BG_STABLE_DIFF = 20.0       # écart max de la couleur de fond entre images
KEY_TOL = 36                # tolérance (somme |ΔRVB|) de la clé du fond uni -> noir
DARK_CONTENT_LUMA = 40.0    # contenu plus sombre que ça après clé : invisible sur DMD, on ne clé pas
MAX_COLORS_OK = 128         # au-delà : « trop de couleurs » (si les dimensions sont déjà bonnes)
MAX_BYTES_OK = 256 * 1024   # au-delà : « trop lourd »
LOW_SCORE = 50              # score dmd_quality <= 50 (Poor/Bad) : contraste/occupation faibles

# Cadrage intelligent (suivi du sujet) -- NumPy seul, pas d'OpenCV (le bot n'a que Pillow + NumPy)
SCROLL_MIN_DIFF = 0.15      # scroll seulement si le ratio du contenu s'écarte de >= 15 % du 4:1
SCROLL_MIN_TRAVEL = 8       # course mini (px DMD) pour parler de défilement
SCROLL_HOLD_MS = 800        # pause au début et à la fin du défilement
SCROLL_BASE_MS = 45         # durée d'un pas d'1 px DMD (modulée par la densité du contenu : 0,7x à 1,5x)
SCROLL_STEP_MIN, SCROLL_STEP_MAX = 40, 90
SCROLL_BACK_FACTOR = 0.75   # le retour (aller-retour) est un peu plus vif
SCROLL_REVERSE_GAIN = 1.15  # on démarre par l'extrémité la plus chargée si elle l'est 15 % de plus que l'autre
SCROLL_MAX_FRAMES = 300
AUTO_SCROLL_MARGIN = 5      # auto : le scroll plein écran doit battre l'image entière d'au moins 5 points de note
FOLLOW_MIN_FRAMES = 4       # moins d'images : pas de suivi
FOLLOW_MARGIN = 1.10        # marge autour de l'étendue du sujet
FOLLOW_MAX_AREA = 0.65      # suivi seulement si la fenêtre fait <= 65 % de la zone de contenu (sinon : gain nul)
FOLLOW_MIN_COVERAGE = 0.88  # part moyenne du sujet qui doit rester dans la fenêtre
FOLLOW_MIN_COVERAGE_P10 = 0.60   # ... et au pire 10 % des images
FOLLOW_ALPHA = 0.35         # lissage exponentiel (appliqué avant ET arrière : aucun retard)
FOLLOW_DEADZONE = 0.10      # la caméra ne bouge pas tant que le sujet reste à +-10 % de la fenêtre
CUT_DIFF = 0.22             # écart moyen de luminance (0-1) entre 2 images = coupure de plan
MOTION_THR = 28.0           # écart de luminance au fond (médiane) pour parler de mouvement
MIN_SUBJECT_FRAC = 0.002    # surface mini du sujet (part de la vignette)

DEFAULT_SETTINGS: dict[str, Any] = {
    "contrast": 1.5,
    "saturation": 1.3,
    "brightness": 1.0,
    "black_threshold": 30,
    "color_count": 64,
    "cleanup_power": 0.5,
    "pixel_perfect": True,
    "invert": False,
}

REASONS = {
    "size": {"fr": "Dimensions différentes de 128×32", "en": "Size is not 128×32", "es": "Tamaño distinto de 128×32"},
    "background": {"fr": "Fond non noir", "en": "Background is not black", "es": "Fondo no negro"},
    "low_quality": {"fr": "Contraste / occupation faibles", "en": "Low contrast / occupancy", "es": "Contraste / ocupación bajos"},
    "too_many_colors": {"fr": "Trop de couleurs", "en": "Too many colors", "es": "Demasiados colores"},
    "too_heavy": {"fr": "Fichier trop lourd", "en": "File too heavy", "es": "Archivo demasiado pesado"},
    "dark_on_light": {"fr": "Contenu sombre sur fond clair : fond conservé (voir l'appli, mode manuel)",
                      "en": "Dark content on light background: background kept (use the app, manual mode)",
                      "es": "Contenido oscuro sobre fondo claro: fondo conservado (use la app, modo manual)"},
    "lit_background": {"fr": "Fond plein non uni : impossible de le passer en noir proprement",
                       "en": "Non-uniform lit background: cannot be turned black cleanly",
                       "es": "Fondo lleno no uniforme: no se puede pasar a negro"},
    "inverted": {"fr": "Texte sombre sur fond clair : couleurs inversées", "en": "Dark text on light background: colors inverted",
                 "es": "Texto oscuro sobre fondo claro: colores invertidos"},
    "empty_content": {"fr": "Aucun contenu visible détecté", "en": "No visible content detected",
                      "es": "No se detecta contenido visible"},
    "reduced_source": {"fr": "Source très grande : réduite avant traitement", "en": "Very large source: reduced before processing",
                       "es": "Origen muy grande: reducido antes de procesar"},
}


def reason_text(code: str, lang: str = "fr") -> str:
    return REASONS.get(code, {}).get(lang) or REASONS.get(code, {}).get("en") or code


# --- Erreurs / limites ------------------------------------------------------------------------------------
class GifError(Exception):
    """GIF refusé ou illisible. `code` : not_gif, too_large, too_many_frames, too_big_dimensions, too_heavy_total,
    unreadable, empty."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class GifLimits:
    max_bytes: int = 25 * 1024 * 1024
    max_frames: int = 600
    max_pixels: int = 4096 * 4096          # par image (avant réduction)
    max_work_side: int = 800               # côté max des images de travail (réduction entière au-delà)
    max_total_pixels: int = 120_000_000    # images × largeur × hauteur de travail (mémoire ~ 3 octets/pixel)


# --- Chargement -------------------------------------------------------------------------------------------
@dataclass
class GifData:
    frames: list                      # images RGB (taille de travail), composées sur noir
    durations: list                   # ms par image (timing d'origine, normalisé comme les navigateurs)
    alphas: list | None               # canaux alpha « L » (taille de travail) si le GIF a de la transparence
    width: int                        # taille d'ORIGINE
    height: int
    work_scale: int                   # facteur de réduction entier appliqué aux images de travail
    n_bytes: int
    dgc: dict | None = None           # résultat de dgc_mark.detect_gif (None : pas de filigrane)

    @property
    def total_ms(self) -> int:
        return int(sum(self.durations))


def _norm_duration(d: Any) -> int:
    try:
        d = int(d or 0)
    except (TypeError, ValueError):
        d = 0
    return 100 if d <= 10 else d      # les navigateurs ramènent <= 10 ms à 100 ms


def load_gif(data: bytes, limits: GifLimits | None = None) -> GifData:
    limits = limits or GifLimits()
    if not data:
        raise GifError("empty", "Fichier vide")
    if len(data) > limits.max_bytes:
        raise GifError("too_large", f"Fichier trop gros ({len(data)} octets > {limits.max_bytes})")
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        raise GifError("not_gif", "Ce fichier n'est pas un GIF")
    try:
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        n = int(getattr(im, "n_frames", 1))
    except Exception as e:  # noqa: BLE001 -- tout échec de décodage = GIF illisible
        raise GifError("unreadable", f"GIF illisible : {e}") from e
    if w <= 0 or h <= 0 or w * h > limits.max_pixels:
        raise GifError("too_big_dimensions", f"Dimensions trop grandes ({w}×{h})")
    if n > limits.max_frames:
        raise GifError("too_many_frames", f"Trop d'images ({n} > {limits.max_frames})")
    scale = max(1, math.ceil(max(w, h) / limits.max_work_side))
    ww, wh = math.ceil(w / scale), math.ceil(h / scale)
    if n * ww * wh > limits.max_total_pixels:
        raise GifError("too_heavy_total", f"GIF trop lourd à traiter ({n} images de {w}×{h})")

    frames, durations, alphas = [], [], []
    any_alpha = False
    try:
        for i in range(n):
            im.seek(i)
            rgba = im.convert("RGBA")
            a = rgba.getchannel("A")
            if a.getextrema()[0] < 255:
                any_alpha = True
                rgb = Image.new("RGB", rgba.size, (0, 0, 0))
                rgb.paste(rgba, mask=a)
            else:
                rgb = rgba.convert("RGB")
            if scale > 1:
                rgb = rgb.reduce(scale)
                a = a.reduce(scale)
            frames.append(rgb)
            alphas.append(a)
            durations.append(_norm_duration(im.info.get("duration", 100)))
    except Exception as e:  # noqa: BLE001
        raise GifError("unreadable", f"GIF illisible (image {len(frames) + 1}) : {e}") from e
    if not frames:
        raise GifError("empty", "GIF sans image")
    try:
        dgc = dgc_mark.detect_gif(data)
    except Exception:  # noqa: BLE001 -- le filigrane n'est qu'un indice
        dgc = None
    return GifData(frames, durations, alphas if any_alpha else None, w, h, scale, len(data), dgc)


def _sample_indices(n: int) -> list[int]:
    """3 images à 25 / 50 / 75 % de la séquence (moins si le GIF est court)."""
    if n <= 1:
        return [0]
    return sorted({min(n - 1, int(n * 0.25)), n // 2, min(n - 1, int(n * 0.75))})


# --- Fond -------------------------------------------------------------------------------------------------
def _ring(arr: np.ndarray) -> np.ndarray:
    r = max(1, min(arr.shape[0], arr.shape[1]) // 16)
    return np.concatenate([arr[:r].reshape(-1, 3), arr[-r:].reshape(-1, 3),
                           arr[:, :r].reshape(-1, 3), arr[:, -r:].reshape(-1, 3)])


def detect_background(src: GifData, idx: Sequence[int]) -> tuple[str, tuple[int, int, int] | None]:
    """-> (genre, couleur) ; genre : "transparent", "black", "uniform" (fond clair/coloré uni et stable) ou
    "complex" (fond clair non uni, ex. photo). La couleur est celle du bord pour uniform/complex."""
    if src.alphas is not None:
        return "transparent", (0, 0, 0)
    dark_all = True
    meds, stds = [], []
    for i in idx:
        fr = src.frames[i]
        _color, is_dark = DMDEngine.detect_background_color(fr)
        dark_all = dark_all and is_dark
        ring = _ring(np.asarray(fr, dtype=np.float32))
        meds.append(np.median(ring, axis=0))
        stds.append(float(ring.std(axis=0).max()))
    if dark_all:
        return "black", (0, 0, 0)
    stack = np.stack(meds)
    med = np.median(stack, axis=0)
    color = tuple(int(v) for v in med)
    stable = float(np.max(np.abs(stack - med))) <= BG_STABLE_DIFF
    if max(stds) <= BG_UNIFORM_STD and stable:
        return "uniform", color
    return "complex", color


def _key_background(img: Image.Image, color: Sequence[int], tol: int = KEY_TOL) -> Image.Image:
    """Fond uni -> noir, avec bord adouci : un pixel mélangé fond/contenu est assombri au prorata (pas de halo clair)."""
    arr = np.asarray(img, dtype=np.int16)
    dist = np.abs(arr - np.array(color, dtype=np.int16)).sum(axis=2).astype(np.float32)
    a = np.clip((dist - tol) / max(1.0, float(tol)), 0.0, 1.0)
    return Image.fromarray((arr * a[..., None]).astype(np.uint8), "RGB")


def _keying_ok(src: GifData, idx: Sequence[int], color: Sequence[int]) -> bool:
    """La clé du fond n'a de sens que si du contenu CLAIR reste visible sur noir (sinon : texte noir sur fond blanc,
    la clé le rendrait invisible -> on garde le fond et on prévient)."""
    for i in idx:
        arr = np.asarray(src.frames[i].reduce(max(1, max(src.frames[i].size) // THUMB_SIDE)), dtype=np.float32)
        dist = np.abs(arr - np.array(color, dtype=np.float32)).sum(axis=2)
        content = dist > 2 * KEY_TOL
        frac = float(content.mean())
        if frac < 0.01 or frac > 0.90:
            return False
        luma = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
        if float(luma[content].mean()) < DARK_CONTENT_LUMA:
            return False
    return True


def _invert_ok(src: GifData, idx: Sequence[int], color: Sequence[int]) -> bool:
    """Fond uni CLAIR + contenu quasi noir et neutre (texte/logo noir) : l'inversion donne un DMD lisible, et ne
    change aucune couleur notable (contenu coloré : on ne touche pas, on prévient)."""
    if float(np.dot(np.array(color, dtype=np.float32), [0.299, 0.587, 0.114])) < 160.0:
        return False
    for i in idx:
        fr = src.frames[i]
        arr = np.asarray(fr.reduce(max(1, max(fr.size) // THUMB_SIDE)), dtype=np.float32)
        content = np.abs(arr - np.array(color, dtype=np.float32)).sum(axis=2) > 2 * KEY_TOL
        if float(content.mean()) < 0.01 or float(content.mean()) > 0.90:
            return False
        px = arr[content]
        luma = float((0.299 * px[:, 0] + 0.587 * px[:, 1] + 0.114 * px[:, 2]).mean())
        spread = float((px.max(axis=1) - px.min(axis=1)).mean())   # ~ saturation (0 = gris)
        if luma >= DARK_CONTENT_LUMA or spread > 40.0:
            return False
    return True


# --- Analyse (verdict) -----------------------------------------------------------------------------------
@dataclass
class Verdict:
    needs_conversion: bool
    already_ok: bool
    reasons: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"needs_conversion": self.needs_conversion, "already_ok": self.already_ok,
                "reasons": list(self.reasons), "metrics": dict(self.metrics)}

    def reasons_text(self, lang: str = "fr") -> list:
        return [reason_text(c, lang) for c in self.reasons]


def _count_colors(src: GifData, idx: Sequence[int]) -> int:
    best = 0
    for i in idx:
        arr = np.asarray(src.frames[i].reduce(max(1, max(src.frames[i].size) // 256)), dtype=np.uint32)
        packed = (arr[..., 0] << 16) | (arr[..., 1] << 8) | arr[..., 2]
        best = max(best, int(np.unique(packed).size))
    return best


def analyze_gif(src: GifData) -> Verdict:
    idx = _sample_indices(len(src.frames))
    reasons: list[str] = []
    size_ok = (src.width, src.height) == (TARGET_W, TARGET_H)
    if not size_ok:
        reasons.append("size")
    bg_kind, _bg = detect_background(src, idx)
    if bg_kind in ("uniform", "complex"):
        reasons.append("background")
    colors = _count_colors(src, idx)
    if colors > MAX_COLORS_OK:
        reasons.append("too_many_colors")
    if src.n_bytes > MAX_BYTES_OK:
        reasons.append("too_heavy")
    score = None
    if size_ok:  # sur d'autres dimensions la note n'a pas de sens : « size » suffit
        score = dq.evaluate_frames(src.frames, src.durations).score
        if score <= LOW_SCORE:
            reasons.append("low_quality")
    marked = bool(src.dgc)
    if marked and size_ok:  # produit par l'appli : jamais reconverti
        reasons = []
    metrics = {"width": src.width, "height": src.height, "frames": len(src.frames), "duration_ms": src.total_ms,
               "bytes": src.n_bytes, "colors": colors, "background": bg_kind, "has_alpha": src.alphas is not None,
               "score": score, "dgc": (src.dgc or {}).get("version") if marked else None}
    return Verdict(bool(reasons), not reasons, reasons, metrics)


# --- Plan de conversion ----------------------------------------------------------------------------------
@dataclass
class Plan:
    layout: str                     # "native" (déjà 128×32) | "fit" (bandes noires) | "fill" (recadré fixe) | "follow" (suivi)
    crop: tuple | None              # (x, y, w, h) en coordonnées des images de travail
    bg_kind: str
    bg_color: tuple | None
    key_background: bool
    settings: dict
    lost_pct: float = 0.0           # % de surface de contenu perdue (layout "fill")
    mode: str = "auto"
    warnings: list = field(default_factory=list)
    windows: list | None = None     # layout "follow" : fenêtre (x, y, w, h) PAR image (taille constante)
    follow: dict | None = None      # diagnostic du suivi (zoom, couverture, trajet, coupures)
    timeline: list | None = None    # layout "scroll" : [(index image source, durée ms)] -- une entrée par image de SORTIE
    scroll: dict | None = None      # diagnostic du scroll (axe, course, sens, durées)

    def to_dict(self) -> dict:
        return {"layout": self.layout, "crop": list(self.crop) if self.crop else None, "background": self.bg_kind,
                "key_background": self.key_background, "lost_pct": round(self.lost_pct, 1), "mode": self.mode,
                "settings": dict(self.settings), "warnings": list(self.warnings), "follow": self.follow,
                "scroll": self.scroll}


def plan_durations(src: "GifData", plan: Plan) -> list:
    """Durées (ms) des images de SORTIE : celles de la source, sauf scroll (chronologie propre)."""
    if plan.layout == "scroll" and plan.timeline:
        return [int(d) for _, d in plan.timeline]
    return list(src.durations)


def plan_source_index(plan: Plan, i: int) -> int:
    """Index de l'image source qui sert l'image de sortie i (aperçu « avant »)."""
    if plan.layout == "scroll" and plan.timeline:
        return int(plan.timeline[min(i, len(plan.timeline) - 1)][0])
    return i


def _make_thumbs(src: GifData, key_color: Sequence[int] | None):
    """Vignettes uint8 (<= THUMB_SIDE px) de toutes les images, fond uni passé au noir si clé ; + alphas booléens."""
    w, h = src.frames[0].size
    f = max(1, math.ceil(max(w, h) / THUMB_SIDE))
    thumbs = []
    for fr in src.frames:
        t = fr.reduce(f) if f > 1 else fr
        if key_color is not None:
            t = _key_background(t, key_color)
        thumbs.append(np.asarray(t, dtype=np.uint8))
    alph = None
    if src.alphas is not None:
        alph = [np.asarray(a.reduce(f) if f > 1 else a) > 0 for a in src.alphas]
    return thumbs, alph, f


def _content_map(thumbs: list, alph: list | None):
    """Union du contenu sur TOUTES les images (vignettes) + carte d'énergie lumineuse. Un seul recadrage en découle."""
    th, tw = thumbs[0].shape[:2]
    union = np.zeros((th, tw), dtype=bool)
    energy = np.zeros((th, tw), dtype=np.float32)
    for i, a8 in enumerate(thumbs):
        arr = a8.astype(np.float32)
        m = arr.max(axis=2) > CONTENT_LEVEL
        if alph is not None:
            m |= alph[i]
        luma = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]) / 255.0
        union |= m
        energy += np.where(m, np.maximum(luma, 0.15), 0.0)
    return union, energy


def _drop_isolated(mask: np.ndarray) -> np.ndarray:
    """Retire les pixels ISOLÉS (aucun des 8 voisins allumé) : poussière / bruit de tramage."""
    p = np.pad(mask, 1)
    h, w = mask.shape
    nb = np.zeros(mask.shape, dtype=np.uint8)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1:
                continue
            nb += p[dy:dy + h, dx:dx + w]
    return mask & (nb >= 1)


def _bbox_from_union(union: np.ndarray):
    """bbox (x0, y0, x1, y1) du contenu, sans les pixels ISOLÉS (poussière/bruit de tramage : aucun des 8 voisins
    allumé) — un bord fin mais connecté est conservé. None si vide."""
    union = _drop_isolated(union)
    rows = np.flatnonzero(union.any(axis=1))
    cols = np.flatnonzero(union.any(axis=0))
    if rows.size == 0 or cols.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def _ema(a: np.ndarray, alpha: float) -> np.ndarray:
    out = np.empty_like(a, dtype=np.float64)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = out[i - 1] + alpha * (a[i] - out[i - 1])
    return out


def _fill_nan(a: np.ndarray, default: float) -> np.ndarray:
    a = a.astype(np.float64).copy()
    if np.isnan(a).all():
        a[:] = default
        return a
    last = np.nan
    for i in range(len(a)):                       # report avant
        if np.isnan(a[i]):
            a[i] = last
        else:
            last = a[i]
    nxt = np.nan
    for i in range(len(a) - 1, -1, -1):           # report arrière (début de séquence)
        if np.isnan(a[i]):
            a[i] = nxt
        else:
            nxt = a[i]
    return a


def _axis_bounds(c0: float, clen: float, wlen: float, flen: float) -> tuple[float, float]:
    """Positions min/max du bord de la fenêtre sur un axe : dans la zone de contenu si elle est plus grande que la
    fenêtre, sinon fenêtre centrée sur le contenu ; toujours dans l'image."""
    if wlen >= clen:
        m = min(max(c0 + clen / 2 - wlen / 2, 0), flen - wlen)
        return m, m
    return max(0.0, c0), min(flen - wlen, c0 + clen - wlen)


def _plan_follow(thumbs: list, alph: list | None, f: int, frame_size: tuple, content: tuple, dark_bg: bool,
                 force: bool = False):
    """Cadrage intelligent : suit le sujet principal avec une fenêtre 4:1 de taille ENTIÈRE (128·d × 32·d) -> chaque LED
    = un bloc d×d de pixels source (pixel-perfect), déplacée par pas de d pixels. Sujet : contenu allumé sur fond noir,
    sinon mouvement (écart à la médiane temporelle du plan). Trajectoire lissée avant+arrière (aucun retard), zone
    morte (pas de frétillement), remise à zéro aux coupures de plan. Zoom d = plus petit entier gardant >= 88 % du
    sujet dans la fenêtre. Retourne (fenêtres, diagnostic) ou None (suivi inutile/impossible -> recadrage fixe)."""
    n = len(thumbs)
    fw, fh = frame_size
    cx0, cy0, cw, ch = content
    th, tw = thumbs[0].shape[:2]
    luma = [(0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]).astype(np.float32) for a in thumbs]

    cuts = [0] + [i for i in range(1, n) if float(np.abs(luma[i] - luma[i - 1]).mean()) / 255.0 > CUT_DIFF]
    segs = list(zip(cuts, cuts[1:] + [n]))

    masks: list = [None] * n
    for s_, e_ in segs:
        seg = luma[s_:e_]
        med = np.median(np.stack(seg), axis=0) if (not dark_bg and len(seg) >= 5) else None
        for k in range(s_, e_):
            if dark_bg:
                m = thumbs[k].max(axis=2) > CONTENT_LEVEL
                if alph is not None:
                    m = m | alph[k]
            elif med is not None:
                m = np.abs(luma[k] - med) > MOTION_THR
            else:                                           # plan trop court pour une médiane : écart à l'image voisine
                ref = luma[k - 1] if k > s_ else luma[min(k + 1, e_ - 1)]
                m = np.abs(luma[k] - ref) > MOTION_THR
            masks[k] = _drop_isolated(m)

    min_pix = max(4, int(MIN_SUBJECT_FRAC * th * tw))
    boxes: list = []
    for m in masks:
        ys, xs = np.nonzero(m)
        if xs.size < min_pix:
            boxes.append(None)
            continue
        xl, xh = np.percentile(xs, [2, 98])
        yl, yh = np.percentile(ys, [2, 98])
        boxes.append(((xl + xh + 1) / 2 * f, (yl + yh + 1) / 2 * f, (xh - xl + 1) * f, (yh - yl + 1) * f))
    valid = [b for b in boxes if b]
    if len(valid) < max(3, n // 2):
        return None

    wc = float(np.percentile([b[2] for b in valid], 95))
    hc = float(np.percentile([b[3] for b in valid], 95))
    d_min = max(1, math.ceil(max(FOLLOW_MARGIN * wc, 4 * 0.8 * hc) / TARGET_W - 1e-6))
    d_max = min(fw // TARGET_W, fh // TARGET_H)
    if d_max < 1:
        return None

    cxr = np.array([b[0] if b else np.nan for b in boxes])
    cyr = np.array([b[1] if b else np.nan for b in boxes])
    sx = np.empty(n)
    sy = np.empty(n)
    for s_, e_ in segs:
        for raw, out, dflt in ((cxr, sx, cx0 + cw / 2), (cyr, sy, cy0 + ch / 2)):
            seg = _fill_nan(raw[s_:e_], dflt)
            out[s_:e_] = (_ema(seg, FOLLOW_ALPHA) + _ema(seg[::-1], FOLLOW_ALPHA)[::-1]) / 2.0

    best = None
    for d in range(min(d_min, d_max), d_max + 1):
        w, h = TARGET_W * d, TARGET_H * d
        if not force and w * h > FOLLOW_MAX_AREA * cw * ch:
            break                                           # fenêtre >= zone de contenu : aucun gain, et d ne fait que croître
        xlo, xhi = _axis_bounds(cx0, cw, w, fw)
        ylo, yhi = _axis_bounds(cy0, ch, h, fh)
        windows, cams = [], []
        for s_, e_ in segs:                                 # zone morte (hystérésis), remise à zéro à chaque coupure
            camx, camy = sx[s_], sy[s_]
            for i in range(s_, e_):
                dzx, dzy = FOLLOW_DEADZONE * w, FOLLOW_DEADZONE * h
                if abs(sx[i] - camx) > dzx:
                    camx = sx[i] - math.copysign(dzx, sx[i] - camx)
                if abs(sy[i] - camy) > dzy:
                    camy = sy[i] - math.copysign(dzy, sy[i] - camy)
                x = int(round((camx - w / 2) / d)) * d      # pas de d pixels source = 1 LED
                y = int(round((camy - h / 2) / d)) * d
                x = int(min(max(x, xlo), xhi))
                y = int(min(max(y, ylo), yhi))
                windows.append((x, y, w, h))
        cov = []
        for i, m in enumerate(masks):
            tot = int(m.sum())
            if tot < min_pix:
                continue
            x, y, w_, h_ = windows[i]
            tx0, ty0 = x // f, y // f
            tx1, ty1 = math.ceil((x + w_) / f), math.ceil((y + h_) / f)
            cov.append(float(m[ty0:ty1, tx0:tx1].sum()) / tot)
        if not cov:
            return None
        mean_c, p10 = float(np.mean(cov)), float(np.percentile(cov, 10))
        best = (windows, d, mean_c, p10)
        if (mean_c >= FOLLOW_MIN_COVERAGE and p10 >= FOLLOW_MIN_COVERAGE_P10) or (force and mean_c >= 0.6):
            travel = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(windows[1:], windows[:-1]))
            return windows, {"d": d, "window": [w, h], "coverage": round(mean_c, 3), "coverage_p10": round(p10, 3),
                             "cuts": len(cuts) - 1, "travel_px": int(travel),
                             "subject_px": [int(round(wc)), int(round(hc))]}
    return None


def _auto_settings(samples: Sequence[Image.Image]) -> dict:
    """auto_quality_settings (VIDEO) pour couleurs / contraste / seuil de noir ; luminosité et saturation sont
    recalculées sur les seuls pixels ALLUMÉS : le fond noir tirait la luminosité moyenne vers le bas et poussait
    toujours +30 % sur un logo sur fond noir."""
    base = VideoEngine.auto_quality_settings(list(samples))
    lum, sat = [], []
    for fr in samples:
        rgb = np.asarray(fr.convert("RGB"), dtype=np.float32)
        lit = rgb.max(axis=2) > CONTENT_LEVEL
        if float(lit.mean()) < 0.005:
            continue
        luma = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])[lit]
        hsv_s = np.asarray(fr.convert("HSV"), dtype=np.float32)[..., 1][lit]
        lum.append(float(luma.mean()))
        sat.append(float(hsv_s.mean()))
    if lum:
        clamp = lambda v, lo, hi: max(lo, min(hi, v))  # noqa: E731 -- mêmes formules/bornes que auto_quality_settings
        base["brightness"] = clamp(1.0 + (128.0 - float(np.mean(lum))) / 256.0, 0.92, 1.3)  # on n'assombrit presque pas
        base["saturation"] = clamp(1.0 + (110.0 - float(np.mean(sat))) / 220.0, 1.0, 1.4)
    return base


def _manual_box(win: Sequence[float], w: int, h: int, size_from: tuple | None = None) -> tuple:
    """Fenêtre 4:1 posée à la main -> (x, y, largeur, hauteur) en pixels, ramenée DANS l'image.
    win = (x, y, largeur) normalisés par la largeur/hauteur de l'image ; size_from = reprend la taille d'une autre fenêtre."""
    target = TARGET_W / TARGET_H
    if size_from is not None:
        bw, bh = size_from[2], size_from[3]
    else:
        bw = int(round(max(8.0, min(1.0, float(win[2]))) * w))
        bh = int(round(bw / target))
        if bh > h:                                   # trop haute pour l'image : on réduit en gardant le 4:1
            bh = h
            bw = int(round(h * target))
    bw = min(bw, w)
    bx = int(round(float(win[0]) * w))
    by = int(round(float(win[1]) * h))
    return (max(0, min(w - bw, bx)), max(0, min(h - bh, by)), bw, bh)


def _plan_scroll(src_durations: Sequence[int], energy: np.ndarray, f: int, content: tuple, back: bool = False,
                 path: tuple | None = None):
    """Scroll intelligent : l'image remplit l'afficheur sur un axe (largeur si le contenu est plus haut que 4:1,
    hauteur s'il est plus large) et la fenêtre 128×32 PARCOURT l'autre axe, par pas d'1 px DMD entier.
    Intelligence : axe choisi d'après le ratio ; on démarre par l'extrémité la plus chargée (titre, logo) ; la
    vitesse ralentit sur les zones denses et accélère sur les zones vides ; pauses au début et à la fin ;
    l'animation d'origine continue de tourner pendant le défilement (durée arrondie à un nombre entier de tours).
    Retourne (fenêtres par image de sortie, chronologie [(index source, ms)], diagnostic) ou None."""
    x0, y0, cw, ch = content
    target = TARGET_W / TARGET_H
    if path is not None:             # trajet posé à la main : fenêtre de départ -> fenêtre d'arrivée (même taille)
        (sx, sy, ww, wh), (ex, ey, _w2, _h2) = path
        axis, scale, base, span = "path", TARGET_W / ww, 0, 0
        travel = int(round(math.hypot(ex - sx, ey - sy) * scale))
        if travel < 1:
            return None
        en = np.full(travel + 1, 0.5)
        reverse = False
    else:
        ratio = cw / ch if ch else target
        if abs(ratio - target) / target < SCROLL_MIN_DIFF:
            return None
        if ratio < target:
            axis, ww, wh = "y", cw, max(1, int(round(cw / target)))
            scale, span, base, wlen = TARGET_W / ww, ch - wh, y0, wh
        else:
            axis, wh, ww = "x", ch, max(1, int(round(ch * target)))
            scale, span, base, wlen = TARGET_H / wh, cw - ww, x0, ww
        travel = int(round(span * scale))
        if travel < SCROLL_MIN_TRAVEL:
            return None
        prof = energy.sum(axis=1 if axis == "y" else 0)
        cum = np.concatenate([[0.0], np.cumsum(prof)])
        grid = np.arange(len(cum), dtype=np.float64)
        o = np.arange(travel + 1, dtype=np.float64)
        s0 = (base + o / scale) / f
        en = np.interp(s0 + wlen / f, grid, cum) - np.interp(s0, grid, cum)
        en = en / en.max() if en.max() > 0 else np.ones_like(en)
        reverse = bool(en[-1] > en[0] * SCROLL_REVERSE_GAIN)
        if reverse:
            en = en[::-1]

    sz = 2 if travel > 160 else 1                    # longue course : pas de 2 px (moitié moins d'images, même vitesse)

    def step_ms(j: int, factor: float = 1.0) -> int:
        v = SCROLL_BASE_MS * (0.7 + 0.8 * float(en[j])) * factor * sz
        return int(min(SCROLL_STEP_MAX * sz, max(SCROLL_STEP_MIN * sz, round(v / 10.0) * 10)))

    js = list(range(sz, travel, sz)) + [travel]
    segs: list[tuple[int, int]] = [(SCROLL_HOLD_MS, 0)]                       # (durée, pas parcourus depuis le départ)
    segs += [(step_ms(j), j) for j in js]
    segs.append((SCROLL_HOLD_MS, travel))
    if back:
        segs += [(step_ms(j, SCROLL_BACK_FACTOR), j) for j in reversed([0] + js[:-1])]
    t_src = max(1, int(sum(src_durations)))
    total = sum(d for d, _ in segs)
    med = sorted(src_durations)[len(src_durations) // 2] if src_durations else 100
    animated = len(src_durations) > 1 and t_src >= 2 * med
    if animated:                                    # nombre entier de tours de la source (bouclage propre), si raisonnable
        loops = math.ceil(total / t_src)
        if loops * t_src <= total * 1.5:
            segs[-1] = (segs[-1][0] + loops * t_src - total, segs[-1][1])
            total = loops * t_src
    dt = 40 if med < 50 else 50
    seg_end = np.cumsum([d for d, _ in segs])
    src_end = np.cumsum([max(1, int(d)) for d in src_durations]) if src_durations else np.array([1])
    while True:
        out: list[list[int]] = []
        t = 0
        while t < total:
            step = min(dt, total - t)
            k = int(np.searchsorted(seg_end, t, side="right"))
            k = min(k, len(segs) - 1)
            si = int(np.searchsorted(src_end, t % t_src, side="right")) if animated else 0
            si = min(si, len(src_durations) - 1) if src_durations else 0
            pos = segs[k][1]
            if out and out[-1][0] == si and out[-1][1] == pos:
                out[-1][2] += step
            else:
                out.append([si, pos, step])
            t += step
        if len(out) <= SCROLL_MAX_FRAMES:
            break
        dt = int(dt * 1.5 / 10) * 10 + 10
    windows, timeline = [], []
    for si, pos, d in out:
        if axis == "path":
            tt = pos / travel
            windows.append((int(round(sx + (ex - sx) * tt)), int(round(sy + (ey - sy) * tt)), ww, wh))
            timeline.append((si, int(d)))
            continue
        ro = (travel - pos) if reverse else pos
        off = base + int(round(ro / scale))
        off = max(base, min(base + span, off))
        windows.append((x0, off, ww, wh) if axis == "y" else (off, y0, ww, wh))
        timeline.append((si, int(d)))
    info = {"axis": axis, "travel_px": travel, "reversed": reverse, "back": bool(back), "frames": len(out),
            "duration_ms": int(total), "scale": round(float(scale), 3)}
    return windows, timeline, info


def _settings_for(mode: str, options: dict | None, samples: Sequence[Image.Image]) -> dict:
    opts = dict(options or {})
    if mode == "auto":
        s = dict(DEFAULT_SETTINGS)
        s.update(_auto_settings(samples))
        # le réglage manuel d'un seul paramètre reste possible depuis l'onglet : options écrasent l'auto
        for k in DEFAULT_SETTINGS:
            if k in opts and opts[k] is not None:
                s[k] = opts[k]
        return s
    s = dict(DEFAULT_SETTINGS)
    for k in DEFAULT_SETTINGS:
        if k in opts and opts[k] is not None:
            s[k] = opts[k]
    return s


def plan_conversion(src: GifData, mode: str = "auto", options: dict | None = None,
                    letterbox: bool | None = None) -> Plan:
    """Décide UNE FOIS, pour tout le GIF : fond, recadrage/bandes noires, réglages.
    letterbox : None = automatique ; True = bandes noires (contenu entier) ; False = « remplir » forcé."""
    opts = dict(options or {})
    mode = "manual" if mode == "manual" else "auto"
    idx = _sample_indices(len(src.frames))
    warnings: list[str] = []
    if src.work_scale > 1:
        warnings.append("reduced_source")
    pixel_perfect = bool(opts["pixel_perfect"]) if opts.get("pixel_perfect") is not None else DEFAULT_SETTINGS["pixel_perfect"]

    bg_kind, bg_color = detect_background(src, idx)
    invert = opts.get("invert")
    if src.alphas is not None:
        invert = False                       # transparence : le fond « noir » est déjà le bon
    elif invert is None:
        invert = bool(bg_kind == "uniform" and not _keying_ok(src, idx, bg_color) and _invert_ok(src, idx, bg_color))
        if invert:
            warnings.append("inverted")
    if invert:
        src = dataclasses.replace(src, frames=[ImageOps.invert(f) for f in src.frames])
        bg_kind, bg_color = detect_background(src, idx)    # après inversion : le fond est (presque) noir
    key = opts.get("key_background")
    if key is None:
        key = False
        if bg_kind == "uniform":
            key = _keying_ok(src, idx, bg_color)
            if not key:
                warnings.append("dark_on_light")
        elif bg_kind == "complex":
            warnings.append("lit_background")
    elif key and bg_color is None:
        key = False
    key_color = bg_color if key else None

    w, h = src.frames[0].size
    native = (src.width, src.height) == (TARGET_W, TARGET_H)
    crop = None
    follow_windows = None
    follow_info = None
    scroll_windows = scroll_timeline = scroll_info = None
    auto_scroll = None
    layout = "native" if native and letterbox is None and opts.get("crop_mode") in (None, "auto", "native") else "fit"
    lost_pct = 0.0
    if native and layout == "native":
        pass
    else:
        thumbs, alph, f = _make_thumbs(src, key_color)
        union, energy = _content_map(thumbs, alph)
        bb = _bbox_from_union(union)
        if bb is None:
            warnings.append("empty_content")
        else:
            pad = CROP_PAD + (f - 1)
            x0, y0 = max(0, bb[0] * f - pad), max(0, bb[1] * f - pad)
            x1, y1 = min(w, bb[2] * f + pad), min(h, bb[3] * f + pad)
            cw, ch = x1 - x0, y1 - y0
            if cw >= FULL_FRAME_RATIO * w and ch >= FULL_FRAME_RATIO * h:
                x0, y0, cw, ch = 0, 0, w, h          # pas de marge à retirer
            crop = (x0, y0, cw, ch)

            crop_mode = opts.get("crop_mode")
            want_fill = None  # None = auto
            if letterbox is True or crop_mode == "letterbox":
                want_fill = False
            elif letterbox is False or crop_mode == "fill":
                want_fill = True
            ratio = cw / ch if ch else 4.0
            target = TARGET_W / TARGET_H
            # Cadre 128×32 posé à la main (onglet GIF, mode manuel + « remplir ») : coordonnées normalisées
            # (x, y, largeur) de la fenêtre de départ ; « window_end » = fenêtre d'arrivée (scroll de l'une à l'autre).
            manual_placed = False
            if want_fill is True and opts.get("window"):
                b0 = _manual_box(opts["window"], w, h)
                if opts.get("scroll") and opts.get("window_end"):
                    b1 = _manual_box(opts["window_end"], w, h, size_from=b0)
                    res_sc = _plan_scroll(src.durations, energy, f, (x0, y0, cw, ch), bool(opts.get("scroll_back")),
                                          path=(b0, b1))
                    if res_sc is not None:
                        scroll_windows, scroll_timeline, scroll_info = res_sc
                        layout, crop, lost_pct, manual_placed = "scroll", None, 0.0, True
                if not manual_placed:
                    layout, crop, lost_pct, manual_placed = "fill", b0, 0.0, True
            # Scroll intelligent : seulement avec « remplir » (forcé) et si l'option est demandée
            if not manual_placed and opts.get("scroll") and want_fill is True:
                res_sc = _plan_scroll(src.durations, energy, f, (x0, y0, cw, ch), bool(opts.get("scroll_back")))
                if res_sc is not None:
                    scroll_windows, scroll_timeline, scroll_info = res_sc
                    layout, crop, lost_pct = "scroll", None, 0.0
                else:
                    warnings.append("scroll_unavailable")
            if not manual_placed and layout != "scroll" and abs(ratio - target) / target >= 0.03 and want_fill is not False:
                # fenêtre 4:1 dans la zone de contenu, centrée sur le barycentre de la lumière
                if ratio > target:
                    ww, wh = int(round(ch * target)), ch
                else:
                    ww, wh = cw, int(round(cw / target))
                ys, xs = np.nonzero(energy)
                wgt = energy[ys, xs]
                cxm = float((xs * wgt).sum() / wgt.sum()) * f + f / 2 if wgt.size else x0 + cw / 2
                cym = float((ys * wgt).sum() / wgt.sum()) * f + f / 2 if wgt.size else y0 + ch / 2
                wx = int(round(min(max(cxm - ww / 2, x0), x0 + cw - ww)))
                wy = int(round(min(max(cym - wh / 2, y0), y0 + ch - wh)))
                lost_area = 1.0 - (ww * wh) / float(cw * ch)
                tx0, ty0 = wx // f, wy // f
                tx1, ty1 = math.ceil((wx + ww) / f), math.ceil((wy + wh) / f)
                total = float(energy.sum())
                lost_energy = 1.0 - float(energy[ty0:ty1, tx0:tx1].sum()) / total if total > 0 else 0.0
                if want_fill is True or (lost_area <= FILL_LOSS_TINY and lost_energy <= FILL_ENERGY_TINY) or (
                        lost_area <= FILL_LOSS_MAX and lost_energy <= FILL_ENERGY_MAX):
                    layout = "fill"
                    crop = (wx, wy, ww, wh)
                    lost_pct = lost_area * 100.0
            # Cadrage intelligent : seulement si ni « remplir » ni bandes noires forcés, et si l'image « entière » ne
            # convient pas (layout encore "fit") -- ou si le suivi est demandé explicitement (options["follow"]=True).
            follow_opt = opts.get("follow")
            if (not manual_placed and layout != "scroll" and letterbox is None and crop_mode not in ("letterbox", "fill") and follow_opt is not False
                    and len(src.frames) >= FOLLOW_MIN_FRAMES
                    and (layout in ("fit", "fill") or follow_opt is True or crop_mode == "follow")):
                res = _plan_follow(thumbs, alph, f, (w, h), (x0, y0, cw, ch), bg_kind in ("black", "transparent") or bool(key),
                                   force=bool(follow_opt is True or crop_mode == "follow"))
                if res is not None:
                    follow_windows, follow_info = res
                    layout = "follow"
                    crop = None
                    lost_pct = 100.0 * (1.0 - follow_info["coverage"])
            # Auto : si l'image « entière » laisse des bandes noires (layout encore "fit"), un scroll plein écran est
            # candidat ; la décision se prend plus bas, au SCORE de rendu (comme l'onglet AUTO : resize vs fill).
            if (layout == "fit" and not manual_placed and letterbox is None and crop_mode in (None, "auto")
                    and opts.get("scroll") is not False and follow_windows is None):
                auto_scroll = _plan_scroll(src.durations, energy, f, (x0, y0, cw, ch), bool(opts.get("scroll_back")))
            # Pas de « calage » de la fenêtre (pp_snap_crop peut ROGNER du contenu en mode bandes noires) : le
            # pixel-perfect est assuré par adaptive_resize (diviseur entier, ou échelle exacte si > 3 % de perte).
            if crop is not None and tuple(crop) == (0, 0, w, h):
                crop = None

    # Réglages : choisis UNE fois, sur les images échantillon recadrées (et sans fond uni si clé)
    samples = []
    for i in idx:
        fr = src.frames[i]
        if key_color is not None:
            fr = _key_background(fr, key_color)
        if follow_windows is not None:
            x, y, cw_, ch_ = follow_windows[i]
            fr = fr.crop((x, y, x + cw_, y + ch_))
        elif scroll_windows is not None:
            x, y, cw_, ch_ = scroll_windows[len(scroll_windows) // 2]
            fr = fr.crop((x, y, x + cw_, y + ch_))
        elif crop is not None:
            x, y, cw_, ch_ = crop
            fr = fr.crop((x, y, x + cw_, y + ch_))
        samples.append(fr)
    settings = _settings_for(mode, opts, samples)
    settings["pixel_perfect"] = pixel_perfect
    settings["invert"] = bool(invert)
    plan = Plan(layout, tuple(int(v) for v in crop) if crop else None, bg_kind, bg_color, bool(key), settings,
                lost_pct, mode, warnings, scroll_windows if scroll_windows is not None else follow_windows, follow_info,
                scroll_timeline, scroll_info)
    if auto_scroll is not None:
        try:
            alt = _auto_scroll_plan(src, plan, auto_scroll, mode, opts, key_color)
        except Exception:  # noqa: BLE001 -- décision d'aide : en cas de souci on garde les bandes noires
            alt = None
        if alt is not None:
            return alt
    return plan


def _sample_positions(n: int, k: int = 8) -> list:
    return sorted({int(round(i * (n - 1) / max(1, k - 1))) for i in range(min(n, k))}) if n > 1 else [0]


def _auto_scroll_plan(src: GifData, fit_plan: Plan, cand: tuple, mode: str, opts: dict, key_color):
    """Compare (note de rendu dmd_quality, sur échantillon) « image entière + bandes noires » et « plein écran avec
    scroll » ; renvoie le plan scroll s'il gagne d'au moins AUTO_SCROLL_MARGIN points, sinon None."""
    windows, timeline, info = cand
    s_samples = []
    for k in _sample_positions(len(timeline), 5):
        fr = src.frames[timeline[k][0]]
        if key_color is not None:
            fr = _key_background(fr, key_color)
        x, y, cw_, ch_ = windows[k]
        s_samples.append(fr.crop((x, y, x + cw_, y + ch_)))
    settings = _settings_for(mode, opts, s_samples)
    settings["pixel_perfect"] = fit_plan.settings.get("pixel_perfect", True)
    settings["invert"] = fit_plan.settings.get("invert", False)
    scroll_plan = dataclasses.replace(fit_plan, layout="scroll", crop=None, settings=settings, lost_pct=0.0,
                                      windows=windows, timeline=timeline, scroll=info)
    fit_idx = _sample_positions(len(src.frames), 8)
    fit_frames = [render_frame(src.frames[i], fit_plan, i) for i in fit_idx]
    sc_idx = _sample_positions(len(timeline), 8)
    sc_frames = [render_frame(src.frames[timeline[k][0]], scroll_plan, k) for k in sc_idx]
    s_fit = dq.evaluate_frames(fit_frames, [max(1, src.total_ms // len(fit_frames))] * len(fit_frames)).score
    s_sc = dq.evaluate_frames(sc_frames, [max(1, info["duration_ms"] // len(sc_frames))] * len(sc_frames)).score
    if s_sc < s_fit + AUTO_SCROLL_MARGIN:
        return None
    scroll_plan.scroll = dict(info, auto=True, score_fit=int(s_fit), score_scroll=int(s_sc))
    return scroll_plan


def _optimize_light(img: Image.Image, s: dict) -> Image.Image:
    """Retouche tonale SANS flou : luminosité, contraste, saturation, seuil de noir. Pour une source déjà petite
    (<= 128×32 : GIF déjà au bon format, pixel art) : optimize_for_dmd applique en plus un filtre médian 3×3 et
    une netteté, qui effacent les traits d'1 pixel (texte, sprites)."""
    img = DMDEngine.ensure_rgb_on_black(img)
    b = float(s.get("brightness", 1.0))
    if b != 1.0:
        img = ImageEnhance.Brightness(img).enhance(b)
    img = ImageEnhance.Contrast(img).enhance(float(s.get("contrast", 1.0)))
    img = ImageEnhance.Color(img).enhance(float(s.get("saturation", 1.0)))
    arr = np.array(img)
    arr[np.all(arr < int(s.get("black_threshold", 30)), axis=2)] = 0
    return Image.fromarray(arr)


# --- Rendu ------------------------------------------------------------------------------------------------
def render_frame(frame: Image.Image, plan: Plan, index: int = 0) -> Image.Image:
    """Une image source -> une image DMD 128×32 (même chaîne que _video_render_frame, VIDEO)."""
    s = plan.settings
    img = ImageOps.invert(frame) if s.get("invert") else frame
    if plan.key_background and plan.bg_color is not None:
        img = _key_background(img, plan.bg_color)
    if plan.layout in ("follow", "scroll") and plan.windows:
        x, y, cw, ch = plan.windows[min(index, len(plan.windows) - 1)]
        img = img.crop((x, y, x + cw, y + ch))
    elif plan.layout != "native" and plan.crop is not None:
        x, y, cw, ch = plan.crop
        img = img.crop((x, y, x + cw, y + ch))
    small = img.width <= TARGET_W and img.height <= TARGET_H     # pas de réduction : on ne floute pas
    img = _optimize_light(img, s) if small else DMDEngine.optimize_for_dmd(img, s)
    if plan.layout == "native":
        canvas = img if img.size == (TARGET_W, TARGET_H) else img.resize((TARGET_W, TARGET_H), Image.Resampling.NEAREST)
    elif (plan.layout in ("scroll", "follow", "fill") and img.width > TARGET_W
          and abs(img.width / img.height - TARGET_W / TARGET_H) < 0.1):
        # Fenêtre déjà au ratio 4:1 (plein écran voulu) : échelle EXACTE vers 128×32. adaptive_resize en pixel-perfect
        # prendrait un diviseur entier (ex. 498/4 = 124 px) et laisserait 2 colonnes noires de chaque côté.
        canvas = img.resize((TARGET_W, TARGET_H), Image.Resampling.BOX)
    else:
        resized, rw, rh = DMDEngine.adaptive_resize(img, TARGET_W, TARGET_H, mode="fit",
                                                    pixel_perfect=bool(s.get("pixel_perfect", True)))
        canvas = Image.new("RGB", (TARGET_W, TARGET_H), (0, 0, 0))
        canvas.paste(resized, ((TARGET_W - rw) // 2, (TARGET_H - rh) // 2))
    return DMDEngine.cleanup_dmd_frame(canvas, power=float(s.get("cleanup_power", 0.5)))


def render_frames(src: GifData, plan: Plan, progress: Callable[[int, str], None] | None = None) -> list:
    out = []
    if plan.layout == "scroll" and plan.timeline:        # une image de sortie par entrée de la chronologie
        n = len(plan.timeline)
        for i, (si, _d) in enumerate(plan.timeline):
            out.append(render_frame(src.frames[si], plan, i))
            if progress and (i % 8 == 0 or i == n - 1):
                progress(int(100 * (i + 1) / n), "render")
        return out
    n = len(src.frames)
    for i, fr in enumerate(src.frames):
        out.append(render_frame(fr, plan, i))
        if progress and (i % 8 == 0 or i == n - 1):
            progress(int(100 * (i + 1) / n), "render")
    return out


def encode_frames(frames: Sequence[Image.Image], durations: Sequence[int], settings: dict,
                  shared_palette: bool | None = None) -> bytes:
    """Encode avec les durées d'origine (filigrane DGC inclus). Palette par image jusqu'à 120 images (scènes
    variées, comme VIDEO), partagée au-delà (beaucoup plus rapide)."""
    n = len(frames)
    mean = sum(durations) / max(1, n)
    fps = max(1, int(round(1000.0 / mean)))
    shared = (n > 120) if shared_palette is None else bool(shared_palette)
    return _encode_gif_bytes(list(frames), fps=fps, color_count=int(settings.get("color_count", 64)),
                             loop_mode="infini", loop_count=0, disposal=2, optimize=False,
                             shared_palette=shared, durations_ms=list(durations))


def _naive_score(src: GifData) -> int | None:
    """Note d'un redimensionnement « bête » (ajusté sur fond noir, sans retouche) : base de comparaison."""
    try:
        frames = []
        n = len(src.frames)
        picks = sorted({int(k * (n - 1) / max(1, min(n, 10) - 1)) for k in range(min(n, 10))}) if n > 1 else [0]
        for i in picks:
            fr = src.frames[i]
            s = min(TARGET_W / fr.width, TARGET_H / fr.height)
            nw, nh = max(1, int(round(fr.width * s))), max(1, int(round(fr.height * s)))
            canvas = Image.new("RGB", (TARGET_W, TARGET_H), (0, 0, 0))
            canvas.paste(fr.resize((nw, nh), Image.Resampling.LANCZOS), ((TARGET_W - nw) // 2, (TARGET_H - nh) // 2))
            frames.append(canvas)
        per = max(1, src.total_ms // len(frames))      # durée TOTALE réelle (pénalité « trop court » équitable)
        return dq.evaluate_frames(frames, [per] * len(frames)).score
    except Exception:  # noqa: BLE001 -- aide seulement
        return None


# --- API principale -------------------------------------------------------------------------------------
@dataclass
class ConvertResult:
    converted: bool
    gif_bytes: bytes
    frames: list | None
    durations: list | None
    report: dict
    plan: Plan | None = None


def convert_gif_to_dmd(data: bytes, mode: str = "auto", options: dict | None = None, letterbox: bool | None = None,
                       force: bool = False, limits: GifLimits | None = None,
                       progress: Callable[[int, str], None] | None = None) -> ConvertResult:
    """GIF (octets) -> GIF DMD 128×32. force=False : un GIF déjà au bon format est rendu tel quel (converted=False).
    Lève GifError pour un GIF refusé/illisible."""
    t0 = time.perf_counter()
    src = load_gif(data, limits)
    verdict = analyze_gif(src)
    report: dict[str, Any] = {"version": REPORT_VERSION, "ok": True, "input": verdict.metrics,
                              "verdict": verdict.to_dict()}
    if not force and not verdict.needs_conversion:
        report.update({"converted": False, "elapsed_ms": int((time.perf_counter() - t0) * 1000)})
        return ConvertResult(False, data, None, None, report)

    plan = plan_conversion(src, mode, options, letterbox)
    frames = render_frames(src, plan, progress)
    durs = plan_durations(src, plan)
    gif = encode_frames(frames, durs, plan.settings)
    q = dq.evaluate_frames(frames, durs)
    report.update({
        "converted": True,
        "variant": "letterbox" if letterbox is True else "auto",
        "plan": plan.to_dict(),
        "output": {"width": TARGET_W, "height": TARGET_H, "frames": len(frames), "bytes": len(gif),
                   "colors": int(plan.settings["color_count"]), "score": q.score, "rating": q.rating,
                   "reasons": list(q.reasons)},
        "score_before": _naive_score(src),
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
    })
    return ConvertResult(True, gif, frames, durs, report, plan)


# --- Ligne de commande --------------------------------------------------------------------------------
def _error_json(code: str, message: str) -> dict:
    return {"version": REPORT_VERSION, "ok": False, "error": {"code": code, "message": message}}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convertit un GIF animé au format DMD 128×32 (DMD GIF Creator).")
    ap.add_argument("input", help="GIF à traiter ('-' = entrée standard)")
    ap.add_argument("-o", "--output", help="GIF de sortie (défaut : <entrée>_dmd.gif)")
    ap.add_argument("--check", action="store_true", help="verdict seul (rien n'est écrit)")
    ap.add_argument("--force", action="store_true", help="convertit même si le GIF est déjà au bon format")
    ap.add_argument("--letterbox", action="store_true", help="force les bandes noires (contenu entier)")
    ap.add_argument("--follow", action="store_true", help="force le cadrage intelligent (suivi du sujet)")
    ap.add_argument("--no-follow", action="store_true", help="désactive le cadrage intelligent")
    ap.add_argument("--scroll", action="store_true",
                    help="« remplir » avec scroll intelligent (la fenêtre 128×32 parcourt le contenu)")
    ap.add_argument("--scroll-back", action="store_true", help="avec --scroll : aller-retour (sans saut à la boucle)")
    ap.add_argument("--no-scroll", action="store_true",
                    help="auto : interdit le scroll plein écran (garde l'image entière + bandes noires)")
    ap.add_argument("--also-letterbox", metavar="PATH",
                    help="si le cadrage auto recadre (remplir / suivi), écrit aussi la variante bandes noires ici")
    ap.add_argument("--json", action="store_true", help="rapport JSON sur la sortie standard")
    ap.add_argument("--max-bytes", type=int, default=GifLimits.max_bytes)
    ap.add_argument("--max-frames", type=int, default=GifLimits.max_frames)
    ap.add_argument("--max-total-mpx", type=float, default=GifLimits.max_total_pixels / 1e6,
                    help="budget images×pixels de travail, en millions")
    a = ap.parse_args(argv)

    limits = GifLimits(max_bytes=a.max_bytes, max_frames=a.max_frames, max_total_pixels=int(a.max_total_mpx * 1e6))

    def emit(obj: dict, human: str) -> None:
        print(json.dumps(obj, ensure_ascii=False) if a.json else human)

    try:
        data = sys.stdin.buffer.read() if a.input == "-" else Path(a.input).read_bytes()
    except OSError as e:
        emit(_error_json("unreadable", str(e)), f"Erreur : {e}")
        return 3
    try:
        if a.check:
            v = analyze_gif(load_gif(data, limits))
            emit({"version": REPORT_VERSION, "ok": True, "verdict": v.to_dict(), "input": v.metrics},
                 "À convertir : %s (%s)" % ("oui" if v.needs_conversion else "non", ", ".join(v.reasons) or "OK"))
            return 0
        opts = {"follow": True} if a.follow else ({"follow": False} if a.no_follow else None)
        if a.no_scroll:
            opts = dict(opts or {}, scroll=False)
        elif a.scroll and not a.letterbox:
            opts = dict(opts or {}, crop_mode="fill", scroll=True, scroll_back=bool(a.scroll_back))
        res = convert_gif_to_dmd(data, "auto", opts, True if a.letterbox else None, a.force, limits)
        rep = res.report
        if res.converted:
            out = Path(a.output) if a.output else (Path(a.input).with_name(Path(a.input).stem + "_dmd.gif")
                                                   if a.input != "-" else Path("out_dmd.gif"))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(res.gif_bytes)
            rep["output_path"] = str(out)
            if a.also_letterbox and not a.letterbox and res.plan and res.plan.layout in ("fill", "follow", "scroll"):
                alt = convert_gif_to_dmd(data, "auto", None, True, True, limits)
                alt_path = Path(a.also_letterbox)
                alt_path.parent.mkdir(parents=True, exist_ok=True)
                alt_path.write_bytes(alt.gif_bytes)
                rep["letterbox_variant"] = {"path": str(alt_path), "bytes": len(alt.gif_bytes),
                                            "score": alt.report["output"]["score"]}
        emit(rep, ("Converti -> %s (%d Ko, score %s)" % (rep.get("output_path"), rep["output"]["bytes"] // 1024,
                                                         rep["output"]["score"]))
             if res.converted else "Déjà au bon format : rien à faire")
        return 0
    except GifError as e:
        emit(_error_json(e.code, str(e)), f"Refusé ({e.code}) : {e}")
        return 3
    except Exception as e:  # noqa: BLE001
        emit(_error_json("internal", f"{type(e).__name__}: {e}"), f"Erreur interne : {e}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
