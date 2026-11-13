"""Panel de administracion: KPIs, ventas, pedidos, menu, usuarios y bitacora."""
import re

from flask import Blueprint, Response, abort, jsonify, render_template, request

from analisis import graficos
from app.auth import registrar, rol_requerido, usuario_actual
from app.extensions import db
from app.models import Auditoria, Categoria, Ingrediente, Pedido, Plato, Rol, Usuario
from app.servicios import admin as servicio

bp = Blueprint("admin", __name__, url_prefix="/admin")
SOLO_ADMIN = rol_requerido("admin")

TITULOS_GRAFICOS = {
    "ventas_por_hora": "Pedidos por hora", "ventas_por_dia_semana": "Ingreso por día de la semana",
    "top_platos": "Platos más vendidos", "ventas_diarias": "Tendencia de ingresos",
    "pareto": "Pareto ABC de platos", "tiempos_por_hora": "Tiempos de cocina por hora",
    "matriz_ingenieria_menu": "Matriz de ingeniería del menú",
    "prediccion_demanda": "Predicción de demanda (7 días)",
}


# ---------------------------------------------------------------- paginas
@bp.get("/")
@SOLO_ADMIN
def resumen():
    return render_template("admin/resumen.html", seccion="resumen")


@bp.get("/api/resumen")
@SOLO_ADMIN
def api_resumen():
    try:
        dias = int(request.args.get("dias", 30))
    except ValueError:
        return jsonify(error="'dias' debe ser un número"), 400
    return jsonify(servicio.resumen(min(max(dias, 1), 3650)))


@bp.get("/api/vivo")
@SOLO_ADMIN
def api_vivo():
    return jsonify(servicio.estado_en_vivo())


@bp.get("/pedidos")
@SOLO_ADMIN
def pedidos():
    estado = request.args.get("estado", "")
    consulta = Pedido.query.order_by(Pedido.creado_en.desc())
    if estado:
        consulta = consulta.filter_by(estado=estado)
    return render_template("admin/pedidos.html", seccion="pedidos", estado=estado,
                           lista=consulta.limit(100).all())


@bp.get("/menu")
@SOLO_ADMIN
def menu():
    return render_template("admin/menu.html", seccion="menu",
                           categorias=Categoria.query.order_by(Categoria.orden).all(),
                           ingredientes=Ingrediente.query.order_by(Ingrediente.nombre).all())


@bp.patch("/api/platos/<int:plato_id>")
@SOLO_ADMIN
def editar_plato(plato_id: int):
    plato = db.get_or_404(Plato, plato_id)
    datos = request.get_json(silent=True) or {}
    cambios = []
    try:
        if "precio" in datos:
            precio = round(float(datos["precio"]), 2)
            if not 0 < precio < 10000:
                raise ValueError("El precio debe ser mayor que 0")
            cambios.append(f"precio {plato.precio:.2f}->{precio:.2f}")
            plato.precio = precio
        if "costo" in datos:
            costo = round(float(datos["costo"]), 2)
            if not 0 <= costo < 10000:
                raise ValueError("El costo no es válido")
            plato.costo = costo
        if "disponible" in datos:
            plato.disponible = bool(datos["disponible"])
            cambios.append("disponible" if plato.disponible else "NO disponible")
        if "imagen_url" in datos:
            url = str(datos["imagen_url"]).strip()
            if url and not re.match(r"^https?://", url):
                raise ValueError("La foto debe ser un enlace http(s)")
            plato.imagen_url = url[:500] or None
            cambios.append("foto")
    except (TypeError, ValueError) as e:
        return jsonify(error=str(e)), 400
    db.session.commit()
    registrar("PLATO_EDITADO", f"{plato.nombre}: {', '.join(cambios) or 'sin cambios'}")
    return jsonify(plato.a_dict())


@bp.post("/api/ingredientes/<int:ingrediente_id>/reponer")
@SOLO_ADMIN
def reponer(ingrediente_id: int):
    ingrediente = db.get_or_404(Ingrediente, ingrediente_id)
    try:
        cantidad = float((request.get_json(silent=True) or {}).get("cantidad"))
    except (TypeError, ValueError):
        return jsonify(error="Indica una cantidad numérica"), 400
    if not 0 < cantidad <= 10000:
        return jsonify(error="La cantidad debe ser mayor que 0"), 400
    ingrediente.stock = round(ingrediente.stock + cantidad, 2)
    db.session.commit()
    registrar("STOCK_REPUESTO", f"{ingrediente.nombre} +{cantidad:g} {ingrediente.unidad}")
    return jsonify(nombre=ingrediente.nombre, stock=ingrediente.stock, bajo=ingrediente.stock_bajo)


