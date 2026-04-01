"""
preprocessor.py — Pipeline Lab+Canny pour détection de fibres fines (iPhone/Vicam).

Pipeline :
  1. BGR -> espace Lab, canal L (luminosité pure, insensible à la couleur)
  2. Filtre bilatéral — conserve les bords nets (important pour mesurer d)
  3. Canny — détecte les contours des fibres (seuils ajustables dans config.py)
  4. Dilatation — solidifie les contours pour findContours
  5. Fermeture morphologique — relie les segments de fibre interrompus

Recommandation physique : placer les fibres sur un fond NOIR MAT ou BLEU FONCÉ
et utiliser un éclairage diffus sans ombres portées.
"""

import cv2
import numpy as np

from config import CANNY_LOW, CANNY_HIGH


def preprocess(frame: np.ndarray) -> np.ndarray:
    """
    Transforme une image BGR en image binaire (contours des fibres en blanc).

    Le canal L de l'espace Lab isole la luminosité indépendamment des couleurs,
    ce qui rend la détection robuste quelle que soit la teinte des fibres.
    """
    # 1. Canal L — luminosité uniquement (pas sensible à la couleur des fibres)
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2Lab)
    l_channel, _, _ = cv2.split(lab)

    # 2. Filtre bilatéral : lisse les textures, préserve les bords fins des fibres
    blurred = cv2.bilateralFilter(l_channel, d=9, sigmaColor=75, sigmaSpace=75)

    # 3. Canny (seuils CANNY_LOW / CANNY_HIGH dans config.py)
    edges = cv2.Canny(blurred, CANNY_LOW, CANNY_HIGH)

    kernel = np.ones((3, 3), np.uint8)

    # 4. Dilatation légère — épaissit les contours pour findContours
    dilated = cv2.dilate(edges, kernel, iterations=1)

    # 5. Fermeture — relie les segments brisés d'une même fibre
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=2)

    return closed
