"""
================================================================================
ANÁLISE DE MOVEMENTOS MELÓDICOS: MUIÑEIRA DE MONTERREI
================================================================================

Traballo Fin de Estudos de Composición
Autor: Xairo Campos Blanco
Institución: CSM da Coruña
Curso académico: 2025-2026

Este programa analiza os movementos melódicos da Muiñeira de Monterrei para
extraer a distribución de probabilidades dos saltos melódicos. Esta información
utilizarase despois para parametrizar o xerador de cadeas de Markov,
facendo que as melodías xeradas imiten os patróns de movemento do repertorio
tradicional galego.

Este código forma parte dun proxecto académico.

================================================================================
"""

import os
from music21 import converter
from collections import Counter
import matplotlib
matplotlib.use('Agg')  # Backend non interactivo, só garda imaxes
import matplotlib.pyplot as plt

# Importar a configuración
import config

# ============================================================================
# 1. DEFINICIÓN DA ESCALA E MAPEADO DE NOTAS
# ============================================================================

# Escala de Do Maior (escala diatónica sobre a que está construída a muiñeira)
# Índices: 0=Do, 1=Re, 2=Mi, 3=Fa, 4=Sol, 5=La, 6=Si
escala_do_maior = ["C", "D", "E", "F", "G", "A", "B"]

def obter_indice_nota(nota_obj):
    """
    Converte unha nota de music21 ao seu índice na escala de Do Maior,
    tendo en conta a octava para calcular os saltos correctamente.
    
    Parámetros:
        nota_obj: Obxecto Note de music21
    
    Retorna:
        Índice absoluto da nota (combina posición na escala + octava)
    """
    nome_nota = nota_obj.pitch.name  # Obtén o nome sen octava (C, D, E, etc.)
    octava = nota_obj.pitch.octave    # Obtén a octava (4, 5, etc.)
    
    try:
        # Busca o índice da nota na escala (0-6)
        indice_escala = escala_do_maior.index(nome_nota)
        # Índice absoluto = (octava * 7) + posición na escala
        # Isto permite calcular correctamente os saltos entre octavas
        indice_absoluto = (octava * 7) + indice_escala
        return indice_absoluto
    except ValueError:
        # Se a nota non está na escala (alteración accidental), retorna None
        return None

# ============================================================================
# 2. LECTURA E PROCESAMENTO DO FICHEIRO MUSICXML
# ============================================================================

print("="*80)
print("ANÁLISE DE MOVEMENTOS MELÓDICOS: MUIÑEIRA DE MONTERREI")
print("Xairo Campos Blanco - CSM da Coruña 2025-2026")
print("="*80)

# Carga do ficheiro MusicXML (formato .mxl comprimido)
ruta_muineira = str(config.MUINEIRA_MONTERREI)
print(f"\nLendo ficheiro: {ruta_muineira}")

try:
    partitura = converter.parse(ruta_muineira)
    print("✓ Ficheiro cargado correctamente")
except Exception as e:
    print(f"✗ Erro ao cargar o ficheiro: {e}")
    exit(1)

# Extracción de todas as notas da partitura
# flat() converte toda a estrutura xerárquica nunha lista plana
todas_notas = partitura.flat.notes

# Filtra só as notas (exclúe acordes e silencios) e mapea aos índices da escala
indices_notas = []
duracions_notas = []  # Lista para almacenar as duracións rítmicas

for elemento in todas_notas:
    # Verifica se é unha nota individual (non un acorde)
    if hasattr(elemento, 'pitch'):
        indice = obter_indice_nota(elemento)
        if indice is not None:
            indices_notas.append(indice)
            # Extrae a duración en quarterLength (negra = 1.0)
            duracions_notas.append(elemento.quarterLength)

print(f"✓ Extraídas {len(indices_notas)} notas da partitura")

# ============================================================================
# 3. CÁLCULO DOS MOVEMENTOS MELÓDICOS
# ============================================================================

print("\n--- ANALIZANDO MOVEMENTOS MELÓDICOS ---")

