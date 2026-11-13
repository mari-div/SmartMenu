// Panel del mozo: mesas, pedidos en curso y ALERTA cuando la cocina marca un pedido como listo.
(() => {
  const $ = (id) => document.getElementById(id);
  const { el, icono, toast, reducido } = SM;

  const ESTADO = {
    libre: "Libre", pendiente: "En espera", en_preparacion: "Cocinando", listo: "¡Listo!",
  };
  let listosPrevios = new Set();
  let primera = true;

  async function accion(id, ruta, boton) {
    boton.disabled = true;
    try {
      const r = await fetch(`/api/pedidos/${id}/${ruta}`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "No se pudo completar la acción");
      toast(ruta === "avanzar" ? `Pedido #${id} entregado` : `Pedido #${id} cancelado`, "ok");
    } catch (e) { toast(e.message, "error"); }
    cargar();
  }

  // ---------------------------------------------------------------- mesas
  function pintarMesas(mesas) {
    $("mesas").replaceChildren(...mesas.map((m) => {
      const a = el("a", { class: `mesa-btn est-${m.estado}`, href: `/mozo/mesa/${m.id}`,
        "aria-label": `Mesa ${m.numero}, ${ESTADO[m.estado]}` },
        el("span", { class: "mesa-btn-num" }, String(m.numero)),
        el("span", { class: "mesa-btn-cap" }, icono("users"), `${m.capacidad}`),
        el("span", { class: "mesa-btn-est" }, ESTADO[m.estado]));
      return a;
    }));
  }

  // ---------------------------------------------------------------- alertas (listos)
  function tarjetaListo(p) {
    const entregar = el("button", { type: "button", class: "btn btn-primary btn-lg" }, icono("package-check"), "Entregar a mesa");
    entregar.addEventListener("click", () => accion(p.id, "avanzar", entregar));
    return el("article", { class: "alerta-card" },
      el("div", { class: "alerta-info" },
        el("span", { class: "alerta-mesa" }, `Mesa ${p.mesa}`),
        el("span", { class: "muted" }, `Pedido #${p.id} · ${p.items.reduce((s, i) => s + i.cantidad, 0)} platos`
          + (p.listo_hace_min != null ? ` · listo hace ${Math.max(0, Math.round(p.listo_hace_min))} min` : "")),
        el("ul", {}, ...p.items.map((i) => el("li", {}, `${i.cantidad}× ${i.plato}`)))),
      entregar);
  }

  // ---------------------------------------------------------------- en curso
  function tarjetaCurso(p) {
    const cancelar = p.estado === "pendiente"
      ? el("button", { type: "button", class: "btn btn-ghost btn-sm" }, "Cancelar") : null;
    cancelar?.addEventListener("click", () => {
      if (confirm(`¿Cancelar el pedido #${p.id} de la mesa ${p.mesa}?`)) accion(p.id, "cancelar", cancelar);
    });
    const eta = p.estado === "listo" ? "Listo para entregar"
      : `~${Math.ceil(p.minutos_estimados)} min restantes`;
    return el("article", { class: `curso-card est-${p.estado}` },
      el("div", { class: "curso-cab" },
        el("b", {}, `Mesa ${p.mesa}`),
        el("span", { class: `badge b-${p.estado}` }, ESTADO[p.estado] || p.estado)),
      el("p", { class: "muted" }, p.items.map((i) => `${i.cantidad}× ${i.plato}`).join(" · ")),
      el("div", { class: "curso-pie" },
        el("span", { class: "muted" }, icono("clock"), eta),
        el("span", { class: "curso-acc" },
          el("a", { class: "btn btn-ghost btn-sm", href: `/mozo/pedido/${p.id}` }, icono("qr"), "QR"),
          cancelar)));
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
      $("lista-curso").replaceChildren(...(enCurso.length ? enCurso.map(tarjetaCurso)
        : [el("p", { class: "vacio-mini" }, "No tienes pedidos en preparación.")]));
      $("c-curso").textContent = enCurso.length;

      // aviso sonoro/visual para cada pedido que acaba de quedar listo
      const nuevos = listos.filter((p) => !listosPrevios.has(p.id));
      if (nuevos.length && !primera) {
        SM.beep("listo");
        nuevos.forEach((p) => toast(`Mesa ${p.mesa}: ¡pedido listo para entregar!`, "ok", 6000));
        if (navigator.vibrate) navigator.vibrate([120, 60, 120]);
      }
      listosPrevios = new Set(listos.map((p) => p.id));
      primera = false;

      document.title = (listos.length ? `(${listos.length}) ` : "") + "Mozo · SmartMenu";
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
