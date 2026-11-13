// Seguimiento del pedido en vivo: consulta el estado cada 4 segundos.
(() => {
  const raiz = document.getElementById("seguimiento");
  const token = raiz.dataset.token;
  const $ = (x) => document.getElementById(x);
  const { dinero, el, icono, toast, contar } = SM;

  const ORDEN = ["pendiente", "en_preparacion", "listo", "entregado"];
  const TEXTOS = {
    pendiente: ["Recibimos tu pedido", "La cocina lo verá en un momento.", "bell"],
    en_preparacion: ["Estamos cocinando", "Tus platos ya están en preparación.", "chef"],
    listo: ["¡Tu pedido está listo!", "En unos segundos llega a tu mesa.", "check"],
    entregado: ["¡Buen provecho!", "Gracias por elegirnos. ¿Algo más?", "utensils"],
    cancelado: ["Pedido cancelado", "Si fue un error, puedes hacer uno nuevo.", "x"],
  };

  let estadoPrevio = raiz.dataset.estado;
  let totalMin = 0;               // el mayor estimado visto: sirve para dibujar el anillo
  let ultimaActualizacion = 0;
  let primera = true;

  function pintarEstado(p) {
    const [titulo, sub, ico] = TEXTOS[p.estado] || TEXTOS.pendiente;
    const h1 = $("estado-titulo");
    if (h1.textContent !== titulo) {
      h1.textContent = titulo;
      h1.classList.remove("cambia"); void h1.offsetWidth; h1.classList.add("cambia");
    }
    $("estado-sub").textContent = sub;
    $("anillo-ico").replaceWith(Object.assign(icono(ico, "anillo-ico"), { id: "anillo-ico" }));
    raiz.dataset.estado = p.estado;

    const idx = ORDEN.indexOf(p.estado);
    document.querySelectorAll("#pasos li").forEach((li, i) => {
      li.classList.toggle("hecho", i < idx || p.estado === "entregado");
      li.classList.toggle("actual", i === idx && p.estado !== "entregado");
      i === idx ? li.setAttribute("aria-current", "step") : li.removeAttribute("aria-current");
    });
    $("pasos").style.setProperty("--progreso", `${Math.max(0, idx) / (ORDEN.length - 1) * 100}%`);
  }

  function pintarEta(p) {
    const restante = Math.ceil(p.minutos_estimados);
    totalMin = Math.max(totalMin, restante, 1);
    const terminado = ["listo", "entregado", "cancelado"].includes(p.estado);
    $("eta-num").textContent = terminado ? "" : (restante || "<1");
    $("eta-unidad").textContent = terminado ? "" : "min";
    $("anillo-prog").style.strokeDashoffset =
      p.estado === "cancelado" ? 100 : terminado ? 0 : 100 - (100 * (1 - restante / totalMin));
    $("eta-num").parentElement.classList.toggle("fin", terminado);
  }

  function pintarDetalle(p) {
    $("detalle").replaceChildren(...p.items.map((i) => el("li", {},
      el("span", { class: "cant" }, `${i.cantidad}×`),
      el("span", {}, i.plato, i.notas ? el("small", { class: "nota" }, i.notas) : null))));
    $("total").textContent = dinero(p.total);
    $("r-fila-desc").hidden = !(p.descuento > 0);
    $("r-descuento").textContent = "-" + dinero(p.descuento);
  }

  async function actualizar() {
    try {
      const r = await fetch(`/api/seguimiento/${token}`);
      if (!r.ok) throw new Error();
      const p = await r.json();
      pintarEstado(p); pintarEta(p); pintarDetalle(p);
      if (!primera && p.estado !== estadoPrevio) {
        toast(TEXTOS[p.estado][0], p.estado === "cancelado" ? "error" : "ok");
        if (navigator.vibrate) navigator.vibrate(60);
      }
      estadoPrevio = p.estado; primera = false;
      ultimaActualizacion = Date.now();
    } catch (_) { ultimaActualizacion = ultimaActualizacion || 0; }
  }

  // "Actualizado hace X s" + indicador de conexion
  setInterval(() => {
    const punto = document.querySelector(".actualizado .punto-vivo");
    if (!ultimaActualizacion) return;
    const seg = Math.round((Date.now() - ultimaActualizacion) / 1000);
    $("actualizado").textContent = seg < 2 ? "Actualizado ahora" : `Actualizado hace ${seg} s`;
    punto.classList.toggle("off", seg > 12);
  }, 1000);

  actualizar();
  setInterval(actualizar, 4000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) actualizar(); });
})();
