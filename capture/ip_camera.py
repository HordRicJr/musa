"""
ip_camera.py — Capture de flux vidéo depuis une caméra (Vicam Desktop, webcam, IP).

Supporte :
  • Vicam Desktop / webcam locale  : index entier  (0, 1, 2…)
  • HTTP MJPEG (Vicam mobile/IP)   : "http://IP:port/video"
  • RTSP                           : "rtsp://IP:port/"
"""

import logging
import time
from typing import Optional, Tuple, Union

import cv2
import numpy as np

from config import CAMERA_RECONNECT_DELAY, CAMERA_TIMEOUT

logger = logging.getLogger(__name__)


class IPCamera:
    """Gère la connexion et la lecture d'images depuis n'importe quelle source vidéo."""

    def __init__(self, source: Union[str, int]) -> None:
        # Normalise : si on reçoit la chaîne "0", "1"… on la convertit en int
        if isinstance(source, str) and source.strip().lstrip('-').isdigit():
            source = int(source.strip())
        self.source = source
        self._cap: Optional[cv2.VideoCapture] = None
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Ouvre la connexion vers la source vidéo. Retourne True si succès."""
        if self._cap is not None:
            self._cap.release()

        # iVCam (et les webcams Windows) s'enregistrent comme périphérique DirectShow.
        # MSMF (backend par défaut d'OpenCV sur Windows) échoue avec iVCam (-1072875772).
        if isinstance(self.source, int):
            self._cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        else:
            self._cap = cv2.VideoCapture(self.source)
            self._cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, CAMERA_TIMEOUT * 1000)
        self._connected = self._cap.isOpened()

        if self._connected:
            logger.info("Caméra connectée : %s", self.source)
        else:
            logger.warning("Impossible de se connecter à : %s", self.source)

        return self._connected

    def reconnect(self) -> bool:
        """Tente une reconnexion après une courte pause."""
        logger.info("Reconnexion dans %.1f s… (source: %s)", CAMERA_RECONNECT_DELAY, self.source)
        time.sleep(CAMERA_RECONNECT_DELAY)
        return self.connect()

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Lit la prochaine image du flux vidéo.

        Retourne (True, frame) en cas de succès,
                 (False, None)  en cas d'échec persistant.

        Tente automatiquement une reconnexion si la lecture échoue.
        """
        if not self._connected or self._cap is None:
            if not self.reconnect():
                return False, None

        ret, frame = self._cap.read()

        if not ret:
            logger.warning("Lecture impossible — tentative de reconnexion…")
            if self.reconnect():
                ret, frame = self._cap.read()
                if ret:
                    return True, frame
            return False, None

        return True, frame

    # ------------------------------------------------------------------
    # Libération
    # ------------------------------------------------------------------

    def release(self) -> None:
        """Libère les ressources de capture vidéo."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._connected = False
        logger.info("Caméra libérée. (source: %s)", self.source)

    @property
    def is_connected(self) -> bool:
        return self._connected
