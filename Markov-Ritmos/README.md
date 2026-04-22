# Markov-Ritmos

Aplicación web en Flask para analizar ficheiros MIDI, construír unha cadea de Markov rítmica de segunda orde e xerar novas secuencias de duracións en 6/8. O sistema tamén pode visualizar o resultado como partitura de percusión e, opcionalmente, aplicar esas duracións ás alturas dun MIDI cargado pola persoa usuaria.

## Funcionalidades

- Lectura recursiva dos ficheiros MIDI presentes no cartafol de materiais.
- Extracción de intervalos entre ataques e cuantización a un conxunto finito de razóns rítmicas.
- Construción dunha matriz global de transicións de Markov.
- Xeración de secuencias con semente reproducible e modo espello.
- Exportación de partitura en MusicXML, PNG e PDF mediante MuseScore.
- Aplicación das duracións xeradas ás alturas dun ficheiro MIDI externo.

## Estrutura principal

- [app.py](app.py): aplicación Flask, renderizado de partitura e rutas HTTP.
- [markov_rhythm.py](markov_rhythm.py): biblioteca principal de análise e xeración rítmica.
- [templates/index.html](templates/index.html): interface web.
- [start.command](start.command) e [stop.command](stop.command): scripts auxiliares para iniciar e deter o servidor.

## Requisitos

- Python 3.11 ou superior recomendado.
- MuseScore 4 instalado en macOS na ruta configurada en [app.py](app.py).
- Dependencias de Python listadas en [requirements.txt](requirements.txt).

## Instalación

```bash
mkdir -p "$HOME/Documents/entornos virtuales"
python3.11 -m venv "$HOME/Documents/entornos virtuales/markov-ritmos"
source "$HOME/Documents/entornos virtuales/markov-ritmos/bin/activate"
pip install -r requirements.txt
```

## Execución

Con Python activado no contorno virtual externo:

```bash
"$HOME/Documents/entornos virtuales/markov-ritmos/bin/python" app.py
```

Despois abre no navegador:

```text
http://127.0.0.1:5000
```

En macOS tamén se pode usar [start.command](start.command), que xa apunta ao contorno externo situado en `~/Documents/entornos virtuales/markov-ritmos`.

## Comprobación rápida

```bash
"$HOME/Documents/entornos virtuales/markov-ritmos/bin/python" test_measures.py
"$HOME/Documents/entornos virtuales/markov-ritmos/bin/python" test_mirror.py
```

## Observacións técnicas

- O modo espello invirte a razón de saída pero conserva o estado interno orixinal da cadea para non alterar a estatística de transición.
- A ruta /apply-pitches reutiliza as alturas dun MIDI cargado e substitúe só as duracións.
- Os ficheiros xerados gárdanse en [static/scores](static/scores).