"""Autenticacion por sesion, control de acceso por rol y bitacora de auditoria."""
from datetime import datetime, timedelta
from functools import wraps

from flask import jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.usuario import Auditoria, Usuario

MAX_INTENTOS = 5                      # intentos fallidos permitidos...
VENTANA_BLOQUEO = timedelta(minutes=5)  # ...dentro de esta ventana


_CLAVE = "smartmenu.usuario"      # se guarda en la peticion (no en `g`) para no mezclar peticiones


def usuario_actual() -> Usuario | None:
    """Usuario con sesion iniciada (se consulta una sola vez por peticion)."""
    if _CLAVE not in request.environ:
        uid = session.get("uid")
        usuario = db.session.get(Usuario, uid) if uid else None
        request.environ[_CLAVE] = usuario if usuario and usuario.activo else None
    return request.environ[_CLAVE]


def iniciar_sesion(usuario: Usuario) -> None:
    session.clear()
    session["uid"] = usuario.id
    session.permanent = False
    usuario.ultimo_acceso = datetime.now()
    request.environ[_CLAVE] = usuario


def cerrar_sesion() -> None:
    session.clear()
    request.environ[_CLAVE] = None


# ---------------------------------------------------------------- bitacora
def registrar(accion: str, detalle: str = "", usuario: Usuario | None = None,
              username: str | None = None) -> None:
    """Guarda una accion en la bitacora. Nunca debe tumbar la peticion que la origino."""
    usuario = usuario or (usuario_actual() if request else None)
    try:
        db.session.add(Auditoria(
            username=username or (usuario.username if usuario else None),
            rol=usuario.rol if usuario else None,
            accion=accion, detalle=detalle[:500],
            ip=request.remote_addr if request else None))
        db.session.commit()
    except Exception:  # pragma: no cover - la auditoria no debe romper el flujo
        db.session.rollback()


def intentos_recientes(username: str, ahora: datetime | None = None) -> int:
    """Cuantos logins fallidos tuvo este usuario en los ultimos minutos."""
    desde = (ahora or datetime.now()) - VENTANA_BLOQUEO
    return Auditoria.query.filter(Auditoria.accion == "LOGIN_FALLIDO",
                                  Auditoria.username == username,
                                  Auditoria.fecha >= desde).count()


# ---------------------------------------------------------------- decoradores
def _es_api() -> bool:
    return request.path.startswith("/api/") or "/api/" in request.path \
        or request.accept_mimetypes.best == "application/json"


def login_requerido(vista):
    return rol_requerido()(vista)


def rol_requerido(*roles: str):
    """Exige sesion y, si se indican roles, que el usuario tenga uno de ellos."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            usuario = usuario_actual()
            if usuario is None:
                if _es_api():
                    return jsonify(error="Debes iniciar sesión"), 401
                return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
            if roles and usuario.rol not in roles:
                registrar("ACCESO_DENEGADO", f"{request.method} {request.path}")
                if _es_api():
                    return jsonify(error="No tienes permiso para esta acción"), 403
                return render_template("403.html"), 403
            return vista(*args, **kwargs)
        return envoltura
    return decorador
