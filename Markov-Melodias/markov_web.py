"""
================================================================================
XERADOR VISUAL DE MELODÍAS CON CADEAS DE MARKOV
Interface Web Interactiva
================================================================================

Autor: Xairo Campos Blanco
Traballo Fin de Estudos - CSM da Coruña 2025-2026

================================================================================
"""

from flask import Flask, render_template, jsonify, request, send_file
import random
import os
import base64
import numpy as np
import scipy.stats
from music21 import stream, note, chord, meter, tempo, metadata, environment, converter
from collections import Counter
import glob
from pathlib import Path
import subprocess

# Importar a configuración
import config

# Configuración de MuseScore
us = environment.UserSettings()
us['musicxmlPath'] = str(config.MUSESCORE_PATH)
us['musescoreDirectPNGPath'] = str(config.MUSESCORE_PATH)

app = Flask(__name__)

# Usar a configuración centralizada
todas_notas = config.TODAS_NOTAS
mapa_ritmos = config.MAPA_RITMOS
RUIDO_MELODIA = config.RUIDO_MELODIA_DEFAULT / 100
RUIDO_RITMO = config.RUIDO_RITMO_DEFAULT / 100
PROBABILIDAD_SILENCIO = config.PROBABILIDAD_SILENCIO

# Estado da aplicación
estado = {
    'partitura': None,
    'parte': None,
    'melodia': [],
    'iniciado': False,
    'escala_actual': [],  # Sen escala por defecto
    'tipo_distribucion': 'analisis',  # 'analisis' ou 'gaussiana'
    'probabilidades_analise': None,  # Probabilidades da análise interválica
    'probabilidades_ritmo_analise': None,  # Probabilidades rítmicas da análise
    'semilla': 0,  # Semente aleatoria para reproducibilidade
    'ruido_melodia': 5,  # % ruído melodía
    'ruido_ritmo': 5,  # % ruído ritmo
    # Sistema de ossia
    'ossia_activo': False,
    'probabilidad_ossia': 0.05,  # 5% por defecto
    'probabilidad_cerrar_ossia': 0.20,  # 20% por defecto
    'voces': [
        {
            'indice_actual': 0,
            'octava_actual': 4,
            'activa': True
        }
    ]
}

def xerar_movemento_gaussiano(ruido_config=None, escala_len=8):
    """Xera movemento melódico con distribución gaussiana centrada en 0
    
    A gaussiana está centrada na nota actual (movemento 0) e é simétrica:
    P(+n) = P(-n), favorecendo graus conxuntos (movementos pequenos).
    """
    if ruido_config is None:
        ruido_config = RUIDO_MELODIA
    
    foi_ruido = False
    if random.random() < ruido_config:
        foi_ruido = True
        # Con ruido: movemento aleatorio no rango do camiño máis curto
        rango = escala_len // 2
        movemento = random.randint(-rango, rango)
    else:
        # Distribución gaussiana: favorece movementos pequenos
        # sigma = 2.5 para ter maior dispersión e variabilidade
        sigma = 2.5
        movemento = int(np.random.normal(0, sigma))
        
        # Limitar ao rango do camiño máis curto (evita dar voltas innecesarias)
        rango = escala_len // 2
        movemento = max(-rango, min(rango, movemento))
    
    return movemento, foi_ruido

def xerar_movemento(ruido_config=None, tipo_distribucion='analisis', escala_len=8):
    """Xera o próximo movemento melódico"""
    if tipo_distribucion == 'gaussiana':
        return xerar_movemento_gaussiano(ruido_config, escala_len)
    
    # Distribución Muiñeira: USAR PROBABILIDADES DA ANÁLISE
    if ruido_config is None:
        ruido_config = RUIDO_MELODIA
    
    foi_ruido = False
    if random.random() < ruido_config:
        foi_ruido = True
        # Con ruido: movementos aleatorios
        rango = escala_len // 2
        movemento = random.randint(-rango, rango)
    else:
        # Usar probabilidades DA ANÁLISE
        if estado['probabilidades_analise'] is not None:
            probs = estado['probabilidades_analise']
            # CRÍTICO: Ordenar keys para garantir determinismo
            # A orde de iteración debe ser sempre a mesma para reproducibilidade
            movementos_posibles = sorted(probs.keys())
            probabilidades = [probs[m] for m in movementos_posibles]
            # Normalizar probabilidades
            total = sum(probabilidades)
            probabilidades = [p/total for p in probabilidades]
            # Escoller movemento segundo probabilidades
            movemento = random.choices(movementos_posibles, weights=probabilidades, k=1)[0]
        else:
            # Sen análise: movemento aleatorio uniforme
            rango = escala_len // 2
            movemento = random.randint(-rango, rango)
    return movemento, foi_ruido

def xerar_ritmo(ruido_config=None):
    """Xera a próxima duración rítmica"""
    if ruido_config is None:
        ruido_config = RUIDO_RITMO
    
    foi_ruido = False
    if random.random() < ruido_config:
        foi_ruido = True
        eventos_ritmicos = ["Corchea", "Negra", "Negra con puntillo", "Semicorchea"]
        ritmo = random.choice(eventos_ritmicos)
    else:
        # Usar probabilidades DA ANÁLISE
        if estado['probabilidades_ritmo_analise'] is not None:
            probs = estado['probabilidades_ritmo_analise']
            # CRÍTICO: Ordenar keys para garantir determinismo
            # Orde alfabética garantida para reproducibilidade
            duracións_posibles = sorted(probs.keys())
            probabilidades = [probs[d] for d in duracións_posibles]
            # Normalizar probabilidades
            total = sum(probabilidades)
            probabilidades = [p/total for p in probabilidades]
            # Escoller duración segundo probabilidades
            ritmo = random.choices(duracións_posibles, weights=probabilidades, k=1)[0]
        else:
            # Sen análise: duración aleatoria uniforme
            eventos_ritmicos = ["Corchea", "Negra", "Negra con puntillo", "Semicorchea"]
            ritmo = random.choice(eventos_ritmicos)
    return ritmo, foi_ruido

def xerar_duracion_silencio():
    """Xera a duración dun silencio: Corchea (0.5) ou Negra con puntillo (1.5)"""
    # 50% Corchea, 50% Negra con puntillo
    if random.random() < 0.5:
        return 0.5  # Corchea
    else:
        return 1.5  # Negra con puntillo