# Lista para almacenar todos os movementos (diferenzas entre notas consecutivas)
movementos = []

# Calcula a diferenza entre cada nota e a anterior
for i in range(1, len(indices_notas)):
    movemento = indices_notas[i] - indices_notas[i-1]
    movementos.append(movemento)

print(f"✓ Analizados {len(movementos)} movementos melódicos")

# ============================================================================
# 3.B. ANÁLISE DE DURACIÓNS RÍTMICAS
# ============================================================================

print("\n--- ANALIZANDO DURACIÓNS RÍTMICAS ---")

# Mapeo de quarterLength a nomes de figuras rítmicas
def clasificar_duracion(duracion):
    """
    Converte un quarterLength a nome de figura rítmica.
    Redondea valores para agrupar tresillos e pequenas variacións.
    IGNORA: Branca con puntillo (duracións moi longas)
    """
    # Redondea a 2 decimais para agrupar tresillos
    duracion = round(duracion, 2)
    
    if duracion == 0.25:
        return "Semicorchea"
    elif duracion == 0.33:  # Tresillo de corcheas
        return "Semicorchea"  # Tratamos tresillos como semicorcheas
    elif duracion == 0.5:
        return "Corchea"
    elif duracion == 0.67:  # Tresillo de negras
        return "Corchea"  # Aproximación
    elif duracion == 1.0:
        return "Negra"
    elif duracion == 1.5:
        return "Negra con puntillo"
    elif duracion == 2.0:
        return "Blanca"
    elif duracion == 3.0:
        return None  # Ignorar branca con puntillo
    else:
        # Para duracións non estándar, clasifícaas polo valor máis próximo
        if duracion < 0.4:
            return "Semicorchea"
        elif duracion < 0.75:
            return "Corchea"
        elif duracion < 1.25:
            return "Negra"
        elif duracion < 1.75:
            return "Negra con puntillo"
        elif duracion < 2.5:
            return "Blanca"
        else:
            return None  # Ignorar duracións moi longas

# Clasifica todas as duracións (filtrando as ignoradas)
clasificacions_ritmo = [clasificar_duracion(d) for d in duracions_notas]
clasificacions_ritmo = [c for c in clasificacions_ritmo if c is not None]  # Eliminar None
contador_ritmos = Counter(clasificacions_ritmo)

# Ordena os ritmos por frecuencia
ritmos_ordenados = sorted(contador_ritmos.items(), key=lambda x: x[1], reverse=True)

total_ritmos = len(clasificacions_ritmo)

print(f"✓ Analizadas {total_ritmos} duracións rítmicas")

# ============================================================================
# 4. CREACIÓN DA TÁBOA DE DISTRIBUCIÓN
# ============================================================================

# Conta cantas veces aparece cada tipo de movemento
contador_movementos = Counter(movementos)

# Ordena os movementos de menor a maior
movementos_ordenados = sorted(contador_movementos.items())

# Calcula o total de movementos para obter porcentaxes
total_movementos = len(movementos)

# Mostra a táboa en consola
print("\n" + "="*80)
print("TÁBOA DE DISTRIBUCIÓN DE MOVEMENTOS MELÓDICOS")
print("="*80)
print(f"{'Movemento':<20} {'Descrición':<35} {'Frecuencia':<12} {'Porcentaxe':<10}")
print("-"*80)

for movemento, frecuencia in movementos_ordenados:
    porcentaxe = (frecuencia / total_movementos) * 100
    
    # Xera unha descrición clara do movemento
    if movemento == 0:
        descricion = "Repetición (mesma nota e octava)"
    elif movemento > 0:
        descricion = f"Ascendente {movemento} pos."
    else:
        descricion = f"Descendente {abs(movemento)} pos."
    
    print(f"{movemento:+3d} ({descricion:<31}) | {frecuencia:<10d} | {porcentaxe:>6.2f}%")

