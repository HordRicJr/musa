"""
analyzer.py — Comptage, classification et calcul de densité des fibres de bananier.

Formule de densité (modèle cylindrique) :

    ρ = m / (N × π × (d_moy / 2)² × L_moy)

Avec :
  m     : masse totale des fibres (g), saisie par l'utilisateur
  N     : nombre de fibres comptées automatiquement
  d_moy : diamètre moyen (cm) mesuré par fitEllipse (axe mineur)
  L_moy : longueur moyenne (cm) mesurée par fitEllipse (axe majeur)
"""

import math
from typing import Dict, List

from analysis.fiber_model import Fiber
from config import MEDIUM_MAX_CM, SHORT_MAX_CM


# ---------------------------------------------------------------------------
# Comptage
# ---------------------------------------------------------------------------

def count_fibers(fibers: List[Fiber]) -> int:
    """Retourne le nombre total de fibres détectées."""
    return len(fibers)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_fibers(fibers: List[Fiber]) -> Dict[str, List[Fiber]]:
    """
    Répartit les fibres en trois catégories selon leur longueur.

    Seuils configurables dans config.py :
      • Court  : length_cm < SHORT_MAX_CM
      • Moyen  : SHORT_MAX_CM ≤ length_cm < MEDIUM_MAX_CM
      • Long   : length_cm ≥ MEDIUM_MAX_CM

    Retourne un dict {"Court": [...], "Moyen": [...], "Long": [...]}.
    """
    classes: Dict[str, List[Fiber]] = {"Court": [], "Moyen": [], "Long": []}
    for f in fibers:
        classes[f.category].append(f)
    return classes


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

def compute_stats(fibers: List[Fiber]) -> Dict[str, float]:
    """
    Calcule les statistiques descriptives de la liste de fibres.

    Retourne
    --------
    dict avec les clés :
      • L_moy    : longueur moyenne (cm)
      • d_moy    : diamètre moyen (cm)
      • aire_moy : aire contour moyenne (cm²)
      • L_min    : longueur minimale (cm)
      • L_max    : longueur maximale (cm)
      • d_min    : diamètre minimal (cm)
      • d_max    : diamètre maximal (cm)
    """
    if not fibers:
        return {
            "L_moy": 0.0, "d_moy": 0.0, "aire_moy": 0.0,
            "L_min": 0.0, "L_max": 0.0, "d_min": 0.0, "d_max": 0.0,
        }

    n = len(fibers)
    lengths   = [f.length_cm   for f in fibers]
    diameters = [f.diameter_cm for f in fibers]
    areas     = [f.area_cm2    for f in fibers]

    return {
        "L_moy":    round(sum(lengths)   / n, 4),
        "d_moy":    round(sum(diameters) / n, 5),
        "aire_moy": round(sum(areas)     / n, 5),
        "L_min":    round(min(lengths),   4),
        "L_max":    round(max(lengths),   4),
        "d_min":    round(min(diameters), 5),
        "d_max":    round(max(diameters), 5),
    }


# ---------------------------------------------------------------------------
# Densité physique
# ---------------------------------------------------------------------------

def compute_density(mass_g: float, fibers: List[Fiber]) -> Dict[str, float]:
    """
    Calcule la densité physique d'une fibre individuelle (g/cm³).

    Modèle : chaque fibre est assimilée à un cylindre.

        V_moy  = π × (d_moy / 2)² × L_moy          [cm³]
        V_tot  = V_moy × N                            [cm³]
        m_fib  = m / N                                [g]
        ρ      = m / V_tot                            [g/cm³]

    Paramètres
    ----------
    mass_g : float
        Masse totale des fibres en grammes (saisie par l'utilisateur).
    fibers : List[Fiber]
        Liste des fibres détectées dans l'image courante.

    Retourne
    --------
    dict avec les clés :
      • rho        : densité (g/cm³), 0.0 si calcul impossible
      • V_moy_cm3  : volume moyen d'une fibre (cm³)
      • m_fibre_g  : masse estimée d'une fibre (g)
      • V_tot_cm3  : volume total estimé (cm³)
    """
    n = len(fibers)
    empty = {"rho": 0.0, "V_moy_cm3": 0.0, "m_fibre_g": 0.0, "V_tot_cm3": 0.0}

    if n == 0 or mass_g <= 0:
        return empty

    stats = compute_stats(fibers)
    L = stats["L_moy"]
    d = stats["d_moy"]

    if L <= 0 or d <= 0:
        return empty

    V_moy   = math.pi * (d / 2.0) ** 2 * L   # volume moyen d'une fibre (cm³)
    V_total = V_moy * n                        # volume total (cm³)
    m_fibre = mass_g / n                       # masse par fibre (g)
    rho     = mass_g / V_total                 # densité (g/cm³)

    return {
        "rho":       round(rho,     5),
        "V_moy_cm3": round(V_moy,   7),
        "m_fibre_g": round(m_fibre, 7),
        "V_tot_cm3": round(V_total, 5),
    }
