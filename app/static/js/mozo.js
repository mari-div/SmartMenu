// Panel del mozo: mesas, pedidos en curso, ALERTAS (pedido listo y avisos del cliente) y cobro.
(() => {
  const $ = (id) => document.getElementById(id);
  const { el, icono, toast, dinero } = SM;

  const ESTADO = {
    libre: "Libre", pendiente: "En espera", en_preparacion: "Cocinando", listo: "¡Listo!", por_cobrar: "Por cobrar",
  };
  let listosPrevios = new Set();
  let avisosPrevios = new Set();
  let primera = true;

  async function enviarAccion(url, cuerpo, mensajeOk) {
    try {
      const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
        body: cuerpo ? JSON.stringify(cuerpo) : undefined });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "No se pudo completar la acción");
      if (mensajeOk) toast(mensajeOk, "ok");
      return d;
    } catch (e) { toast(e.message, "error"); return null; }
    finally { cargar(); }
  }

  // Mantiene los nodos existentes (para no borrar lo que el mozo esta escribiendo) y solo agrega/quita
  function sincronizar(contenedor, items, crear, clave = (x) => x.id) {
    const existentes = new Map([...contenedor.children].map((n) => [n.dataset.clave, n]));
    const ids = new Set(items.map((x) => String(clave(x))));
    existentes.forEach((n, k) => { if (!ids.has(k)) n.remove(); });
    items.forEach((x, i) => {
      let nodo = existentes.get(String(clave(x)));
      if (!nodo) { nodo = crear(x); nodo.dataset.clave = String(clave(x)); }
      if (contenedor.children[i] !== nodo) contenedor.insertBefore(nodo, contenedor.children[i] || null);
    });
  }

  // ---------------------------------------------------------------- mesas
  function pintarMesas(mesas) {
    $("mesas").replaceChildren(...mesas.map((m) => el("a", {
      class: `mesa-btn est-${m.estado}`, href: `/mozo/mesa/${m.id}`, "aria-label": `Mesa ${m.numero}, ${ESTADO[m.estado]}` },
      el("span", { class: "mesa-btn-num" }, String(m.numero)),
      el("span", { class: "mesa-btn-cap" }, icono("users"), `${m.capacidad}`),
      el("span", { class: "mesa-btn-est" }, ESTADO[m.estado]))));
  }

  // ---------------------------------------------------------------- alertas: pedido listo
  function tarjetaListo(p) {
    const entregar = el("button", { type: "button", class: "btn btn-primary btn-lg" }, icono("package-check"), "Entregar a mesa");
    entregar.addEventListener("click", () => { entregar.disabled = true; enviarAccion(`/api/pedidos/${p.id}/avanzar`, null, `Pedido #${p.id} entregado`); });
    return el("article", { class: "alerta-card" },
      el("div", { class: "alerta-info" },
        el("span", { class: "alerta-mesa" }, `Mesa ${p.mesa}`),
        el("span", { class: "muted" }, `Pedido #${p.id} · ${p.items.reduce((s, i) => s + i.cantidad, 0)} platos`
          + (p.listo_hace_min != null ? ` · listo hace ${Math.max(0, Math.round(p.listo_hace_min))} min` : "")),
        el("ul", {}, ...p.items.map((i) => el("li", {}, `${i.cantidad}× ${i.plato}`)))),
      entregar);
  }

  // ---------------------------------------------------------------- avisos del cliente
  function filaAviso(a) {
    const atender = el("button", { type: "button", class: "btn btn-primary btn-sm" }, icono("check"), "Atendido");
    atender.addEventListener("click", () => { atender.disabled = true; enviarAccion(`/api/avisos/${a.id}/atender`, null, "Aviso atendido"); });
    return el("div", { class: "aviso-fila" },
      el("span", {}, el("b", {}, `Mesa ${a.mesa}`), ` · ${a.etiqueta} (hace ${Math.max(0, Math.round(a.hace_min))} min)`), atender);
  }

  // ---------------------------------------------------------------- en curso
  function tarjetaCurso(p) {
    const acciones = [];
    if (p.estado === "pendiente" || p.estado === "en_preparacion") {
      acciones.push(el("a", { class: "btn btn-ghost btn-sm", href: `/mozo/mesa/${p.mesa_id}?pedido=${p.id}` }, icono("plus"), "Agregar"));
    }
    if (p.estado === "pendiente") {
      const cancelar = el("button", { type: "button", class: "btn btn-ghost btn-sm" }, "Cancelar");
      cancelar.addEventListener("click", () => {
        if (confirm(`¿Cancelar el pedido #${p.id} de la mesa ${p.mesa}?`)) enviarAccion(`/api/pedidos/${p.id}/cancelar`, null, `Pedido #${p.id} cancelado`);
      });
      acciones.push(cancelar);
    }
    const eta = p.estado === "listo" ? "Listo para entregar" : `~${Math.ceil(p.minutos_estimados)} min restantes`;
    return el("article", { class: `curso-card est-${p.estado}` },
      el("div", { class: "curso-cab" }, el("b", {}, `Mesa ${p.mesa}`),
        el("span", { class: `badge b-${p.estado}` }, ESTADO[p.estado] || p.estado)),
      el("p", { class: "muted" }, p.items.map((i) => `${i.cantidad}× ${i.plato}`).join(" · ")),
      el("div", { class: "curso-pie" },
        el("span", { class: "muted" }, icono("clock"), eta),
        el("span", { class: "curso-acc" }, el("a", { class: "btn btn-ghost btn-sm", href: `/mozo/pedido/${p.id}` }, icono("qr"), "QR"), ...acciones)));
  }

  // ---------------------------------------------------------------- por cobrar
  function tarjetaCobro(p) {
    const metodo = el("select", { "aria-label": `Método de pago de la mesa ${p.mesa}` },
      ...[["efectivo", "Efectivo"], ["tarjeta", "Tarjeta"], ["yape", "Yape"], ["plin", "Plin"]]
        .map(([v, t]) => el("option", { value: v }, t)));
    const propina = el("select", { "aria-label": `Propina de la mesa ${p.mesa}` },
      ...[["0", "Sin propina"], ["0.05", "Propina 5 %"], ["0.1", "Propina 10 %"], ["0.15", "Propina 15 %"]]
        .map(([v, t]) => el("option", { value: v }, t)));
    const boton = el("button", { type: "button", class: "btn btn-primary btn-sm" }, icono("cash"), "Cobrar");
    boton.addEventListener("click", async () => {
      boton.disabled = true;
      const d = await enviarAccion(`/api/pedidos/${p.id}/cobrar`, { metodo: metodo.value, propina: Number(propina.value) },
        `Mesa ${p.mesa} cobrada y liberada`);
      if (!d) boton.disabled = false;
    });
    return el("article", { class: "cobro-card" },
      el("div", { class: "cobro-cab" }, el("b", {}, `Mesa ${p.mesa}`), el("b", {}, dinero(p.total))),
      el("p", { class: "muted" }, `Pedido #${p.id} · ${p.items.length} ítems${p.descuento > 0 ? ` · descuento ${dinero(p.descuento)}` : ""}`),
      el("div", { class: "cobro-form" }, metodo, propina, boton));
  }

  async function cargar() {
    try {
      const r = await fetch("/api/mozo/panel");
      if (r.status === 401) { location.href = "/login?next=/mozo/"; return; }
      if (!r.ok) throw new Error();
      const d = await r.json();

      pintarMesas(d.mesas);
      const listos = d.pedidos.filter((p) => p.estado === "listo");
      const enCurso = d.pedidos.filter((p) => p.estado !== "listo");

      $("alertas").hidden = listos.length === 0;
      $("lista-listos").replaceChildren(...listos.map(tarjetaListo));
      $("c-listos").textContent = listos.length;

      $("avisos").hidden = d.avisos.length === 0;
      sincronizar($("lista-avisos"), d.avisos, filaAviso);
      $("c-avisos").textContent = d.avisos.length;

      $("lista-curso").replaceChildren(...(enCurso.length ? enCurso.map(tarjetaCurso)
        : [el("p", { class: "vacio-mini" }, "No tienes pedidos en preparación.")]));
      $("c-curso").textContent = enCurso.length;

      sincronizar($("lista-cobrar"), d.por_cobrar, tarjetaCobro);
      if (!d.por_cobrar.length && !$("lista-cobrar").querySelector(".vacio-mini")) {
        $("lista-cobrar").append(el("p", { class: "vacio-mini" }, "No hay cuentas por cobrar."));
      } else if (d.por_cobrar.length) { $("lista-cobrar").querySelector(".vacio-mini")?.remove(); }
      $("c-cobrar").textContent = d.por_cobrar.length;

      // sonido, vibracion y aviso en pantalla para lo que acaba de llegar
      const nuevosListos = listos.filter((p) => !listosPrevios.has(p.id));
      const nuevosAvisos = d.avisos.filter((a) => !avisosPrevios.has(a.id));
      if (!primera && (nuevosListos.length || nuevosAvisos.length)) {
        SM.beep("listo");
        nuevosListos.forEach((p) => toast(`Mesa ${p.mesa}: ¡pedido listo para entregar!`, "ok", 6000));
        nuevosAvisos.forEach((a) => toast(`Mesa ${a.mesa}: ${a.etiqueta}`, "info", 8000));
        if (navigator.vibrate) navigator.vibrate([120, 60, 120]);
      }
      listosPrevios = new Set(listos.map((p) => p.id));
      avisosPrevios = new Set(d.avisos.map((a) => a.id));
      primera = false;

      const alertas = listos.length + d.avisos.length;
      document.title = (alertas ? `(${alertas}) ` : "") + "Mozo · SmartMenu";
      $("vivo-txt").textContent = "En vivo";
      document.querySelector(".vivo .punto-vivo").classList.remove("off");
    } catch (_) {
      $("vivo-txt").textContent = "Sin conexión…";
      document.querySelector(".vivo .punto-vivo").classList.add("off");
    }
  }

  cargar();
  setInterval(cargar, 3000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) cargar(); });
})();
