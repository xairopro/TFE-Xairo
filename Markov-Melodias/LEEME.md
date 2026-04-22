# LEEME

Este documento resume o uso diario do proxecto sen entrar no detalle completo da documentación principal.

## Que fai este proxecto

- Analiza unha partitura MusicXML e calcula distribucións de movemento melódico.
- Extrae tamén a distribución das duracións rítmicas.
- Xera novas melodías nunha interface web con escalas personalizadas.
- Permite exportar a partitura e escoitar o resultado xerado.

## Inicio rápido

```bash
mkdir -p "$HOME/Documents/entornos virtuales"
python3 -m venv "$HOME/Documents/entornos virtuales/venv-markov-melodias"
source "$HOME/Documents/entornos virtuales/venv-markov-melodias/bin/activate"
pip install -r requirements.txt
./iniciar_markov.command
```

Se prefires non usar o script:

```bash
source "$HOME/Documents/entornos virtuales/venv-markov-melodias/bin/activate"
python3 markov_web.py
```

## Antes de iniciar

1. Comproba que MuseScore está instalado.
2. Revisa `config.py` e axusta `MUSESCORE_PATH` se a ruta non coincide coa túa instalación.
3. Executa `python3 config.py` para verificar a configuración.

## Fluxo recomendado na aplicación

1. Vai á lapela de análise.
2. Escolle o ficheiro MusicXML e define a escala de análise.
3. Executa a análise e revisa os resultados.
4. Vai á lapela de xeración.
5. Define a escala de destino, a nota inicial, o ritmo inicial e a configuración.
6. Xera a partitura e gárdaa no formato que precises.

## Ficheiros clave

- `README.md`: visión xeral do proxecto.
- `INSTALACION.md`: guía completa de instalación e resolución de incidencias.
- `markov_web.py`: servidor e lóxica principal.
- `config.py`: rutas e parámetros configurables.
- `templates/markov.html`: interface web.

## Observacións

- O cartafol `temp/` garda ficheiros temporais que a aplicación pode rexenerar.
- O ficheiro `MuineiraMonterrei.mxl` úsase como material de referencia.
- A versión actual do script de inicio usa o contorno `~/Documents/entornos virtuales/venv-markov-melodias` e non precisa un `.venv` dentro do proxecto.
