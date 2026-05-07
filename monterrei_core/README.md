# Monterrei Core

Aplicación de show-control para a obra interactiva *Monterrei* (TFE de composición, CSM).

## Arquitectura

- **FastAPI + python-socketio** (ASGI) sobre Uvicorn.
- Único proceso Python que escoita en **varios portos**:
  - `:8000` → músicos / director (vinculado ás IPs reais da LAN, ex. `192.168.1.126` e `192.168.0.2`).
  - `:8800` → admin + proxección (HTTP Basic Auth).
  - `:8001` → público (votación / apagado).
  - `:80`   → público estándar HTTP, redirixido a `:8001` con `iptables` automaticamente cando se lanza con `sudo ./start.sh` (ver máis abaixo).
- Threads de fondo para hardware (MIDI vía ALSA / RTP-MIDI, DMX vía Enttec USB Pro / pyserial).
- Lóxica de movementos en `app/movements/`.

## Sistema soportado

- **Ubuntu / Linux** (probado en Ubuntu 24.04). O entorno virtual créase en `~/Documents/Monterrei_Venv`, fóra do repo.

## Arranque

```bash
sudo ./start.sh               # arranca o servidor + redirixe :80 -> :8001 (recomendado)
./start.sh                    # arranca sen redirección :80 (público só en :8001)
./stop.sh                     # parada limpa
```

`monterrei.sh` é un atallo equivalente a `./start.sh`.

### Sobre o porto 80

O `start.sh` xa integra a redirección `iptables` `:80 → :8001`. As regras
de `iptables` **non persisten** despois dun reinicio do equipo, polo que
`start.sh` reaplícaas en cada arranque (require `sudo`).

- Lanzando con `sudo ./start.sh`: aplica a redirección, despois solta
  privilexios e arranca Python como o usuario normal (para non correr o
  servidor como root).
- Lanzando con `./start.sh` (sen sudo): tenta aplicar a redirección con
  `sudo -n` (sen pedir contrasinal, só funciona se sudo está configurado
  así). Se non, avisa que o porto 80 non se redirixe e arranca igual.

## Surfaces (vistas)

| URL | Vista | Porto |
|---|---|---|
| `http://<ip>:8000/`            | Músicos / Director (selector inicial)  | 8000 |
| `http://<ip>:8800/admin`       | Panel admin (HTTP Basic)               | 8800 |
| `http://<ip>:8800/projection`  | Proxección pública (HTTP Basic)        | 8800 |
| `http://<ip>:8001/` ou `:80/`  | Público (votación / apagado)           | 8001 / 80 |

## Configuración

Todo no `.env` (ver `.env.example`). Os datos máis críticos:

- `MONTERREI_HOST` – `0.0.0.0` para que valga calquera IP da rede actual (admin/público).
- `MONTERREI_HOST_MAIN` / `MONTERREI_HOST_MAIN_EXTRA` – IPs nas que se publica o porto 8000 (músicos/director). Se algunha non existe na máquina, ignórase con aviso.
- `MONTERREI_BPM_DIVIDER` – correctivo se o secuenciador envía o dobre/metade do BPM esperado.
- `MONTERREI_DMX_PORT_HINT` – substring para localizar o serial do Enttec (ex. `ttyUSB`, `FT232`).
- `MONTERREI_MIDI_PORT_HINT` – substring para o porto MIDI ALSA (`Midi Through`, `VirMIDI`, nome do DAW…).

## MIDI en Linux

Para recibir o *MIDI Clock* dende **Logic Pro** no Mac vía **RTP-MIDI**
(*Apple Network MIDI*), toda a configuración está automatizada na carpeta
[`install-midi/`](install-midi/README.md):

```bash
sudo ./install-midi/setup_midi.sh   # instala rtpmidid + avahi + virmidi + ufw
./install-midi/check_midi.sh        # diagnóstico
```

Logo, no Mac, abre *Audio MIDI Setup → MIDI Studio → Network*, crea unha
sesión e conecta a esta máquina (debería aparecer vía Bonjour como
`monterrei._apple-midi._udp` ou similar; se non, engade host manualmente:
`192.168.0.2:5004`). Os detalles paso a paso, o uso con Logic e a resolución
de problemas están en [`install-midi/README.md`](install-midi/README.md).

O hint en `.env` `MONTERREI_MIDI_PORT_HINT=rtpmidi` xa colle automaticamente
`rtpmidi`, `rtpmidid`, `network` ou `rtp`.

### Test sen Mac (USB-MIDI físico ou loopback virtual)

O `setup_midi.sh` xa carga o módulo `snd-virmidi` (portos `VirMIDI 1-0..3`).
Axusta `MONTERREI_MIDI_PORT_HINT=VirMIDI` para usalos.

## DMX en Linux

O usuario actual debe pertencer ao grupo `dialout` para acceder a `/dev/ttyUSB*`:

```bash
sudo usermod -aG dialout "$USER"   # require pechar sesión
```

## Estrutura

Ver `app/` para o backend, `static/` e `templates/` para os frontends. Os tests están en `tests/`.

## Notas

- O directorio `Grafos-Markov` orixinal **non se modifica**. O Markov integrado vive en `static/markov/`.
- O vídeo do Mov. 1 cárgase desde `static/assets/videos/castelo_monterrei_1.mp4`.
- O venv vive **fóra** do repo (en `~/Documents/Monterrei_Venv`).