def clasificar_duracion(duracion):
    """Clasifica a duración dunha nota"""
    if duracion >= 3.0:
        return None  # Ignorar brancas con puntillo
    elif 1.25 <= duracion <= 1.75:
        return "Negra con puntillo"
    elif 0.75 <= duracion <= 1.25:
        return "Negra"
    elif 0.375 <= duracion <= 0.625:
        return "Corchea"
    elif duracion < 0.375:
        return "Semicorchea"
    return None

@app.route('/')
def index():
    return render_template('markov.html')

@app.route('/api/configurar_escala', methods=['POST'])
def configurar_escala():
    """Configura a escala personalizada"""
    data = request.json
    notas = data.get('notas', [])
    
    if len(notas) < 2:
        return jsonify({'success': False, 'error': 'Mínimo 2 notas'})
    
    # Validar que todas as notas existan
    for nota in notas:
        if nota not in todas_notas:
            return jsonify({'success': False, 'error': f'Nota non válida: {nota}'})
    
    # CRÍTICO: Ordenar cromáticamente para garantir determinismo
    # Independentemente da orde de clic, a orde interna sempre será a mesma
    notas_ordenadas = sorted(notas, key=lambda n: list(todas_notas.keys()).index(n))
    
    estado['escala_actual'] = notas_ordenadas
    return jsonify({'success': True, 'escala': notas_ordenadas})

@app.route('/api/obter_escala')
def obter_escala():
    """Devolve a escala actual"""
    return jsonify({'escala': estado['escala_actual']})

@app.route('/api/iniciar', methods=['POST'])
def iniciar():
    """Inicializa a partitura coa nota e ritmo inicial"""
    data = request.json
    nota_inicial = data.get('nota')
    ritmo_inicial = data.get('ritmo')
    tipo_distribucion = data.get('tipo_distribucion', 'analisis')
    semilla = data.get('semilla', 0)
    prob_ossia = data.get('probabilidad_ossia', 5) / 100
    prob_cerrar = data.get('probabilidad_cerrar_ossia', 20) / 100
    ruido_mel = data.get('ruido_melodia', 5)
    ruido_rit = data.get('ruido_ritmo', 5)
    
    # CRÍTICO: establecer unha semente reproducible
    # Usar int() para asegurar que é un enteiro válido
    semilla_int = int(semilla)
    random.seed(semilla_int)
    np.random.seed(semilla_int)
    
    # Para garantir reproducibilidade total, reiniciar completamente o estado
    # Facer algunhas chamadas de preparación para estabilizar o xerador
    _ = random.random()
    _ = np.random.random()
    # Reiniciar de novo coa semente para comezar desde un estado limpo
    random.seed(semilla_int)
    np.random.seed(semilla_int)
    
    # Gardar configuración no estado
    estado['tipo_distribucion'] = tipo_distribucion
    estado['semilla'] = semilla
    estado['probabilidad_ossia'] = prob_ossia
    estado['probabilidad_cerrar_ossia'] = prob_cerrar
    estado['ruido_melodia'] = ruido_mel
    estado['ruido_ritmo'] = ruido_rit
    estado['ossia_activo'] = False
    
    # Crear información completa no composer
    escala_str = '-'.join(estado['escala_actual'])
    tipo_str = 'Análise' if tipo_distribucion == 'analisis' else 'Gaussiana'
    parametros = f"{escala_str}, {tipo_str} ({ruido_mel}%, {ruido_rit}%, {int(prob_ossia*100)}%, {int(prob_cerrar*100)}%, {semilla})"
    
    # Crear nova partitura
    estado['partitura'] = stream.Score()
    estado['partitura'].metadata = metadata.Metadata()
    estado['partitura'].metadata.title = "Melodías de Markov"
    estado['partitura'].metadata.composer = f"Xairo Campos Blanco\n{parametros}"
    
    estado['parte'] = stream.Part()
    estado['parte'].append(meter.TimeSignature(config.TIME_SIGNATURE))
    estado['parte'].append(tempo.MetronomeMark(number=config.TEMPO_BPM))
    
    # Inicializar primeira voz
    indice = estado['escala_actual'].index(nota_inicial)
    nota_music21 = todas_notas[nota_inicial]
    duracion = mapa_ritmos[ritmo_inicial]
    
    estado['voces'] = [{
        'indice_actual': indice,
        'octava_actual': 4,
        'activa': True
    }]
    
    n = note.Note(nota_music21 + str(estado['voces'][0]['octava_actual']), quarterLength=duracion)
    estado['parte'].append(n)
    
    estado['melodia'] = [(indice, duracion, nota_inicial, ritmo_inicial)]
    estado['iniciado'] = True
    
    # Renderizar
    renderizar_partitura_temp()
    
    return jsonify({
        'success': True,
        'nota': nota_inicial,
        'ritmo': ritmo_inicial,
        'posicion': 1,
        'ossia_activo': False
    })

