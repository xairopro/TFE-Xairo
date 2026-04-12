# Portada — Espectrograma do Alalá

Xerador dunha imaxe artística baseada no **espectrograma mel** dos primeiros 70 segundos do *Alalá de Monterrei*. Produce un gráfico abstracto de liñas en formato apaisado 16:9, con fondo transparente e unha distorsión vertical no punto áureo (φ).

## Contido

| Ficheiro | Descrición |
|---|---|
| `xerar_arte_alala.py` | Script principal: analiza o audio e xera a arte |
| `executar_alala.command` | Fai dobre clic para executar todo automaticamente |
| `Alalá de Monterrei.mp3` | Gravación orixinal de entrada |
| `portada_alala.png` | Saída PNG de alta resolución (6400 × 3600 px) |
| `portada_alala.svg` | Saída vectorial SVG |

## Uso

1. Fai dobre clic en `executar_alala.command`.
2. O script crea un entorno virtual (se non existe), instala as dependencias e executa o xerador.
3. Ao rematar, produce `portada_alala.png` e `portada_alala.svg` na mesma carpeta.

## Parámetros destacados

- **Duración analizada**: 70 s
- **Punto áureo**: ~43,3 s (liña vertical distorsionada)
- **Resolución PNG**: 6400 × 3600 px (200 ppp)
- **Paleta**: liñas verde-azulado escuro (`#1a3c3c`) sobre fondo transparente

## Requisitos

- Python 3
- librosa, matplotlib, numpy, scipy (instálanse automaticamente co script)
