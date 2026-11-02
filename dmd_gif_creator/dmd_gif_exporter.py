from __future__ import annotations

# ============================================
# safe-modify — Historique des modifications
# ============================================
# Version actuelle : v4
#
# v4 — 2026-11-02 — safe-modify — Filigrane invisible "DGC" sur tous les GIF produits (demande : savoir si un GIF
#      vient de DMD GIF Creator ou d'ailleurs ; détection côté Discord). Paramètre `watermark` (défaut True, coupé
#      seulement par les tests) de `_encode_gif_bytes` : bit de poids faible des couleurs de la palette de chaque
#      image + extension Comment « DGC1:… », voir dgc_mark.py. Un seul point d'ancrage : aucun site d'appel modifié.
#
# v3 — 2026-09-24 — safe-modify — Option `shared_palette` (défaut False = comportement inchangé) : une seule
#      palette adaptative calculée sur un échantillon de frames (≤ 32, réparties sur toute la séquence) puis
#      appliquée à toutes les frames sans tramage, au lieu d'une quantization adaptative par frame. Utilisée par
#      le traitement par lot AUTO (process_one_image), où toutes les frames viennent de la même image source
#      (défilement/effet) : encodage mesuré ×19 plus rapide (2,75 s → 0,14 s sur 12 images mame/S), écart moyen à
#      la source 1,9 contre 1,6 (sur 255), fichiers légèrement plus petits. PAS utilisée pour VIDEO (scènes
#      variées, palette par frame conservée) ni pour les exports unitaires.
#
# v2 — 2026-07-19 — safe-modify — Refactor : logique d'encodage GIF extraite
#      de `export_frames_to_gif` vers un helper interne `_encode_gif_bytes`
#      (encode en mémoire, `io.BytesIO`, retourne les octets) partagé par
#      `export_frames_to_gif` (écrit ces octets sur disque via
#      `Path.write_bytes`) et la nouvelle `estimate_gif_size` (retourne juste
#      `len(...)`, sans écrire sur disque) — demande utilisateur : estimation
#      du poids du GIF résultant dans l'onglet VIDEO, calculée avec les
#      MÊMES paramètres qu'un export réel (pas une heuristique). Comportement
#      externe de `export_frames_to_gif` inchangé (mêmes validations, mêmes
#      octets produits — vérifié par ré-exécution des tests du pipeline
#      VIDEO existants après le refactor).
# v1 — 2026-07-19 — safe-modify — Version de base (avant refactor v2).
# ============================================

import io
from pathlib import Path
from typing import Any, Sequence

from PIL import Image

try:
    from . import dgc_mark
except ImportError:
    import dgc_mark

# Pillow compatibility: ADAPTIVE may not exist in some stubs.
_ADAPTIVE_RESAMPLING = getattr(Image, "ADAPTIVE", None)
if _ADAPTIVE_RESAMPLING is None:
    _ADAPTIVE_RESAMPLING = Image.Resampling.LANCZOS

# Pylance: `palette=` attend un type "Palette". En pratique, Pillow accepte
# Image.ADAPTIVE (ou une valeur équivalente). On caste pour désactiver le faux positif.
_PALETTE_VALUE: Any = _ADAPTIVE_RESAMPLING


def _encode_gif_bytes(
    frames: Sequence[Image.Image],
    *,
    fps: int,
    color_count: int,
    loop_mode: str,
    loop_count: int,
    disposal: int = 2,
    optimize: bool = False,
    shared_palette: bool = False,
    watermark: bool = True,
) -> bytes:
    """Encode une séquence de frames en GIF (mêmes règles que
    export_frames_to_gif) et retourne les octets bruts, sans rien écrire sur
    disque — utilisé à la fois par export_frames_to_gif (écriture) et
    estimate_gif_size (estimation de poids avant export)."""
    if not frames:
        raise ValueError("_encode_gif_bytes: 'frames' est vide")

    if fps <= 0:
        raise ValueError("_encode_gif_bytes: 'fps' doit être > 0")

    if color_count <= 0:
        raise ValueError("_encode_gif_bytes: 'color_count' doit être > 0")

    # Conversion palette
    p_frames: list[Image.Image] = []
    if shared_palette and len(frames) > 1:
        # v3 -- une palette pour toute la séquence (voir en-tête)
        rgb_frames = [f.convert("RGB") for f in frames]
        w, h = rgb_frames[0].size
        step = max(1, len(rgb_frames) // 32)
        sample = rgb_frames[::step]
        mosaic = Image.new("RGB", (w, h * len(sample)))
        for i, f in enumerate(sample):
            mosaic.paste(f.resize((w, h)) if f.size != (w, h) else f, (0, i * h))
        palette_img = mosaic.convert(
            "P", palette=_PALETTE_VALUE, colors=color_count, dither=Image.Dither.NONE
        )
        for f in rgb_frames:
            p_frames.append(f.quantize(palette=palette_img, dither=Image.Dither.NONE))
    else:
        for frame in frames:
            p_frames.append(
                frame.convert(
                    "P",
                    palette=_PALETTE_VALUE,
                    colors=color_count,
                    dither=Image.Dither.NONE,
                )
            )

    loop = 0 if str(loop_mode) == "infini" else int(loop_count)
    duration_ms = int(1000 / fps)

    # v4 -- filigrane invisible (voir dgc_mark) : palette de chaque image + commentaire GIF
    extra = {"comment": dgc_mark.embed_gif_frames(p_frames)} if watermark else {}

    buf = io.BytesIO()
    p_frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=p_frames[1:],
        duration=duration_ms,
        loop=loop,
        disposal=disposal,
        optimize=optimize,
        **extra,
    )
    return buf.getvalue()


def export_frames_to_gif(
    frames: Sequence[Image.Image],
    output_path: str | Path,
    *,
    fps: int,
    color_count: int,
    loop_mode: str,
    loop_count: int,
    disposal: int = 2,
    optimize: bool = False,
    shared_palette: bool = False,
) -> None:
    """
    Exporte une séquence de frames PIL (RGB/anything convertissable) en GIF.

    - Conversion en palette (mode "P") avec palette adaptative
      (par frame, ou une seule pour toute la séquence si shared_palette)
    - Duration = 1000/fps
    - loop: 0 si loop_mode == "infini", sinon loop_count
    """
    data = _encode_gif_bytes(
        frames,
        fps=fps,
        color_count=color_count,
        loop_mode=loop_mode,
        loop_count=loop_count,
        disposal=disposal,
        optimize=optimize,
        shared_palette=shared_palette,
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


def estimate_gif_size(
    frames: Sequence[Image.Image],
    *,
    fps: int,
    color_count: int,
    loop_mode: str,
    loop_count: int,
    disposal: int = 2,
    optimize: bool = False,
) -> int:
    """Encode les frames en mémoire avec les MÊMES paramètres qu'un export
    réel et retourne la taille exacte résultante en octets, sans écrire sur
    disque — poids exact pour ces réglages, pas une heuristique."""
    return len(
        _encode_gif_bytes(
            frames,
            fps=fps,
            color_count=color_count,
            loop_mode=loop_mode,
            loop_count=loop_count,
            disposal=disposal,
            optimize=optimize,
        )
    )
