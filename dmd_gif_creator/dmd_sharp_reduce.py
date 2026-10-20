# ============================================
# Prototype (branche dev/engine-reduction) -- NON publie
# Reduction « aire exacte + traits fins epaissis », portee depuis le moteur des
# logos de theme du toolkit RecalBoxDMD (theme_logos.py v21 : thicken_thin_strokes,
# area_downscale, _win_extreme). Memes algorithmes, seule dependance : numpy + Pillow.
# ============================================
"""
dmd_sharp_reduce.py -- reduction pleine largeur ET nette pour images fixes / texte / pixel-art.

Principe : (1) les traits lumineux plus fins qu'environ une demi-LED (detectes par
ouverture morphologique) sont epaissis AVANT la reduction ; (2) reduction BOX = moyenne
exacte de chaque LED. Suppose des traits clairs sur fond sombre : `is_dark_background`
sert de garde-fou (meme condition que le Mode 10 du toolkit).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

THIN_OPEN, THIN_GROW = 0.25, 0.15   # rayons (en LED) de detection / d'epaississement (reglage D du banc)
MAX_LUMA_GAIN = 0.08                # gain de luminance maxi tolere avant repli sur la moyenne exacte
DARK_MEAN_MAX = 60.0                # luminance moyenne max du fond pour activer le moteur
DARK_BORDER_FRAC = 0.80             # part minimale de pixels de bord sombres


def _win_extreme(a: np.ndarray, k: int, use_max: bool) -> np.ndarray:
    """Equivalent exact de MinFilter/MaxFilter(k) de Pillow (fenetre carree impaire), separable."""
    r = k // 2
    if r == 0:
        return a.copy()
    h, w = a.shape[:2]
    f = np.maximum if use_max else np.minimum
    pad = [(r, r), (r, r)] + [(0, 0)] * (a.ndim - 2)
    p = np.pad(a, pad, mode="constant", constant_values=0 if use_max else 255)
    t = p[:h]
    for d in range(1, 2 * r + 1):
        t = f(t, p[d:h + d])
    u = t[:, :w]
    for d in range(1, 2 * r + 1):
        u = f(u, t[:, d:w + d])
    return u


def thicken_thin_strokes(rgb: Image.Image, nw: int, open_r: float = THIN_OPEN,
                         grow_r: float = THIN_GROW, thr: int = 40) -> Image.Image:
    """Epaissit les traits plus fins qu'environ une demi-LED (rgb : image RGB fond noir,
    nw : largeur de sortie en LED)."""
    if not open_r or not grow_r:
        return rgb
    led = rgb.width / float(nw)
    ro = max(1, int(round(open_r * led)))
    rg = max(1, int(round(grow_r * led)))
    a = np.asarray(rgb)
    mask = a.max(axis=2) >= thr
    if not mask.any():
        return rgb
    m8 = (mask * 255).astype(np.uint8)
    opened = _win_extreme(_win_extreme(m8, 2 * ro + 1, False), 2 * ro + 1, True) > 0
    thin = mask & ~opened
    if not thin.any():
        return rgb
    tm = _win_extreme((thin * 255).astype(np.uint8), 2 * rg + 1, True) > 0
    grow = tm & ~mask
    src = _win_extreme(np.where(thin[..., None], a, 0).astype(np.uint8), 2 * rg + 1, True)
    out = a.copy()
    out[grow] = src[grow]
    return Image.fromarray(out, "RGB")


def area_downscale(rgb: Image.Image, nw: int, nh: int, thicken: bool = True,
                   max_gain: float = MAX_LUMA_GAIN) -> Image.Image:
    """Reduction par aire exacte (BOX), apres epaississement optionnel des traits fins.
    Garde-fou de fidelite : si l'epaississement augmente la luminance moyenne de plus de
    `max_gain` (ex. 0.08 = +8 %) par rapport a la moyenne exacte, on garde la moyenne exacte
    (logos illustres a contours fins, type Garou : +18 % meme au reglage le plus doux)."""
    box = rgb.resize((nw, nh), Image.Resampling.BOX)
    if not thicken:
        return box
    thick = thicken_thin_strokes(rgb, nw).resize((nw, nh), Image.Resampling.BOX)
    if max_gain is not None:
        lb = float(np.asarray(box.convert("L"), dtype=np.float64).mean())
        lt = float(np.asarray(thick.convert("L"), dtype=np.float64).mean())
        if lb > 0 and lt / lb - 1.0 > max_gain:
            return box
    return thick


def is_dark_background(img: Image.Image) -> bool:
    """Vrai si le fond est sombre (pixels de bord de l'image composee sur noir)."""
    rgba = img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
    bg.alpha_composite(rgba)
    g = np.asarray(bg.convert("L"), dtype=np.float32)
    if g.size == 0:
        return False
    border = np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])
    return bool((border < 40).mean() >= DARK_BORDER_FRAC and g.mean() <= DARK_MEAN_MAX)