print("-"*80)
print(f"Total de movementos: {total_movementos}")
print(f"\nNOTA: Os movementos inclúen saltos de octava. Un salto de octava (7 posicións)")
print(f"represéntase como ±7, ±14, etc., segundo a distancia real na escala diatónica.")

# Mostra a táboa de ritmos en consola
print("\n" + "="*80)
print("TÁBOA DE DISTRIBUCIÓN DE DURACIÓNS RÍTMICAS")
print("="*80)
print(f"{'Duración':<25} {'Frecuencia':<12} {'Porcentaxe':<10}")
print("-"*80)

for ritmo, frecuencia in ritmos_ordenados:
    porcentaxe = (frecuencia / total_ritmos) * 100
    print(f"{ritmo:<25} | {frecuencia:<10d} | {porcentaxe:>6.2f}%")

print("-"*80)
print(f"Total de duracións: {total_ritmos}")

# ============================================================================
# 5. XERACIÓN DO HISTOGRAMA VISUAL, TÁBOA DE DATOS E RITMOS
# ============================================================================

print("\n--- XERANDO VISUALIZACIÓN GRÁFICA ---")

# Preparación de datos para visualización
movementos_vals = [m[0] for m in movementos_ordenados]
frecuencias = [m[1] for m in movementos_ordenados]
porcentaxes = [(freq / total_movementos) * 100 for freq in frecuencias]

# Separa os movementos en ascendentes, descendentes e repetición
mov_ascendentes = [(m, p, f) for m, p, f in zip(movementos_vals, porcentaxes, frecuencias) if m > 0]
mov_descendentes = [(m, p, f) for m, p, f in zip(movementos_vals, porcentaxes, frecuencias) if m < 0]
mov_repeticion = [(m, p, f) for m, p, f in zip(movementos_vals, porcentaxes, frecuencias) if m == 0]

# ============================================================================
# VISUALIZACIÓN: Layout en 2 columnas (Melodía | Ritmo)
# ============================================================================

fig = plt.figure(figsize=(20, 10))

# COLUMNA ESQUERDA: MELODÍA
# Panel 1: Gráfico de distribución dos movementos melódicos
ax1 = plt.subplot(2, 2, 1)
cores = ['red' if mov < 0 else 'green' if mov > 0 else 'blue' for mov in movementos_vals]
ax1.bar(range(len(movementos_vals)), porcentaxes, color=cores, alpha=0.7, edgecolor='black')
ax1.set_xlabel('Tipo de Movemento Melódico', fontsize=11)
ax1.set_ylabel('Porcentaxe (%)', fontsize=11)
ax1.set_title('Distribución de Movementos Melódicos\n(Muiñeira de Monterrei)', fontsize=13, fontweight='bold')
ax1.set_xticks(range(len(movementos_vals)))
ax1.set_xticklabels([f'{m:+d}' for m in movementos_vals], fontsize=10)
ax1.grid(axis='y', alpha=0.3)

# Engadir porcentaxes enriba das barras
for i, (frec, porc) in enumerate(zip(frecuencias, porcentaxes)):
    ax1.text(i, porc + 1, f'{porc:.1f}%', ha='center', va='bottom', fontsize=9)

# Panel 2: Táboa de movementos melódicos
ax2 = plt.subplot(2, 2, 3)
ax2.axis('tight')
ax2.axis('off')

# Crear táboa con totais
datos_tabla = []
for i, mov in enumerate(movementos_vals):
    tipo = 'Ascendente' if mov > 0 else 'Descendente' if mov < 0 else 'Repetición'
    datos_tabla.append([f'{mov:+d}', tipo, str(frecuencias[i]), f'{porcentaxes[i]:.2f}%'])

# Engadir totais
total_freq_ascendentes = sum(f for _, _, f in mov_ascendentes)
total_porc_ascendentes = sum(p for _, p, _ in mov_ascendentes)
total_freq_descendentes = sum(f for _, _, f in mov_descendentes)
total_porc_descendentes = sum(p for _, p, _ in mov_descendentes)

