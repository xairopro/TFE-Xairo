#!/usr/bin/env python3
"""
xerar_arte_alala_cinzas.py
──────────────────────────
Variante do xerador de arte espectrograma con efecto progresivo
de erosión / cinzas baseado na Proporción Áurea (φ).

As liñas mantéñense sólidas e elegantes ata o punto áureo (~43.27 s)
e despois disolven-se progresivamente en ruído, estática e partículas
de cinza ata desaparecer completamente no bordo dereito.

Saída   : portada_alala_cinzas.png  (fondo transparente, 6400 × 3600 px)
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
PUNTO_AUREO      = DURACION / PHI            # ≈ 43.27 s  (61.8% do total)
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

# Distorsión áurea (só no punto φ do tempo)
GROSOR_AUREO     = 2.5
ALFA_AUREO       = 0.95

# Parámetros do efecto de erosión / cinzas
SEMENTE_ALEATORIA = 42                       # semente para reproducibilidade
XITTER_MAX        = 0.06                     # desprazamento vertical máximo (en unidades normalizadas)
N_PARTICULAS_CINZA = 18000                   # número de partículas de cinza flotantes
LIMIAR_RUPTURA     = 0.4                     # a partir deste nivel de erosión, as liñas rompen en puntos

FICHEIRO_AUDIO   = pathlib.Path(__file__).with_name("Alalá de Monterrei.mp3")
FICHEIRO_PNG     = pathlib.Path(__file__).with_name("portada_alala_cinzas.png")

# ──────────────────────────────────────────────
# 1.  CARGAR E ANALIZAR O AUDIO
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
# 2.  FUNCIÓN DE EROSIÓN BASEADA NA PROPORCIÓN ÁUREA
# ──────────────────────────────────────────────
print(f"Punto áureo da liña temporal: {PUNTO_AUREO:.2f} s  (φ = {PHI:.6f})")
print(f"  → 0 s  ata  {PUNTO_AUREO:.1f} s : liñas sólidas e elegantes")
print(f"  → {PUNTO_AUREO:.1f} s  ata  {DURACION:.0f} s : erosión progresiva → cinzas")

def calcular_erosion(t):
    """
    Calcula o factor de erosión para un instante temporal t.
    Devolve un valor entre 0.0 (sen erosión, liña intacta)
    e 1.0 (erosión total, cinzas / ruído branco).

    A transición segue unha curva exponencial suave despois do punto áureo.
    """
    if t <= PUNTO_AUREO:
        return 0.0
    # Proporción no tramo de erosión [0, 1]
    progreso = (t - PUNTO_AUREO) / (DURACION - PUNTO_AUREO)
    # Curva exponencial para unha disolución progresiva e dramática
    # Usamos potencia 2.5 para que comece suave e acelere ao final
    return np.clip(progreso ** 2.5, 0.0, 1.0)


# Precalcular o vector de erosión para cada fotograma temporal
erosion_por_fotograma = np.array([calcular_erosion(t) for t in tempos])

# ──────────────────────────────────────────────
# 3.  CONSTRUÍR SEGMENTOS DE LIÑA CON EROSIÓN
# ──────────────────────────────────────────────
print("Construíndo arte de liñas con efecto de cinzas …")

# Inicializar xerador aleatorio para reproducibilidade
rng = np.random.default_rng(SEMENTE_ALEATORIA)

# Centros verticais para cada banda mel (frecuencia no eixe Y)
centros_y = np.linspace(0.0, 1.0, N_MELS)

# Submostrar bandas para manter a densidade manexable (≈ 180 liñas)
paso_banda = max(1, N_MELS // 180)
indices_banda = np.arange(0, N_MELS, paso_banda)

# Preparar figura (apaisado 16:9: tempo en X, frecuencia en Y)
fig, ax = plt.subplots(
    figsize=(ANCHO_POLG, ALTO_POLG), dpi=PPP,
    facecolor="none",
)
ax.set_facecolor("none")
ax.set_xlim(0, DURACION)
ax.set_ylim(-0.05, 1.05)
ax.axis("off")
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

r_cor, g_cor, b_cor = matplotlib.colors.to_rgb(COR_LIÑA)

# Contadores para as estatísticas de depuración
total_segmentos = 0
segmentos_erosionados = 0
segmentos_convertidos_puntos = 0

for idx in indices_banda:
    amp = S_norm[idx]
    amp_suave = gaussian_filter1d(amp, sigma=SUAVIZADO_SIGMA)

    cy = centros_y[idx]

    # Desprazamento vertical base (ondulación orixinal)
    desp_max = 0.018
    x = tempos.copy()
    y_base = cy + (amp_suave - 0.5) * desp_max

    # ── Aplicar xitter (desprazamento aleatorio) proporcional á erosión ──
    # O ruído crece co factor de erosión
    ruido_y = rng.normal(0, 1, size=len(tempos))
    ruido_x = rng.normal(0, 1, size=len(tempos))

    # Desprazamento vertical: aumenta exponencialmente coa erosión
    y_erosionada = y_base + ruido_y * erosion_por_fotograma * XITTER_MAX
    # Desprazamento horizontal lixeiro (menos que o vertical, para efecto de dispersión)
    x_erosionada = x + ruido_x * erosion_por_fotograma * XITTER_MAX * 0.5 * DURACION

    # ── Construír segmentos ──
    puntos = np.column_stack([x_erosionada, y_erosionada])
    segmentos = np.stack([puntos[:-1], puntos[1:]], axis=1)

    # Amplitude media por segmento
    seg_amp = 0.5 * (amp_suave[:-1] + amp_suave[1:])
    # Erosión media por segmento
    seg_erosion = 0.5 * (erosion_por_fotograma[:-1] + erosion_por_fotograma[1:])

    # ── Alfas: reducir opacidade coa erosión ──
    alfas_base = ALFA_MIN + (ALFA_MAX - ALFA_MIN) * seg_amp
    # A opacidade diminúe co cadrado da erosión (desvanecemento progresivo)
    factor_alfa_erosion = (1.0 - seg_erosion) ** 1.5
    alfas = alfas_base * factor_alfa_erosion

    # ── Grosores: adelgazar coa erosión ──
    grosores_base = GROSOR_BASE + (GROSOR_PICO - GROSOR_BASE) * seg_amp
    # As liñas fanse máis finas coa erosión
    factor_grosor_erosion = (1.0 - seg_erosion * 0.85)
    grosores = grosores_base * factor_grosor_erosion

    # ── Romper liñas en zonas de alta erosión ──
    # Onde a erosión supera o limiar, eliminamos segmentos aleatorios
    # para crear o efecto de fragmentación e dispersión
    mascara_visible = np.ones(len(segmentos), dtype=bool)
    zonas_alta_erosion = seg_erosion > LIMIAR_RUPTURA
    if np.any(zonas_alta_erosion):
        # Probabilidade de eliminar un segmento: crece coa erosión
        ratio_erosion = np.clip((seg_erosion - LIMIAR_RUPTURA) / (1.0 - LIMIAR_RUPTURA), 0, 1)
        prob_eliminar = ratio_erosion ** 1.8
        prob_eliminar = np.clip(prob_eliminar, 0, 0.97)
        dados = rng.random(len(segmentos))
        mascara_visible[zonas_alta_erosion] = dados[zonas_alta_erosion] > prob_eliminar[zonas_alta_erosion]

    # Aplicar máscara: só debuxar segmentos visibles
    segmentos_vis = segmentos[mascara_visible]
    alfas_vis = alfas[mascara_visible]
    grosores_vis = grosores[mascara_visible]

    total_segmentos += len(segmentos)
    segmentos_erosionados += np.sum(seg_erosion > 0)
    segmentos_convertidos_puntos += np.sum(~mascara_visible)

    if len(segmentos_vis) == 0:
        continue

    # Cores RGBA
    cores = np.zeros((len(segmentos_vis), 4))
    cores[:, 0] = r_cor
    cores[:, 1] = g_cor
    cores[:, 2] = b_cor
    cores[:, 3] = np.clip(alfas_vis, 0, 1)

    lc = LineCollection(segmentos_vis, linewidths=grosores_vis, colors=cores,
                        capstyle="round")
    ax.add_collection(lc)

print(f"  Segmentos totais: {total_segmentos}")
print(f"  Segmentos con erosión: {segmentos_erosionados}")
print(f"  Segmentos eliminados (fragmentados): {segmentos_convertidos_puntos}")

# ──────────────────────────────────────────────
# 4.  LIÑA DE DISTORSIÓN ÁUREA (marca o punto φ de transición)
# ──────────────────────────────────────────────
print(f"Engadindo liña de distorsión áurea no segundo {PUNTO_AUREO:.1f} …")

idx_aureo = np.argmin(np.abs(tempos - PUNTO_AUREO))

x_base_aureo = PUNTO_AUREO
x_ondulacion = np.zeros(N_MELS)
for i in range(N_MELS):
    x_ondulacion[i] = x_base_aureo + (S_norm[i, idx_aureo] - 0.5) * 1.8

x_ondulacion_suave = gaussian_filter1d(x_ondulacion, sigma=2.0)
y_aureo = np.linspace(0.0, 1.0, N_MELS)

puntos_aureos = np.column_stack([x_ondulacion_suave, y_aureo])
segmentos_aureos = np.stack([puntos_aureos[:-1], puntos_aureos[1:]], axis=1)

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
# 5.  PARTÍCULAS DE CINZA FLOTANTES (zona de disolución)
# ──────────────────────────────────────────────
print(f"Xerando {N_PARTICULAS_CINZA} partículas de cinza na zona de disolución …")

# As partículas aparecen só despois do punto áureo e increméntanse cara á dereita
# Distribución temporal: concentrada cara ao final (distribución beta)
particulas_t_norm = rng.beta(2.0, 1.2, size=N_PARTICULAS_CINZA)  # sesgada cara á dereita
particulas_t = PUNTO_AUREO + particulas_t_norm * (DURACION - PUNTO_AUREO)

# Posición vertical: distribuída por todo o eixe Y con algo de concentración
# arredor das bandas de frecuencia orixinais
particulas_y_base = rng.uniform(-0.02, 1.02, size=N_PARTICULAS_CINZA)
# Engadir un desprazamento aleatorio para dar efecto de dispersión
particulas_y = particulas_y_base + rng.normal(0, 0.02, size=N_PARTICULAS_CINZA)

# Opacidade das partículas: máis visibles onde hai máis erosión, pero sempre tenues
erosion_particulas = np.array([calcular_erosion(t) for t in particulas_t])
alfas_particulas = erosion_particulas * rng.uniform(0.03, 0.35, size=N_PARTICULAS_CINZA)

# Tamaño das partículas: variable, máis grandes nas zonas de máis disolución
tamanos_particulas = rng.uniform(0.1, 2.5, size=N_PARTICULAS_CINZA) * (0.3 + 0.7 * erosion_particulas)

# Debuxar as partículas como puntos dispersos
ax.scatter(
    particulas_t, particulas_y,
    s=tamanos_particulas,
    c=[[r_cor, g_cor, b_cor, a] for a in np.clip(alfas_particulas, 0, 1)],
    marker='.',
    edgecolors='none',
    zorder=2,
)

# ──────────────────────────────────────────────
# 6.  GARDAR A IMAXE FINAL
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

plt.close(fig)
print("Feito ✓  — A imaxe con efecto de cinzas áureas gardouse correctamente.")
