"""M3 - Markov: control da visualización lanzando triggers ao iframe en proxección."""
from ..core.broadcaster import to_projection
from ..state import state
from ..logger import log


async def start():
    state.snap.movement = 3
    await to_projection("m3:trigger", {"action": "start"})
    log.info("M3 markov: start")


async def stop():
    await to_projection("m3:trigger", {"action": "stop"})
    log.info("M3 markov: stop")


async def control(params: dict):
    """Reenvía parámetros (velocidade, modo, cores...) ao iframe Markov."""
    await to_projection("m3:trigger", {"action": "control", "params": params})