@app.route('/api/avanzar', methods=['POST'])
def avanzar():
    """Avanza un paso na melodía con soporte para ossia"""
    if not estado['iniciado']:
        return jsonify({'success': False})
    
    # Obter configuración do request
    data = request.json or {}
    ruido_mel_config = data.get('ruido_melodia', RUIDO_MELODIA * 100) / 100
    ruido_rit_config = data.get('ruido_ritmo', RUIDO_RITMO * 100) / 100
    tipo_dist = data.get('tipo_distribucion', estado.get('tipo_distribucion', 'analisis'))
    
    escala_len = len(estado['escala_actual'])
    
    # ===== COMPROBAR SE SE DISPARA OU PECHA OSSIA =====
    ossia_disparado = False
    ossia_pechado = False
    
    if not estado['ossia_activo']:
        # Probabilidade de activar a ossia
        if random.random() < estado['probabilidad_ossia']:
            ossia_disparado = True
            estado['ossia_activo'] = True
            # Crear segunda voz clonando o estado da primeira
            estado['voces'].append({
                'indice_actual': estado['voces'][0]['indice_actual'],
                'octava_actual': estado['voces'][0]['octava_actual'],
                'activa': True
            })
    else:
        # Probabilidade de pechar a ossia
        if random.random() < estado['probabilidad_cerrar_ossia']:
            ossia_pechado = True
            estado['ossia_activo'] = False
            # Manter só a primeira voz, eliminar a segunda
            estado['voces'] = [estado['voces'][0]]
    
    # ===== XERAR NOTAS PARA CADA VOZ ACTIVA =====
    notas_xeradas = []
    
    for i, voz in enumerate(estado['voces']):
        if not voz['activa']:
            continue
        
        # Decidir se xerar silencio
        es_silencio = random.random() < PROBABILIDAD_SILENCIO
        
        if es_silencio:
            # Xerar SILENCIO
            duracion_silencio = xerar_duracion_silencio()
            
            notas_xeradas.append({
                'nome': 'Silencio',
                'music21': None,
                'octava': voz['octava_actual'],  # Mantén octava (non se usa)
                'duracion': duracion_silencio,
                'ritmo_nome': 'Silencio',
                'indice': voz['indice_actual'],  # Mantén índice (nota fantasma)
                'voz': i,
                'es_silencio': True
            })
            # NON actualizar indice_actual nin octava_actual
            # A nota fantasma mantén a referencia para o seguinte evento
        else:
            # Xerar NOTA normal
            # Xerar movemento e ritmo INDEPENDENTES para cada voz
            movemento, ruido_mel = xerar_movemento(ruido_mel_config, tipo_dist, escala_len)
            ritmo_nome, ruido_rit = xerar_ritmo(ruido_rit_config)
            
            # Calcular nova nota usando o índice DESTA voz
            novo_indice = (voz['indice_actual'] + movemento) % escala_len
            
            # Xestionar octavas para ESTA voz
            nova_octava = voz['octava_actual']
            if voz['indice_actual'] + movemento < 0:
                nova_octava -= 1
            elif voz['indice_actual'] + movemento >= escala_len:
                nova_octava += 1
            
            # Limitar octavas
            nova_octava = max(3, min(6, nova_octava))
            
            # Actualizar o estado da voz (só se non é silencio)
            voz['indice_actual'] = novo_indice
            voz['octava_actual'] = nova_octava
            
            # Preparar nota
            nova_nota_nome = estado['escala_actual'][novo_indice]
            nota_music21 = todas_notas[nova_nota_nome]
            duracion = mapa_ritmos[ritmo_nome]
            
            notas_xeradas.append({
                'nome': nova_nota_nome,
                'music21': nota_music21,
                'octava': nova_octava,
                'duracion': duracion,
                'ritmo_nome': ritmo_nome,
                'indice': novo_indice,
                'voz': i,
                'es_silencio': False
            })
    
    # ===== RENDERIZAR NA PARTITURA =====
    if len(notas_xeradas) == 1:
        # Unha soa voz: nota simple ou silencio
        nota_info = notas_xeradas[0]
        if nota_info.get('es_silencio', False):
            # Crear SILENCIO
            r = note.Rest(quarterLength=nota_info['duracion'])
            estado['parte'].append(r)
        else:
            # Crear NOTA normal
            n = note.Note(
                nota_info['music21'] + str(nota_info['octava']),
                quarterLength=nota_info['duracion']
            )
            estado['parte'].append(n)
    else:
        # Ossia: manexar notas e silencios
        # Filtrar silencios e notas reais
        notas_reais = [n for n in notas_xeradas if not n.get('es_silencio', False)]
        silencios = [n for n in notas_xeradas if n.get('es_silencio', False)]
        
        if len(notas_reais) == 0:
            # Ambas voces son silencios: crear un silencio coa duración máis longa
            duracion_max = max(n['duracion'] for n in silencios)
            r = note.Rest(quarterLength=duracion_max)
            estado['parte'].append(r)
        elif len(notas_reais) == 1:
            # Unha voz é silencio, outra é nota: crear só a nota
            nota_info = notas_reais[0]
            n = note.Note(
                nota_info['music21'] + str(nota_info['octava']),
                quarterLength=nota_info['duracion']
            )
            estado['parte'].append(n)
        else:
            # Ambas voces son notas: crear acorde
            duracion_max = max(n['duracion'] for n in notas_reais)
            
            # Crear notas para o acorde
            notas_chord = []
            for i, n_info in enumerate(notas_reais):
                n = note.Note(
                    n_info['music21'] + str(n_info['octava']),
                    quarterLength=duracion_max  # Todas coa mesma duración no acorde
                )
                # Diferenciar voces con dirección de plicas
                if i == 0:
                    n.stemDirection = 'up'
                else:
                    n.stemDirection = 'down'
                
                # Cores diferentes para cada voz
                if i == 0:
                    n.style.color = '#2196F3'  # Azul para voz 1
                else:
                    n.style.color = '#F44336'  # Vermello para voz 2
                
                notas_chord.append(n)
            
            # Crear acorde
            c = chord.Chord(notas_chord)
            c.quarterLength = duracion_max
            estado['parte'].append(c)
    
    # Renderizar
    renderizar_partitura_temp()
    
    # Preparar resposta
    response_data = {
        'success': True,
        'posicion': len(estado['melodia']) + 1,
        'ossia_activo': estado['ossia_activo'],
        'ossia_disparado': ossia_disparado,
        'ossia_pechado': ossia_pechado,
        'notas': [
            {
                'nota': n['nome'],
                'ritmo': n['ritmo_nome'],
                'voz': n['voz']
            } for n in notas_xeradas
        ]
    }
    
    # Actualizar melodía (gardamos info da primeira voz principalmente)
    estado['melodia'].append(notas_xeradas[0])
    
    return jsonify(response_data)

