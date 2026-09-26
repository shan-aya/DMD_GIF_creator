# ============================================
# safe-modify — Historique des modifications
# ============================================
# Version actuelle : v2
#
# v2 — 2026-09-25 — safe-modify — Calibrage validé par l'utilisateur sur le
#      pack réel F:\systems_rawpack (54 765 GIF) : le taux de pixels allumés
#      est noté au maximum sur un PALIER (FILL_LOW..FILL_HIGH = 8-60 %) au lieu
#      d'un pic à IDEAL_FILL=0.4 -- l'ancien pic classait "Poor" (31-50) des
#      logos de taille normale (10-15 % d'écran : Monkey Island, Agent USA...).
#      Simulé sur le pack : 31-50 passe de 400 à 66 GIF, 353 bons logos
#      remontés > 50, AUCUN nouveau GIF <= 30 ; les 61 GIF non noirs restant
#      <= 30 vérifiés à l'oeil (tous ratés). Raison "too_cluttered" (code
#      inchangé) : libellé "Écran trop chargé" -> "Fond plein" (ce sont des
#      logos à fond plein, Pac-Man/Tetris, pas des ratés).
# v1 — 2026-09-25 — Version reçue (écrite hors session), ajoutée telle quelle.
# ============================================
"""
dmd_quality.py — Score de qualité 0-100 pour les GIF DMD 128x32.

Réimplémentation en Pillow + NumPy (sans OpenCV) de l'approche de
red77290/dmd_gif_converter (MIT), fichier src/engine/conversion/quality.py.
Formule, poids et seuils repris à l'identique ; adaptations :
  * pas de dépendance OpenCV (fonctionne dans AUTO sans opencv-contrib) ;
  * peut noter des frames en mémoire (avant/pendant l'export) ;
  * raisons sous forme de codes, traduites FR/EN/ES ;
  * un seul index JSON par dossier (pas un fichier .scores.json par GIF) ;
  * les GIF faibles sont DÉPLACÉS vers un dossier "à revoir", jamais supprimés ;
  * un GIF statique (1 image) n'est pas pénalisé par défaut.

Usage dans l'app :
    from dmd_quality import evaluate_frames, save_index, summarize
    res = evaluate_frames(frames, durations_ms=[50]*len(frames))
    rows[rel_path] = res.to_dict()          # dans la boucle du lot
    save_index(output_dir, rows)            # une fois le lot terminé

Usage en ligne de commande (noter un dossier de GIF existant) :
    python dmd_quality.py DOSSIER [--threshold 30] [--move] [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass, field
from typing import Iterable, Sequence, Union

import numpy as np
from PIL import Image

# --- Paramètres (valeurs de la référence) -----------------------------------
W_NON_BLACK = 0.3      # poids du taux de pixels allumés
W_CONTRAST = 0.5       # poids du contraste (gradient de Sobel moyen)
W_OCCUPATION = 0.2     # poids de l'occupation de l'écran
FILL_LOW = 0.08        # palier de remplissage noté au maximum (v2) :
FILL_HIGH = 0.60       #   de FILL_LOW à FILL_HIGH de pixels allumés
BLACK_THRESHOLD = 10   # niveau de gris sous lequel un pixel est "éteint"
GRADIENT_FULL = 80.0   # gradient moyen donnant le contraste maximal
MAX_SAMPLED_FRAMES = 10
MIN_DURATION_MS = 400

INDEX_NAME = "dmd_scores.json"
REVIEW_DIR = "_a_revoir"

# --- Raisons traduites -------------------------------------------------------
REASONS = {
    "empty_frame":        {"fr": "Image vide", "en": "Empty frame", "es": "Imagen vacía"},
    "mostly_empty":       {"fr": "Écran presque vide", "en": "Screen mostly empty", "es": "Pantalla casi vacía"},
    "too_cluttered":      {"fr": "Fond plein", "en": "Full background", "es": "Fondo lleno"},
    "excellent_occupancy": {"fr": "Excellente occupation", "en": "Excellent occupancy", "es": "Ocupación excelente"},
    "poor_occupancy":     {"fr": "Faible occupation du DMD", "en": "Poor DMD occupancy", "es": "Baja ocupación del DMD"},
    "strong_contrast":    {"fr": "Fort contraste", "en": "Strong contrast", "es": "Contraste fuerte"},
    "low_contrast":       {"fr": "Contraste faible", "en": "Low contrast", "es": "Contraste bajo"},
    "too_few_frames":     {"fr": "Pas assez d'images", "en": "Not enough frames", "es": "Pocas imágenes"},
    "too_fast":           {"fr": "Animation trop courte/rapide", "en": "Animation too short/fast", "es": "Animación demasiado corta/rápida"},
    "average":            {"fr": "Conversion moyenne", "en": "Average conversion", "es": "Conversión media"},
    "unreadable":         {"fr": "Fichier illisible", "en": "Unreadable file", "es": "Archivo ilegible"},
}


def reason_text(code: str, lang: str = "fr") -> str:
    return REASONS.get(code, {}).get(lang) or REASONS.get(code, {}).get("en") or code


def rating_for(score: int) -> tuple[str, str]:
    """(libellé, pastille) — mêmes seuils que la référence."""
    if score <= 30:
        return "Bad", "🔴"
    if score <= 50:
        return "Poor", "🟠"
    if score <= 70:
        return "Acceptable", "🟡"
    if score <= 85:
        return "Good", "🟢"
    return "Excellent", "🌟"


@dataclass
class QualityResult:
    score: int
    rating: str
    color: str
    reasons: list[str] = field(default_factory=list)   # codes, cf. REASONS

    def reasons_text(self, lang: str = "fr") -> list[str]:
        return [reason_text(c, lang) for c in self.reasons]

    def to_dict(self) -> dict:
        return {"score": self.score, "rating": self.rating,
                "color": self.color, "reasons": list(self.reasons)}


def _result(score: int, reasons: list[str]) -> QualityResult:
    score = max(0, min(100, int(score)))
    rating, color = rating_for(score)
    return QualityResult(score, rating, color, reasons or ["average"])


# --- Score d'une image -------------------------------------------------------
FrameLike = Union[Image.Image, np.ndarray]


def _to_gray(frame: FrameLike) -> np.ndarray:
    """Niveaux de gris float64 ; la transparence est composée sur du noir."""
    if isinstance(frame, np.ndarray):
        frame = Image.fromarray(frame.astype(np.uint8))
    rgba = frame.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
    bg.alpha_composite(rgba)
    return np.asarray(bg.convert("L"), dtype=np.float64)


def _mean_sobel(gray: np.ndarray) -> float:
    """Gradient de Sobel moyen (noyau 3x3 non normalisé, bords en miroir)."""
    if gray.shape[0] < 2 or gray.shape[1] < 2:
        return 0.0
    p = np.pad(gray, 1, mode="reflect")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - \
         (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - \
         (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return float(np.hypot(gx, gy).mean())


def _fill_score(ratio: float) -> float:
    """0..1 : 1 sur le palier FILL_LOW..FILL_HIGH, linéaire vers 0 en dessous,
    vers 0.5 à 100 % au-dessus (un fond plein reste lisible)."""
    if ratio < FILL_LOW:
        return ratio / FILL_LOW
    if ratio > FILL_HIGH:
        return max(0.0, 1.0 - (ratio - FILL_HIGH) * 1.25)
    return 1.0


def score_frame(frame: FrameLike) -> tuple[float, list[str]]:
    """Retourne (score 0..1, codes de raisons) pour UNE image."""
    gray = _to_gray(frame)
    if gray.size == 0:
        return 0.0, ["empty_frame"]

    h, w = gray.shape
    lit = gray > BLACK_THRESHOLD
    non_black_ratio = float(lit.mean())
    mean_gradient = _mean_sobel(gray)

    ys, xs = np.nonzero(lit)
    if ys.size:
        h_occ = (xs.max() - xs.min() + 1) / w
        v_occ = (ys.max() - ys.min() + 1) / h
    else:
        h_occ = v_occ = 0.0
    occupancy = (h_occ + v_occ) / 2.0

    reasons: list[str] = []
    if non_black_ratio < 0.05:
        reasons.append("mostly_empty")
    elif non_black_ratio > 0.8:
        reasons.append("too_cluttered")
    if occupancy > 0.7:
        reasons.append("excellent_occupancy")
    elif occupancy < 0.3:
        reasons.append("poor_occupancy")
    if mean_gradient > 60:
        reasons.append("strong_contrast")
    elif mean_gradient < 20:
        reasons.append("low_contrast")

    ratio_score = _fill_score(non_black_ratio)
    score = (W_NON_BLACK * ratio_score
             + W_CONTRAST * min(1.0, mean_gradient / GRADIENT_FULL)
             + W_OCCUPATION * occupancy)
    return score, reasons


# --- Score d'un GIF / d'une séquence -----------------------------------------
def _base_score(frames: Sequence[FrameLike]) -> tuple[float, list[str]]:
    """Moyenne des scores sur <= 10 images réparties ; retourne (0..100, raisons)."""
    n = len(frames)
    step = max(1, n // MAX_SAMPLED_FRAMES)
    scores: list[float] = []
    reasons: list[str] = []
    for i in range(0, n, step):
        s, r = score_frame(frames[i])
        scores.append(s)
        for code in r:
            if code not in reasons:
                reasons.append(code)
    return float(np.mean(scores)) * 100.0, reasons


def _apply_temporal(final: float, reasons: list[str], n_frames: int,
                    total_ms: int, penalize_static: bool) -> QualityResult:
    """Pénalités sur le nombre d'images et la durée totale."""
    if n_frames == 1:
        if penalize_static:
            final *= 0.2
            reasons.append("too_few_frames")
    elif n_frames <= 2:
        final *= 0.2
        reasons.append("too_few_frames")
    elif total_ms < MIN_DURATION_MS:
        final *= 0.4
        reasons.append("too_fast")
    return _result(round(final), reasons)