datos_tabla.append(['---', '---', '---', '---'])
datos_tabla.append(['TOTAL', 'Ascendentes', str(total_freq_ascendentes), f'{total_porc_ascendentes:.2f}%'])
datos_tabla.append(['TOTAL', 'Descendentes', str(total_freq_descendentes), f'{total_porc_descendentes:.2f}%'])
datos_tabla.append(['---', '---', '---', '---'])
datos_tabla.append(['TOTAL', 'Xeral', str(total_movementos), '100.00%'])

tabla = ax2.table(cellText=datos_tabla,
                 colLabels=['Movemento', 'Tipo', 'Frecuencia', 'Porcentaxe'],
                 cellLoc='center',
                 loc='center',
                 colWidths=[0.15, 0.25, 0.15, 0.15])
tabla.auto_set_font_size(False)
tabla.set_fontsize(10)
tabla.scale(1, 1.8)

# Formateo da táboa con cores
for i, key in enumerate(tabla._cells):
    cell = tabla._cells[key]
    if key[0] == 0:  # Cabeceira
        cell.set_facecolor('#2196F3')
        cell.set_text_props(weight='bold', color='white', size=11)
    else:
        # Obtén o tipo de movemento da fila actual
        fila_idx = key[0] - 1  # -1 porque a fila 0 é a cabeceira
        if fila_idx < len(datos_tabla):
            tipo_texto = datos_tabla[fila_idx][1] if len(datos_tabla[fila_idx]) > 1 else ''
            
            # Destaca as filas de totais
            if 'TOTAL' in datos_tabla[fila_idx][0]:
                cell.set_facecolor('#E3F2FD')
                cell.set_text_props(weight='bold')
            elif tipo_texto == 'Repetición':
                cell.set_facecolor('#FFF9C4')
                if key[1] == 0:
                    cell.set_text_props(weight='bold')
            elif tipo_texto == '---':  # Fila separadora
                cell.set_facecolor('#FFFFFF')
            else:
                # Alterna cores para mellor lexibilidade
                if key[0] % 2 == 0:
                    cell.set_facecolor('#F5F5F5')
                else:
                    cell.set_facecolor('#FFFFFF')

# COLUMNA DEREITA: RITMO
# Panel 3: Gráfico de distribución rítmica
ax3 = plt.subplot(2, 2, 2)
categorias_unicas = [r[0] for r in ritmos_ordenados]
frecuencias_ritmo = [r[1] for r in ritmos_ordenados]
porcentaxes_ritmo = [(f/len(clasificacions_ritmo))*100 for f in frecuencias_ritmo]

cores_ritmo = ['purple', 'orange', 'cyan', 'magenta'][:len(categorias_unicas)]
ax3.bar(range(len(categorias_unicas)), porcentaxes_ritmo, color=cores_ritmo, alpha=0.7, edgecolor='black')
ax3.set_xlabel('Tipo de Duración Rítmica', fontsize=11)
ax3.set_ylabel('Porcentaxe (%)', fontsize=11)
ax3.set_title('Distribución de Duracións Rítmicas\n(Muiñeira de Monterrei)', fontsize=13, fontweight='bold')
ax3.set_xticks(range(len(categorias_unicas)))
ax3.set_xticklabels(categorias_unicas, fontsize=10, rotation=20, ha='right')
ax3.grid(axis='y', alpha=0.3)

# Engadir porcentaxes enriba das barras
for i, (frec, porc) in enumerate(zip(frecuencias_ritmo, porcentaxes_ritmo)):
    ax3.text(i, porc + 2, f'{porc:.1f}%', ha='center', va='bottom', fontsize=9)

# Panel 4: Táboa de ritmos
ax4 = plt.subplot(2, 2, 4)
ax4.axis('tight')
ax4.axis('off')

# Crear táboa de ritmos
datos_tabla_ritmo = []
for i, (cat, frec) in enumerate(zip(categorias_unicas, frecuencias_ritmo)):
    datos_tabla_ritmo.append([cat, str(frec), f'{porcentaxes_ritmo[i]:.2f}%'])

