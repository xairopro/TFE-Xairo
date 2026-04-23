# Grafos de Markov

Aplicación web interactiva que xera e visualiza **grafos de cadeas de Markov** con estética futurista. Pensada para producir gráficos vectoriais (SVG / PNG) aptos para a maquetación do TFE.

## Contido

| Ficheiro / Carpeta | Descrición |
|---|---|
| `iniciar-markov-grafos.command` | Fai dobre clic para lanzar o servidor local e abrir o navegador |
| `deter-markov-grafos.command` | Fai dobre clic para deter o servidor |
| `server.py` | Servidor Flask (porto 5050) |
| `requirements.txt` | Dependencias de Python |
| `static/` | Frontend: HTML, CSS e JavaScript |

## Uso

1. **Iniciar**: fai dobre clic en `iniciar-markov-grafos.command`.
2. Ábrese automaticamente o navegador en `http://localhost:5050`.
3. Xera o grafo e descárgao como SVG ou PNG.
4. **Deter**: fai dobre clic en `deter-markov-grafos.command` ou preme `Ctrl+C` no terminal.

## Requisitos

- Python 3
- Flask (instálase automaticamente co script)