def evaluate_frames(frames: Sequence[FrameLike],
                    durations_ms: Union[int, Sequence[int], None] = None,
                    penalize_static: bool = False) -> QualityResult:
    """Note une animation à partir de ses images (déjà en mémoire).

    durations_ms : durée de chaque image (liste) ou durée commune (int).
    penalize_static : si False (défaut), un GIF d'une seule image est
        considéré comme volontairement statique et n'est pas pénalisé.
    """
    n = len(frames)
    if n == 0:
        return _result(0, ["empty_frame"])

    if durations_ms is None:
        total_ms = n * 100
    elif isinstance(durations_ms, (int, float)):
        total_ms = int(durations_ms) * n
    else:
        total_ms = int(sum(durations_ms))

    final, reasons = _base_score(frames)
    return _apply_temporal(final, reasons, n, total_ms, penalize_static)


def evaluate_gif_quality(path: str, penalize_static: bool = False) -> QualityResult:
    """Note un fichier GIF existant (décode seulement les images échantillonnées)."""
    try:
        with Image.open(path) as im:
            n = getattr(im, "n_frames", 1)
            step = max(1, n // MAX_SAMPLED_FRAMES)
            sampled: list[Image.Image] = []
            total_ms = 0
            for i in range(n):
                im.seek(i)
                total_ms += int(im.info.get("duration", 100) or 100)
                if i % step == 0:
                    sampled.append(im.convert("RGBA"))
    except Exception:
        return _result(0, ["unreadable"])

    final, reasons = _base_score(sampled)
    return _apply_temporal(final, reasons, n, total_ms, penalize_static)


# --- Index par dossier, tri, résumé, mise à l'écart --------------------------
def index_path(folder: str) -> str:
    return os.path.join(folder, INDEX_NAME)


def save_index(folder: str, rows: dict[str, dict]) -> None:
    """rows : {chemin_relatif_posix: QualityResult.to_dict()}"""
    tmp = index_path(folder) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    os.replace(tmp, index_path(folder))


def load_index(folder: str) -> dict[str, dict]:
    try:
        with open(index_path(folder), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def sorted_rows(rows: dict[str, dict], ascending: bool = True) -> list[tuple[str, dict]]:
    """Pour la liste de revue : les pires d'abord (ascending=True)."""
    live = [(k, v) for k, v in rows.items() if not v.get("moved")]
    return sorted(live, key=lambda kv: kv[1]["score"], reverse=not ascending)


def summarize(rows: dict[str, dict]) -> dict:
    live = [v for v in rows.values() if not v.get("moved")]
    counts: dict[str, int] = {}
    for v in live:
        counts[v["rating"]] = counts.get(v["rating"], 0) + 1
    mean = float(np.mean([v["score"] for v in live])) if live else 0.0
    return {"count": len(live), "mean": round(mean, 1), "by_rating": counts}


def review_low(folder: str, threshold: int = 30, dest: str = REVIEW_DIR,
               dry_run: bool = False) -> list[str]:
    """Déplace (jamais supprime) les GIF dont le score <= threshold vers
    folder/dest/, en conservant l'arborescence. Retourne les chemins déplacés."""
    rows = load_index(folder)
    moved: list[str] = []
    for rel, info in rows.items():
        if info.get("moved") or info["score"] > threshold:
            continue
        src = os.path.join(folder, *rel.split("/"))
        if not os.path.isfile(src):
            continue
        dst = os.path.join(folder, dest, *rel.split("/"))
        if not dry_run:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            info["moved"] = True
        moved.append(rel)
    if moved and not dry_run:
        save_index(folder, rows)
    return moved


# --- Ligne de commande : noter un dossier de GIF existant --------------------
def _iter_gifs(folder: str) -> Iterable[str]:
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d != REVIEW_DIR]
        for name in files:
            if name.lower().endswith(".gif"):
                yield os.path.join(root, name)


def _worker(args: tuple[str, str]) -> tuple[str, dict]:
    folder, path = args
    rel = os.path.relpath(path, folder).replace(os.sep, "/")
    return rel, evaluate_gif_quality(path).to_dict()


def main() -> None:
    from concurrent.futures import ProcessPoolExecutor

    ap = argparse.ArgumentParser(description="Score de qualité de GIF DMD 128x32")
    ap.add_argument("folder")
    ap.add_argument("--threshold", type=int, default=30,
                    help="seuil (<=) pour lister/déplacer les GIF faibles")
    ap.add_argument("--move", action="store_true",
                    help=f"déplace les GIF faibles vers {REVIEW_DIR}/")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--lang", default="fr", choices=["fr", "en", "es"])
    args = ap.parse_args()

    paths = list(_iter_gifs(args.folder))
    rows: dict[str, dict] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for rel, res in ex.map(_worker, [(args.folder, p) for p in paths], chunksize=32):
            rows[rel] = res
    save_index(args.folder, rows)

    s = summarize(rows)
    print(f"{s['count']} GIF — score moyen {s['mean']} — {s['by_rating']}")
    print(f"\n20 plus faibles (index : {index_path(args.folder)}):")
    for rel, info in sorted_rows(rows)[:20]:
        why = ", ".join(reason_text(c, args.lang) for c in info["reasons"])
        print(f"  {info['color']} {info['score']:3d}  {rel}  — {why}")

    moved = review_low(args.folder, args.threshold, dry_run=not args.move)
    verb = "déplacés" if args.move else "à déplacer (relancer avec --move)"
    print(f"\n{len(moved)} GIF <= {args.threshold} {verb}.")


if __name__ == "__main__":
    main()