# Engadir total
datos_tabla_ritmo.append(['---', '---', '---'])
datos_tabla_ritmo.append(['TOTAL', str(len(clasificacions_ritmo)), '100.00%'])

tabla_ritmo = ax4.table(cellText=datos_tabla_ritmo,
                       colLabels=['Duración', 'Frecuencia', 'Porcentaxe'],
                       cellLoc='center',
                       loc='center',
                       colWidths=[0.35, 0.20, 0.20])
tabla_ritmo.auto_set_font_size(False)
tabla_ritmo.set_fontsize(10)
tabla_ritmo.scale(1, 2.5)

# Formateo da táboa de ritmos con cores
for i, key in enumerate(tabla_ritmo._cells):
    cell = tabla_ritmo._cells[key]
    if key[0] == 0:  # Cabeceira
        cell.set_facecolor('#2196F3')
        cell.set_text_props(weight='bold', color='white', size=11)
    else:
        # Obtén o nome do ritmo da fila actual
        fila_idx = key[0] - 1
        if fila_idx < len(datos_tabla_ritmo):
            nome_ritmo = datos_tabla_ritmo[fila_idx][0]
            
            # Destaca a fila de total
            if nome_ritmo == 'TOTAL':
                cell.set_facecolor('#E3F2FD')
                cell.set_text_props(weight='bold')
            elif nome_ritmo == '---':  # Fila separadora
                cell.set_facecolor('#FFFFFF')
            else:
                # Alterna cores para mellor lexibilidade
                if key[0] % 2 == 0:
                    cell.set_facecolor('#F5F5F5')
                else:
                    cell.set_facecolor('#FFFFFF')

# Engadir texto explicativo
lenda_texto = """
INTERPRETACIÓN: Na análise móstrase os movementos melódicos calculados como diferenzas de posición na escala de Do Maior.
Verde=Ascendentes | Vermello=Descendentes | Azul=Repetición. Os saltos de octava contabilízanse segundo a súa distancia real (±7, ±14, etc.).
RITMOS: Análise de duracións rítmicas (excluíndo Branca con puntillo). Cores alternadas para mellor lexibilidade.
"""
fig.text(0.5, 0.01, lenda_texto, ha='center', fontsize=9, style='italic',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout(pad=4.0, h_pad=4.0, w_pad=4.0, rect=[0, 0.05, 1, 1])

# Gardar con alta resolución SEN modo interactivo
ruta_imaxe = str(config.OUTPUT_ANALISE_PNG)
plt.savefig(ruta_imaxe, dpi=300, bbox_inches='tight')
print(f"✓ Gráfico gardado en: {ruta_imaxe}")
plt.close()  # Pechar figura sen mostrar

# ============================================================================
# 6. EXPORTACIÓN DE DATOS PARA O SISTEMA MARKOV
# ============================================================================

print("\n" + "="*80)
print("DATOS PARA PARAMETRIZAR O XERADOR DE MARKOV")
print("="*80)
print("\nDistribución de probabilidades para aplicar ao xerador:\n")

print("--- MOVEMENTOS MELÓDICOS ---")
# Crea un dicionario con todas as probabilidades
probabilidades_markov = {}
for movemento, frecuencia in movementos_ordenados:
    probabilidade = (frecuencia / total_movementos) * 100
    probabilidades_markov[movemento] = probabilidade
    print(f"Movemento {movemento:+2d}: {probabilidade:6.2f}%")

print("\n--- DURACIÓNS RÍTMICAS ---")
probabilidades_ritmo = {}
for ritmo, frecuencia in ritmos_ordenados:
    probabilidade = (frecuencia / total_ritmos) * 100
    probabilidades_ritmo[ritmo] = probabilidade
    print(f"{ritmo:<25}: {probabilidade:6.2f}%")

print("\n" + "="*80)
print("ANÁLISE COMPLETADA")
print("="*80)
print("\nOs datos obtidos úsaranse para actualizar o ficheiro 'markov test.py'")
print("co fin de que as melodías xeradas imiten os patróns melódicos da tradición galega.")
