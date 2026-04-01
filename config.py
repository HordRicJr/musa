# =============================================================================
# config.py — Configuration du prototype : Comptage Fibres de Bananier
# =============================================================================

# --- Caméra (Vicam Desktop / webcam / IP) ------------------------------------
# Vicam Desktop (iPhone comme webcam virtuelle Windows) : entier  → 0, 1, 2…
# Flux IP HTTP MJPEG (Vicam mobile)                    : string  → "http://192.168.x.x:8080/video"
# Flux RTSP                                            : string  → "rtsp://192.168.x.x:8554/"
#
# Par défaut : 0 = première caméra détectée par Windows (Vicam Desktop / webcam intégrée)
CAMERA_SOURCE = 0              # int (index) OU str (URL)
CAMERA_RECONNECT_DELAY = 2.0   # secondes avant chaque tentative de reconnexion
CAMERA_TIMEOUT = 5.0           # délai d'attente à l'ouverture (secondes)

# --- Calibration -------------------------------------------------------------
# Nombre de pixels correspondant à 1 cm à la distance de travail habituelle.
# À mesurer une fois avec une règle placée dans le champ de vue.
PIXELS_PER_CM = 50.0
REFERENCE_LENGTH_CM = 10.0     # longueur de l'objet de référence (mode calibration)

# --- Détection des contours --------------------------------------------------
MIN_CONTOUR_AREA = 200         # aire min (px²) — adapté aux fibres fines haute résolution
MAX_CONTOUR_AREA = 80000       # aire max (exclut les très grands artefacts)
MIN_ASPECT_RATIO = 3.0         # ratio L/d ≥ 3 → fibres allongées ; souris ratio ~1 → exclue

# --- Prétraitement (Lab + Canny) ---------------------------------------------
# Canal L de l'espace Lab = luminosité pure (insensible à la couleur des fibres)
# Filtre bilatéral préserve les bords nets → mesure précise du diamètre d
# Ajuster CANNY_LOW/HIGH selon l'éclairage de votre setup
CANNY_LOW  = 50                # seuil bas  (baisser si fibres manquées)
CANNY_HIGH = 150               # seuil haut (augmenter si trop de bruit)

# --- Classification des fibres (seuils en cm) --------------------------------
SHORT_MAX_CM  = 2.0            # longueur < SHORT_MAX_CM  → "Court"
MEDIUM_MAX_CM = 5.0            # longueur < MEDIUM_MAX_CM → "Moyen" ; sinon "Long"

# --- Suivi inter-frames (tracker) --------------------------------------------
TRACKER_MAX_DIST_PX = 40    # distance max centroïde (px) pour associer deux détections
TRACKER_MIN_AGE     = 3     # frames consécutives avant de confirmer une fibre
TRACKER_MAX_MISSED  = 5     # frames sans détection avant suppression du track

# --- Affichage (couleurs BGR) -------------------------------------------------
COLOR_SHORT   = (0, 255, 255)  # jaune
COLOR_MEDIUM  = (0, 165, 255)  # orange
COLOR_LONG    = (0, 0, 255)    # rouge
COLOR_TEXT    = (255, 255, 255)
FONT_SCALE    = 0.45
LINE_THICKNESS = 2