@app.route('/api/probabilidades', methods=['GET', 'POST'])
def probabilidades():
    """Devolve as probabilidades de melodía e ritmo relativas á nota actual"""
    # Obter tipo de distribución do request (se POST) ou do estado
    tipo_dist = 'analisis'
    if request.method == 'POST':
        data = request.json or {}
        tipo_dist = data.get('tipo_distribucion', estado.get('tipo_distribucion', 'analisis'))
    else:
        tipo_dist = estado.get('tipo_distribucion', 'analisis')
    
    escala_usar = estado['escala_actual']
    escala_len = len(escala_usar)
    probs_melodia = []
    
    if tipo_dist == 'gaussiana':
        # DISTRIBUCIÓN GAUSSIANA: centrada na nota actual (movemento 0)
        # Simétrica: P(+n) = P(-n)
        sigma = 2.5  # Aumentada para maior varianza
        
        if estado['iniciado']:
            # Usar o índice da primeira voz
            indice_actual = estado['voces'][0]['indice_actual']
            probs_raw = {}
            
            # Para cada nota, calcular o movemento MÁIS CURTO (camiño óptimo)
            for i, nota in enumerate(escala_usar):
                movemento_directo = i - indice_actual
                
                # Escoller o camiño máis curto en valor absoluto
                # Se a distancia directa é maior que a metade da escala, é máis curto dar a volta
                if abs(movemento_directo) <= escala_len / 2:
                    movemento = movemento_directo
                else:
                    # Dando a volta é máis curto
                    if movemento_directo > 0:
                        movemento = movemento_directo - escala_len
                    else:
                        movemento = movemento_directo + escala_len
                
                # Calcular probabilidade gaussiana centrada en 0
                prob = scipy.stats.norm.pdf(movemento, 0, sigma)
                probs_raw[nota] = prob
            
            # Normalizar a 100%
            total = sum(probs_raw.values())
            for nota in escala_usar:
                prob_norm = (probs_raw[nota] / total) * 100.0 if total > 0 else 0.0
                # Para gaussiana, ascendente e descendente son iguais (simétrica)
                probs_melodia.append({
                    'nota': nota, 
                    'prob_ascendente': prob_norm,
                    'prob_descendente': prob_norm
                })
        else:
            # Se non está iniciado, distribución uniforme
            prob_uniforme = 100.0 / escala_len if escala_len > 0 else 0.0
            for nota in escala_usar:
                probs_melodia.append({
                    'nota': nota, 
                    'prob_ascendente': prob_uniforme,
                    'prob_descendente': prob_uniforme
                })
    
    else:
        # DISTRIBUCIÓN MUIÑEIRA: usar probabilidades da ANÁLISE
        # IMPORTANTE: Sempre mostrar as notas da ESCALA DE XERACIÓN, non da análise
        escala_usar = estado['escala_actual']
        escala_len = len(escala_usar)
        
        if estado['iniciado'] and estado['probabilidades_analise'] is not None:
            movementos_probs = estado['probabilidades_analise']
            indice_actual = estado['voces'][0]['indice_actual']
            
            # Primeiro paso: calcular probabilidades brutas para cada nota DA ESCALA DE XERACIÓN
            probs_raw_asc = {}
            probs_raw_desc = {}
            
            for i, nota in enumerate(escala_usar):
                # Calcular AMBAS as direccións posibles
                movemento_directo = i - indice_actual
                
                # Calcular movemento alternativo (dando a volta)
                if movemento_directo > 0:
                    movemento_alternativo = movemento_directo - escala_len
                elif movemento_directo < 0:
                    movemento_alternativo = movemento_directo + escala_len
                else:
                    movemento_alternativo = 0  # Repetición
                
                # Obter probabilidades de AMBAS as direccións (xa en %)
                # As probabilidades da análise refírense a MOVEMENTOS, non a notas específicas
                prob_directa = movementos_probs.get(movemento_directo, 0.0)
                prob_alternativa = movementos_probs.get(movemento_alternativo, 0.0)
                
                # Determinar cal é ascendente e cal descendente
                if movemento_directo > 0:
                    probs_raw_asc[nota] = prob_directa
                    probs_raw_desc[nota] = prob_alternativa
                elif movemento_directo < 0:
                    probs_raw_asc[nota] = prob_alternativa
                    probs_raw_desc[nota] = prob_directa
                else:  # movemento_directo == 0 (repetición)
                    probs_raw_asc[nota] = prob_directa
                    probs_raw_desc[nota] = prob_directa
            
            # Segundo paso: normalizar para que a suma sexa 100%
            total_asc = sum(probs_raw_asc.values())
            total_desc = sum(probs_raw_desc.values())
            
            for nota in escala_usar:
                prob_asc_norm = (probs_raw_asc[nota] / total_asc * 100.0) if total_asc > 0 else 0.0
                prob_desc_norm = (probs_raw_desc[nota] / total_desc * 100.0) if total_desc > 0 else 0.0
                
                probs_melodia.append({
                    'nota': nota, 
                    'prob_ascendente': prob_asc_norm,
                    'prob_descendente': prob_desc_norm
                })
        else:
            # Se non está iniciado ou sen análise, mostrar escala sen probabilidades específicas
            prob_uniforme = 100.0 / escala_len if escala_len > 0 else 0.0
            for nota in escala_usar:
                probs_melodia.append({
                    'nota': nota, 
                    'prob_ascendente': prob_uniforme,
                    'prob_descendente': prob_uniforme
                })
    
    # Probabilidades ritmo
    if estado['probabilidades_ritmo_analise'] is not None:
        # USAR PROBABILIDADES DA ANÁLISE POSICIONAL
        probs_ritmo = []
        for duracion, prob in estado['probabilidades_ritmo_analise'].items():
            probs_ritmo.append({'nome': duracion, 'probabilidade': prob})
        # Ordenar por probabilidade descendente
        probs_ritmo.sort(key=lambda x: x['probabilidade'], reverse=True)
    else:
        # Sen análise: distribución uniforme
        duracions = ['Corchea', 'Negra', 'Negra con puntillo', 'Semicorchea']
        prob_uniforme = 100.0 / len(duracions)
        probs_ritmo = [{'nome': d, 'probabilidade': prob_uniforme} for d in duracions]
    
    return jsonify({
        'melodia': probs_melodia,
        'ritmo': probs_ritmo,
        'escala': escala_usar
    })
