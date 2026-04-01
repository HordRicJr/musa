"""
fiber_model.py — Modèle de données représentant une fibre de bananier mesurée.
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


@dataclass
class Fiber:
    """
    Représente une fibre individuelle détectée et mesurée dans une image.

    Attributs
    ---------
    length_cm   : longueur de la fibre (axe majeur de l'ellipse ajustée), en cm.
    diameter_cm : diamètre de la fibre (axe mineur de l'ellipse ajustée), en cm.
    area_cm2    : aire du contour détecté, en cm².
    centroid    : position (x, y) du centre de la fibre dans l'image (pixels).
    contour     : tableau NumPy du contour brut (non affiché en repr).
    ellipse     : tuple retourné par cv2.fitEllipse (non affiché en repr).
    """

    length_cm:   float
    diameter_cm: float
    area_cm2:    float
    centroid:    Tuple[int, int]
    contour:     Optional[np.ndarray] = field(default=None, repr=False)
    ellipse:     Optional[tuple]      = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Propriétés calculées
    # ------------------------------------------------------------------

    @property
    def volume_cm3(self) -> float:
        """
        Volume approximé de la fibre en supposant un modèle cylindrique :

            V = π × (d / 2)² × L
        """
        return math.pi * (self.diameter_cm / 2.0) ** 2 * self.length_cm

    @property
    def category(self) -> str:
        """Catégorie de longueur (Court / Moyen / Long)."""
        from config import SHORT_MAX_CM, MEDIUM_MAX_CM

        if self.length_cm < SHORT_MAX_CM:
            return "Court"
        if self.length_cm < MEDIUM_MAX_CM:
            return "Moyen"
        return "Long"
