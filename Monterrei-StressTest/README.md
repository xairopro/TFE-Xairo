# Monterrei Stress Test

Simulador de carga para `monterrei_core`. Crea N teléfonos virtuais que se
comportan como músicos (e opcionalmente como público) para validar que o
servidor aguanta o concerto enteiro.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(Alternativa: usa o venv de Monterrei `~/Documents/Monterrei_Venv` se xa o
tes; só lle faltan as dependencias deste cartafol.)

## Uso

### Modo doado: dobre clic

Dobre clic en `iniciar_simulacion.command` (xa é executable). Pregunta:
- Host (por defecto `127.0.0.1`)
- Cantos músicos (70)
- Cantos espectadores de público (30)
- Cantos segundos de vida por conexión (180)

Lánzao en modo verboso, así verás cada evento que o servidor lle manda
a cada teléfono (cor, label_suffix, voting_open, voting_close, reset:all,
movement_changed, etc.) -- útil para facer unha "simulación humana" do
concerto sen ter 70 móbiles físicos.

### Modo CLI

Coa Monterrei Core levantada (./start.command):

```bash
# 70 músicos en local, vida útil 2 minutos
python simulate_70.py

# 70 músicos + 30 público apuntando ao Mac de produción, verboso
python simulate_70.py --musicians 70 --public 30 \
    --host 192.168.0.2 --verbose

# Stress longo (10 min) con lanzamentos máis espazados (200ms entre cada un)
python simulate_70.py --musicians 70 --lifetime 600 --stagger 0.2

# Tamén imprimir cada midi:bar (moi ruidoso)
python simulate_70.py --verbose --verbose-bars
```

## Que fai cada cliente

**Músico** (`/musician`):
1. `GET /` para recoller a cookie `monterrei_sid`.
2. Conecta vía Socket.IO co `sid` da cookie.
3. Espera o evento `catalog`, escolle o instrumento menos ocupado.
4. Envía `register`. Espera o `registered` ack.
5. Mantense conectado durante `--lifetime` segundos escoitando eventos.

**Público** (`/public`):
1. Igual ca o músico pero no namespace `/public`.
2. Cando recibe `m4:voting_open`, vota un loop ao chou.

## Que comprobas

- Que o servidor non se cae con 70 sockets concorrentes.
- Que o reparto automático de instrumentos (ata as duplicacións) funciona.
- Que admin contador `Músicos` chega a 70.
- Cando reduces público mediante `Iniciar Apagado` (M4) os clientes seguen
  conectados sen perder eventos.

Saída final:
```
== Resultado ==
Músicos OK:  70
Músicos KO:  0
Público OK:  30
Público KO:  0
```
