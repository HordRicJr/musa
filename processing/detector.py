"""
detector.py — Détection des fibres dans une image binaire et extraction des mesures.

Pour chaque contour valide, un rectangle orienté (minAreaRect) est ajusté :
  • longueur  (côté long)   → L en cm
  • diamètre  (côté court)  → d en cm
  • centroïde (x, y)        → position dans l'image (pixels)

minAreaRect est plus robuste que fitEllipse : fonctionne avec tous les
contours (pas besoin de ≥5 points) et donne L et d directement.
"""

import logging
from typing import List, Optional

import cv2
import numpy as np

from analysis.fiber_model import Fiber
from config import (
    COLOR_LONG,
    COLOR_MEDIUM,
    COLOR_SHORT,
    COLOR_TEXT,
    FONT_SCALE,
    LINE_THICKNESS,
    MAX_CONTOUR_AREA,
    MEDIUM_MAX_CM,
    MIN_ASPECT_RATIO,
    MIN_CONTOUR_AREA,
    PIXELS_PER_CM,
    SHORT_MAX_CM,
)

logger = logging.getLogger(__name__)


def detect_fibers(
    binary: np.ndarray,
    pixels_per_cm: float = PIXELS_PER_CM,
) -> List[Fiber]:
    """
    Détecte les fibres dans une image binaire via minAreaRect.

    Filtres :
      • Aire entre MIN_CONTOUR_AREA et MAX_CONTOUR_AREA
      • Rapport d'aspect (côté long / côté court) ≥ MIN_ASPECT_RATIO
        → exclut les formes rondes (souris, poussières)
    """
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    fibers: List[Fiber] = []

    for contour in contours:
        area_px = cv2.contourArea(contour)

        # --- Filtre aire ------------------------------------------------
        if not (MIN_CONTOUR_AREA <= area_px <= MAX_CONTOUR_AREA):
            continue

        # --- Rectangle orienté minimal (L = côté long, d = côté court) --
        rect = cv2.minAreaRect(contour)
        (cx, cy), (w_px, h_px), angle = rect

        major_px = max(w_px, h_px)
        minor_px = min(w_px, h_px)

        if minor_px < 1.0:
            continue

        # --- Filtre rapport d'aspect ------------------------------------
        if (major_px / minor_px) < MIN_ASPECT_RATIO:
            continue

        # --- Conversion pixels → cm -------------------------------------
        length_cm   = round(major_px / pixels_per_cm, 3)
        diameter_cm = round(minor_px / pixels_per_cm, 4)
        area_cm2    = round(area_px  / (pixels_per_cm ** 2), 5)

        fibers.append(
            Fiber(
                length_cm=length_cm,
                diameter_cm=diameter_cm,
                area_cm2=area_cm2,
                centroid=(int(cx), int(cy)),
                contour=contour,
                ellipse=rect,   # rect stocké dans le champ ellipse
            )
        )

    return fibers


def annotate_frame(
    frame: np.ndarray,
    fibers: List[Fiber],
    track_ids: Optional[List[int]] = None,
) -> np.ndarray:
    """
    Dessine sur l'image les contours et mesures de chaque fibre détectée.

    Code couleur :
      • Jaune  — fibre courte (< SHORT_MAX_CM)
      • Orange — fibre moyenne
      • Rouge  — fibre longue (≥ MEDIUM_MAX_CM)

    track_ids : si fourni, utilise ces IDs stables au lieu de la numérotation locale.
    """
    annotated = frame.copy()

    for idx, fiber in enumerate(fibers, start=1):
        # Couleur selon la catégorie de longueur
        if fiber.length_cm < SHORT_MAX_CM:
            color = COLOR_SHORT
        elif fiber.length_cm < MEDIUM_MAX_CM:
            color = COLOR_MEDIUM
        else:
            color = COLOR_LONG

        # Rectangle orienté (minAreaRect → boxPoints)
        if fiber.ellipse is not None:
            box = cv2.boxPoints(fiber.ellipse)
            box = np.intp(box)
            cv2.drawContours(annotated, [box], 0, color, LINE_THICKNESS)

        # Étiquette : ID stable (tracker) + longueur + diamètre
        label_id = track_ids[idx - 1] if track_ids is not None else idx
        label = f"#{label_id} L={fiber.length_cm:.1f}cm  d={fiber.diameter_cm:.2f}cm"
        x, y = fiber.centroid
        cv2.putText(
            annotated,
            label,
            (max(0, x - 55), max(14, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            FONT_SCALE,
            COLOR_TEXT,
            1,
            cv2.LINE_AA,
        )

    # Compteur total en haut à gauche
    cv2.putText(
        annotated,
        f"Fibres detectees : {len(fibers)}",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (50, 255, 50),
        2,
        cv2.LINE_AA,
    )

    return annotated
