"""
app.py — Interface graphique principale (Tkinter + fenêtre OpenCV).

Fenêtres :
  • Tkinter  : panneau de contrôle (config, boutons, résultats)
  • OpenCV 1 : flux vidéo annoté (contours colorés + mesures de chaque fibre)
  • OpenCV 2 : image binaire issue du prétraitement (diagnostic)
"""

import logging
import threading
from typing import List, Optional, Union

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk

from analysis.analyzer import (
    classify_fibers,
    compute_density,
    compute_stats,
    count_fibers,
)
from analysis.fiber_model import Fiber
from capture.ip_camera import IPCamera
from processing.detector import annotate_frame, detect_fibers
from processing.preprocessor import preprocess
from processing.tracker import FiberTracker
import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Palette de couleurs (thème sombre)
# ---------------------------------------------------------------------------
BG        = "#1e1e2e"
FG        = "#cdd6f4"
ACCENT    = "#89b4fa"
GREEN     = "#a6e3a1"
ORANGE    = "#fab387"
RED_LIGHT = "#f38ba8"
PANEL_BG  = "#313244"
ENTRY_BG  = "#45475a"
MUTED     = "#a6adc8"
SUBTLE    = "#585b70"


class FiberApp(tk.Tk):
    """Fenêtre principale de l'application de comptage de fibres de bananier."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Comptage Fibres de Bananier")
        self.configure(bg=BG)
        self.resizable(False, False)

        # --- État interne ---------------------------------------------------
        self._running:    bool                = False
        self._camera:     Optional[IPCamera]  = None
        self._thread:     Optional[threading.Thread] = None
        self._last_frame: Optional[np.ndarray] = None
        self._tracker = FiberTracker(
            max_dist_px=config.TRACKER_MAX_DIST_PX,
            min_age=config.TRACKER_MIN_AGE,
            max_missed=config.TRACKER_MAX_MISSED,
        )

        # --- Variables Tkinter (configuration) ------------------------------
        # Accepte un entier (index webcam) ou une URL (caméra IP)
        self._camera_url    = tk.StringVar(value=str(config.CAMERA_SOURCE))
        self._pixels_per_cm = tk.DoubleVar(value=config.PIXELS_PER_CM)
        self._mass_g        = tk.DoubleVar(value=0.0)

        # --- Variables Tkinter (résultats) -----------------------------------
        self._var_count    = tk.StringVar(value="—")
        self._var_short    = tk.StringVar(value="—")
        self._var_medium   = tk.StringVar(value="—")
        self._var_long     = tk.StringVar(value="—")
        self._var_l_moy    = tk.StringVar(value="—")
        self._var_d_moy    = tk.StringVar(value="—")
        self._var_v_moy    = tk.StringVar(value="—")
        self._var_m_fibre  = tk.StringVar(value="—")
        self._var_rho      = tk.StringVar(value="—")
        self._var_l_range  = tk.StringVar(value="—")
        self._var_d_range  = tk.StringVar(value="—")
        self._var_status   = tk.StringVar(value="Arrete")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================================
    # Construction de l'interface
    # =========================================================================

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 5}

        # ---- Titre ----------------------------------------------------------
        tk.Label(
            self, text="Analyse des Fibres de Bananier",
            font=("Segoe UI", 14, "bold"), bg=BG, fg=ACCENT,
        ).pack(pady=(12, 2))
        tk.Label(
            self, text="OpenCV  |  Python  |  iVCam Desktop (iPhone)",
            font=("Segoe UI", 8), bg=BG, fg=SUBTLE,
        ).pack(pady=(0, 8))

        # ---- Configuration --------------------------------------------------
        cfg = tk.LabelFrame(
            self, text="  Configuration  ",
            bg=PANEL_BG, fg=FG, font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove",
        )
        cfg.pack(fill="x", **pad)

        self._entry_row(cfg, "Source caméra  :",   self._camera_url,    width=38)
        self._entry_row(cfg, "Pixels / cm   :",    self._pixels_per_cm, width=12)
        self._entry_row(cfg, "Masse totale (g) :", self._mass_g,        width=12)

        # Aide source caméra
        tk.Label(
            cfg,
            text="iVCam Desktop = 0 (ou 1 si webcam intégrée présente)  |  http://... = IP",
            font=("Segoe UI", 7, "italic"), bg=PANEL_BG, fg=SUBTLE,
        ).grid(row=cfg.grid_size()[1], column=0, columnspan=2,
               sticky="w", padx=10, pady=(0, 2))
        # Aide calibration
        tk.Label(
            cfg,
            text="Astuce : placez une regle de 10 cm pour mesurer pixels/cm.",
            font=("Segoe UI", 7, "italic"), bg=PANEL_BG, fg=SUBTLE,
        ).grid(row=cfg.grid_size()[1], column=0, columnspan=2,
               sticky="w", padx=10, pady=(0, 4))

        # ---- Boutons --------------------------------------------------------
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=8)

        self._btn_start = self._make_btn(
            btn_frame, "  Demarrer", self._start, "#40a02b", "#2d7620",
        )
        self._btn_stop = self._make_btn(
            btn_frame, "  Arreter", self._stop, "#e64553", "#a0243a",
            state="disabled",
        )
        self._btn_capture = self._make_btn(
            btn_frame, "  Capturer", self._capture_frame, "#7287fd", "#5468f5",
            state="disabled",
        )
        for btn in (self._btn_start, self._btn_stop, self._btn_capture):
            btn.pack(side="left", padx=6)

        # ---- Résultats comptage ---------------------------------------------
        res = tk.LabelFrame(
            self, text="  Résultats  ",
            bg=PANEL_BG, fg=FG, font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove",
        )
        res.pack(fill="x", **pad)

        self._result_row(res, "Fibres detectees :", self._var_count,  GREEN,
                         font=("Segoe UI", 12, "bold"))
        self._result_row(res, "Court  (< 2 cm)  :", self._var_short,  "#f9e2af")
        self._result_row(res, "Moyen  (2-5 cm)  :", self._var_medium, ORANGE)
        self._result_row(res, "Long   (> 5 cm)  :", self._var_long,   RED_LIGHT)

        ttk.Separator(res, orient="horizontal").grid(
            row=res.grid_size()[1], column=0, columnspan=2,
            sticky="ew", padx=6, pady=4,
        )

        self._result_row(res, "Longueur moy. (cm) :", self._var_l_moy,   FG)
        self._result_row(res, "Plage L (min-max)  :", self._var_l_range, MUTED)
        self._result_row(res, "Diametre moy. (cm) :", self._var_d_moy,   FG)
        self._result_row(res, "Plage d (min-max)  :", self._var_d_range, MUTED)
        self._result_row(res, "Volume moy. (cm3)  :", self._var_v_moy,   FG)
        self._result_row(res, "Masse / fibre (g)  :", self._var_m_fibre, FG)

        ttk.Separator(res, orient="horizontal").grid(
            row=res.grid_size()[1], column=0, columnspan=2,
            sticky="ew", padx=6, pady=4,
        )

        self._result_row(
            res, "Densite rho (g/cm3) :", self._var_rho, ACCENT,
            font=("Segoe UI", 12, "bold"),
        )

        # ---- Formule affichée -----------------------------------------------
        formula_frame = tk.Frame(self, bg=BG)
        formula_frame.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(
            formula_frame,
            text="rho = m / (N x pi x (d/2)^2 x L)",
            font=("Courier New", 9), bg=BG, fg=SUBTLE,
        ).pack()

        # ---- Barre de statut ------------------------------------------------
        status_bar = tk.Frame(self, bg="#11111b")
        status_bar.pack(fill="x", side="bottom", pady=(6, 0))
        tk.Label(
            status_bar, textvariable=self._var_status,
            bg="#11111b", fg=MUTED, font=("Segoe UI", 8), anchor="w", padx=8,
        ).pack(fill="x")

    # =========================================================================
    # Widgets helpers
    # =========================================================================

    def _entry_row(self, parent: tk.Widget, label: str,
                   variable: tk.Variable, width: int = 20) -> None:
        r = parent.grid_size()[1]
        tk.Label(
            parent, text=label, bg=PANEL_BG, fg=FG,
            font=("Segoe UI", 9), anchor="e", width=22,
        ).grid(row=r, column=0, sticky="e", padx=(8, 4), pady=3)
        tk.Entry(
            parent, textvariable=variable, width=width,
            bg=ENTRY_BG, fg=FG, insertbackground=FG,
            relief="flat", font=("Segoe UI", 9),
        ).grid(row=r, column=1, sticky="w", padx=(0, 8), pady=3)

    def _result_row(self, parent: tk.Widget, label: str,
                    variable: tk.StringVar, color: str = FG,
                    font: tuple = ("Segoe UI", 10)) -> None:
        r = parent.grid_size()[1]
        tk.Label(
            parent, text=label, bg=PANEL_BG, fg=MUTED,
            font=("Segoe UI", 9), anchor="e", width=24,
        ).grid(row=r, column=0, sticky="e", padx=(8, 4), pady=2)
        tk.Label(
            parent, textvariable=variable, bg=PANEL_BG, fg=color,
            font=font, anchor="w",
        ).grid(row=r, column=1, sticky="w", padx=(0, 8), pady=2)

    @staticmethod
    def _make_btn(parent: tk.Widget, text: str, cmd, bg: str,
                  active_bg: str, state: str = "normal") -> tk.Button:
        return tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg="white", font=("Segoe UI", 9, "bold"),
            activebackground=active_bg, relief="flat",
            padx=14, pady=5, state=state,
        )

    # =========================================================================
    # Contrôle de la capture
    # =========================================================================

    def _start(self) -> None:
        """Valide la configuration, ouvre la caméra et lance le thread de capture."""
        raw = self._camera_url.get().strip()
        if not raw:
            messagebox.showerror("Erreur", "Veuillez entrer une source caméra (0, 1 ou une URL).")
            return

        # Convertit en entier si la saisie est un index numérique (ex: "0", "1")
        source: Union[str, int] = int(raw) if raw.lstrip('-').isdigit() else raw

        try:
            ppc = float(self._pixels_per_cm.get())
            if ppc <= 0:
                raise ValueError("pixels_per_cm doit être positif")
        except (ValueError, tk.TclError):
            messagebox.showerror("Erreur", "Pixels/cm doit être un nombre positif.")
            return

        self._camera = IPCamera(source)
        if not self._camera.connect():
            if isinstance(source, int):
                msg = (
                    f"Impossible d'ouvrir la caméra index {source}.\n\n"
                    "Vérifications :\n"
                    "  • iVCam Desktop (PC) est lancé\n"
                    "  • L'app iVCam est ouverte sur l'iPhone\n"
                    "  • iPhone et PC sur le même réseau Wi-Fi\n"
                    "  • Essayez index 1 si une webcam intégrée occupe le 0."
                )
            else:
                msg = (
                    f"Impossible de se connecter à :\n{source}\n\n"
                    "Vérifiez que l'URL est correcte.\n"
                    "Format : http://192.168.x.x:8080/video"
                )
            messagebox.showerror("Connexion échouée", msg)
            self._camera = None
            return

        self._tracker.reset()
        self._last_frame = None
        self._running = True
        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._btn_capture.config(state="normal")
        self._var_status.set(f"En cours — source: {source}")

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _stop(self) -> None:
        """Arrête la capture et libère les ressources."""
        self._running = False
        if self._camera:
            self._camera.release()
            self._camera = None
        cv2.destroyAllWindows()
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled")
        self._btn_capture.config(state="disabled")
        self._var_status.set("Arrete")

    def _on_close(self) -> None:
        self._stop()
        self.destroy()

    # =========================================================================
    # Boucle de capture (thread secondaire)
    # =========================================================================

    def _capture_loop(self) -> None:
        """Lit les images en continu, les traite et met à jour l'affichage."""
        ppc = float(self._pixels_per_cm.get())

        while self._running:
            ret, frame = self._camera.read_frame()

            if not ret or frame is None:
                self.after(0, self._var_status.set, "Flux perdu — reconnexion...")
                continue

            # --- Détection écran d'attente iVCam (image statique) -----------
            if self._last_frame is not None:
                diff = cv2.absdiff(frame, self._last_frame).mean()
                if diff < 0.05:
                    self.after(
                        0, self._var_status.set,
                        "iVCam : en attente de l'iPhone — ouvrez l'app iVCam sur l'iPhone",
                    )
                    self._last_frame = frame
                    continue
            self._last_frame = frame

            source = self._camera_url.get().strip()
            self.after(0, self._var_status.set, f"Actif — source: {source}")

            # --- Traitement --------------------------------------------------
            binary   = preprocess(frame)
            fibers   = detect_fibers(binary, pixels_per_cm=ppc)
            tracked  = self._tracker.update(fibers)
            t_fibers = [t.fiber    for t in tracked]
            t_ids    = [t.track_id for t in tracked]
            display  = annotate_frame(frame, t_fibers, track_ids=t_ids)

            # --- Mise à jour Tkinter (thread-safe via after) -----------------
            self.after(0, self._update_results, t_fibers)

            # --- Affichage OpenCV --------------------------------------------
            cv2.imshow("Fibres de Bananier — Flux annote", display)
            cv2.imshow("Pretraitement (binaire)", binary)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                self.after(0, self._stop)
                break

        cv2.destroyAllWindows()

    # =========================================================================
    # Mise à jour des labels de résultats (thread principal)
    # =========================================================================

    def _update_results(self, fibers: List[Fiber]) -> None:
        try:
            mass = float(self._mass_g.get())
        except (ValueError, tk.TclError):
            mass = 0.0

        n       = count_fibers(fibers)
        classes = classify_fibers(fibers)
        stats   = compute_stats(fibers)
        density = compute_density(mass, fibers)

        self._var_count.set(str(n))
        self._var_short.set(str(len(classes["Court"])))
        self._var_medium.set(str(len(classes["Moyen"])))
        self._var_long.set(str(len(classes["Long"])))

        if n > 0:
            self._var_l_moy.set(f"{stats['L_moy']:.4f} cm")
            self._var_d_moy.set(f"{stats['d_moy']:.5f} cm")
            self._var_l_range.set(f"{stats['L_min']:.3f}  —  {stats['L_max']:.3f} cm")
            self._var_d_range.set(f"{stats['d_min']:.4f}  —  {stats['d_max']:.4f} cm")
            self._var_v_moy.set(f"{density['V_moy_cm3']:.7f} cm3")
        else:
            for var in (self._var_l_moy, self._var_d_moy,
                        self._var_l_range, self._var_d_range, self._var_v_moy):
                var.set("—")

        if mass > 0 and n > 0:
            self._var_m_fibre.set(f"{density['m_fibre_g']:.7f} g")
            self._var_rho.set(f"{density['rho']:.5f} g/cm3")
        else:
            self._var_m_fibre.set("— (entrez la masse)")
            self._var_rho.set("— (masse non saisie)")

    # =========================================================================
    # Capture d'une image fixe
    # =========================================================================

    def _capture_frame(self) -> None:
        """Sauvegarde l'image courante sur disque."""
        if self._camera is None:
            return

        ret, frame = self._camera.read_frame()
        if ret and frame is not None:
            path = "capture_fibre.png"
            cv2.imwrite(path, frame)
            self._var_status.set(f"Image sauvegardee -> {path}")
            messagebox.showinfo("Capture", f"Image sauvegardée :\n{path}")
        else:
            messagebox.showwarning("Capture", "Impossible de lire une image.")
