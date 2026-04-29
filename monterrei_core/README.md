# Monterrei Core

Aplicación de show-control para a obra interactiva *Monterrei* (TFE de composición, CSM).

## Arquitectura

- **FastAPI + python-socketio** (ASGI) sobre Uvicorn.
- Único proceso Python que escoita en **dous portos**: `:8000` (admin / director / músicos / proxección) e `:8001` (público).
  - Para o porto **:80** úsase a redirección `pfctl` que carga `setup_port80.command`.
- Threads de fondo para hardware (MIDI vía IAC, DMX vía Enttec USB Pro).
- Lóxica de movementos en `app/movements/`.

## Arranque

```bash
./start.command          # crea o venv en ~/Documents/Monterrei_Venv se non existe
./stop.command           # parada limpa
./setup_port80.command   # (opcional) redirixe 80 -> 8001 con pfctl
```

## Surfaces (vistas)

| URL | Vista | Porto |
|---|---|---|
| `http://<ip>:8000/`            | Músicos / Director (selector inicial) | 8000 |
| `http://<ip>:8000/admin`       | Panel admin                            | 8000 |
| `http://<ip>:8000/projection`  | Proxección pública                    | 8000 |
| `http://<ip>:8001/` ou `:80/`  | Público (votación / apagado)          | 8001 / 80 |

## Configuración

Todo no `.env` (ver `.env.example`). Os datos máis críticos:

- `MONTERREI_HOST` – `0.0.0.0` para que valga calquera IP da rede actual.
- `MONTERREI_BPM_DIVIDER` – correctivo se Logic envía o dobre/metade do BPM esperado.
- `MONTERREI_DMX_PORT_HINT` – substring para localizar o serial do Enttec.

## Estrutura

Ver `app/` para o backend, `static/` e `templates/` para os frontends.
Os tests están en `tests/`.

## Notas

- O directorio `Grafos-Markov` orixinal **non se modifica**. O Markov integrado vive en `static/markov/` (refactor do orixinal).
- O vídeo do Mov. 1 cárgase desde `Graficos-Maquetacion/Monterrei-Debuxos/Castelo/castelo_monterrei_1.mp4` (vía symlink en `static/assets/videos/`).
- O venv vive **fóra** do repo (en `~/Documents/Monterrei_Venv`) para evitar problemas de Google Drive.
