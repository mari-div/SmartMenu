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


  // ---------------------------------------------------------------- avisos al mozo / cuenta
  async function avisar(tipo) {
    const r = await fetch(`/api/seguimiento/${token}/avisar`, { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tipo }) });
    const d = await r.json();
    if (!r.ok) { toast(d.error || "No se pudo avisar", "error"); return; }
    toast(tipo === "cuenta" ? "Pedimos tu cuenta. En un momento te la traen" : "Avisamos a tu mozo", "ok");
    pintarExtras(d);
  }
  $("btn-mozo").addEventListener("click", () => avisar("mozo"));
  $("btn-cuenta").addEventListener("click", () => avisar("cuenta"));

  // ---------------------------------------------------------------- dividir cuenta (el calculo lo hace el servidor)
  let propina = 0;
  async function pintarPartes() {
    const n = Math.max(1, Math.min(30, Number($("personas").value) || 1));
    $("personas").value = n;
    try {
      const r = await fetch(`/api/seguimiento/${token}/cuenta?personas=${n}&propina=${propina}`);
      const d = await r.json();
      if (!r.ok) return;
      const filas = [el("div", { class: "fila" }, el("span", {}, "Consumo"), el("span", {}, dinero(d.total)))];
      if (d.propina > 0) filas.push(el("div", { class: "fila" }, el("span", {}, "Propina"), el("span", {}, dinero(d.propina))));
      filas.push(el("div", { class: "fila total" }, el("span", {}, "Total"), el("strong", {}, dinero(d.total_con_propina))));
      if (d.personas > 1) {
        const iguales = d.partes.every((x) => x === d.partes[0]);
        filas.push(el("p", { class: "muted peq" }, iguales ? `Cada persona paga ${dinero(d.partes[0])}`
          : `Cada persona paga ${dinero(d.partes[d.partes.length - 1])} (alguien pone ${dinero(d.partes[0])} para cuadrar los centavos)`));
      }
      $("partes").replaceChildren(...filas);
    } catch (_) {}
  }
  $("personas").addEventListener("change", pintarPartes);
  $("per-menos").addEventListener("click", () => { $("personas").value = Number($("personas").value) - 1; pintarPartes(); });
  $("per-mas").addEventListener("click", () => { $("personas").value = Number($("personas").value) + 1; pintarPartes(); });
  document.querySelectorAll(".chips-propina .chip").forEach((c) => c.addEventListener("click", () => {
    document.querySelectorAll(".chips-propina .chip").forEach((x) => x.setAttribute("aria-pressed", String(x === c)));
    propina = Number(c.dataset.propina); pintarPartes();
  }));

  // ---------------------------------------------------------------- calificacion
  let estrellas = 0;
  const botones = [1, 2, 3, 4, 5].map((n) => {
    const b = el("button", { type: "button", class: "estrella", "aria-label": `${n} estrella${n > 1 ? "s" : ""}`, "aria-pressed": "false" }, icono("star"));
    b.addEventListener("click", () => {
      estrellas = n;
      botones.forEach((x, i) => { x.classList.toggle("on", i < n); x.setAttribute("aria-pressed", String(i + 1 === n)); });
      $("enviar-calif").disabled = false;
    });
    return b;
  });
  $("estrellas").replaceChildren(...botones);
  $("enviar-calif").addEventListener("click", async () => {
    $("enviar-calif").disabled = true; $("error-calif").hidden = true;
    const r = await fetch(`/api/seguimiento/${token}/calificar`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estrellas, comentario: $("comentario").value }) });
    const d = await r.json();
    if (!r.ok) { $("error-calif").textContent = d.error; $("error-calif").hidden = false; $("enviar-calif").disabled = false; return; }
    toast("¡Gracias por tu opinión!", "ok");
    pintarExtras(d);
  });

  function pintarExtras(p) {
    const activo = p.estado !== "cancelado" && !p.pagado;
    $("acciones").hidden = !activo;
    const mozoAvisado = p.avisos_pendientes.includes("mozo"), cuentaPedida = p.avisos_pendientes.includes("cuenta");
    $("btn-mozo").disabled = mozoAvisado;
    $("btn-mozo").querySelector("span").textContent = mozoAvisado ? "Mozo avisado" : "Llamar al mozo";
    $("btn-cuenta").hidden = !p.puede_pedir_cuenta;
    $("btn-cuenta").disabled = cuentaPedida;
    $("btn-cuenta").querySelector("span").textContent = cuentaPedida ? "Cuenta solicitada" : "Pedir la cuenta";
    $("acciones-estado").textContent = cuentaPedida ? "Tu mozo viene con la cuenta." : mozoAvisado ? "Tu mozo ya fue avisado." : "";

    const mostrarCuenta = ["listo", "entregado"].includes(p.estado) && !p.pagado;
    if ($("card-cuenta").hidden && mostrarCuenta) pintarPartes();
    $("card-cuenta").hidden = !mostrarCuenta;

    $("card-calificar").hidden = !p.puede_calificar;
    $("gracias").hidden = !(p.calificacion || p.pagado);
    if (p.calificacion) $("gracias").textContent = `Tu calificación: ${"★".repeat(p.calificacion)}${"☆".repeat(5 - p.calificacion)} · ¡gracias!`;
    else if (p.pagado) $("gracias").textContent = "Pedido pagado. ¡Gracias por tu visita!";
  }

  async function actualizar() {
    try {
      const r = await fetch(`/api/seguimiento/${token}`);
      if (!r.ok) throw new Error();
      const p = await r.json();
      pintarEstado(p); pintarEta(p); pintarDetalle(p); pintarExtras(p);
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
