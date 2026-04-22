"""
================================================================================
CONFIGURACIÓN DO XERADOR DE MELODÍAS CON CADEAS DE MARKOV
================================================================================

Autor: Xairo Campos Blanco
Traballo Fin de Estudos - CSM da Coruña 2025-2026

Este arquivo centraliza todas as configuracións e rutas do proxecto,
facilitando a portabilidade entre diferentes ordenadores.

================================================================================
"""

import os
from pathlib import Path

# ============================================================================
# RUTAS DO PROXECTO
# ============================================================================

# Directorio base do proxecto (onde está este arquivo config.py)
BASE_DIR = Path(__file__).parent.absolute()

# Directorio de templates
TEMPLATES_DIR = BASE_DIR / "templates"

# Directorio de arquivos temporais (créase automaticamente se non existe)
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# ============================================================================
# CONFIGURACIÓN DE MUSESCORE
# ============================================================================

# Ruta de MuseScore 4 (modifica segundo a túa instalación)
# macOS (por defecto):
MUSESCORE_PATH = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

# Windows (exemplos):
# MUSESCORE_PATH = r'C:\Program Files\MuseScore 4\bin\MuseScore4.exe'

# Linux (exemplos):
# MUSESCORE_PATH = '/usr/bin/musescore'
# MUSESCORE_PATH = '/usr/local/bin/mscore'

# Variable de entorno (alternativa): export MUSESCORE_PATH="/ruta/a/musescore"
MUSESCORE_PATH = os.environ.get('MUSESCORE_PATH', MUSESCORE_PATH)

# ============================================================================
# ARQUIVOS DO PROXECTO
# ============================================================================

# Arquivo MusicXML de referencia (Muiñeira de Monterrei)
MUINEIRA_MONTERREI = BASE_DIR / "MuineiraMonterrei.mxl"

# Arquivos temporais
TEMP_PARTITURA_XML = TEMP_DIR / "temp_partitura_web.musicxml"
TEMP_PARTITURA_PNG = TEMP_DIR / "temp_partitura_web-1.png"
TEMP_PARTITURA_PNG_BASE = TEMP_DIR / "temp_partitura_web"
TEMP_PARTITURA_PDF = TEMP_DIR / "temp_partitura_web.pdf"
TEMP_PARTITURA_MP3 = TEMP_DIR / "temp_partitura_web.mp3"
TEMP_PARTITURA_MP3_VOZ1 = TEMP_DIR / "temp_partitura_voz1.mp3"
TEMP_PARTITURA_MP3_VOZ2 = TEMP_DIR / "temp_partitura_voz2.mp3"
TEMP_PARTITURA_XML_VOZ1 = TEMP_DIR / "temp_partitura_voz1.musicxml"
TEMP_PARTITURA_XML_VOZ2 = TEMP_DIR / "temp_partitura_voz2.musicxml"

# Arquivos de saída
OUTPUT_PARTITURA_BASE = BASE_DIR / "partitura_markov_web"
OUTPUT_ANALISE_PNG = BASE_DIR / "analise_movementos_muineira.png"

# ============================================================================
# CONFIGURACIÓN DA APLICACIÓN WEB
# ============================================================================

# Porto do servidor Flask
FLASK_PORT = 5000

# Modo debug (cambiar a False en produción)
FLASK_DEBUG = False

# Host (127.0.0.1 = só local, 0.0.0.0 = rede)
FLASK_HOST = '127.0.0.1'

# ============================================================================
# PARÁMETROS DO XERADOR DE MARKOV
# ============================================================================

# Ruído por defecto (%)
RUIDO_MELODIA_DEFAULT = 5
RUIDO_RITMO_DEFAULT = 5

# Probabilidade de silencios (%)
PROBABILIDAD_SILENCIO = 0.1  # 10%

# Parámetros de ossia
PROBABILIDAD_OSSIA_DEFAULT = 5  # 5%
PROBABILIDAD_CERRAR_OSSIA_DEFAULT = 20  # 20%

# Desviación estándar da distribución gaussiana
SIGMA_GAUSSIANA = 2.5

# ============================================================================
# CONFIGURACIÓN DE NOTACIÓN MUSICAL
# ============================================================================

# Compás por defecto
TIME_SIGNATURE = '6/8'

# Tempo por defecto (BPM)
TEMPO_BPM = 120

# Mapa de ritmos (quarterLength)
MAPA_RITMOS = {
    "Negra": 1.0,
    "Corchea": 0.5,
    "Semicorchea": 0.25,
    "Negra con puntillo": 1.5,
    "Blanca": 2.0
}

# Todas as notas cromáticas dispoñibles
TODAS_NOTAS = {
    "Do": "C", "Do#": "C#", "Re": "D", "Re#": "D#", "Mi": "E", "Fa": "F",
    "Fa#": "F#", "Sol": "G", "Sol#": "G#", "La": "A", "La#": "A#", "Si": "B"
}

# ============================================================================
# LÍMITES E VALIDACIÓNS
# ============================================================================

# Octavas mínima e máxima
OCTAVA_MIN = 3
OCTAVA_MAX = 6

# Número máximo de eventos a xerar de unha vez
MAX_EVENTOS = 1000

# Tamaño mínimo dunha escala
MIN_NOTAS_ESCALA = 2

# ============================================================================
# FUNCIÓNS AUXILIARES
# ============================================================================

def verificar_musescore():
    """Verifica se MuseScore está instalado na ruta especificada"""
    if not os.path.exists(MUSESCORE_PATH):
        print(f"⚠️  AVISO: MuseScore non atopado en {MUSESCORE_PATH}")
        print("   Configura a ruta correcta en config.py ou na variable MUSESCORE_PATH")
        return False
    return True

def crear_directorios():
    """Crea os directorios necesarios se non existen"""
    TEMP_DIR.mkdir(exist_ok=True)
    print(f"✓ Directorio temporal: {TEMP_DIR}")

def mostrar_configuracion():
    """Mostra a configuración actual"""
    print("\n" + "="*80)
    print("CONFIGURACIÓN DO SISTEMA")
    print("="*80)
    print(f"Directorio base:   {BASE_DIR}")
    print(f"Directorio temp:   {TEMP_DIR}")
    print(f"MuseScore:         {MUSESCORE_PATH}")
    print(f"Porto Flask:       {FLASK_PORT}")
    print(f"Muiñeira ref.:     {MUINEIRA_MONTERREI}")
    print("="*80 + "\n")

if __name__ == '__main__':
    # Test da configuración
    mostrar_configuracion()
    crear_directorios()
    if verificar_musescore():
        print("✓ MuseScore detectado correctamente")
    else:
        print("✗ MuseScore non detectado")
