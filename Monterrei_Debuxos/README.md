# Monterrei Debuxos — Visualización SVG/Vídeo

Script de Python que a partir de fotografías de monumentos xera animacións estilo wireframe/ciberpunk onde as liñas se van debuxando soas ao longo de dous minutos. Pensado para proxectar en directo durante a peza sinfónica.

Actualmente procesa dous monumentos: o **Castelo de Monterrei** e o **Forte da Atalaia**.

---

## Estrutura do proxecto

```
Monterrei_Debuxos/
├── castelo_monterrei.py        ← Script principal (válido para calquera imaxe)
├── executar.command            ← Dobre clic → xera SVGs e vídeo de ambos monumentos
├── exportar_video.command      ← Dobre clic → só compila o MP4
├── test_ffmpeg.py              ← Test rápido de ffmpeg
├── test_mp4.py                 ← Test de xeración de MP4
├── Castelo/
│   ├── castillo-de-monterrei.png          ← Fotografía de entrada
│   ├── castelo_monterrei_1.svg            ← SVG animado (saída)
│   ├── castelo_monterrei_static_1.svg     ← SVG estático fondo escuro (saída)
│   ├── castelo_monterrei_transparent_1.svg← SVG estático fondo transparente (saída)
│   └── castelo_monterrei_1.mp4            ← Vídeo MP4 (saída)
└── Forte/
    ├── Forta-da-Atalaia_6-1024x682.jpg.webp ← Fotografía de entrada
    ├── forte_atalaia_1.svg                  ← SVG animado (saída)
    ├── forte_atalaia_static_1.svg           ← SVG estático fondo escuro (saída)
    └── forte_atalaia_transparent_1.svg      ← SVG estático fondo transparente (saída)
```

---

## Requisitos

- **Python 3.9+** (xa vén con macOS, non hai que instalar nada extra)
- **ffmpeg** — para xerar o vídeo MP4

  ```bash
  brew install ffmpeg
  ```

- As dependencias de Python instálanse soas a primeira vez que executes `executar.command`:
  - `opencv-python`
  - `numpy`
  - `cairosvg`

---

## Como executar

### Opción 1 — Dobre clic (o máis sinxelo)

1. Abre a carpeta `Monterrei_Debuxos` no Finder.
2. Fai dobre clic en **`executar.command`**.
3. A primeira vez vai tardar un anaco instalando as dependencias.
4. Procesa o Castelo (con vídeo) e despois o Forte (só SVGs). Ao rematar abre o SVG animado do Castelo no navegador automaticamente.

> Se macOS di que non pode abrir o ficheiro por ser dun "programador non identificado", vai a  
> **Preferencias do Sistema → Seguridade e Privacidade** e pulsa en "Abrir igualmente".

### Opción 2 — Só o vídeo (se os SVGs xa están xerados)

Dobre clic en **`exportar_video.command`**.

### Opción 3 — Dende o terminal

```bash
cd ruta/a/Monterrei_Debuxos
source ~/Documents/entornos_virtuais/castelo_env/bin/activate

# Castelo de Monterrei (con vídeo)
python castelo_monterrei.py Castelo/castillo-de-monterrei.png Castelo castelo_monterrei

# Forte da Atalaia (só SVGs, sen vídeo)
python castelo_monterrei.py Forte/Forta-da-Atalaia_6-1024x682.jpg.webp Forte forte_atalaia --no-video
```

O script acepta os seguintes argumentos posicionais:
1. `input_image` — ruta á fotografía de entrada
2. `output_dir` — carpeta onde se gardan as saídas
3. `prefix` — prefixo dos ficheiros de saída
4. `--no-video` (opcional) — omite a xeración do MP4

---

## Saídas

Para cada monumento os ficheiros de saída gárdanse na súa subcarpeta (`Castelo/` ou `Forte/`):

- **`<prefix>_1.svg`** — SVG animado, debúxase en 2 minutos. Ábrese en calquera navegador.
- **`<prefix>_static_1.svg`** — SVG estático co debuxo completo, fondo escuro.
- **`<prefix>_transparent_1.svg`** — SVG estático con fondo transparente, útil para superpoñer sobre outros elementos.
- **`<prefix>_1.mp4`** — Vídeo H.264 a 1920×1080 e 24 fps, listo para proxectar (só se non se usa `--no-video`).

---

## Notas técnicas

- O script detecta as arestas da fotografía con **Canny** (OpenCV), simplifica os contornos e asígnalles un retardo de animación segundo a súa posición vertical: a metade superior (o edificio) ocupa o 70% do tempo de debuxo, a metade inferior o 30% restante.
- A zona superior esquerda (ceo con nubes) está filtrada para non xerar liñas de ruído.
- O vídeo xérase directamente en memoria con numpy/OpenCV e pásase por pipe a ffmpeg, sen ficheiros temporais intermedios. Con 8 núcleos tarda uns 5-10 minutos.
- O entorno virtual créase en `~/Documents/entornos_virtuais/castelo_env` e non hai que tocalo.
