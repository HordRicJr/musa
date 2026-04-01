"""
main.py — Point d'entrée du prototype de comptage de fibres de bananier.

Lancement :
    python main.py

Quitter :
    • Bouton "Arreter" dans l'interface Tkinter
    • Touche 'q' dans la fenêtre OpenCV
"""

import logging
import sys

from ui.app import FiberApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(name)s : %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)


def main() -> None:
    try:
        app = FiberApp()
        app.mainloop()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Arret demande (Ctrl+C).")


if __name__ == "__main__":
    main()
