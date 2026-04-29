"""Servidor Socket.IO único compartido entre as dúas ASGI apps (8000 e 8001).

Usamos namespaces para separar os roles:
- /admin       (admin)
- /musician    (músicos + director)
- /public      (público)
- /projection  (vista de proxección)
"""
import socketio

# Async server, CORS open (rede local). Permitimos engine.io v4.
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=10,
    ping_timeout=20,
)

NAMESPACES = ["/admin", "/musician", "/public", "/projection"]
