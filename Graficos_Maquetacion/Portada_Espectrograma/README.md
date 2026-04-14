# Portada — Espectrograma do Alalá

Xerador de imaxes artísticas baseadas no **espectrograma mel** dos primeiros 70 segundos do *Alalá de Monterrei*. Produce gráficos abstractos de liñas en formato apaisado 16:9, con fondo transparente e distorsión no punto áureo (φ).

---

## Contido

| Ficheiro | Descrición |
|---|---|
| `xerar_arte_alala.py` | Script orixinal: xera a arte limpa de liñas espectrográficas |
| `xerar_arte_alala_cinzas.py` | **Variante con efecto de cinzas**: erosión progresiva baseada na Proporción Áurea |
| `executar_alala.command` | Fai dobre clic para executar todo automaticamente |
| `Alalá de Monterrei.mp3` | Gravación orixinal de entrada |
| `portada_alala.png` | Saída PNG orixinal (6400 × 3600 px) |
| `portada_alala.svg` | Saída vectorial SVG orixinal |
| `portada_alala_cinzas.png` | **Saída PNG co efecto de cinzas** (6400 × 3600 px) |

---

## Uso

### Imaxe orixinal (liñas limpas)

1. Fai dobre clic en `executar_alala.command`.
2. O script crea un entorno virtual (se non existe), instala as dependencias e executa o xerador.
3. Ao rematar, produce `portada_alala.png` e `portada_alala.svg` na mesma carpeta.

### Imaxe con efecto de cinzas áureas

1. Activa o entorno virtual:
   ```bash
   source ~/Documents/entornos_virtuais/alala_cover_env/bin/activate
   ```
2. Executa o script de cinzas:
   ```bash
   python3 xerar_arte_alala_cinzas.py
   ```
3. Ao rematar, produce `portada_alala_cinzas.png` na mesma carpeta.

---

## Efecto de cinzas e a Proporción Áurea

O script `xerar_arte_alala_cinzas.py` aplica un efecto visual de **erosión progresiva** ás liñas do espectrograma, matematicamente estruturado arredor da **Proporción Áurea** (φ ≈ 1,618).

### Cálculo do punto áureo

O eixe X representa os 70 segundos do audio. O punto focal calcúlase así:

$$t_{\varphi} = \frac{70}{\varphi} = \frac{70}{1{,}618} \approx 43{,}27 \text{ s}$$

Isto sitúa o punto áureo ao **61,8 %** da liña temporal.

### Fases da erosión

| Tramo temporal | Comportamento visual |
|---|---|
| **0 s → 43,3 s** | As liñas mantéñense **sólidas e elegantes**, sen alteración. |
| **≈ 43,3 s** | A erosión **comeza a activarse** de xeito sutil. Marca-se cunha liña vertical distorsionada. |
| **43,3 s → 70 s** | A degradación **aumenta exponencialmente** (curva de potencia 2,5). |
| **Bordo dereito** | As liñas disolven-se por completo en **ruído abstracto, estática e partículas de cinza**. |

### Técnicas de erosión empregadas

1. **Xitter (desprazamento aleatorio)**: As coordenadas X e Y de cada punto da liña reciben un desprazamento aleatorio proporcional ao factor de erosión. O ruído vertical crece ata un máximo de ±0,06 unidades normalizadas.

2. **Desvanecemento de opacidade**: A opacidade (alfa) de cada segmento redúcese progresivamente co cadrado da erosión, creando un efecto de desaparición gradual.

3. **Adelgazamento de liñas**: O grosor das liñas diminúe co avance da erosión, pasando de trazos nítidos a fíos case invisibles.

4. **Fragmentación aleatoria**: Cando a erosión supera un limiar (40 %), os segmentos de liña elimínanse con probabilidade crecente, rompendo as liñas continuas en fragmentos dispersos.

5. **Partículas de cinza**: 18.000 puntos diminutos espallan-se pola zona de disolución, simulando cinzas ou estática flotante. A súa distribución está sesgada cara ao bordo dereito mediante unha distribución Beta.

### Curva de erosión

A función de erosión segue esta fórmula:

$$\text{erosión}(t) = \begin{cases} 0 & \text{se } t \leq t_{\varphi} \\ \left(\frac{t - t_{\varphi}}{T - t_{\varphi}}\right)^{2{,}5} & \text{se } t > t_{\varphi} \end{cases}$$

onde $T = 70$ s é a duración total. A potencia 2,5 garante que a erosión comeza de xeito suave e acelera dramaticamente ao final.

---

## Parámetros destacados

- **Duración analizada**: 70 s
- **Punto áureo**: ~43,3 s (liña vertical distorsionada)
- **Resolución PNG**: 6400 × 3600 px (200 ppp)
- **Paleta**: liñas verde-azulado escuro (`#1a3c3c`) sobre fondo transparente
- **Partículas de cinza**: 18.000 puntos na zona de disolución
- **Semente aleatoria**: 42 (resultados reproducibles)

## Requisitos

- Python 3
- librosa, matplotlib, numpy, scipy (instálanse automaticamente co script `executar_alala.command`)
