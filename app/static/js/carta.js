// Carta digital: carrito, filtros sin recarga, categorias y panel movil.
// Los totales NO se calculan aqui: se piden al servidor (/api/cotizar) para que
// siempre coincidan con lo que se cobra.
(() => {
  const $ = (id) => document.getElementById(id);
  const { dinero, el, icono, toast, contar, reducido } = SM;
  const aside = $("carrito");
    const menu = $("menu");
  const mesaId = Number(aside.dataset.mesaId);
  const claveCarrito = "sm-carrito-mesa-" + mesaId;

  // ---------------------------------------------------------------- estado
  let carrito = new Map();                                // id -> {id, nombre, precio, cantidad}
  try {
    const guardado = JSON.parse(sessionStorage.getItem(claveCarrito) || "[]");
    carrito = new Map(guardado.map((i) => [String(i.id), i]));
  } catch (_) { /* sin almacenamiento: carrito solo en memoria */ }
  const guardar = () => {
    try { sessionStorage.setItem(claveCarrito, JSON.stringify([...carrito.values()])); } catch (_) {}
  };
  const unidades = () => [...carrito.values()].reduce((s, i) => s + i.cantidad, 0);
  const items = () => [...carrito.values()].map((i) => ({ plato_id: i.id, cantidad: i.cantidad }));
  const comensales = () => Math.max(1, Math.min(30, Number($("comensales").value) || 1));

  // ---------------------------------------------------------------- tarjetas de platos
  function sincronizarTarjetas() {
    menu.querySelectorAll(".plato").forEach((card) => {
      const cant = carrito.get(card.dataset.id)?.cantidad || 0;
      const n = card.querySelector(".n");
      card.classList.toggle("sel", cant > 0);
      if (n.textContent !== String(cant)) {
        n.textContent = cant;
        if (!reducido) { n.classList.remove("salta"); void n.offsetWidth; n.classList.add("salta"); }
      }
    });
  }

  function cambiar(card, delta) {
    const id = card.dataset.id;
    const nueva = Math.max(0, Math.min(20, (carrito.get(id)?.cantidad || 0) + delta));
    if (nueva === 0) carrito.delete(id);
    else carrito.set(id, { id: Number(id), nombre: card.dataset.nombre, precio: Number(card.dataset.precio), cantidad: nueva });
    guardar();
    actualizar();
  }

  menu.addEventListener("click", (e) => {
    const card = e.target.closest(".plato");
    if (!card) return;
    if (e.target.closest(".btn-add, .mas")) cambiar(card, 1);
    else if (e.target.closest(".menos")) cambiar(card, -1);
  });

  // ---------------------------------------------------------------- panel del carrito
  function pintarLista() {
    const lista = $("lista-carrito");
    const previos = new Set([...lista.children].map((li) => li.dataset.id));
    lista.replaceChildren(...[...carrito.values()].map((i) => {
      const li = el("li", { "data-id": i.id },
        el("span", { class: "li-nombre" }, i.nombre),
        el("span", { class: "li-det" }, `${i.cantidad} × ${dinero(i.precio)}`),
        el("span", { class: "li-precio" }, dinero(i.precio * i.cantidad)));
      if (previos.has(String(i.id))) li.style.animation = "none";    // solo anima los nuevos
      return li;
    }));
    $("carrito-vacio").hidden = carrito.size > 0;
  }

  let controlCotizar;
  async function cotizar() {
    if (carrito.size === 0) { $("totales").hidden = true; return; }
    controlCotizar?.abort();
    controlCotizar = new AbortController();
    try {
      const r = await fetch("/api/cotizar", {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: controlCotizar.signal,
        body: JSON.stringify({ items: items(), comensales: comensales() }),
      });
      if (!r.ok) return;
      const d = await r.json();
      $("totales").hidden = false;
      contar($("t-subtotal"), d.subtotal, dinero);
      contar($("t-total"), d.total, dinero);
      contar($("bc-total"), d.total, dinero);
      $("fila-desc").hidden = d.descuento <= 0;
      if (d.descuento > 0) {
        $("t-regla").textContent = d.regla_aplicada || "Descuento";
        contar($("t-descuento"), d.descuento, (n) => "-" + dinero(n));
      }
    } catch (e) { if (e.name !== "AbortError") toast("No se pudo calcular el total", "error"); }
  }

  let ultimoN = 0;
  function actualizar() {
    const n = unidades();
    sincronizarTarjetas();
    pintarLista();
    $("enviar").disabled = n === 0;
    $("barra-carrito").hidden = n === 0;
    $("bc-n").textContent = n;
    if (n !== ultimoN && n > 0 && !reducido) {
      const barra = $("barra-carrito");
      barra.classList.remove("bump"); void barra.offsetWidth; barra.classList.add("bump");
    }
    ultimoN = n;
    if (n === 0) cerrarPanel();
    cotizar();
  }

  // ---------------------------------------------------------------- panel movil (hoja inferior)
  const movil = matchMedia("(max-width: 900px)");
  function abrirPanel() {
    if (!movil.matches) return;
    aside.classList.add("abierto"); aside.inert = false;
    $("velo").hidden = false; $("barra-carrito").setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }
  function cerrarPanel() {
    aside.classList.remove("abierto"); $("velo").hidden = true;
    $("barra-carrito").setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
    aside.inert = movil.matches;                       // fuera de pantalla: no enfocable
  }
  $("barra-carrito").addEventListener("click", abrirPanel);
  $("cerrar-carrito").addEventListener("click", cerrarPanel);
  $("velo").addEventListener("click", cerrarPanel);
  addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarPanel(); });
  movil.addEventListener("change", cerrarPanel);

  // ---------------------------------------------------------------- comensales
  const cambiarCom = (d) => { $("comensales").value = Math.max(1, Math.min(30, comensales() + d)); cotizar(); };
  $("com-menos").addEventListener("click", () => cambiarCom(-1));
  $("com-mas").addEventListener("click", () => cambiarCom(1));
  $("comensales").addEventListener("change", () => { $("comensales").value = comensales(); cotizar(); });

  // ---------------------------------------------------------------- filtros de dieta (sin recargar)
  let controlFiltro;
  async function aplicarFiltros() {
    const dietas = [...document.querySelectorAll(".chip[aria-pressed='true']")].map((c) => c.dataset.dieta);
    const params = new URLSearchParams();
    dietas.forEach((d) => params.append("dieta", d));
    history.replaceState(null, "", params.size ? "?" + params : location.pathname);
    params.set("parcial", "1");
    controlFiltro?.abort();
    controlFiltro = new AbortController();
    menu.classList.add("cargando");
    try {
      const r = await fetch(`${menu.dataset.url}?${params}`, { signal: controlFiltro.signal });
      menu.innerHTML = await r.text();
      sincronizarTarjetas();
      vigilarCategorias();
    } catch (e) { if (e.name !== "AbortError") toast("No se pudo filtrar la carta", "error"); }
    menu.classList.remove("cargando");
  }
  document.querySelectorAll(".chip").forEach((chip) => chip.addEventListener("click", () => {
    chip.setAttribute("aria-pressed", chip.getAttribute("aria-pressed") === "true" ? "false" : "true");
    aplicarFiltros();
  }));

  // ---------------------------------------------------------------- categoria activa al hacer scroll
  let observador;
  function vigilarCategorias() {
    observador?.disconnect();
    const enlaces = [...menu.querySelectorAll(".catnav a")];
    if (!enlaces.length || !("IntersectionObserver" in window)) return;
    observador = new IntersectionObserver((entradas) => {
      entradas.forEach((en) => {
        if (!en.isIntersecting) return;
        enlaces.forEach((a) => {
          const activa = a.getAttribute("href") === "#" + en.target.id;
          a.setAttribute("aria-current", activa ? "true" : "false");
          if (activa) a.scrollIntoView({ block: "nearest", inline: "center", behavior: reducido ? "auto" : "smooth" });
        });
      });
    }, { rootMargin: "-25% 0px -65% 0px" });
    menu.querySelectorAll(".categoria").forEach((s) => observador.observe(s));
  }

  // ---------------------------------------------------------------- enviar pedido
  $("enviar").addEventListener("click", async () => {
    const boton = $("enviar");
    boton.disabled = true; boton.classList.add("enviando");
    $("error").hidden = true;
    try {
      const r = await fetch("/api/pedidos", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mesa_id: mesaId, items: items(), comensales: comensales(), notas: $("notas").value }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "No se pudo enviar el pedido");
      try { sessionStorage.removeItem(claveCarrito); } catch (_) {}
      boton.classList.remove("enviando"); boton.classList.add("ok");
      boton.querySelector(".btn-texto").textContent = "¡Pedido enviado!";
      toast("Pedido enviado a cocina", "ok");
      setTimeout(() => { location.href = "/mozo/pedido/" + d.id; }, reducido ? 0 : 700);
    } catch (e) {
      boton.classList.remove("enviando"); boton.disabled = false;
      $("error").textContent = e.message; $("error").hidden = false;
      toast(e.message, "error");
    }
  });

  // ---------------------------------------------------------------- inicio
  aside.inert = movil.matches;
  vigilarCategorias();
  actualizar();
})();
