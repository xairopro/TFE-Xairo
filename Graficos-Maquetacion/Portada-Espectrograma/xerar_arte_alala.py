#!/usr/bin/env python3
"""
xerar_arte_alala.py
───────────────────
Analiza os primeiros 70 s dunha gravación de Alalá e xera
unha imaxe PNG (alta resolución) e SVG abstractas, transparentes
e en formato apaisado 16:9 horizontal, axeitadas para portada de libro.

Saída   : portada_alala.png  (fondo transparente, 6400 × 3600 px)
          portada_alala.svg  (vectorial, fondo transparente)
Lenzo   : 16:9  — apaisado
Paleta  : liñas verde-azulado escuro sobre transparencia
"""

import pathlib
import numpy as np
import librosa
import matplotlib
matplotlib.use("Agg")                       # sen interface gráfica
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy.ndimage import gaussian_filter1d

# ──────────────────────────────────────────────
# 0.  CONSTANTES
# ──────────────────────────────────────────────
PHI              = (1 + np.sqrt(5)) / 2      # ≈ 1.618
DURACION         = 70.0                      # segundos a analizar
PUNTO_AUREO      = DURACION / PHI            # ≈ 43.27 s
TAXA_MOSTRAXE    = 22050                     # frecuencia de mostraxe
FREC_BAIXA       = 200                       # Hz — corte baixo
FREC_ALTA        = 4000                      # Hz — corte alto
N_MELS           = 256                       # bandas mel
SALTO_MOSTRA     = 512                       # hop length
N_FFT            = 2048

# Lenzo (apaisado horizontal 16:9)
ANCHO_POLG       = 32                        # polgadas
ALTO_POLG        = ANCHO_POLG * 9 / 16       # 18 polg → ratio 16:9 horizontal
PPP              = 200                       # puntos por polgada → 6400 × 3600 px

# Visual
COR_LIÑA         = "#1a3c3c"                 # verde-azulado escuro
ALFA_MAX         = 0.92
ALFA_MIN         = 0.04
GROSOR_BASE      = 0.25                      # liña máis fina
GROSOR_PICO      = 1.8                       # liña máis grosa
SUAVIZADO_SIGMA  = 3.0

# Distorsión áurea (só na sección áurea do tempo)
GROSOR_AUREO     = 2.5                       # grosor da liña de distorsión
ALFA_AUREO       = 0.95                      # opacidade da distorsión

FICHEIRO_AUDIO   = pathlib.Path(__file__).with_name("Alalá de Monterrei.mp3")
FICHEIRO_PNG     = pathlib.Path(__file__).with_name("portada_alala.png")
FICHEIRO_SVG     = pathlib.Path(__file__).with_name("portada_alala.svg")

# ──────────────────────────────────────────────
# 1.  CARGAR E ANALIZAR
# ──────────────────────────────────────────────
print(f"Cargando  {FICHEIRO_AUDIO.name}  (primeiros {DURACION:.0f} s) …")
y, _ = librosa.load(str(FICHEIRO_AUDIO), sr=TAXA_MOSTRAXE,
                     duration=DURACION, mono=True)

print("Calculando mel-espectrograma …")
S = librosa.feature.melspectrogram(
    y=y, sr=TAXA_MOSTRAXE, n_fft=N_FFT, hop_length=SALTO_MOSTRA,
    n_mels=N_MELS, fmin=FREC_BAIXA, fmax=FREC_ALTA, power=2.0,
)
S_db = librosa.power_to_db(S, ref=np.max)

# Normalizar a [0, 1]  (1 = máis alto)
S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-9)

# Array de tempos (un valor por fotograma)
n_fotogramas = S_norm.shape[1]
tempos = librosa.frames_to_time(
    np.arange(n_fotogramas), sr=TAXA_MOSTRAXE, hop_length=SALTO_MOSTRA
)

# Frecuencias centrais mel
frecs_mel = librosa.mel_frequencies(n_mels=N_MELS, fmin=FREC_BAIXA, fmax=FREC_ALTA)

# ──────────────────────────────────────────────
# 2.  CONSTRUÍR SEGMENTOS DE LIÑA
# ──────────────────────────────────────────────
print("Construíndo arte de liñas …")

# Centros verticais para cada banda mel (frecuencia no eixe Y)
centros_y = np.linspace(0.0, 1.0, N_MELS)

