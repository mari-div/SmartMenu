// Panel de administracion: KPIs reales, comparativa con el periodo anterior y graficos (Chart.js).
(() => {
  const $ = (id) => document.getElementById(id);
  const { el, icono, contar } = SM;
  const soles = (n) => "S/ " + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const soles0 = (n) => "S/ " + Math.round(n).toLocaleString("en-US");
  const entero = (n) => Math.round(n).toLocaleString("en-US");

  let dias = 30;
  let datos = null;
  let graficos = [];

  // ---------------------------------------------------------------- colores segun el tema
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const paleta = () => ({
    texto: css("--muted"), rejilla: css("--border"), fondo: css("--surface"),
    rojo: css("--primary-text"), dorado: css("--gold"), verde: css("--green"),
    serie: [css("--primary-text"), css("--gold"), css("--green"), "#3b82f6", "#a855f7", "#14b8a6"],
  });

  // ---------------------------------------------------------------- KPIs
  const KPIS = [
    { k: "ingresos", nombre: "Ingresos", icono: "dollar", fmt: soles0, var: "var_ingresos" },
    { k: "pedidos", nombre: "Pedidos", icono: "receipt", fmt: entero, var: "var_pedidos" },
    { k: "ticket_promedio", nombre: "Ticket promedio", icono: "tag", fmt: soles, var: "var_ticket" },
    { k: "platos_vendidos", nombre: "Platos vendidos", icono: "utensils", fmt: entero },
    { k: "margen_pct", nombre: "Margen bruto", icono: "trend", fmt: (n) => n.toFixed(1) + "%", sub: (d) => soles0(d.margen_bruto) + " de utilidad" },
    { k: "cancelados_pct", nombre: "Cancelaciones", icono: "x", fmt: (n) => n.toFixed(1) + "%", sub: (d) => `${d.cancelados} pedidos`, malo: true },
    { k: "espera_cocina_min", nombre: "Espera en cocina", icono: "clock", fmt: (n) => n.toFixed(1) + " min" },
    { k: "prep_min", nombre: "Preparación", icono: "timer", fmt: (n) => n.toFixed(1) + " min", sub: (d) => `${d.comensales_prom} comensales por pedido` },
  ];

  function pintarKpis(k) {
    $("kpis").replaceChildren(...KPIS.map((d, i) => {
      const valor = el("strong", { class: "kpi-valor" }, d.fmt(0));
      const v = d.var ? k[d.var] : null;
      const delta = v == null ? null : el("span", { class: `delta ${v >= 0 ? "sube" : "baja"}`, title: "Frente al periodo anterior" },
        icono("trend"), `${v >= 0 ? "+" : ""}${v}%`);
      const tarjeta = el("div", { class: "kpi visto", style: `--i:${i}` },
        el("span", { class: "kpi-ico" }, icono(d.icono)),
        el("span", { class: "kpi-nombre" }, d.nombre), valor, delta,
        d.sub ? el("small", { class: "kpi-sub" }, d.sub(k)) : null);
      SM.contar(valor, k[d.k], d.fmt, 900);
      return tarjeta;
    }));
  }

  // ---------------------------------------------------------------- graficos
  function ejes(c, titulo) {
    return {
      x: { ticks: { color: c.texto, maxRotation: 0, autoSkipPadding: 14 }, grid: { display: false }, border: { color: c.rejilla } },
      y: { beginAtZero: true, ticks: { color: c.texto }, grid: { color: c.rejilla }, border: { display: false },
           title: titulo ? { display: true, text: titulo, color: c.texto } : undefined },
    };
  }

  function crear(id, config) {
    const ctx = $(id).getContext("2d");
    const g = new Chart(ctx, config);
    graficos.push(g);
    return g;
  }

  function pintarGraficos(s) {
    graficos.forEach((g) => g.destroy()); graficos = [];
    const c = paleta();
    Chart.defaults.font.family = '"Karla", system-ui, sans-serif';
    Chart.defaults.color = c.texto;
    const base = { responsive: true, maintainAspectRatio: false, animation: SM.reducido ? false : { duration: 700 } };
    const tip = { callbacks: {} };

    crear("g-diarias", { type: "line", data: {
      labels: s.diarias.map((d) => d.fecha.slice(5)),
      datasets: [
        { label: "Ingreso diario", data: s.diarias.map((d) => d.ingresos), borderColor: c.rejilla, backgroundColor: c.rojo + "22", fill: true, tension: .3, pointRadius: 0, borderWidth: 2 },
        { label: "Media móvil 7 días", data: s.diarias.map((d) => d.media_movil), borderColor: c.rojo, tension: .35, pointRadius: 0, borderWidth: 3 },
      ] },
      options: { ...base, interaction: { mode: "index", intersect: false }, scales: ejes(c, "Soles (S/)"),
        plugins: { legend: { labels: { color: c.texto, usePointStyle: true } },
          tooltip: { callbacks: { label: (x) => `${x.dataset.label}: ${soles(x.parsed.y)}` } } } } });

    crear("g-categorias", { type: "doughnut", data: {
      labels: s.categorias.map((d) => d.categoria),
      datasets: [{ data: s.categorias.map((d) => d.ingresos), backgroundColor: c.serie, borderColor: c.fondo, borderWidth: 3 }] },
      options: { ...base, cutout: "62%", plugins: { legend: { position: "bottom", labels: { color: c.texto, usePointStyle: true } },
        tooltip: { callbacks: { label: (x) => `${x.label}: ${soles0(x.parsed)}` } } } } });

    const maxHora = Math.max(...s.horas.map((h) => h.pedidos));
    crear("g-horas", { type: "bar", data: {
      labels: s.horas.map((h) => h.hora + "h"),
      datasets: [{ label: "Pedidos", data: s.horas.map((h) => h.pedidos), borderRadius: 6,
        backgroundColor: s.horas.map((h) => (h.pedidos >= maxHora * 0.75 ? c.rojo : c.rojo + "88")) }] },
      options: { ...base, scales: ejes(c), plugins: { legend: { display: false } } } });

    crear("g-top", { type: "bar", data: {
      labels: s.top_platos.map((p) => p.plato),
      datasets: [{ label: "Unidades", data: s.top_platos.map((p) => p.unidades), backgroundColor: c.dorado, borderRadius: 6 }] },
      options: { ...base, indexAxis: "y", scales: { x: ejes(c).y, y: { ...ejes(c).x, ticks: { color: c.texto } } }, plugins: { legend: { display: false } } } });

    crear("g-mozos", { type: "bar", data: {
      labels: s.mozos.map((m) => m.mozo),
      datasets: [{ label: "Ingresos", data: s.mozos.map((m) => m.ingresos), backgroundColor: c.verde, borderRadius: 6 }] },
      options: { ...base, scales: ejes(c), plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (x) => { const m = s.mozos[x.dataIndex]; return [`${soles0(m.ingresos)}`, `${m.pedidos} pedidos · ticket ${soles(m.ticket)}`]; } } } } } });

    crear("g-tiempos", { type: "line", data: {
      labels: s.tiempos.map((t) => t.hora + "h"),
      datasets: [
        { label: "Espera antes de cocinar", data: s.tiempos.map((t) => t.espera_cocina), borderColor: c.dorado, tension: .3, borderWidth: 3, pointRadius: 3 },
        { label: "Preparación", data: s.tiempos.map((t) => t.preparacion), borderColor: c.rojo, tension: .3, borderWidth: 3, pointRadius: 3 },
      ] },
      options: { ...base, interaction: { mode: "index", intersect: false }, scales: ejes(c, "Minutos"),
        plugins: { legend: { labels: { color: c.texto, usePointStyle: true } } } } });

    crear("g-dias", { type: "bar", data: {
      labels: s.dias_semana.map((d) => d.nombre_dia),
      datasets: [{ label: "Ingreso promedio", data: s.dias_semana.map((d) => d.ingreso_prom_dia), backgroundColor: c.serie[2], borderRadius: 6 }] },
      options: { ...base, scales: ejes(c), plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (x) => soles0(x.parsed.y) } } } } });
  }

  // Mapa de calor dia x hora (HTML + CSS, sin libreria)
  function pintarCalor({ horas, dias: nombres, valores }) {
    const max = Math.max(1, ...valores.flat());
    const rejilla = el("div", { class: "calor-grid", style: `--cols:${horas.length}` });
    rejilla.append(el("span"), ...horas.map((h) => el("span", { class: "calor-h" }, h + "h")));
    valores.forEach((fila, d) => {
      rejilla.append(el("span", { class: "calor-d" }, nombres[d]));
      fila.forEach((v, i) => {
        const celda = el("span", { class: "calor-c", title: `${nombres[d]} ${horas[i]}h: ${v} pedidos` });
        celda.style.background = `color-mix(in srgb, var(--primary) ${Math.round((v / max) * 100)}%, var(--surface-2))`;
        rejilla.append(celda);
      });
    });
    $("calor").replaceChildren(rejilla);
  }

  // ---------------------------------------------------------------- alertas y tabla
  function pintarAlertas(vivo) {
    const bloques = [];
    if (vivo.stock_bajo.length) bloques.push(el("div", { class: "alerta-bloque" },
      el("h3", {}, icono("alert"), `Stock bajo (${vivo.stock_bajo.length})`),
      el("ul", {}, ...vivo.stock_bajo.slice(0, 8).map((i) => el("li", {}, `${i.nombre}: ${i.stock} ${i.unidad} (mín. ${i.minimo})`))),
      el("a", { class: "btn btn-ghost btn-sm", href: "/admin/menu" }, "Reponer en inventario")));
    if (vivo.platos_no_disponibles.length) bloques.push(el("div", { class: "alerta-bloque" },
      el("h3", {}, icono("x"), "Platos no disponibles"),
      el("ul", {}, ...vivo.platos_no_disponibles.map((n) => el("li", {}, n)))));
    $("alertas-admin").replaceChildren(...bloques);
  }

  function pintarVivo(v) {
    $("v-activos").textContent = v.activos; $("v-pendientes").textContent = v.pendientes;
    $("v-prep").textContent = v.en_preparacion; $("v-listos").textContent = v.listos;
    $("v-demorados-wrap").hidden = v.demorados.length === 0;
    $("v-demorados").textContent = v.demorados.length;
  }

  function pintarTabla(top) {
    $("tabla-top").querySelector("tbody").replaceChildren(...top.map((p) => el("tr", {},
      el("td", { "data-label": "Plato" }, p.plato), el("td", { "data-label": "Categoría" }, p.categoria),
      el("td", { class: "num", "data-label": "Unidades" }, entero(p.unidades)),
      el("td", { class: "num", "data-label": "Ingresos" }, soles(p.ingresos)),
      el("td", { class: "num", "data-label": "Margen" }, `${soles(p.margen)} (${p.margen_pct}%)`))));
  }

  // ---------------------------------------------------------------- carga
  async function cargar() {
    const r = await fetch(`/admin/api/resumen?dias=${dias}`);
    if (r.status === 401 || r.status === 403) { location.href = "/login?next=/admin/"; return; }
    datos = await r.json();
    pintarVivo(datos.vivo);
    $("vacio-resumen").hidden = !datos.vacio;
    $("contenido-resumen").hidden = !!datos.vacio;
    if (datos.vacio) return;
    pintarKpis(datos.kpis);
    const l = datos.limpieza;
    $("limpieza").replaceChildren(icono("check"), el("span", {},
      `Datos depurados: ${l.pedidos_iniciales} pedidos leídos → ${l.pedidos_cancelados} cancelados excluidos, `
      + `${l.pedidos_sin_tiempos} sin marca de tiempo y ${l.pedidos_con_tiempo_atipico} con tiempo atípico descartado → ${l.pedidos_validos} válidos.`));
    pintarGraficos(datos.series);
    pintarCalor(datos.series.calor);
    pintarAlertas(datos.vivo);
    pintarTabla(datos.series.top_platos);
  }

  document.querySelectorAll(".selector-rango button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".selector-rango button").forEach((x) => x.classList.toggle("activo", x === b));
    dias = Number(b.dataset.dias);
    cargar();
  }));
  SM.alCambiarTema(() => { if (datos && !datos.vacio) pintarGraficos(datos.series); });

  setInterval(async () => {                         // el bloque "en vivo" se refresca solo
    try { const r = await fetch("/admin/api/vivo"); if (r.ok) { const v = await r.json(); pintarVivo(v); if (datos && !datos.vacio) pintarAlertas(v); } } catch (_) {}
  }, 5000);
  cargar();
})();
