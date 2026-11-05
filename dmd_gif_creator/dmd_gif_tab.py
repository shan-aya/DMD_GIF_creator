from __future__ import annotations

# ============================================
# safe-modify — Historique des modifications
# ============================================
# Version actuelle : v1
#
# v1 — 2026-11-05 — safe-modify — Onglet « GIF » : conversion d'un GIF animé existant au format DMD 128×32
#      (moteur : dmd_gif_convert, partagé avec le bot Discord). Code Tk isolé dans ce module pour ne pas gonfler
#      dmd_converter.py : `GifTab(app, parent, tr)` ; l'appli ne fait que l'instancier et lui passer les fichiers
#      déposés (`load_path`). Un GIF à la fois, traitement en thread, aperçu LED avant/après, Auto/Manuel,
#      choix du cadrage (auto / suivi du sujet / bandes noires / remplir), export avec les durées d'origine.
# ============================================

import dataclasses
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

try:
    from . import dmd_gif_convert as gc
    from .dmd_engine import DMDEngine
except ImportError:
    import dmd_gif_convert as gc
    from dmd_engine import DMDEngine

CROP_MODES = ("auto", "follow", "letterbox", "fill")
CROP_LABELS = {
    "auto": ("gif_crop_auto", "Automatique"),
    "follow": ("gif_crop_follow", "Suivre le sujet"),
    "letterbox": ("gif_crop_letterbox", "Bandes noires"),
    "fill": ("gif_crop_fill", "Remplir (recadrer)"),
}


