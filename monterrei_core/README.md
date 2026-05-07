# Monterrei Core

Aplicación de show-control para a obra interactiva *Monterrei* (TFE de composición, CSM).

## Arquitectura

- **FastAPI + python-socketio** (ASGI) sobre Uvicorn.
- Único proceso Python que escoita en **varios portos**:
  - `:8000` → músicos / director (vinculado ás IPs reais da LAN, ex. `192.168.1.126` e `192.168.0.2`).
  - `:8800` → admin + proxección (HTTP Basic Auth).
  - `:8001` → público (votación / apagado).
  - `:80`   → público estándar HTTP, opcional vía redirección con `iptables` (`setup_port80.sh`).
- Threads de fondo para hardware (MIDI vía ALSA, DMX vía Enttec USB Pro / pyserial).
- Lóxica de movementos en `app/movements/`.

## Sistema soportado

- **Ubuntu / Linux** (probado en Ubuntu 24.04). O entorno virtual créase en `~/Documents/Monterrei_Venv`, fóra do repo.

## Arranque

```bash
./start.sh                    # crea o venv en ~/Documents/Monterrei_Venv se non existe
./stop.sh                     # parada limpa
sudo ./setup_port80.sh        # (opcional) redirixe 80 -> 8001 con iptables
sudo ./setup_port80.sh --off  # quita a redirección
```

`monterrei.sh` é un atallo equivalente a `./start.sh`.

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

Hai dúas vías:

**A) Logic / Mac na rede (recomendado para esta instalación)** — vía RTP-MIDI (Apple Network MIDI):

```bash
sudo apt install rtpmidid
sudo systemctl enable --now rtpmidid
```

No Mac (`192.168.0.3` neste setup):

1. *Audio MIDI Setup* → *Window* → *Show MIDI Studio* → dobre clic en **Network**.
2. Na sección *My Sessions* crea unha sesión (p. ex. `Monterrei`) e marca *Enabled*.
3. En *Directory* preme **+**, introduce *Name* `linux` e *Host* `192.168.0.2` (a IP da máquina Linux na mesma rede que use a sesión actual; tamén funciona `192.168.1.126`).
4. Selecciona a entrada `linux` e preme **Connect**.
5. En Logic, en *Project Settings → Synchronization → MIDI*, activa *Transmit MIDI Clock* e selecciona como destino a sesión Network creada.

En Linux, `aconnect -i` mostrará un cliente novo (algo como `rtpmidid:Monterrei`). O `MONTERREI_MIDI_PORT_HINT=rtpmidi` xa o colle automaticamente.

**B) USB-MIDI físico ou porto virtual local** (para tests sen Mac):

```bash
sudo modprobe snd-virmidi   # crea VirMIDI 1-0..3 (ALSA)
```

E axusta `MONTERREI_MIDI_PORT_HINT` ao nome correspondente.

### Diagnóstico rápido MIDI sobre rede

1. **No Linux** comproba o servizo:
   ```bash
   systemctl status rtpmidid
   sudo ss -lunp | grep 5004    # debe escoitar UDP 5004 e 5005
   sudo ufw status              # se ufw está activo, abre 5004/udp e 5005/udp
   ```
2. **Conecta dende o Mac** (Audio MIDI Setup → Network → preme *Connect*).
   En canto a sesión está activa, en Linux executa:
   ```bash
   aconnect -i        # debe aparecer un cliente novo (ex. "Network <Mac>")
   ```
3. **Comproba que `mido` o ve**:
   ```bash
   source ~/Documents/Monterrei_Venv/bin/activate
   python -c "import mido; print(mido.get_input_names())"
   ```
   Debe aparecer algo como `'Network <Mac>:Apple Network Session 1 128:0'` ou `'rtpmidid:...'`. Se non aparece, **a sesión non está conectada** (paso 2).
4. **Hint en `.env`**: o valor `MONTERREI_MIDI_PORT_HINT=rtpmidi` xa fai matching contra `rtpmidi`, `rtpmidid`, `network` ou `rtp`. Se o teu porto se chama doutra forma, edita o hint co texto exacto (ou unha substring) que aparece no paso 3.
5. **No Mac** envía clock dende Logic: *File → Project Settings → Synchronization → MIDI* → activa *Transmit MIDI Clock* e selecciona o destino *Network*.
6. Reinicia `./start.sh`. Nos logs verás `MIDI: escoitando en '...'` co nome do porto. Se segue saíndo `Midi Through`, o `.env` non se está cargando ou o hint non coincide.

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