# Submostrar bandas para manter a densidade manexable (≈ 180 liñas)
paso_banda = max(1, N_MELS // 180)
indices_banda = np.arange(0, N_MELS, paso_banda)

# Preparar figura  (apaisado 16:9: tempo en X, frecuencia en Y)
fig, ax = plt.subplots(
    figsize=(ANCHO_POLG, ALTO_POLG), dpi=PPP,
    facecolor="none",
)
ax.set_facecolor("none")
ax.set_xlim(0, DURACION)                     # tempo de esquerda a dereita
ax.set_ylim(-0.05, 1.05)                     # frecuencia de abaixo a arriba
ax.axis("off")
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

r_cor, g_cor, b_cor = matplotlib.colors.to_rgb(COR_LIÑA)

for idx in indices_banda:
    amp = S_norm[idx]
    amp_suave = gaussian_filter1d(amp, sigma=SUAVIZADO_SIGMA)

    cy = centros_y[idx]

    # Desprazamento vertical proporcional á amplitude (sen sección áurea)
    desp_max = 0.018
    x = tempos                                # eixe X = tempo
    y = cy + (amp_suave - 0.5) * desp_max     # eixe Y = frecuencia + ondulación

    # Segmentos para LineCollection
    puntos = np.column_stack([x, y])
    segmentos = np.stack([puntos[:-1], puntos[1:]], axis=1)

    # Propiedades por segmento: só amplitude, sen modulación áurea
    seg_amp = 0.5 * (amp_suave[:-1] + amp_suave[1:])

    alfas   = ALFA_MIN + (ALFA_MAX - ALFA_MIN) * seg_amp
    grosores = GROSOR_BASE + (GROSOR_PICO - GROSOR_BASE) * seg_amp

    # Cores RGBA
    cores = np.zeros((len(segmentos), 4))
    cores[:, 0] = r_cor
    cores[:, 1] = g_cor
    cores[:, 2] = b_cor
    cores[:, 3] = np.clip(alfas, 0, 1)

    lc = LineCollection(segmentos, linewidths=grosores, colors=cores,
                        capstyle="round")
    ax.add_collection(lc)

# ──────────────────────────────────────────────
# 3.  LIÑA DE DISTORSIÓN ÁUREA (só no punto φ)
# ──────────────────────────────────────────────
print(f"Engadindo distorsión áurea no segundo {PUNTO_AUREO:.1f} …")

# Buscamos o fotograma máis próximo ó punto áureo
idx_aureo = np.argmin(np.abs(tempos - PUNTO_AUREO))

# Trazar unha liña VERTICAL distorsionada no punto áureo:
# a liña ondula horizontalmente segundo a amplitude de cada banda
x_base = PUNTO_AUREO
x_ondulacion = np.zeros(N_MELS)
for i in range(N_MELS):
    x_ondulacion[i] = x_base + (S_norm[i, idx_aureo] - 0.5) * 1.8

x_ondulacion_suave = gaussian_filter1d(x_ondulacion, sigma=2.0)
y_aureo = np.linspace(0.0, 1.0, N_MELS)

puntos_aureos = np.column_stack([x_ondulacion_suave, y_aureo])
segmentos_aureos = np.stack([puntos_aureos[:-1], puntos_aureos[1:]], axis=1)

# Grosor e opacidade modulados pola amplitude de cada banda
amp_banda_aureo = S_norm[:, idx_aureo]
seg_amp_aureo = 0.5 * (amp_banda_aureo[:-1] + amp_banda_aureo[1:])

grosores_aureo = GROSOR_BASE + (GROSOR_AUREO - GROSOR_BASE) * seg_amp_aureo
alfas_aureo = 0.3 + (ALFA_AUREO - 0.3) * seg_amp_aureo

cores_aureo = np.zeros((len(segmentos_aureos), 4))
cores_aureo[:, 0] = r_cor
cores_aureo[:, 1] = g_cor
cores_aureo[:, 2] = b_cor
cores_aureo[:, 3] = np.clip(alfas_aureo, 0, 1)

lc_aureo = LineCollection(segmentos_aureos, linewidths=grosores_aureo,
                          colors=cores_aureo, capstyle="round")
ax.add_collection(lc_aureo)

# ──────────────────────────────────────────────
# 4.  GARDAR
# ──────────────────────────────────────────────
ancho_px = int(ANCHO_POLG * PPP)
alto_px = int(ALTO_POLG * PPP)

print(f"Gardando  {FICHEIRO_PNG.name}  ({ancho_px} × {alto_px} px, transparente) …")
fig.savefig(
    str(FICHEIRO_PNG),
    dpi=PPP,
    transparent=True,
    bbox_inches="tight",
    pad_inches=0,
)

print(f"Gardando  {FICHEIRO_SVG.name}  (vectorial, transparente) …")
fig.savefig(
    str(FICHEIRO_SVG),
    format="svg",
    transparent=True,
    bbox_inches="tight",
    pad_inches=0,
)

plt.close(fig)
print("Feito ✓")