@app.route('/api/xerar_eventos', methods=['POST'])
def xerar_eventos():
    """Xera múltiples eventos de unha vez con soporte para ossia"""
    if not estado['iniciado']:
        return jsonify({'success': False, 'error': 'Non iniciado'})
    
    data = request.json
    num_eventos = data.get('eventos', 10)
    ruido_mel_config = data.get('ruido_melodia', RUIDO_MELODIA * 100) / 100
    ruido_rit_config = data.get('ruido_ritmo', RUIDO_RITMO * 100) / 100
    tipo_dist = data.get('tipo_distribucion', estado.get('tipo_distribucion', 'analisis'))
    
    if num_eventos < 1 or num_eventos > config.MAX_EVENTOS:
        return jsonify({'success': False, 'error': f'O número de eventos debe estar entre 1 e {config.MAX_EVENTOS}'})
    
    try:
        escala_len = len(estado['escala_actual'])
        
        for _ in range(num_eventos):
            # ===== COMPROBAR SE SE DISPARA OU PECHA OSSIA =====
            if not estado['ossia_activo']:
                # Probabilidade de activar a ossia
                if random.random() < estado['probabilidad_ossia']:
                    estado['ossia_activo'] = True
                    # Crear segunda voz clonando o estado da primeira
                    estado['voces'].append({
                        'indice_actual': estado['voces'][0]['indice_actual'],
                        'octava_actual': estado['voces'][0]['octava_actual'],
                        'activa': True
                    })
            else:
                # Probabilidade de pechar a ossia
                if random.random() < estado['probabilidad_cerrar_ossia']:
                    estado['ossia_activo'] = False
                    # Manter só a primeira voz, eliminar a segunda
                    estado['voces'] = [estado['voces'][0]]
            
            # ===== XERAR NOTAS PARA CADA VOZ ACTIVA =====
            notas_xeradas = []
            
            for i, voz in enumerate(estado['voces']):
                if not voz['activa']:
                    continue
                
                # Decidir se xerar silencio
                es_silencio = random.random() < PROBABILIDAD_SILENCIO
                
                if es_silencio:
                    # Xerar SILENCIO
                    duracion_silencio = xerar_duracion_silencio()
                    
                    notas_xeradas.append({
                        'nome': 'Silencio',
                        'music21': None,
                        'octava': voz['octava_actual'],
                        'duracion': duracion_silencio,
                        'ritmo_nome': 'Silencio',
                        'indice': voz['indice_actual'],
                        'voz': i,
                        'es_silencio': True
                    })
                    # NON actualizar indice_actual nin octava_actual
                else:
                    # Xerar NOTA normal
                    # Xerar movemento e ritmo INDEPENDENTES para cada voz
                    movemento, ruido_mel = xerar_movemento(ruido_mel_config, tipo_dist, escala_len)
                    ritmo_nome, ruido_rit = xerar_ritmo(ruido_rit_config)
                    
                    # Calcular nova nota usando o índice DESTA voz
                    novo_indice = (voz['indice_actual'] + movemento) % escala_len
                    
                    # Xestionar octavas para ESTA voz
                    nova_octava = voz['octava_actual']
                    if voz['indice_actual'] + movemento < 0:
                        nova_octava -= 1
                    elif voz['indice_actual'] + movemento >= escala_len:
                        nova_octava += 1
                    
                    # Limitar octavas
                    nova_octava = max(3, min(6, nova_octava))
                    
                    # Actualizar o estado da voz (só se non é silencio)
                    voz['indice_actual'] = novo_indice
                    voz['octava_actual'] = nova_octava
                    
                    # Preparar nota
                    nova_nota_nome = estado['escala_actual'][novo_indice]
                    nota_music21 = todas_notas[nova_nota_nome]
                    duracion = mapa_ritmos[ritmo_nome]
                    
                    notas_xeradas.append({
                        'nome': nova_nota_nome,
                        'music21': nota_music21,
                        'octava': nova_octava,
                        'duracion': duracion,
                        'ritmo_nome': ritmo_nome,
                        'indice': novo_indice,
                        'voz': i,
                        'es_silencio': False
                    })
            
            # ===== RENDERIZAR NA PARTITURA =====
            if len(notas_xeradas) == 1:
                # Unha soa voz: nota simple ou silencio
                nota_info = notas_xeradas[0]
                if nota_info.get('es_silencio', False):
                    # Crear SILENCIO
                    r = note.Rest(quarterLength=nota_info['duracion'])
                    estado['parte'].append(r)
                else:
                    # Crear NOTA normal
                    n = note.Note(
                        nota_info['music21'] + str(nota_info['octava']),
                        quarterLength=nota_info['duracion']
                    )
                    estado['parte'].append(n)
            else:
                # Ossia: crear acorde con plicas en direccións diferentes
                duracion_max = max(n['duracion'] for n in notas_xeradas)
                
                # Crear notas para o acorde
                notas_chord = []
                for i, n_info in enumerate(notas_xeradas):
                    n = note.Note(
                        n_info['music21'] + str(n_info['octava']),
                        quarterLength=duracion_max
                    )
                    # Diferenciar voces con dirección de plicas
                    if i == 0:
                        n.stemDirection = 'up'
                    else:
                        n.stemDirection = 'down'
                    
                    # Cores diferentes para cada voz
                    if i == 0:
                        n.style.color = '#2196F3'  # Azul para voz 1
                    else:
                        n.style.color = '#F44336'  # Vermello para voz 2
                    
                    notas_chord.append(n)
                
                # Crear acorde
                c = chord.Chord(notas_chord)
                c.quarterLength = duracion_max
                estado['parte'].append(c)
            
            # Actualizar melodía
            estado['melodia'].append(notas_xeradas[0])
        
        # Renderizar a partitura INMEDIATAMENTE despois de xerar
        # E devolver a imaxe directamente na resposta
        renderizar_partitura_temp()
        
        # Ler a imaxe renderizada
        ruta_png = str(config.TEMP_PARTITURA_PNG)
        img_data = None
        if os.path.exists(ruta_png):
            with open(ruta_png, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'total_notas': len(estado['melodia']),
            'ultima_nota': estado['escala_actual'][estado['voces'][0]['indice_actual']],
            'ossia_activo': estado['ossia_activo'],
            'renderizado': True,  # Indica que xa está renderizada
            'imaxe': img_data  # Devolver imaxe directamente
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/api/partitura')
def partitura():
    """Devolve a imaxe da partitura actual (sen volver renderizar)"""
    # NON renderizar aquí - a partitura xa foi renderizada en xerar_eventos ou xerar_nota
    ruta_png = str(config.TEMP_PARTITURA_PNG)
    if os.path.exists(ruta_png):
        with open(ruta_png, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        return jsonify({'success': True, 'imaxe': img_data})
    return jsonify({'success': False})

@app.route('/api/partitura_pdf')
def partitura_pdf():
    """Xera e devolve a partitura en PDF"""
    if not estado['iniciado']:
        return jsonify({'success': False})
    
    try:
        temp_score = stream.Score()
        temp_score.metadata = estado['partitura'].metadata
        temp_score.append(estado['parte'])
        
        ruta_pdf = str(config.TEMP_PARTITURA_PDF)
        temp_score.write('musicxml.pdf', fp=ruta_pdf.replace('.pdf', ''))
        
        return send_file(ruta_pdf, as_attachment=True, download_name='partitura_markov.pdf')
    except Exception as e:
        print(f"Erro ao xerar PDF: {e}")
        return jsonify({'success': False, 'error': str(e)})

def extraer_voz(parte_orixinal, voz_numero):
    """Extrae só unha voz dunha partitura con ossia
    voz_numero: 1 ou 2
    As notas simples e silencios mantéñense en ambas voces
    """
    parte_nova = stream.Part()
    
    # Copiar metadatos (compás, tempo, etc.)
    for elemento in parte_orixinal:
        if isinstance(elemento, (meter.TimeSignature, tempo.MetronomeMark)):
            parte_nova.append(elemento)
    
    # Procesar notas e acordes
    for elemento in parte_orixinal.flatten().notesAndRests:
        if isinstance(elemento, note.Rest):
            # Silencios van a ambas voces
            parte_nova.append(elemento)
        elif isinstance(elemento, note.Note):
            # Notas simples van a ambas voces
            parte_nova.append(elemento)
        elif isinstance(elemento, chord.Chord):
            # Acordes: extraer só a nota da voz correspondente
            notas_do_acorde = list(elemento.pitches)
            
            if len(notas_do_acorde) >= voz_numero:
                # Extraer a nota correspondente
                if voz_numero == 1:
                    # Voz 1: primeira nota (plica arriba, azul)
                    pitch_extraida = notas_do_acorde[0]
                else:
                    # Voz 2: segunda nota (plica abaixo, vermella)
                    pitch_extraida = notas_do_acorde[-1]
                
                # Crear nova nota con esa altura
                nota_nova = note.Note(pitch_extraida, quarterLength=elemento.quarterLength)
                parte_nova.append(nota_nova)
            else:
                # Se o acorde ten menos notas do esperado, usar a primeira
                nota_nova = note.Note(notas_do_acorde[0], quarterLength=elemento.quarterLength)
                parte_nova.append(nota_nova)
    
    return parte_nova

def ten_ossia_na_partitura(parte):
    """Detecta se a partitura ten acordes (ossia activo en algún momento)"""
    for elemento in parte.flatten():
        if isinstance(elemento, chord.Chord):
            return True
    return False

@app.route('/api/exportar_audio', methods=['POST'])
def exportar_audio():
    """Exporta a partitura actual a MP3 usando MuseScore
    Se hai ossia, exporta 3 versións: completa, voz1, voz2
    """
    if not estado['iniciado']:
        return jsonify({'success': False, 'error': 'Non hai partitura para exportar'})
    
    try:
        # Crear partitura completa
        temp_score = stream.Score()
        temp_score.metadata = estado['partitura'].metadata
        temp_score.append(estado['parte'])
        
        # Detectar se hai ossia
        hai_ossia = ten_ossia_na_partitura(estado['parte'])
        
        # Exportar partitura completa
        ruta_xml = str(config.TEMP_PARTITURA_XML)
        temp_score.write('musicxml', fp=ruta_xml)
        
        ruta_mp3 = str(config.TEMP_PARTITURA_MP3)
        cmd = [str(config.MUSESCORE_PATH), ruta_xml, '-o', ruta_mp3]
        print(f"Exportando audio completo: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Erro MuseScore: {result.stderr}")
            return jsonify({'success': False, 'error': 'Erro ao exportar audio'})
        
        if not os.path.exists(ruta_mp3):
            return jsonify({'success': False, 'error': 'Ficheiro de audio non se creou'})
        
        print(f"✓ Audio completo exportado: {ruta_mp3}")
        
        # Se hai ossia, exportar voces separadas
        if hai_ossia:
            # Voz 1
            parte_voz1 = extraer_voz(estado['parte'], 1)
            score_voz1 = stream.Score()
            score_voz1.metadata = estado['partitura'].metadata
            score_voz1.append(parte_voz1)
            
            ruta_xml_voz1 = str(config.TEMP_PARTITURA_XML_VOZ1)
            score_voz1.write('musicxml', fp=ruta_xml_voz1)
            
            ruta_mp3_voz1 = str(config.TEMP_PARTITURA_MP3_VOZ1)
            cmd_voz1 = [str(config.MUSESCORE_PATH), ruta_xml_voz1, '-o', ruta_mp3_voz1]
            print(f"Exportando voz 1: {' '.join(cmd_voz1)}")
            result_voz1 = subprocess.run(cmd_voz1, capture_output=True, text=True, timeout=30)
            
            if result_voz1.returncode == 0 and os.path.exists(ruta_mp3_voz1):
                print(f"✓ Audio voz 1 exportado: {ruta_mp3_voz1}")
            
            # Voz 2
            parte_voz2 = extraer_voz(estado['parte'], 2)
            score_voz2 = stream.Score()
            score_voz2.metadata = estado['partitura'].metadata
            score_voz2.append(parte_voz2)
            
            ruta_xml_voz2 = str(config.TEMP_PARTITURA_XML_VOZ2)
            score_voz2.write('musicxml', fp=ruta_xml_voz2)
            
            ruta_mp3_voz2 = str(config.TEMP_PARTITURA_MP3_VOZ2)
            cmd_voz2 = [str(config.MUSESCORE_PATH), ruta_xml_voz2, '-o', ruta_mp3_voz2]
            print(f"Exportando voz 2: {' '.join(cmd_voz2)}")
            result_voz2 = subprocess.run(cmd_voz2, capture_output=True, text=True, timeout=30)
            
            if result_voz2.returncode == 0 and os.path.exists(ruta_mp3_voz2):
                print(f"✓ Audio voz 2 exportado: {ruta_mp3_voz2}")
        else:
            # Sen ossia: copiar o audio completo para voz1 e voz2 (ambas iguais)
            import shutil
            ruta_mp3_voz1 = str(config.TEMP_PARTITURA_MP3_VOZ1)
            ruta_mp3_voz2 = str(config.TEMP_PARTITURA_MP3_VOZ2)
            shutil.copy2(ruta_mp3, ruta_mp3_voz1)
            shutil.copy2(ruta_mp3, ruta_mp3_voz2)
            print(f"✓ Audio copiado a voz1 e voz2 (sen ossia)")
        
        return jsonify({'success': True, 'ten_ossia': hai_ossia})
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Timeout ao exportar audio'})
    except Exception as e:
        print(f"Erro ao exportar audio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/audio')
def obter_audio():
    """Sirve o ficheiro de audio MP3 completo"""
    ruta_mp3 = str(config.TEMP_PARTITURA_MP3)
    if not os.path.exists(ruta_mp3):
        return jsonify({'success': False, 'error': 'Audio non dispoñible'})
    
    return send_file(ruta_mp3, mimetype='audio/mpeg')

@app.route('/api/audio_voz1')
def obter_audio_voz1():
    """Sirve o ficheiro de audio MP3 da voz 1"""
    ruta_mp3 = str(config.TEMP_PARTITURA_MP3_VOZ1)
    if not os.path.exists(ruta_mp3):
        return jsonify({'success': False, 'error': 'Audio voz 1 non dispoñible'})
    
    return send_file(ruta_mp3, mimetype='audio/mpeg')

@app.route('/api/audio_voz2')
def obter_audio_voz2():
    """Sirve o ficheiro de audio MP3 da voz 2"""
    ruta_mp3 = str(config.TEMP_PARTITURA_MP3_VOZ2)
    if not os.path.exists(ruta_mp3):
        return jsonify({'success': False, 'error': 'Audio voz 2 non dispoñible'})
    
    return send_file(ruta_mp3, mimetype='audio/mpeg')

@app.route('/api/gardar', methods=['POST'])
def gardar():
    """Garda a partitura final"""
    if not estado['iniciado']:
        return jsonify({'success': False, 'error': 'Non iniciado'})
    
    # Gardar partitura final
    partitura_final = stream.Score()
    partitura_final.metadata = estado['partitura'].metadata
    partitura_final.append(estado['parte'])
    
    ruta_base = str(config.OUTPUT_PARTITURA_BASE)
    
    ruta_xml = ruta_base + ".musicxml"
    partitura_final.write('musicxml', fp=ruta_xml)
    partitura_final.write('musicxml.png', fp=ruta_base)
    
    # Limpar temporais
    limpar_temporais()
    
    return jsonify({
        'success': True,
        'total_notas': len(estado['melodia']),
        'musicxml': os.path.basename(ruta_xml),
        'png': os.path.basename(ruta_base + '-1.png')
    })

@app.route('/api/listar_xml')
def listar_xml():
    """Lista todos os ficheiros XML na carpeta"""
    carpeta = str(config.BASE_DIR)
    ficheiros = glob.glob(os.path.join(carpeta, "*.mxl")) + glob.glob(os.path.join(carpeta, "*.musicxml"))
    ficheiros = [os.path.basename(f) for f in ficheiros]
    return jsonify({'ficheiros': ficheiros})

@app.route('/api/analizar_histograma', methods=['POST'])
def analizar_histograma():
    """Xera histogramas de análise e devólveos como base64"""
    data = request.json
    ficheiro = data.get('ficheiro')
    escala_analise = data.get('escala', [])
    
    if not ficheiro:
        return jsonify({'success': False, 'error': 'Non se especificou ficheiro'})
    
    if len(escala_analise) < config.MIN_NOTAS_ESCALA:
        return jsonify({'success': False, 'error': f'A escala debe ter polo menos {config.MIN_NOTAS_ESCALA} notas'})
    
    ruta = os.path.join(str(config.BASE_DIR), ficheiro)
    
    if not os.path.exists(ruta):
        return jsonify({'success': False, 'error': 'Ficheiro non atopado'})
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        
        # Cargar partitura
        partitura = converter.parse(ruta)
        notas = partitura.flatten().notes
        
        # Crear mapa de notas da escala personalizada (ordenadas)
        escala_ordenada = sorted(escala_analise, key=lambda n: list(todas_notas.keys()).index(n))
        mapa_escala = {todas_notas[n]: i for i, n in enumerate(escala_ordenada)}
        
        # Analizar movementos e duracións - SÓ NOTAS NA ESCALA
        movementos = []
        duracións_lista = []
        
        for i in range(len(notas) - 1):
            if notas[i].isNote and notas[i+1].isNote:
                nota1 = notas[i].pitch.name
                nota2 = notas[i+1].pitch.name
                
                # SÓ analizar se ambas notas están na escala
                if nota1 in mapa_escala and nota2 in mapa_escala:
                    idx1 = mapa_escala[nota1]
                    idx2 = mapa_escala[nota2]
                    movemento = idx2 - idx1
                    movementos.append(movemento)
            
            if notas[i].isNote:
                duracion = notas[i].quarterLength
                clase = clasificar_duracion(duracion)
                if clase:
                    duracións_lista.append(clase)
        
        # Contar frecuencias
        movementos_count = Counter(movementos)
        duracións_count = Counter(duracións_lista)
        
        # Crear figura con 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        fig.patch.set_facecolor('#f8f9fa')
        
        # Histograma de movementos
        movs_sorted = sorted(movementos_count.keys())
        freqs_mov = [movementos_count[m] for m in movs_sorted]
        
        bars1 = ax1.bar(range(len(movs_sorted)), freqs_mov, color='#667eea', edgecolor='#764ba2', linewidth=1.5)
        ax1.set_xticks(range(len(movs_sorted)))
        ax1.set_xticklabels([f"{m:+d}" if m != 0 else "0" for m in movs_sorted], fontsize=10)
        ax1.set_xlabel('Movemento Melódico', fontweight='bold', fontsize=11)
        ax1.set_ylabel('Frecuencia', fontweight='bold', fontsize=11)
        ax1.set_title('Distribución de Movementos Melódicos', fontweight='bold', fontsize=12, color='#667eea')
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.set_facecolor('#ffffff')
        
        # Histograma de duracións
        ritmos_orden = ["Semicorchea", "Corchea", "Negra", "Negra con puntillo"]
        freqs_rit = [duracións_count.get(r, 0) for r in ritmos_orden]
        
        bars2 = ax2.bar(range(len(ritmos_orden)), freqs_rit, color='#764ba2', edgecolor='#667eea', linewidth=1.5)
        ax2.set_xticks(range(len(ritmos_orden)))
        ax2.set_xticklabels(ritmos_orden, rotation=15, ha='right', fontsize=9)
        ax2.set_xlabel('Duración Rítmica', fontweight='bold', fontsize=11)
        ax2.set_ylabel('Frecuencia', fontweight='bold', fontsize=11)
        ax2.set_title('Distribución de Duracións Rítmicas', fontweight='bold', fontsize=12, color='#764ba2')
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        ax2.set_facecolor('#ffffff')
        
        plt.tight_layout()
        
        # Gardar a base64
        import io
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#f8f9fa')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return jsonify({'success': True, 'imaxe': img_base64})
        
    except Exception as e:
        print(f"Erro ao xerar histograma: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analizar_xml', methods=['POST'])
def analizar_xml():
    """Analiza un ficheiro XML e devolve movementos e duracións"""
    data = request.json
    ficheiro = data.get('ficheiro')
    escala_analise = data.get('escala', [])
    
    if not ficheiro:
        return jsonify({'success': False, 'error': 'Non se especificou ficheiro'})
    
    if len(escala_analise) < config.MIN_NOTAS_ESCALA:
        return jsonify({'success': False, 'error': f'A escala debe ter polo menos {config.MIN_NOTAS_ESCALA} notas'})
    
    ruta = os.path.join(str(config.BASE_DIR), ficheiro)
    
    if not os.path.exists(ruta):
        return jsonify({'success': False, 'error': 'Ficheiro non atopado'})
    
    try:
        # Cargar partitura
        partitura = converter.parse(ruta)
        notas = partitura.flatten().notes
        
        # Crear mapa de notas da escala personalizada (ordenadas de baixo a arriba)
        escala_ordenada = sorted(escala_analise, key=lambda n: list(todas_notas.keys()).index(n))
        mapa_escala = {todas_notas[n]: i for i, n in enumerate(escala_ordenada)}
        
        # Analizar movementos e duracións - SÓ NOTAS NA ESCALA
        movementos = []
        duracións_lista = []
        
        for i in range(len(notas) - 1):
            if notas[i].isNote and notas[i+1].isNote:
                nota1 = notas[i].pitch.name
                nota2 = notas[i+1].pitch.name
                
                # SÓ analizar se ambas notas están na escala
                if nota1 in mapa_escala and nota2 in mapa_escala:
                    idx1 = mapa_escala[nota1]
                    idx2 = mapa_escala[nota2]
                    movemento = idx2 - idx1
                    movementos.append(movemento)
            
            # Clasificar duración
            if notas[i].isNote:
                duracion = notas[i].quarterLength
                clase = clasificar_duracion(duracion)
                if clase:
                    duracións_lista.append(clase)
        
        # Contar frecuencias
        movementos_count = Counter(movementos)
        duracións_count = Counter(duracións_lista)
        
        total_movementos = sum(movementos_count.values())
        total_duracións = sum(duracións_count.values())
        
        # *** GARDAR PROBABILIDADES NO ESTADO GLOBAL ***
        probs_mov = {}
        for mov, freq in movementos_count.items():
            probs_mov[mov] = (freq / total_movementos * 100.0) if total_movementos > 0 else 0.0
        
        probs_dur = {}
        for dur, freq in duracións_count.items():
            probs_dur[dur] = (freq / total_duracións * 100.0) if total_duracións > 0 else 0.0
        
        estado['probabilidades_analise'] = probs_mov
        estado['probabilidades_ritmo_analise'] = probs_dur
        estado['escala_analise'] = escala_ordenada  # GARDAR A ESCALA USADA NA ANÁLISE
        
        print(f"=== PROBABILIDADES GARDADAS ===")
        print(f"Escala de análise: {escala_ordenada}")
        print(f"Movementos: {probs_mov}")
        print(f"Duracións: {probs_dur}")
        
        # Preparar resultados
        resultado_movementos = []
        for mov in sorted(movementos_count.keys()):
            freq = movementos_count[mov]
            porc = (freq / total_movementos * 100) if total_movementos > 0 else 0
            if mov > 0:
                nome = f"Ascenso {mov} pos (+{mov})"
            elif mov < 0:
                nome = f"Descenso {abs(mov)} pos ({mov})"
            else:
                nome = "Repetición (0)"
            resultado_movementos.append({
                'movemento': nome,
                'frecuencia': freq,
                'porcentaxe': porc
            })
        
        resultado_duracións = []
        for dur in ["Semicorchea", "Corchea", "Negra", "Negra con puntillo"]:
            freq = duracións_count.get(dur, 0)
            porc = (freq / total_duracións * 100) if total_duracións > 0 else 0
            resultado_duracións.append({
                'duracion': dur,
                'frecuencia': freq,
                'porcentaxe': porc
            })
        
        return jsonify({
            'success': True,
            'movementos': resultado_movementos,
            'duracións': resultado_duracións,
            'total_notas': len(notas)
        })
        
    except Exception as e:
        print(f"Erro ao analizar: {e}")
        return jsonify({'success': False, 'error': str(e)})

def renderizar_partitura_temp():
    """Renderiza a partitura actual a un ficheiro temporal"""
    try:
        temp_score = stream.Score()
        temp_score.metadata = estado['partitura'].metadata
        temp_score.append(estado['parte'])
        temp_score.write('musicxml.png', fp=str(config.TEMP_PARTITURA_PNG_BASE))
    except Exception as e:
        print(f"Erro ao renderizar: {e}")

def limpar_temporais():
    """Elimina ficheiros temporais"""
    ficheiros = [
        "/Users/xairo/Desktop/Simulacion Markov/temp_partitura_web.musicxml",
        "/Users/xairo/Desktop/Simulacion Markov/temp_partitura_web-1.png",
        "/Users/xairo/Desktop/Simulacion Markov/temp_partitura_web.pdf",
    ]
    for f in ficheiros:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass

if __name__ == '__main__':
    # Verificar e crear directorios necesarios
    config.crear_directorios()
    
    # Verificar MuseScore
    if not config.verificar_musescore():
        print("\n⚠️  AVISO: Continúa de todos modos, pero as partituras non se renderizarán correctamente.\n")
    
    print("\n" + "="*80)
    print("  XERADOR VISUAL DE MELODÍAS CON CADEAS DE MARKOV")
    print("  Traballo Fin de Estudos - Xairo Campos Blanco - CSM da Coruña 2025-2026")
    print("="*80)
    print(f"\nAbrindo interface web en: http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print("Preme Ctrl+C para deter o servidor\n")
    
    # Abrir navegador automaticamente
    import webbrowser
    import threading
    def abrir_navegador():
        import time
        time.sleep(1.5)
        webbrowser.open(f'http://{config.FLASK_HOST}:{config.FLASK_PORT}')
    
    threading.Thread(target=abrir_navegador, daemon=True).start()
    
    app.run(debug=config.FLASK_DEBUG, host=config.FLASK_HOST, port=config.FLASK_PORT)
