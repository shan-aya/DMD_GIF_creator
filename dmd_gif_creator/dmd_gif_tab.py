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

import threading
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
            c = tk.Canvas(f, width=520, height=150, bg="#000000", highlightthickness=0)
            c.pack(padx=4, pady=4)
            self.cv.append(c)

        ttk.Label(m, textvariable=self.info, justify=tk.LEFT, wraplength=1000).pack(fill=tk.X)
        ttk.Label(m, textvariable=self.status, foreground="#3d9a46").pack(fill=tk.X, pady=(2, 6))

        opt = ttk.LabelFrame(m, text=tr("gif_settings", "Réglages"))
        opt.pack(fill=tk.X)
        row = ttk.Frame(opt)
        row.pack(fill=tk.X, padx=6, pady=4)
        ttk.Checkbutton(row, text=tr("gif_auto", "Mode automatique"), variable=self.auto_var,
                        command=self._on_mode).pack(side=tk.LEFT)
        ttk.Label(row, text=tr("gif_crop", "Cadrage :")).pack(side=tk.LEFT, padx=(16, 4))
        self.crop_cb = ttk.Combobox(row, state="readonly", width=22, textvariable=self.crop_var,
                                    values=[tr(*CROP_LABELS[k]) for k in CROP_MODES])
        self.crop_cb.pack(side=tk.LEFT)
        self.crop_cb.bind("<<ComboboxSelected>>", lambda e: self.reprocess())
        self.btn_apply = ttk.Button(row, text=tr("gif_apply", "Appliquer"), command=self.reprocess)
        self.btn_apply.pack(side=tk.LEFT, padx=10)

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

    def _on_mode(self):
        st = tk.DISABLED if self.auto_var.get() else tk.NORMAL
        for w in self.manual_widgets:
            try:
                w.configure(state=st)
            except tk.TclError:
                pass
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
        self._show_before()
        self.reprocess()

    # ------------------------------------------------------------------ traitement
    def _options(self):
        crop = CROP_MODES[[self.tr(*CROP_LABELS[k]) for k in CROP_MODES].index(self.crop_var.get())] \
            if self.crop_var.get() in [self.tr(*CROP_LABELS[k]) for k in CROP_MODES] else "auto"
        opts = {"crop_mode": crop}
        if not self.auto_var.get():
            opts.update(contrast=float(self.contrast.get()), saturation=float(self.saturation.get()),
                        brightness=float(self.brightness.get()), black_threshold=int(self.black.get()),
                        cleanup_power=float(self.cleanup.get()), color_count=int(self.colors.get()),
                        pixel_perfect=bool(self.pp.get()))
        return crop, opts

    def reprocess(self):
        if self.src is None or self.busy:
            return
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
                gif = gc.encode_frames(frames, src.durations, plan.settings)
                score = gc.dq.evaluate_frames(frames, src.durations)
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
        if err is not None:
            self.status.set(str(err))
            return
        self.plan, self.result_frames, self.result_durations, self.gif_bytes = plan, frames, list(self.src.durations), gif
        layout = {"native": "d'origine", "fit": "bandes noires si besoin", "fill": "recadré plein écran",
                  "follow": "suivi du sujet"}.get(plan.layout, plan.layout)
        extra = ""
        if plan.follow:
            extra = f" (zoom ×{plan.follow['d']}, sujet gardé à {int(plan.follow['coverage'] * 100)} %)"
        self.status.set(self.tr("gif_result", "Cadrage : {layout}{extra} — note {score}/100 ({rating}) — {kb} Ko",
                                layout=layout, extra=extra, score=score.score, rating=score.rating,
                                kb=max(1, len(gif) // 1024)))
        self.btn_export.configure(state=tk.NORMAL)
        self.btn_lb.configure(state=tk.NORMAL if plan.layout in ("fill", "follow") else tk.DISABLED)
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
        for k, img in enumerate((self.src.frames[i], self.result_frames[i])):
            c = self.cv[k]
            if k == 0:
                w, h = img.size
                s = min(520 / w, 150 / h)
                pic = img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.BILINEAR)
            else:
                pic = DMDEngine.render_led_style(img, scale=4, led_ratio=0.525, glow=True,
                                                 brightness=self.app.led_brightness_var.get())
            self._photos[k] = ImageTk.PhotoImage(pic)
            c.delete("all")
            c.create_image(260, 75, image=self._photos[k])
        self._idx = (i + 1) % len(self.result_frames)
        self._job = self.root.after(max(20, int(self.src.durations[i])), self._play)

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
            self._save(gc.encode_frames(frames, self.src.durations, plan.settings), "_dmd_bandes")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("GIF", str(e))
