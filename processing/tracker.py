"""
tracker.py — Suivi de fibres entre frames consécutives (IDs stables).

Principe :
  • Chaque fibre détectée est associée au track le plus proche (distance centroïde).
  • Un track n'est "confirmé" (retourné à l'UI) qu'après MIN_AGE frames consécutives
    → élimine les faux positifs fugaces (bruit, reflets).
  • Un track disparu depuis MAX_MISSED frames est supprimé.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from analysis.fiber_model import Fiber


@dataclass
class TrackedFiber:
    track_id: int
    fiber: Fiber
    age: int = 1      # frames consécutives avec détection
    missed: int = 0   # frames consécutives SANS détection


class FiberTracker:
    """
    Associe les fibres détectées frame par frame via distance de centroïde.
    Une fibre n'est confirmée (et comptée) qu'après min_age frames consécutives.
    """

    def __init__(
        self,
        max_dist_px: float = 40.0,
        min_age: int = 3,
        max_missed: int = 5,
    ) -> None:
        self._next_id: int = 1
        self._tracks: Dict[int, TrackedFiber] = {}
        self.max_dist_px = max_dist_px
        self.min_age = min_age
        self.max_missed = max_missed

    # ------------------------------------------------------------------
    # API principale
    # ------------------------------------------------------------------

    def update(self, fibers: List[Fiber]) -> List[TrackedFiber]:
        """
        Intègre les nouvelles détections, met à jour les tracks existants,
        et retourne uniquement les tracks confirmés (age >= min_age).
        """
        unmatched = list(range(len(fibers)))
        matched_ids: set = set()

        # Associer chaque track existant à la détection la plus proche
        for tid, track in self._tracks.items():
            if not unmatched:
                break
            tx, ty = track.fiber.centroid
            best_dist = self.max_dist_px
            best_i = -1
            for i in unmatched:
                fx, fy = fibers[i].centroid
                dist = ((tx - fx) ** 2 + (ty - fy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_i = i
            if best_i >= 0:
                track.fiber = fibers[best_i]
                track.age += 1
                track.missed = 0
                unmatched.remove(best_i)
                matched_ids.add(tid)

        # Tracks non associés : incrémenter missed
        for tid, track in self._tracks.items():
            if tid not in matched_ids:
                track.missed += 1

        # Nouvelles détections sans track correspondant → nouveau track
        for i in unmatched:
            self._tracks[self._next_id] = TrackedFiber(
                track_id=self._next_id,
                fiber=fibers[i],
            )
            self._next_id += 1

        # Supprimer les tracks perdus depuis trop longtemps
        self._tracks = {
            tid: t for tid, t in self._tracks.items()
            if t.missed <= self.max_missed
        }

        # Retourner seulement les tracks confirmés (age >= min_age)
        return [t for t in self._tracks.values() if t.age >= self.min_age]

    def reset(self) -> None:
        """Remet le tracker à zéro (appeler à chaque démarrage de capture)."""
        self._tracks.clear()
        self._next_id = 1
