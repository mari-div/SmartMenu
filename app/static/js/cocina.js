// Panel de cocina en vivo. Cada pedido es una tarjeta con identidad propia: al refrescar
// solo se actualizan los datos que cambian (reloj, prioridad); las tarjetas nuevas
// entran con animacion y las que cambian de columna salen de una y entran en otra.
(() => {
  const $ = (id) => document.getElementById(id);
  const { el, icono, toast, reducido } = SM;

  const rol = document.getElementById("kanban").dataset.rol;
  const COLUMNAS = {
    pendientes: { lista: $("col-pendientes"), contador: $("c-pendientes"), boton: ["Empezar a cocinar", "flame"] },
    en_preparacion: { lista: $("col-preparacion"), contador: $("c-preparacion"), boton: ["Marcar listo", "check"] },
    listos: { lista: $("col-listos"), contador: $("c-listos"), boton: ["Entregar a mesa", "utensils"] },
  };
  COLUMNAS.pendientes.lista.dataset.vacio = "Sin pedidos pendientes. ¡Todo al día!";
  COLUMNAS.en_preparacion.lista.dataset.vacio = "Nada en preparación ahora.";
  COLUMNAS.listos.lista.dataset.vacio = "Aún no hay pedidos listos.";
  if (rol === "cocina") COLUMNAS.listos.boton = ["", "check"];

  let primeraCarga = true;
  const vistos = new Set();                            // para avisar de pedidos nuevos

  async function enviar(id, accion, boton) {
    boton.disabled = true;
    try {
      const r = await fetch(`/api/pedidos/${id}/${accion}`, { method: "POST" });
      if (!r.ok) throw new Error((await r.json()).error || "Error");
      if (accion === "cancelar") toast(`Pedido #${id} cancelado`, "info");
    } catch (e) { toast(e.message, "error"); }
    cargar();
  }

  function claseReloj(min) { return min >= 12 ? "alto" : min >= 6 ? "medio" : ""; }

  function crear(p, columna) {
    const [textoBoton, icoBoton] = COLUMNAS[columna].boton;
    const reloj = el("span", { class: "reloj" }, icono("clock"), el("span", { class: "min" }));
    const meta = el("div", { class: "ticket-meta" },
      el("span", {}, icono("users"), `${p.comensales} comensal${p.comensales === 1 ? "" : "es"}`),
      p.mozo ? el("span", {}, icono("user"), p.mozo) : null,
      el("span", { class: "prio" }));
    const ul = el("ul", {}, ...p.items.map((i) =>
      el("li", {}, el("b", {}, `${i.cantidad}×`), el("span", {}, i.plato, i.notas ? el("small", {}, ` — ${i.notas}`) : null))));
    const t = el("article", { class: "ticket", "data-id": p.id },
      el("div", { class: "ticket-cab" },
        el("span", { class: "ticket-mesa" }, `Mesa ${p.mesa}`, el("small", {}, `#${p.id}`)), reloj),
      meta, ul);
    if (p.notas) t.append(el("div", { class: "ticket-nota" }, icono("note"), p.notas));

    const acciones = el("div", { class: "ticket-acc" });
    if (columna === "listos" && rol === "cocina") {
      // La cocina no entrega: el mozo ya fue avisado y viene por el pedido
      acciones.append(el("span", { class: "espera-mozo" }, icono("bell"), `Esperando a ${p.mozo || "el mozo"}`));
    } else {
      const principal = el("button", { type: "button", class: "principal" }, icono(icoBoton), textoBoton);
      principal.addEventListener("click", () => enviar(p.id, "avanzar", principal));
      acciones.append(principal);
    }
    if (columna !== "listos") {
      const cancelar = el("button", { type: "button", class: "cancelar", "aria-label": `Cancelar pedido ${p.id}` }, icono("x"));
      let temporizador;
      cancelar.addEventListener("click", () => {
        if (cancelar.classList.contains("seguro")) { clearTimeout(temporizador); enviar(p.id, "cancelar", cancelar); return; }
        cancelar.classList.add("seguro"); cancelar.replaceChildren(icono("x"), "¿Seguro?");
        temporizador = setTimeout(() => { cancelar.classList.remove("seguro"); cancelar.replaceChildren(icono("x")); }, 3000);
      });
      acciones.append(cancelar);
    }
    t.append(acciones);
    return t;
  }

  function actualizar(t, p, esPrimero, columna) {
    const min = Math.round(p.espera_min);
    t.querySelector(".min").textContent = `${min} min`;
    t.querySelector(".reloj").className = "reloj " + claseReloj(p.espera_min);
    t.classList.toggle("siguiente", esPrimero && columna === "pendientes");
    const prio = t.querySelector(".prio");
    prio.replaceChildren();
    if (columna === "pendientes") {
      prio.append(icono("flame", esPrimero ? "sig" : ""), esPrimero ? "Siguiente · " : "", `prioridad ${p.prioridad}`);
      prio.className = "prio" + (esPrimero ? " sig" : "");
    }
  }

  function renderColumna(columna, pedidos) {
    const { lista, contador } = COLUMNAS[columna];
    const existentes = new Map([...lista.children].filter((c) => !c.classList.contains("sale")).map((c) => [c.dataset.id, c]));
    const ids = new Set(pedidos.map((p) => String(p.id)));

    existentes.forEach((nodo, id) => {                       // los que ya no estan: salen
      if (ids.has(id)) return;
      nodo.classList.add("sale");
      setTimeout(() => nodo.remove(), reducido ? 0 : 300);
    });

    pedidos.forEach((p, i) => {                              // crear/actualizar y ordenar
      let nodo = existentes.get(String(p.id));
      if (!nodo) nodo = crear(p, columna);
      actualizar(nodo, p, i === 0, columna);
      const referencia = lista.children[i];
      if (referencia !== nodo) lista.insertBefore(nodo, referencia || null);
    });

    if (contador.textContent !== String(pedidos.length)) {
      contador.textContent = pedidos.length;
      contador.classList.remove("bump"); void contador.offsetWidth; contador.classList.add("bump");
    }
  }

  async function cargar() {
    try {
      const r = await fetch("/api/cocina/cola");
      if (r.status === 401) { location.href = "/login?next=/cocina"; return; }
      if (!r.ok) throw new Error();
      const d = await r.json();

      const nuevos = d.pendientes.filter((p) => !vistos.has(p.id));
      nuevos.forEach((p) => vistos.add(p.id));
      if (!primeraCarga && nuevos.length) {
        SM.beep("nuevo");
        toast(nuevos.length === 1 ? `Nuevo pedido: Mesa ${nuevos[0].mesa}` : `${nuevos.length} pedidos nuevos`, "info");
        if (navigator.vibrate) navigator.vibrate(80);
      }
      primeraCarga = false;

      // Las listas se pintan en orden de salida primero para que no "salten" tarjetas
      renderColumna("pendientes", d.pendientes);
      renderColumna("en_preparacion", d.en_preparacion);
      renderColumna("listos", d.listos);
      document.title = (d.pendientes.length ? `(${d.pendientes.length}) ` : "") + "Cocina · SmartMenu";
      $("vivo-txt").textContent = "En vivo · actualiza cada 4 s";
      document.querySelector("#vivo .punto-vivo").classList.remove("off");
    } catch (_) {
      $("vivo-txt").textContent = "Sin conexión, reintentando…";
      document.querySelector("#vivo .punto-vivo").classList.add("off");
    }
  }

  cargar();
  setInterval(cargar, 3000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) cargar(); });
})();
