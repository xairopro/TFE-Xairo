"""Rutas HTTP. Tres apps:
- main (porto 8000)  -> Músicos / Director (sen contrasinal, en LAN)
- admin (porto 8800) -> Admin + Proxección (HTTP Basic Auth)
- public (porto 8001 e 80) -> Público (sen contrasinal)
"""
import secrets
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from ..config import settings, BASE_DIR
from ..core.session_manager import get_or_create_sid
from ..data.instruments import CATALOG
from ..data.loops import LOOP_COLORS

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
security = HTTPBasic()


def _check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    user_ok = secrets.compare_digest(credentials.username, settings.admin_user)
    pass_ok = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _render_with_cookie(request: Request, template: str, context: dict) -> HTMLResponse:
    """Renderiza un template e asegura unha cookie de sesión persistente.

    Crea unha HTMLResponse directamente (evita o bug de Content-Length duplicado).
    """
    sid = request.cookies.get(settings.session_cookie)
    new_sid = None
    if not sid:
        new_sid = secrets.token_urlsafe(16)
        sid = new_sid
    context = dict(context)
    context.setdefault("request", request)
    context["sid"] = sid
    body = templates.TemplateResponse(template, context).body
    resp = HTMLResponse(content=body)
    if new_sid:
        resp.set_cookie(
            key=settings.session_cookie,
            value=new_sid,
            max_age=60 * 60 * 8,
            httponly=False,
            samesite="lax",
        )
    return resp


def make_main_router() -> APIRouter:
    """Porto 8000: só vista de músicos/director."""
    r = APIRouter()

    @r.get("/", response_class=HTMLResponse)
    async def musician(request: Request):
        return _render_with_cookie(request, "musician.html", {
            "instruments": CATALOG,
        })

    @r.get("/api/health")
    async def health():
        return JSONResponse({"ok": True})

    return r


def make_admin_router() -> APIRouter:
    """Porto 8800: Admin + Proxección, protexido con HTTP Basic."""
    r = APIRouter()

    @r.get("/", response_class=HTMLResponse)
    async def admin_root(request: Request, _: str = Depends(_check_admin)):
        return templates.TemplateResponse("admin.html", {
            "request": request, "loops": LOOP_COLORS,
        })

    @r.get("/admin", response_class=HTMLResponse)
    async def admin(request: Request, _: str = Depends(_check_admin)):
        return templates.TemplateResponse("admin.html", {
            "request": request, "loops": LOOP_COLORS,
        })

    @r.get("/projection", response_class=HTMLResponse)
    async def projection(request: Request, _: str = Depends(_check_admin)):
        from ..data.topography import POSITIONS, SEMICIRCLES, SEMI_RADIUS
        from ..data.groups import GROUPS
        import json as _json
        # base_id -> etiqueta humana curta (sen "1 ", etc.). Reusamos CATALOG_BY_ID.
        from ..data.instruments import CATALOG_BY_ID
        labels = {bid: (CATALOG_BY_ID[bid].label if bid in CATALOG_BY_ID else bid)
                  for bid in POSITIONS.keys()}
        instrument_group = {}
        for g, members in GROUPS.items():
            for inst in members:
                instrument_group[inst] = g
        projection_group_colors = {
            "G1": "#2f7dff",
            "G2": "#22c86f",
            "G3": "#ff59b0",
        }
        return templates.TemplateResponse("projection.html", {
            "request": request,
            "positions_json": _json.dumps(POSITIONS),
            "semicircles_json": _json.dumps(SEMICIRCLES),
            "semi_radius_json": _json.dumps(SEMI_RADIUS),
            "instrument_labels_json": _json.dumps(labels),
            "instrument_group_json": _json.dumps(instrument_group),
            "group_colors_json": _json.dumps(projection_group_colors),
        })

    @r.get("/api/health")
    async def health():
        return JSONResponse({"ok": True})

    return r


def make_public_router() -> APIRouter:
    """Portos 8001 e 80: vista de público."""
    r = APIRouter()

    @r.get("/", response_class=HTMLResponse)
    async def public(request: Request):
        return _render_with_cookie(request, "public.html", {})

    return r

