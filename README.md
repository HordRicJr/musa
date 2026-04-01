# Comptage & Analyse des Fibres de Bananier

Prototype de vision par ordinateur pour **compter, mesurer et calculer la densité** de fibres de bananier (*Musa*) en temps réel depuis un iPhone via **iVCam Desktop**.

---

## Sommaire

1. [Présentation](#présentation)
2. [Architecture du projet](#architecture-du-projet)
3. [Prérequis & Installation](#prérequis--installation)
4. [Configuration de la caméra (iVCam)](#configuration-de-la-caméra-ivcam)
5. [Lancement](#lancement)
6. [Interface Tkinter — panneau de contrôle](#interface-tkinter--panneau-de-contrôle)
7. [Fenêtres OpenCV](#fenêtres-opencv)
8. [Paramètres (`config.py`)](#paramètres-configpy)
9. [Pipeline de traitement](#pipeline-de-traitement)
10. [Tracker inter-frames](#tracker-inter-frames)
11. [Formule de densité](#formule-de-densité)
12. [Classification des fibres](#classification-des-fibres)
13. [Marges d'erreur](#marges-derreur)
14. [Structure des modules](#structure-des-modules)
15. [FAQ / Dépannage](#faq--dépannage)

---

## Présentation

Le système prend en entrée un flux vidéo live de fibres de bananier posées sur un fond contrasté, et produit en temps réel :

| Sortie | Description |
|---|---|
| **N** | Nombre de fibres détectées et confirmées |
| **L_moy** | Longueur moyenne des fibres (cm) |
| **d_moy** | Diamètre moyen des fibres (cm) |
| **ρ** | Densité apparente (g/cm³) — nécessite la saisie de la masse |
| **Affichage annoté** | Chaque fibre encadrée avec son ID stable, sa longueur et son diamètre |

---

## Architecture du projet

```
e:\musa\
│
├── main.py                    # Point d'entrée — lance l'app Tkinter
├── config.py                  # Tous les paramètres réglables
├── requirements.txt           # Dépendances Python
├── README.md                  # Ce fichier
│
├── capture/
│   └── ip_camera.py           # Connexion caméra (iVCam / webcam / IP)
│
├── processing/
│   ├── preprocessor.py        # Pipeline Lab + Canny → image binaire
│   ├── detector.py            # Détection des contours + mesures (minAreaRect)
│   └── tracker.py             # Tracker inter-frames (IDs stables, anti-bruit)
│
├── analysis/
│   ├── fiber_model.py         # Dataclass Fiber (L, d, V, catégorie)
│   └── analyzer.py            # Comptage, classification, stats, densité
│
└── ui/
    └── app.py                 # Interface Tkinter + boucle de capture (thread)
```

**Flux de données par frame :**

```
Caméra (iVCam)
    │
    ▼
ip_camera.read_frame()         → frame BGR
    │
    ▼
preprocessor.preprocess()      → image binaire (contours blancs sur fond noir)
    │
    ▼
detector.detect_fibers()       → liste de Fiber (brutes, non confirmées)
    │
    ▼
tracker.update()               → liste de TrackedFiber (confirmées, IDs stables)
    │
    ├──▶ detector.annotate_frame()   → fenêtre OpenCV annotée
    └──▶ analyzer.*()                → résultats Tkinter (N, L, d, ρ…)
```

---

## Prérequis & Installation

### Python

- Python **3.10+** (testé sur 3.14)
- Plateforme : **Windows** (requis pour iVCam Desktop + DirectShow)

### Dépendances

```
opencv-python
numpy
Pillow
```

### Installation

```powershell
# 1. Créer et activer l'environnement virtuel
python -m venv .venv
& .venv\Scripts\Activate.ps1

# 2. Installer les dépendances
pip install -r requirements.txt
```

---

## Configuration de la caméra (iVCam)

**iVCam Desktop** permet d'utiliser l'iPhone comme caméra virtuelle Windows (périphérique DirectShow).

### Étapes

1. Installer **iVCam Desktop** sur le PC : https://www.e2esoft.com/ivcam/
2. Installer l'app **iVCam** sur l'iPhone (App Store)
3. iPhone et PC sur le **même réseau Wi-Fi**
4. Ouvrir **iVCam Desktop** sur le PC **avant** de lancer `python main.py`
5. Ouvrir l'app **iVCam** sur l'iPhone → connexion automatique

### Index caméra

| Situation | Index à utiliser |
|---|---|
| Pas de webcam intégrée (PC fixe) | `0` |
| Webcam intégrée présente (laptop) | `1` (iVCam) ou essayer `0` et `1` |

> **Important :** OpenCV utilise le backend **DirectShow** (`CAP_DSHOW`) pour les sources entières.
> Le backend MSMF (défaut Windows) est incompatible avec iVCam et produit l'erreur `-1072875772`. Ce comportement est corrigé automatiquement dans le code.

### Écran d'attente iVCam

Quand l'iPhone n'est pas connecté, iVCam affiche un écran statique (icône téléphone).
L'app détecte cet état (différence inter-frames < 0.05) et affiche en barre de statut :

```
iVCam : en attente de l'iPhone — ouvrez l'app iVCam sur l'iPhone
```

---

## Lancement

```powershell
# Depuis le dossier e:\musa, venv actif
python main.py
```

**Quitter :**
- Bouton **Arrêter** dans le panneau Tkinter
- Touche **`q`** dans la fenêtre OpenCV
- **Ctrl+C** dans le terminal

---

## Interface Tkinter — panneau de contrôle

```
┌─────────────────────────────────────────────┐
│      Analyse des Fibres de Bananier         │
│  OpenCV  |  Python  |  iVCam Desktop        │
├─────────────────────────────────────────────┤
│ CONFIGURATION                               │
│  Source caméra    : [ 0               ]     │
│  Pixels / cm      : [ 50.0            ]     │
│  Masse totale (g) : [ 0.0             ]     │
│  iVCam Desktop = 0 (ou 1 si webcam présente)│
├─────────────────────────────────────────────┤
│  [ Démarrer ]  [ Arrêter ]  [ Capturer ]    │
├─────────────────────────────────────────────┤
│ RÉSULTATS                                   │
│  Fibres détectées :   12                    │
│  Court  (< 2 cm)  :    4                    │
│  Moyen  (2-5 cm)  :    5                    │
│  Long   (> 5 cm)  :    3                    │
│  ──────────────────────────────             │
│  Longueur moy.    :  3.4500 cm              │
│  Plage L          :  1.200 — 7.800 cm       │
│  Diamètre moy.    :  0.04200 cm             │
│  Plage d          :  0.0200 — 0.0800 cm     │
│  Volume moy.      :  0.0047832 cm³          │
│  Masse / fibre    :  0.0041667 g            │
│  ──────────────────────────────             │
│  Densité ρ        :  0.87120 g/cm³          │
│                                             │
│    ρ = m / (N × π × (d/2)² × L)            │
├─────────────────────────────────────────────┤
│ Actif — source: 0                           │
└─────────────────────────────────────────────┘
```

### Champs de configuration

| Champ | Description | Défaut |
|---|---|---|
| **Source caméra** | Index entier (iVCam/webcam) ou URL HTTP/RTSP | `0` |
| **Pixels / cm** | Calibration : pixels correspondant à 1 cm réel | `50.0` |
| **Masse totale (g)** | Masse pesée de l'échantillon (pour calculer ρ) | `0.0` |

### Boutons

| Bouton | Action |
|---|---|
| **Démarrer** | Ouvre la caméra, lance le thread de capture, remet le tracker à zéro |
| **Arrêter** | Ferme toutes les fenêtres OpenCV et libère la caméra |
| **Capturer** | Sauvegarde l'image courante annotée dans `capture_fibre.png` |

### Barre de statut

| Message | Signification |
|---|---|
| `Actif — source: 0` | Flux actif, analyse en cours |
| `iVCam : en attente de l'iPhone…` | Écran statique détecté, iPhone non connecté |
| `Flux perdu — reconnexion...` | Frame non reçue, reconnexion automatique |
| `Arrêté` | Capture stoppée manuellement |
| `Image sauvegardée -> capture_fibre.png` | Capture réussie |

---

## Fenêtres OpenCV

### Fenêtre 1 — « Fibres de Bananier — Flux annoté »

Flux vidéo en direct avec chaque fibre encadrée et étiquetée.

- **Couleur du cadre** → catégorie de longueur :
  - **Jaune** : Court (< 2 cm)
  - **Orange** : Moyen (2–5 cm)
  - **Rouge** : Long (> 5 cm)

- **Étiquette** affichée au-dessus de chaque fibre :
  ```
  #7 L=3.2cm  d=0.04cm
  ```
  - `#7` = ID de track stable (ne change pas entre les frames)
  - `L` = longueur mesurée
  - `d` = diamètre mesuré

- **Compteur** en haut à gauche : `Fibres détectées : 12`

### Fenêtre 2 — « Prétraitement (binaire) »

Image binaire issue du pipeline Lab+Canny.

- Les fibres détectables apparaissent en **blanc**
- Utile pour diagnostiquer et ajuster `CANNY_LOW` / `CANNY_HIGH`
- Si une fibre n'apparaît pas en blanc ici, elle ne sera pas détectée

---

## Paramètres (`config.py`)

Tous les paramètres sont centralisés dans `config.py`. **Ne modifier aucune constante numérique ailleurs.**

### Caméra

| Paramètre | Défaut | Description |
|---|---|---|
| `CAMERA_SOURCE` | `0` | Index entier (iVCam/webcam) ou URL string (HTTP/RTSP) |
| `CAMERA_RECONNECT_DELAY` | `2.0` | Secondes d'attente entre deux tentatives de reconnexion |
| `CAMERA_TIMEOUT` | `5.0` | Délai max d'ouverture pour sources réseau (secondes) |

### Calibration

| Paramètre | Défaut | Description |
|---|---|---|
| `PIXELS_PER_CM` | `50.0` | **Paramètre le plus important.** Nombre de pixels = 1 cm réel. |
| `REFERENCE_LENGTH_CM` | `10.0` | Longueur de l'objet de référence pour le mode calibration |

> **Comment calibrer `PIXELS_PER_CM` :**
> 1. Placer une règle dans le champ de vue, dans le même plan que les fibres
> 2. Faire un screenshot (bouton **Capturer**)
> 3. Ouvrir l'image dans un éditeur, compter les pixels entre 0 et 10 cm
> 4. Diviser par 10 → valeur à entrer dans `PIXELS_PER_CM`
> 5. Recalibrer si la distance caméra–fibres change

### Détection des contours

| Paramètre | Défaut | Description |
|---|---|---|
| `MIN_CONTOUR_AREA` | `200` | Aire minimale (px²). Augmenter pour ignorer les très petits artefacts |
| `MAX_CONTOUR_AREA` | `80000` | Aire maximale (px²). Exclut les très grands objets parasites |
| `MIN_ASPECT_RATIO` | `3.0` | Rapport L/d minimum. `3.0` = fibre 3× plus longue que large. Exclut les formes rondes |

### Prétraitement Canny

| Paramètre | Défaut | Guide de réglage |
|---|---|---|
| `CANNY_LOW` | `50` | **Baisser** (ex: 30) si des fibres ne sont pas détectées |
| `CANNY_HIGH` | `150` | **Augmenter** (ex: 200) si trop de bruit / faux positifs |

### Classification des fibres

| Paramètre | Défaut | Description |
|---|---|---|
| `SHORT_MAX_CM` | `2.0` | Longueur max pour la catégorie "Court" |
| `MEDIUM_MAX_CM` | `5.0` | Longueur max pour "Moyen" — au-delà = "Long" |

### Tracker inter-frames

| Paramètre | Défaut | Guide de réglage |
|---|---|---|
| `TRACKER_MAX_DIST_PX` | `40` | Distance max centroïde (px) pour associer la même fibre entre 2 frames. Augmenter si la caméra bouge |
| `TRACKER_MIN_AGE` | `3` | Frames consécutives avant de confirmer une fibre. **Augmenter** pour plus de stabilité |
| `TRACKER_MAX_MISSED` | `5` | Frames sans détection avant suppression d'un track |

### Affichage

| Paramètre | Défaut | Description |
|---|---|---|
| `COLOR_SHORT` | `(0, 255, 255)` | Jaune (BGR) — fibres courtes |
| `COLOR_MEDIUM` | `(0, 165, 255)` | Orange (BGR) — fibres moyennes |
| `COLOR_LONG` | `(0, 0, 255)` | Rouge (BGR) — fibres longues |
| `COLOR_TEXT` | `(255, 255, 255)` | Blanc — texte des étiquettes |
| `FONT_SCALE` | `0.45` | Taille du texte OpenCV |
| `LINE_THICKNESS` | `2` | Épaisseur des cadres dessinés |

---

## Pipeline de traitement

Chaque frame passe par la chaîne suivante (`processing/preprocessor.py`) :

```
Frame BGR
    │
    ▼  cv2.cvtColor(BGR → Lab)
Canal L — luminosité pure, insensible à la couleur des fibres
    │
    ▼  cv2.bilateralFilter(d=9, σColor=75, σSpace=75)
Lissage doux — préserve les bords fins (important pour mesurer d)
    │
    ▼  cv2.Canny(CANNY_LOW, CANNY_HIGH)
Contours des fibres
    │
    ▼  cv2.dilate(kernel 3×3, iter=1)
Contours épaissis — meilleure détection par findContours
    │
    ▼  cv2.morphologyEx(MORPH_CLOSE, kernel 3×3, iter=2)
Segments brisés d'une même fibre réunis
    │
    ▼
Image binaire
```

**Pourquoi le canal L de l'espace Lab ?**
Le canal L encode uniquement la luminosité, totalement indépendant de la teinte.
Les fibres de bananier (beige, brun, doré) sont détectées de façon identique
quelle que soit leur couleur — seul le contraste de luminosité compte.

**Mesure géométrique par `minAreaRect` (`processing/detector.py`) :**

Pour chaque contour retenu :
1. Filtre : `MIN_CONTOUR_AREA ≤ aire_px ≤ MAX_CONTOUR_AREA`
2. `cv2.minAreaRect(contour)` → rectangle orienté minimal → côtés `w` et `h`
3. `L = max(w, h)` (axe long), `d = min(w, h)` (axe court)
4. Filtre : `L / d ≥ MIN_ASPECT_RATIO`
5. Conversion : `length_cm = L / PIXELS_PER_CM`, `diameter_cm = d / PIXELS_PER_CM`

---

## Tracker inter-frames

**Problème sans tracker :** OpenCV renuméroté les contours à chaque frame → le compte fluctue, les IDs changent à chaque image.

**Solution — `FiberTracker` (`processing/tracker.py`) :**

```
Frame N   : détections brutes [A, B, C]
Tracks existants : [#3 (age=15), #5 (age=7), #7 (age=2, non confirmé)]
    │
    ▼  Association par distance centroïde (seuil = TRACKER_MAX_DIST_PX)
#3 ← A  (12 px)   → age=16, confirmé ✓
#5 ← B  (8 px)    → age=8,  confirmé ✓
C  →    nouveau track #9, age=1    ✗ (pas encore confirmé)
#7      non associé → missed=1
    │
    ▼  Filtrage age ≥ TRACKER_MIN_AGE
Retourné à l'UI : [#3, #5]
```

**Effets concrets :**

| Comportement | Avec tracker |
|---|---|
| Bruit / reflet fugace | Ignoré — n'atteint jamais age ≥ 3 |
| Fibre temporairement cachée | Conservée pendant `TRACKER_MAX_MISSED` frames |
| ID d'une fibre | Stable : `#7` reste `#7` tant qu'elle est visible |
| Comptage | Stable — ne fluctue plus entre frames |

`reset()` est appelé automatiquement à chaque clic **Démarrer**.

---

## Formule de densité

```
ρ = m / (N × π × (d_moy / 2)² × L_moy)
```

| Variable | Source | Unité |
|---|---|---|
| `m` | Masse saisie dans "Masse totale (g)" | g |
| `N` | Nombre de fibres confirmées par le tracker | — |
| `d_moy` | Diamètre moyen — axe court de minAreaRect | cm |
| `L_moy` | Longueur moyenne — axe long de minAreaRect | cm |
| `ρ` | Densité apparente calculée | g/cm³ |

**Modèle géométrique :** chaque fibre est approximée par un cylindre de longueur `L` et de rayon `d/2`.

**Volume d'une fibre :** `V = π × (d/2)² × L`

**Volume total :** `V_tot = N × V_moy`

**Masse par fibre :** `m_fibre = m / N`

> Si la masse n'est pas saisie (= 0), les champs `Masse/fibre` et `Densité ρ` affichent `— (masse non saisie)`.

---

## Classification des fibres

Basée uniquement sur la longueur mesurée. Seuils ajustables dans `config.py`.

| Catégorie | Condition | Couleur cadre |
|---|---|---|
| **Court** | `length_cm < SHORT_MAX_CM` (< 2.0 cm) | Jaune |
| **Moyen** | `SHORT_MAX_CM ≤ length_cm < MEDIUM_MAX_CM` (2.0–5.0 cm) | Orange |
| **Long** | `length_cm ≥ MEDIUM_MAX_CM` (≥ 5.0 cm) | Rouge |

---

## Marges d'erreur

### Source principale : la calibration

Une erreur de ±1 px/cm sur `PIXELS_PER_CM = 50` représente ±2% sur L et d,
et **±6% sur ρ** (la densité contient `d²`).

| Erreur calibration | Erreur sur L | Erreur sur d | Erreur sur ρ |
|---|---|---|---|
| ±1 px/cm (2%) | ±2% | ±2% | ~±6% |
| ±2 px/cm (4%) | ±4% | ±4% | ~±12% |

### Mesure géométrique

Le contour Canny a une épaisseur de ±1–2 px :

| Dimension | Erreur typique | En cm (à 50 px/cm) |
|---|---|---|
| Longueur L | ±2 px | ±0.04 cm |
| Diamètre d | ±2 px | ±0.04 cm |

> Pour une fibre très fine (d ≈ 0.5 mm ≈ 2.5 px à 50 px/cm), 2 px d'erreur = **80% d'erreur sur d** → ρ inexact. Rapprocher la caméra (augmenter px/cm) est la correction principale.

### Résumé global

| Grandeur | Erreur (bonne calibration) | Erreur (calibration ±2%) |
|---|---|---|
| Longueur L | ±0.04–0.10 cm | ~±5–10% |
| Diamètre d | ±0.02–0.05 cm | ~±5–10% |
| Densité ρ | ±5–15% | ~±10–25% |
| Comptage N | ±0 (tracker stable) | ±0–2 (occlusion/bord image) |

### Recommandations pour minimiser l'erreur

1. **Calibrer précisément** `PIXELS_PER_CM` avec une règle — c'est le levier le plus impactant
2. **Rapprocher la caméra** → plus de px/cm → diamètre plus précis
3. **Fond noir mat** → Canny propre → contours d'1 px d'épaisseur
4. **Éclairage diffus** sans reflets ni ombres portées
5. **Fibres espacées** d'au moins 50 px → pas de fusion dans le tracker

---

## Structure des modules

### `config.py`
Fichier central. Toutes les constantes numériques. **Ne jamais hardcoder de valeur numérique dans un autre module.**

### `capture/ip_camera.py` — classe `IPCamera`
| Méthode | Description |
|---|---|
| `__init__(source)` | Normalise la source (string "0" → int 0) |
| `connect()` | Ouvre `cv2.VideoCapture` avec `CAP_DSHOW` pour les entiers |
| `read_frame()` | Lit une frame ; appelle `reconnect()` automatiquement en cas d'échec |
| `reconnect()` | Attend `CAMERA_RECONNECT_DELAY` secondes, rappelle `connect()` |
| `release()` | Libère la ressource VideoCapture |

### `processing/preprocessor.py`
| Fonction | Description |
|---|---|
| `preprocess(frame)` | `np.ndarray BGR → np.ndarray binaire`. Pipeline Lab+Canny complet. |

### `processing/detector.py`
| Fonction | Description |
|---|---|
| `detect_fibers(binary, pixels_per_cm)` | `binaire → List[Fiber]`. Filtre aire + ratio, mesure minAreaRect. |
| `annotate_frame(frame, fibers, track_ids)` | `frame BGR + fibres → frame annotée BGR`. `track_ids` = IDs stables du tracker. |

### `processing/tracker.py` — classe `FiberTracker`
| Méthode | Description |
|---|---|
| `update(fibers)` | Associe détections aux tracks, crée nouveaux tracks, retourne les tracks confirmés |
| `reset()` | Vide tous les tracks et reset les compteurs d'ID |

### `analysis/fiber_model.py` — dataclass `Fiber`
| Attribut | Type | Description |
|---|---|---|
| `length_cm` | float | Longueur (axe majeur minAreaRect) |
| `diameter_cm` | float | Diamètre (axe mineur minAreaRect) |
| `area_cm2` | float | Aire du contour |
| `centroid` | Tuple[int, int] | Position (x, y) dans l'image |
| `volume_cm3` | float (property) | `π × (d/2)² × L` |
| `category` | str (property) | "Court" / "Moyen" / "Long" |

### `analysis/analyzer.py`
| Fonction | Retour |
|---|---|
| `count_fibers(fibers)` | `int` |
| `classify_fibers(fibers)` | `Dict[str, List[Fiber]]` — clés : "Court", "Moyen", "Long" |
| `compute_stats(fibers)` | `Dict[str, float]` — L_moy, d_moy, L_min, L_max, d_min, d_max, aire_moy |
| `compute_density(mass, fibers)` | `Dict[str, float]` — rho, V_moy_cm3, m_fibre_g, V_tot_cm3 |

### `ui/app.py` — classe `FiberApp(tk.Tk)`
- Thread principal : Tkinter (toutes les opérations UI)
- Thread secondaire (daemon) : `_capture_loop()` — lecture caméra + traitement
- Communication inter-threads : `self.after(0, callback, data)` (thread-safe Tkinter)
- `FiberTracker` instancié dans `__init__`, remis à zéro dans `_start()`

### `main.py`
Point d'entrée. Configure le logging (`INFO`, format horodaté), instancie `FiberApp`, lance `mainloop()`. Intercepte `KeyboardInterrupt` proprement.

---

## FAQ / Dépannage

**Erreur `-1072875772` (MSMF) dans les logs**
→ Backend OpenCV incompatible avec iVCam. Corrigé automatiquement : `CAP_DSHOW` est utilisé pour toutes les sources entières.

**"iVCam : en attente de l'iPhone"**
→ Ouvrir l'app iVCam sur l'iPhone. Vérifier que iPhone et PC sont sur le même Wi-Fi.

**Le comptage fluctue encore**
→ Augmenter `TRACKER_MIN_AGE` à `5` ou `7`.
→ Vérifier l'éclairage (ombres = faux contours fugaces).

**Des fibres ne sont pas détectées**
→ Baisser `CANNY_LOW` (ex: `30`).
→ Baisser `MIN_CONTOUR_AREA` (ex: `100`).
→ Regarder la fenêtre "Prétraitement" : les fibres doivent apparaître en blanc.

**Trop de faux positifs (poussières, ombres, reflets)**
→ Augmenter `MIN_ASPECT_RATIO` (ex: `4.5`) — les formes rondes sont exclues.
→ Augmenter `CANNY_HIGH` (ex: `200`).
→ Augmenter `TRACKER_MIN_AGE`.

**La densité ρ affiche "— (masse non saisie)"**
→ Saisir la masse de l'échantillon dans le champ **Masse totale (g)** avant de lire les résultats.

**Les mesures de longueur semblent incorrectes**
→ Recalibrer `PIXELS_PER_CM` avec une règle physique dans le champ de vue.
→ S'assurer que la règle est dans le **même plan** que les fibres.

**L'image est trop sombre ou trop claire**
→ Ajuster l'exposition directement dans l'app iVCam sur l'iPhone.

**Deux fibres proches se fusionnent en une seule**
→ Espacer physiquement les fibres (≥ 5 mm).
→ Réduire `TRACKER_MAX_DIST_PX` (ex: `25`).

---

## Conditions optimales de prise de vue

| Paramètre physique | Recommandation |
|---|---|
| **Fond** | Noir mat ou bleu foncé — contraste maximal avec les fibres beige/brun |
| **Éclairage** | Diffus, uniforme, sans ombres portées ni reflets spéculaires |
| **Distance caméra** | La plus proche possible pour maximiser `PIXELS_PER_CM` |
| **Orientation** | Caméra perpendiculaire au plan des fibres (vue de dessus) |
| **Fibres** | Bien à plat, espacées d'au moins 5 mm, sans croisements |
| **Calibration** | Recalibrer `PIXELS_PER_CM` à chaque changement de distance caméra |