class GifTab:
    def __init__(self, app, parent, tr):
        self.app, self.parent, self.tr = app, parent, tr
        self.root = app.root
        self.src = None            # GifData
        self.path = None
        self.result_frames = None
        self.result_durations = None
        self.plan = None
        self.report = None
        self.busy = False
        self._job = None
        self._idx = 0
        self._photos = [None, None]

        self.auto_var = tk.BooleanVar(value=True)
        self.crop_var = tk.StringVar(value=self.tr(*CROP_LABELS["auto"]))
        self.contrast = tk.DoubleVar(value=gc.DEFAULT_SETTINGS["contrast"])
        self.saturation = tk.DoubleVar(value=gc.DEFAULT_SETTINGS["saturation"])
        self.brightness = tk.DoubleVar(value=gc.DEFAULT_SETTINGS["brightness"])
        self.black = tk.IntVar(value=gc.DEFAULT_SETTINGS["black_threshold"])
        self.cleanup = tk.DoubleVar(value=gc.DEFAULT_SETTINGS["cleanup_power"])
        self.colors = tk.IntVar(value=gc.DEFAULT_SETTINGS["color_count"])
        self.pp = tk.BooleanVar(value=True)
        self.scroll_var = tk.BooleanVar(value=True)
        self.scroll_back_var = tk.BooleanVar(value=False)
        self.speed_var = tk.DoubleVar(value=1.0)          # multiplicateur de vitesse du scroll (1 = auto)
        self.speed_txt = tk.StringVar(value="×1.0")
        # cadre 128×32 posé à la main (mode manuel + « Remplir ») ; positions normalisées (0-1) du coin haut-gauche
        self.win_on = tk.BooleanVar(value=False)
        self.win_target = tk.StringVar(value="start")
        self.win_zoom = tk.DoubleVar(value=1.0)          # part de la taille maximale du cadre
        self.win_s = [0.0, 0.0]
        self.win_e = [1.0, 1.0]
        self._geo = None
        self._drag_img = None       # aperçu immédiat du cadre en cours de déplacement (case de droite)
        self._pending = False       # un réglage a changé pendant une conversion : on relance à la fin
        self.status = tk.StringVar(value=self.tr("gif_status_idle", "Ouvrez ou déposez un GIF animé."))
        self.info = tk.StringVar(value="")
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self):
        tr = self.tr
        m = ttk.Frame(self.parent, padding=10)
        m.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(m)
        top.pack(fill=tk.X)
        ttk.Button(top, text=tr("gif_open", "Ouvrir un GIF…"), command=self.open_dialog).pack(side=tk.LEFT)
        self.btn_export = ttk.Button(top, text=tr("gif_export", "Exporter le GIF DMD…"), command=self.export,
                                     state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=6)
        self.btn_lb = ttk.Button(top, text=tr("gif_export_lb", "Exporter la variante bandes noires…"),
                                 command=self.export_letterbox, state=tk.DISABLED)
        self.btn_lb.pack(side=tk.LEFT)
        ttk.Button(top, text=tr("gif_open_app", "Retouche manuelle (site de l'appli)"),
                   command=lambda: webbrowser.open(gc.APP_PAGE)).pack(side=tk.RIGHT)

        prev = ttk.Frame(m)
        prev.pack(fill=tk.X, pady=8)
        self.cv = []
        for i, key in enumerate((("gif_before", "Avant"), ("gif_after", "Après (aperçu LED)"))):
            f = ttk.LabelFrame(prev, text=tr(*key))
            f.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=4)
            # « Avant » : 520×150 (sources de toute forme) ; « Après » : EXACTEMENT l'aperçu LED (4 × 128 par 4 × 32)
            c = tk.Canvas(f, width=520 if i == 0 else 512, height=150 if i == 0 else 128, bg="#000000",
                          highlightthickness=0)
            c.pack(padx=4, pady=4, expand=True)        # expand sans fill : la case reste centrée dans son cadre
            self.cv.append(c)

        ttk.Label(m, textvariable=self.info, justify=tk.LEFT, wraplength=1000).pack(fill=tk.X)
        ttk.Label(m, textvariable=self.status, foreground="#3d9a46").pack(fill=tk.X, pady=(2, 6))

        opt = ttk.LabelFrame(m, text=tr("gif_settings", "Réglages"))
        opt.pack(fill=tk.X)
        row = self.row = ttk.Frame(opt)
        row.pack(fill=tk.X, padx=6, pady=4)
        ttk.Checkbutton(row, text=tr("gif_auto", "Mode automatique"), variable=self.auto_var,
                        command=self._on_mode).pack(side=tk.LEFT)
        ttk.Label(row, text=tr("gif_crop", "Cadrage :")).pack(side=tk.LEFT, padx=(16, 4))
        self.crop_cb = ttk.Combobox(row, state="readonly", width=22, textvariable=self.crop_var,
                                    values=[tr(*CROP_LABELS[k]) for k in CROP_MODES])
        self.crop_cb.pack(side=tk.LEFT)
        self.crop_cb.bind("<<ComboboxSelected>>", lambda e: (self._on_crop(), self.reprocess()))
        self.scroll_cb = ttk.Checkbutton(row, text=tr("gif_scroll", "Scroll intelligent"),
                                         variable=self.scroll_var,
                                         command=lambda: (self._refresh_win_ui(), self.reprocess()))
        self.scroll_back_cb = ttk.Checkbutton(row, text=tr("gif_scroll_back", "Aller-retour"),
                                              variable=self.scroll_back_var, command=self.reprocess)
        self._on_crop()
        self.btn_apply = ttk.Button(row, text=tr("gif_apply", "Appliquer"), command=self.reprocess)
        self.btn_apply.pack(side=tk.LEFT, padx=10)
        ttk.Label(row, text=tr("gif_scroll_speed", "Vitesse du scroll :")).pack(side=tk.LEFT, padx=(8, 4))
        sp = ttk.Scale(row, from_=gc.SCROLL_SPEED_MIN, to=gc.SCROLL_SPEED_MAX, variable=self.speed_var, length=130)
        sp.pack(side=tk.LEFT)
        sp.bind("<ButtonRelease-1>", lambda e: self.reprocess())
        ttk.Label(row, textvariable=self.speed_txt, width=5).pack(side=tk.LEFT)
        self.speed_var.trace_add("write", lambda *a: self.speed_txt.set(f"×{self.speed_var.get():.1f}"))
        self.speed_txt.set(f"×{self.speed_var.get():.1f}")

        self.row2 = ttk.Frame(opt)
        self.win_chk = ttk.Checkbutton(self.row2, text=tr("gif_win_manual", "Cadre 128×32 manuel (glisser sur « Avant »)"),
                                       variable=self.win_on, command=self._on_win)
        self.win_chk.pack(side=tk.LEFT)
        self.win_rb_s = ttk.Radiobutton(self.row2, text=tr("gif_win_start", "Départ"), value="start",
                                        variable=self.win_target, command=self._draw_overlay)
        self.win_rb_e = ttk.Radiobutton(self.row2, text=tr("gif_win_end", "Arrivée"), value="end",
                                        variable=self.win_target, command=self._draw_overlay)
        self.win_rb_s.pack(side=tk.LEFT, padx=(12, 2))
        self.win_rb_e.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.row2, text=tr("gif_win_size", "Taille :")).pack(side=tk.LEFT, padx=(12, 4))
        self.win_scale = ttk.Scale(self.row2, from_=0.1, to=1.0, variable=self.win_zoom, length=150)
        self.win_scale.pack(side=tk.LEFT)
        self.win_scale.bind("<B1-Motion>", lambda e: self._on_zoom(False))
        self.win_scale.bind("<ButtonRelease-1>", lambda e: self._on_zoom(True))
        self.cv[0].bind("<Button-1>", self._win_press)
        self.cv[0].bind("<B1-Motion>", self._win_press)
        self.cv[0].bind("<ButtonRelease-1>", self._win_release)
        self.cv[0].bind("<MouseWheel>", self._win_wheel)

        grid = ttk.Frame(opt)
        grid.pack(fill=tk.X, padx=6, pady=4)
        self.manual_widgets = []
        specs = [("gif_contrast", "Contraste", self.contrast, 0.5, 3.0),
                 ("gif_saturation", "Saturation", self.saturation, 0.0, 3.0),
                 ("gif_brightness", "Luminosité", self.brightness, 0.5, 2.0),
                 ("gif_black", "Seuil de noir", self.black, 0, 80),
                 ("gif_cleanup", "Nettoyage", self.cleanup, 0.0, 1.0),
                 ("gif_colors", "Couleurs", self.colors, 8, 128)]
        for i, (k, d, var, lo, hi) in enumerate(specs):
            ttk.Label(grid, text=tr(k, d)).grid(row=i // 3, column=(i % 3) * 2, sticky="e", padx=(8, 4), pady=2)
            s = ttk.Scale(grid, from_=lo, to=hi, variable=var, length=170)
            s.grid(row=i // 3, column=(i % 3) * 2 + 1, sticky="w")
            s.bind("<ButtonRelease-1>", lambda e: self.reprocess())
            self.manual_widgets.append(s)
        c = ttk.Checkbutton(grid, text=tr("gif_pp", "Pixel perfect"), variable=self.pp, command=self.reprocess)
        c.grid(row=2, column=0, columnspan=2, sticky="w", padx=8)
        self.manual_widgets.append(c)
        self._on_mode()

    def _crop_key(self):
        labels = [self.tr(*CROP_LABELS[k]) for k in CROP_MODES]
        return CROP_MODES[labels.index(self.crop_var.get())] if self.crop_var.get() in labels else "auto"

    def _on_crop(self):
        """Les options de scroll n'apparaissent qu'avec « Remplir » ; le cadre manuel, en plus, qu'en mode manuel."""
        key = self._crop_key()
        self.scroll_cb.pack_forget()
        self.scroll_back_cb.pack_forget()
        if key == "fill":
            self.scroll_cb.pack(side=tk.LEFT, padx=(12, 0), after=self.crop_cb)
            self.scroll_back_cb.pack(side=tk.LEFT, padx=(6, 0), after=self.scroll_cb)
        elif key == "auto":                  # en auto, « Aller-retour » s'applique si l'auto choisit un scroll
            self.scroll_back_cb.pack(side=tk.LEFT, padx=(12, 0), after=self.crop_cb)
        if hasattr(self, "row2"):
            self._refresh_win_ui()

    # ------------------------------------------------------------------ cadre 128×32 manuel
    def _win_active(self):
        return (self._crop_key() == "fill" and not self.auto_var.get() and self.win_on.get() and self.src is not None)

    def _refresh_win_ui(self):
        avail = self._crop_key() == "fill" and not self.auto_var.get()
        if avail:
            self.row2.pack(fill=tk.X, padx=6, pady=(0, 2), after=self.row)
        else:
            self.row2.pack_forget()
        has_end = self.win_on.get() and self.scroll_var.get()
        self.win_rb_e.configure(state=tk.NORMAL if has_end else tk.DISABLED)
        if not has_end and self.win_target.get() == "end":
            self.win_target.set("start")
        self._draw_overlay()

    def _win_dims(self):
        """(W, H, nw_max, nw, nh) -- image de travail, largeur max du cadre et taille actuelle (normalisées)."""
        W, H = self.src.frames[0].size
        nwmax = min(1.0, 4.0 * H / W)
        nw = max(8.0 / W, nwmax * float(self.win_zoom.get()))
        return W, H, nwmax, nw, nw * W / (4.0 * H)

    def _reset_win(self):
        if self.src is None:
            return
        self.win_zoom.set(1.0)
        _, _, _, nw, nh = self._win_dims()
        self.win_s = [0.0, 0.0]
        self.win_e = [max(0.0, 1.0 - nw), max(0.0, 1.0 - nh)]

    def _clamp_win(self):
        _, _, _, nw, nh = self._win_dims()
        for p in (self.win_s, self.win_e):
            p[0] = min(max(0.0, p[0]), max(0.0, 1.0 - nw))
            p[1] = min(max(0.0, p[1]), max(0.0, 1.0 - nh))

    def _on_win(self):
        self._refresh_win_ui()
        self.reprocess()

    def _on_zoom(self, final):
        if self.src is None:
            return
        self._clamp_win()
        self._draw_overlay()
        if self._win_active():
            self._quick_preview()
        if final and self._win_active():
            self.reprocess()

    def _win_move(self, ev):
        if not self._win_active() or not self._geo:
            return
        ox, oy, s, W, H = self._geo
        _, _, _, nw, nh = self._win_dims()
        p = self.win_e if self.win_target.get() == "end" else self.win_s
        p[0] = (ev.x - ox) / (s * W) - nw / 2
        p[1] = (ev.y - oy) / (s * H) - nh / 2
        self._clamp_win()
        self._draw_overlay()
        self._quick_preview()

    def _quick_preview(self):
        """Aperçu immédiat (une image, fixe) du cadre en cours de déplacement dans la case de droite, sans attendre
        la conversion complète (relancée au relâchement de la souris)."""
        if self.plan is None or self.src is None:
            return
        now = time.monotonic()
        if now - getattr(self, "_qp_t", 0.0) < 0.05:            # ~20 images/s max
            return
        self._qp_t = now
        try:
            W, H = self.src.frames[0].size
            _, _, _, nw, _ = self._win_dims()
            p = self.win_e if self.win_target.get() == "end" else self.win_s
            box = gc._manual_box((p[0], p[1], nw), W, H)
            tmp = dataclasses.replace(self.plan, layout="fill", crop=box, windows=None, timeline=None, scroll=None)
            j = min(len(self.src.frames) - 1, len(self.src.frames) // 2)
            self._drag_img = gc.render_frame(self.src.frames[j], tmp, 0)
            self._show_right(self._drag_img)
        except Exception:  # noqa: BLE001 -- aperçu d'aide : jamais bloquant
            self._drag_img = None

    def _show_right(self, img):
        pic = DMDEngine.render_led_style(img, scale=4, led_ratio=0.525, glow=True,
                                         brightness=self.app.led_brightness_var.get())
        self._photos[1] = ImageTk.PhotoImage(pic)
        self.cv[1].delete("all")
        self.cv[1].create_image(256, 64, image=self._photos[1])

    def _win_press(self, ev):
        self._win_move(ev)

    def _win_release(self, ev):
        if self._win_active():
            self.reprocess()

    def _win_wheel(self, ev):
        if self._win_active():
            self.win_zoom.set(min(1.0, max(0.1, self.win_zoom.get() + (0.05 if ev.delta > 0 else -0.05))))
            self._on_zoom(True)

    def _draw_overlay(self):
        c = self.cv[0]
        c.delete("ov")
        if not self._win_active() or not self._geo:
            return
        ox, oy, s, W, H = self._geo
        _, _, _, nw, nh = self._win_dims()
        pts = [("start", self.win_s, "#2ecc71")]
        if self.scroll_var.get():
            pts.append(("end", self.win_e, "#ff9f1a"))
        for name, p, col in pts:
            x1, y1 = ox + p[0] * W * s, oy + p[1] * H * s
            x2, y2 = x1 + nw * W * s, y1 + nh * H * s
            sel = self.win_target.get() == name
            c.create_rectangle(x1, y1, x2, y2, outline=col, width=3 if sel else 1, tags="ov")
            c.create_text(x1 + 3, y1 + 2, anchor="nw", text=("D" if name == "start" else "A"), fill=col, tags="ov")

    def _on_mode(self):
        st = tk.DISABLED if self.auto_var.get() else tk.NORMAL
        for w in self.manual_widgets:
            try:
                w.configure(state=st)
            except tk.TclError:
                pass
        self._refresh_win_ui()
        if self.src is not None:
            self.reprocess()

    # ------------------------------------------------------------------ fichier
    def open_dialog(self):
        p = filedialog.askopenfilename(title=self.tr("gif_open", "Ouvrir un GIF…"),
                                       filetypes=[("GIF", "*.gif"), ("*", "*.*")])
        if p:
            self.load_path(p)

    def load_path(self, path):
        if self.busy:
            return
        try:
            data = Path(path).read_bytes()
            self.src = gc.load_gif(data)
        except (gc.GifError, OSError) as e:
            messagebox.showerror("GIF", str(e))
            return
        self.path = str(path)
        v = gc.analyze_gif(self.src)
        lang = "fr"
        why = ", ".join(gc.reason_text(r, lang) for r in v.reasons) if v.reasons else ""
        head = Path(path).name + f" — {self.src.width}×{self.src.height}, {len(self.src.frames)} images, " \
                                 f"{self.src.n_bytes // 1024} Ko"
        verdict = self.tr("gif_needs", "À convertir : {why}", why=why) if v.needs_conversion \
            else self.tr("gif_ok", "Déjà au bon format (reconversion possible).")
        self.info.set(head + "\n" + verdict)
        self.result_frames = None
        self._reset_win()
        self._show_before()
        self.reprocess()

    # ------------------------------------------------------------------ traitement
    def _options(self):
        crop = self._crop_key()
        opts = {"crop_mode": crop}
        if crop == "fill" and self.scroll_var.get():
            opts.update(scroll=True, scroll_back=bool(self.scroll_back_var.get()))
        if abs(float(self.speed_var.get()) - 1.0) > 0.04:
            opts["scroll_speed"] = round(float(self.speed_var.get()), 2)
        if crop == "auto" and self.scroll_back_var.get():
            opts["scroll_back"] = True
        if self._win_active():
            _, _, _, nw, _ = self._win_dims()
            opts["window"] = (self.win_s[0], self.win_s[1], nw)
            if self.scroll_var.get():
                opts["window_end"] = (self.win_e[0], self.win_e[1], nw)
        if not self.auto_var.get():
            opts.update(contrast=float(self.contrast.get()), saturation=float(self.saturation.get()),
                        brightness=float(self.brightness.get()), black_threshold=int(self.black.get()),
                        cleanup_power=float(self.cleanup.get()), color_count=int(self.colors.get()),
                        pixel_perfect=bool(self.pp.get()))
        return crop, opts

    def reprocess(self):
        if self.src is None:
            return
        if self.busy:                   # une conversion tourne : on en relance une dès qu'elle finit (rien n'est perdu)
            self._pending = True
            return
        self._pending = False
        self.busy = True
        self.status.set(self.tr("gif_working", "Conversion en cours…"))
        crop, opts = self._options()
        mode = "auto" if self.auto_var.get() else "manual"
        src = self.src

        box: dict = {}

        def work():
            try:
                plan = gc.plan_conversion(src, mode, opts, True if crop == "letterbox" else None)
                frames = gc.render_frames(src, plan)
                durs = gc.plan_durations(src, plan)
                gif = gc.encode_frames(frames, durs, plan.settings)
                score = gc.dq.evaluate_frames(frames, durs)
                box["r"] = (plan, frames, gif, score, None)
            except Exception as e:  # noqa: BLE001 -- affichée à l'utilisateur
                box["r"] = (None, None, None, None, e)

        def poll():                     # le thread ne touche jamais à Tk : le fil principal vient chercher le résultat
            if "r" in box:
                self._done(*box["r"])
            else:
                self.root.after(50, poll)

        threading.Thread(target=work, daemon=True).start()
        self.root.after(50, poll)

    def _done(self, plan, frames, gif, score, err):
        self.busy = False
        if getattr(self, "_pending", False):        # des réglages ont changé pendant le calcul : résultat périmé
            self._pending = False
            self.reprocess()
            return
        self._drag_img = None
        if err is not None:
            self.status.set(str(err))
            return
        self.plan, self.result_frames, self.result_durations, self.gif_bytes = plan, frames, gc.plan_durations(self.src, plan), gif
        layout = {"native": "d'origine", "fit": "bandes noires si besoin", "fill": "recadré plein écran",
                  "follow": "suivi du sujet", "scroll": "remplir + scroll intelligent"}.get(plan.layout, plan.layout)
        extra = ""
        if plan.scroll:
            sc = plan.scroll
            axis_txt = {"y": "vertical", "x": "horizontal"}.get(sc["axis"], "départ → arrivée")
            auto_txt = f"choisi par l'auto : note {sc['score_fit']} → {sc['score_scroll']}, " if sc.get("auto") else ""
            extra = (f" ({auto_txt}{axis_txt}, {sc['travel_px']} px"
                     f"{', départ inversé' if sc['reversed'] else ''}{', aller-retour' if sc['back'] else ''}, "
                     f"{sc['duration_ms'] / 1000:.1f} s)")
        if plan.follow:
            extra = f" (zoom ×{plan.follow['d']}, sujet gardé à {int(plan.follow['coverage'] * 100)} %)"
        self.status.set(self.tr("gif_result", "Cadrage : {layout}{extra} — note {score}/100 ({rating}) — {kb} Ko",
                                layout=layout, extra=extra, score=score.score, rating=score.rating,
                                kb=max(1, len(gif) // 1024)))
        self.btn_export.configure(state=tk.NORMAL)
        self.btn_lb.configure(state=tk.NORMAL if plan.layout in ("fill", "follow", "scroll") else tk.DISABLED)
        self._idx = 0
        self._play()

    # ------------------------------------------------------------------ aperçu
    def _show_before(self):
        self._before_idx = 0

    def _play(self):
        if self._job:
            try:
                self.root.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if not self.result_frames or self.src is None:
            return
        i = self._idx % len(self.result_frames)
        si = min(gc.plan_source_index(self.plan, i), len(self.src.frames) - 1) if self.plan else i
        right = self._drag_img if getattr(self, "_drag_img", None) is not None else self.result_frames[i]
        for k, img in enumerate((self.src.frames[si], right)):
            c = self.cv[k]
            if k == 0:
                w, h = img.size
                s = min(520 / w, 150 / h)
                pw, ph = max(1, int(w * s)), max(1, int(h * s))
                pic = img.resize((pw, ph), Image.Resampling.BILINEAR)
                self._geo = (260 - pw / 2, 75 - ph / 2, pw / w, w, h)
            else:
                pic = DMDEngine.render_led_style(img, scale=4, led_ratio=0.525, glow=True,
                                                 brightness=self.app.led_brightness_var.get())
            self._photos[k] = ImageTk.PhotoImage(pic)
            c.delete("all")
            c.create_image(260 if k == 0 else 256, 75 if k == 0 else 64, image=self._photos[k])
            if k == 0:
                self._draw_overlay()
        self._idx = (i + 1) % len(self.result_frames)
        self._job = self.root.after(max(20, int(self.result_durations[i])), self._play)

    # ------------------------------------------------------------------ export
    def _save(self, data: bytes, suffix: str):
        base = Path(self.path).stem if self.path else "dmd"
        p = filedialog.asksaveasfilename(defaultextension=".gif", initialfile=f"{base}{suffix}.gif",
                                         filetypes=[("GIF", "*.gif")])
        if p:
            Path(p).write_bytes(data)
            self.status.set(self.tr("gif_saved", "Enregistré : {p}", p=p))

    def export(self):
        if self.result_frames:
            self._save(self.gif_bytes, "_dmd")

    def export_letterbox(self):
        if self.src is None:
            return
        _, opts = self._options()
        try:
            plan = gc.plan_conversion(self.src, "auto" if self.auto_var.get() else "manual", opts, True)
            frames = gc.render_frames(self.src, plan)
            self._save(gc.encode_frames(frames, gc.plan_durations(self.src, plan), plan.settings), "_dmd_bandes")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("GIF", str(e))