# ---------------------------------------------------------------- usuarios
@bp.get("/usuarios")
@SOLO_ADMIN
def usuarios():
    return render_template("admin/usuarios.html", seccion="usuarios",
                           lista=Usuario.query.order_by(Usuario.rol, Usuario.username).all(),
                           roles=[r.value for r in Rol])


@bp.post("/api/usuarios")
@SOLO_ADMIN
def crear_usuario():
    d = request.get_json(silent=True) or {}
    username = str(d.get("username", "")).strip().lower()
    nombre = str(d.get("nombre", "")).strip()
    rol, clave = d.get("rol"), str(d.get("password", ""))
    if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
        return jsonify(error="Usuario: 3-30 caracteres (letras minúsculas, números o _)"), 400
    if not nombre:
        return jsonify(error="Escribe el nombre completo"), 400
    if rol not in {r.value for r in Rol}:
        return jsonify(error="Rol no válido"), 400
    if len(clave) < 6:
        return jsonify(error="La contraseña debe tener al menos 6 caracteres"), 400
    if Usuario.query.filter_by(username=username).first():
        return jsonify(error="Ese usuario ya existe"), 409
    usuario = Usuario(username=username, nombre=nombre[:80], rol=rol)
    usuario.set_password(clave)
    db.session.add(usuario)
    db.session.commit()
    registrar("USUARIO_CREADO", f"{username} ({rol})")
    return jsonify(usuario.a_dict()), 201


@bp.patch("/api/usuarios/<int:usuario_id>")
@SOLO_ADMIN
def editar_usuario(usuario_id: int):
    usuario = db.get_or_404(Usuario, usuario_id)
    d = request.get_json(silent=True) or {}
    yo = usuario_actual()
    if "activo" in d:
        if usuario.id == yo.id and not d["activo"]:
            return jsonify(error="No puedes desactivar tu propia cuenta"), 400
        usuario.activo = bool(d["activo"])
        registrar("USUARIO_ACTIVO" if usuario.activo else "USUARIO_DESACTIVADO", usuario.username)
    if d.get("password"):
        if len(str(d["password"])) < 6:
            return jsonify(error="La contraseña debe tener al menos 6 caracteres"), 400
        usuario.set_password(str(d["password"]))
        registrar("CLAVE_RESTABLECIDA", usuario.username)
    db.session.commit()
    return jsonify(usuario.a_dict())


# ---------------------------------------------------------------- bitacora
@bp.get("/logs")
@SOLO_ADMIN
def logs():
    accion = request.args.get("accion", "")
    q = request.args.get("q", "").strip()
    try:
        pagina = max(1, int(request.args.get("pagina", 1)))
    except ValueError:
        pagina = 1
    consulta = Auditoria.query.order_by(Auditoria.fecha.desc(), Auditoria.id.desc())
    if accion:
        consulta = consulta.filter_by(accion=accion)
    if q:
        patron = f"%{q}%"
        consulta = consulta.filter(db.or_(Auditoria.username.ilike(patron),
                                          Auditoria.detalle.ilike(patron)))
    total = consulta.count()
    filas = consulta.offset((pagina - 1) * 50).limit(50).all()
    acciones = [a for (a,) in db.session.query(Auditoria.accion).distinct().order_by(Auditoria.accion)]
    return render_template("admin/logs.html", seccion="logs", filas=filas, acciones=acciones,
                           accion=accion, q=q, pagina=pagina, total=total,
                           paginas=max(1, -(-total // 50)))


# ---------------------------------------------------------------- analisis avanzado (matplotlib)
@bp.get("/analisis")
@SOLO_ADMIN
def analisis():
    limpio, informe = servicio.cargar_limpio()
    return render_template("admin/analisis.html", seccion="analisis", hay_datos=limpio is not None,
                           informe=informe, graficos=list(graficos.GRAFICOS),
                           titulos=TITULOS_GRAFICOS)


@bp.get("/grafico/<nombre>.png")
@SOLO_ADMIN
def grafico(nombre: str):
    funcion = graficos.GRAFICOS.get(nombre)
    if funcion is None:
        abort(404)
    limpio, _ = servicio.cargar_limpio()
    if limpio is None:
        abort(404)
    oscuro = request.args.get("tema") == "oscuro"
    return Response(graficos.a_png(funcion(limpio), oscuro=oscuro, sin_titulo=True),
                    mimetype="image/png")
