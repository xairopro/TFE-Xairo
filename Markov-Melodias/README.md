# Xerador de Melodías con Cadeas de Markov

Aplicación web e conxunto de scripts para analizar unha melodía de referencia e xerar novas partituras a partir de cadeas de Markov de primeira orde. O proxecto forma parte do Traballo Fin de Estudos de Composición de Xairo Campos Blanco no Conservatorio Superior de Música da Coruña, curso 2025-2026.

O sistema está pensado para dous usos complementarios:

1. Analizar unha partitura MusicXML e extraer patróns de movemento melódico e duración.
2. Xerar novas melodías mantendo un comportamento estilístico próximo ao corpus de partida ou, se se prefire, usando unha distribución gaussiana máis neutra.

## Visión xeral

O modelo melódico funciona como unha cadea de Markov: a seguinte nota escóllese a partir da nota actual e das probabilidades de transición dispoñibles. O ritmo, en cambio, trátase como unha distribución independente de duracións. Esta separación permite conservar unha lóxica clara:

- A melodía depende do estado actual.
- O ritmo non necesita memoria.
- A escala de traballo pode ser personalizada.
- O sistema admite xeración monódica e episodios de ossia a dúas voces.

Hai dous modos de xeración:

- `análise`: usa as probabilidades extraídas da partitura analizada.
- `gaussiana`: reparte as probabilidades arredor da nota actual cunha campá simétrica.

## Funcionalidades principais

- Interface web para analizar e xerar partituras.
- Configuración de escalas personalizadas para análise e xeración.
- Xestión de ruído controlado en melodía e ritmo.
- Xeración paso a paso ou por lotes.
- Exportación de MusicXML, PNG, PDF e reprodución de audio.
- Renderización con MuseScore a partir de ficheiros temporais.

## Estrutura do proxecto

```text
Melodias_Markov/
├── README.md
├── LEEME.md
├── INSTALACION.md
├── requirements.txt
├── config.py
├── markov_web.py
├── analise_muineira.py
├── iniciar_markov.command
├── MuineiraMonterrei.mxl
├── templates/
│   └── markov.html
└── temp/
    ├── temp_partitura_web.musicxml
    ├── temp_partitura_voz1.musicxml
    └── temp_partitura_voz2.musicxml
```

## Dependencias

As dependencias do proxecto están definidas en `requirements.txt` e cobren o núcleo da aplicación:

- `Flask` para a interface web.
- `music21` para ler e escribir partituras.
- `matplotlib` para as visualizacións da análise.
- `numpy` e `scipy` para o tratamento estatístico.

## Instalación rápida

```bash
mkdir -p "$HOME/Documents/entornos virtuales"
python3 -m venv "$HOME/Documents/entornos virtuales/venv-markov-melodias"
source "$HOME/Documents/entornos virtuales/venv-markov-melodias/bin/activate"
pip install -r requirements.txt
```

Despois hai que revisar a ruta de MuseScore en `config.py` ou definila coa variable de contorno `MUSESCORE_PATH`.

## Execución

O modo máis directo en macOS é:

```bash
./iniciar_markov.command
```

Tamén se pode iniciar manualmente:

```bash
source "$HOME/Documents/entornos virtuales/venv-markov-melodias/bin/activate"
python3 markov_web.py
```

A aplicación queda dispoñible en `http://127.0.0.1:5000` mentres o servidor estea en execución.

## Fluxo de uso recomendado

1. Abre a lapela de análise e escolle un ficheiro MusicXML.
2. Define a escala que vas empregar como referencia analítica.
3. Executa a análise e revisa os gráficos e as táboas xeradas.
4. Vai á lapela de xeración e define a escala de destino.
5. Escolle nota inicial, ritmo inicial, distribución, ruído e semente.
6. Xera eventos paso a paso ou nun lote completo.
7. Garda o resultado en MusicXML ou descárgao como PDF.

## Escalas e movementos relativos

O proxecto non interpreta os movementos como semitonos absolutos, senón como posicións relativas dentro da escala activa. Isto permite trasladar unha lóxica melódica a diferentes coleccións de notas sen forzar unha equivalencia cromática estrita.

Exemplo:

- Nunha escala de sete notas, pasar de `Fa` a `La` pode entenderse como un ascenso de dúas posicións.
- Nunha escala máis curta, un salto con esa mesma función estrutural seguirá tratándose como un cambio relativo dentro do novo contexto.

Esta decisión é a que fai viable usar unha análise sobre unha escala e unha xeración sobre outra distinta.

## Ficheiros principais

- `markov_web.py`: servidor Flask e lóxica de xeración.
- `analise_muineira.py`: análise estatística do corpus de referencia.
- `config.py`: rutas, parámetros do sistema e configuración xeral.
- `templates/markov.html`: interface web.
- `iniciar_markov.command`: script de inicio para macOS.

## Notas prácticas

- O cartafol `temp/` garda saídas temporais xeradas pola aplicación. Son ficheiros de traballo e poden rexenerarse.
- `MuineiraMonterrei.mxl` consérvase como partitura de referencia do corpus.
- `LEEME.md` ofrece un resumo operativo curto.
- `INSTALACION.md` detalla a configuración paso a paso e a resolución de incidencias frecuentes.

## Validación recomendada

Antes de dar unha instalación por boa convén comprobar:

```bash
python3 config.py
python3 -m py_compile markov_web.py analise_muineira.py config.py
```

Se MuseScore está correctamente localizado e a compilación non devolve erros, o proxecto debería estar listo para uso local.

## Autoría

Xairo Campos Blanco  
Traballo Fin de Estudos de Composición  
Conservatorio Superior de Música da Coruña  
Curso 2025-2026
