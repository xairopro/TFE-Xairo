# Instalación e configuración

Esta guía recolle os pasos necesarios para deixar o proxecto operativo nun equipo novo.

## Requisitos previos

- Python 3.10 ou superior.
- MuseScore 4 instalado e accesible dende o sistema.
- Un contorno virtual de Python situado en `~/Documents/entornos virtuales/`.

## 1. Crear o contorno virtual

```bash
mkdir -p "$HOME/Documents/entornos virtuales"
python3 -m venv "$HOME/Documents/entornos virtuales/venv-markov-melodias"
```

## 2. Activar o contorno

macOS e Linux:

```bash
source "$HOME/Documents/entornos virtuales/venv-markov-melodias/bin/activate"
```

Windows:

```powershell
$HOME/Documents/entornos virtuales/venv-markov-melodias/Scripts/Activate.ps1
```

## 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configurar MuseScore

O proxecto usa MuseScore para renderizar PNG, PDF e saídas derivadas da partitura. Revisa a constante `MUSESCORE_PATH` en `config.py`.

Exemplo habitual en macOS:

```python
MUSESCORE_PATH = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
```

Tamén podes indicar a ruta cunha variable de contorno:

```bash
export MUSESCORE_PATH="/ruta/ao/musescore"
```

## 5. Verificar a configuración

```bash
python3 config.py
```

Se a configuración é correcta, deberías ver:

- o cartafol base do proxecto,
- o cartafol temporal,
- a ruta de MuseScore,
- e unha confirmación de que MuseScore foi detectado.

## 6. Iniciar a aplicación

O método recomendado en macOS é:

```bash
./iniciar_markov.command
```

O script fai o seguinte:

- sitúase no cartafol do proxecto,
- pecha un proceso anterior no porto 5000 se o houbese,
- usa o contorno `~/Documents/entornos virtuales/venv-markov-melodias`,
- e inicia o servidor Flask.

Tamén podes iniciar a aplicación manualmente:

```bash
source "$HOME/Documents/entornos virtuales/venv-markov-melodias/bin/activate"
python3 markov_web.py
```

## 7. Enderezo local

A aplicación publícase por defecto en:

```text
http://127.0.0.1:5000
```

## Parámetros configurables

Os principais axustes están en `config.py`:

- `FLASK_PORT`: porto do servidor.
- `FLASK_HOST`: enderezo de escoita.
- `RUIDO_MELODIA_DEFAULT`: ruído melódico inicial.
- `RUIDO_RITMO_DEFAULT`: ruído rítmico inicial.
- `PROBABILIDAD_SILENCIO`: probabilidade de inserir silencios.
- `SIGMA_GAUSSIANA`: apertura da distribución gaussiana.

## Validación recomendada

Despois de instalar, convén executar:

```bash
python3 -m py_compile markov_web.py analise_muineira.py config.py
```

Se non hai saída, a sintaxe dos ficheiros Python é correcta.

## Incidencias frecuentes

### MuseScore non aparece detectado

- Verifica a ruta configurada en `config.py`.
- Comproba que o executábel existe realmente.
- Se usas unha instalación non estándar, define `MUSESCORE_PATH` na sesión actual.

### O porto 5000 xa está ocupado

Podes cambiar o porto en `config.py`:

```python
FLASK_PORT = 8080
```

Ou pechar o proceso que o estea a usar:

```bash
lsof -ti:5000 | xargs kill -9
```

### Faltan dependencias de Python

Asegúrate de ter o contorno virtual activado e reinstala os paquetes:

```bash
source "$HOME/Documents/entornos virtuales/venv-markov-melodias/bin/activate"
pip install -r requirements.txt
```

### O script de inicio non usa o Python correcto

A versión actual de `iniciar_markov.command` usa directamente `~/Documents/entornos virtuales/venv-markov-melodias/bin/python` se existe. Se non existe, cae a `python3` do sistema.

## Organización dos ficheiros temporais

O cartafol `temp/` utilízase para:

- MusicXML temporais de traballo,
- PNG xerados por MuseScore,
- PDF de saída,
- ficheiros de audio temporais cando o fluxo o require.

Son ficheiros auxiliares: poden borrarse e a aplicación volvelos crear cando faga falta.
