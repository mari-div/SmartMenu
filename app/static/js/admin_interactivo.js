// Admin > Analisis avanzado: matriz de ingenieria de menu y prediccion de demanda interactivas (Chart.js).
// Los datos los calcula pandas/numpy en el servidor (/admin/api/analisis/...); aqui solo se dibujan.
(() => {
  const $ = (id) => document.getElementById(id);
  if (!$("c-matriz") || typeof Chart === "undefined") return;

  const COLORES = { Estrella: "#e0a30c", Vaca: "#22a06b", Puzzle: "#ef4444", Perro: "#8b93a1" };
  const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const soles = (n) => "S/ " + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
  const ddmm = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;

  let gMatriz = null, gPred = null;
  let datosMatriz = null, datosPred = null;

  async function pedir(url) {
    const r = await fetch(url, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  }

  function colores() {
    const c = { texto: css("--muted"), rejilla: css("--border"), linea: css("--primary-text") || "#ef4444" };
    Chart.defaults.font.family = '"Karla", system-ui, sans-serif';
    Chart.defaults.color = c.texto;
    return c;
  }

  const base = () => ({ responsive: true, maintainAspectRatio: false,
                        animation: window.SM && SM.reducido ? false : { duration: 600 } });

  function ejes(c, tx, ty) {
    return {
      x: { beginAtZero: true, title: { display: !!tx, text: tx, color: c.texto }, ticks: { color: c.texto }, grid: { color: c.rejilla }, border: { color: c.rejilla } },
      y: { beginAtZero: true, title: { display: !!ty, text: ty, color: c.texto }, ticks: { color: c.texto }, grid: { color: c.rejilla }, border: { display: false } },
    };
  }

  function llenarSelect(select, valores, primera) {
    if (select.options.length > 1) return;                 // ya se llenó
    select.replaceChildren(new Option(primera, ""), ...valores.map((v) => new Option(v, v)));
  }

  function listar(id, platos, textoVacio) {
    const ul = $(id);
    ul.replaceChildren(...(platos.length ? platos : [null]).map((p) => {
      const li = document.createElement("li");
      li.textContent = p ? `${p.plato}: ${p.unidades} uds, margen ${soles(p.margen)}` : textoVacio;
      return li;
    }));
  }

  // ------------------------------------------------------------ matriz de ingenieria de menu
  function pintarMatriz(d) {
    if (gMatriz) { gMatriz.destroy(); gMatriz = null; }
    $("m-estado").textContent = d.platos.length ? "" : "No hay ventas para ese filtro.";
    listar("l-promocionar", d.platos.filter((p) => p.clasificacion === "Puzzle").sort((a, b) => b.margen - a.margen),
           "Ningún plato en este grupo.");
    listar("l-retirar", d.platos.filter((p) => p.clasificacion === "Perro").sort((a, b) => a.unidades - b.unidades),
           "Ningún plato en este grupo.");
    if (!d.platos.length) return;

    const c = colores();
    const maxX = Math.max(...d.platos.map((p) => p.unidades), d.mediana_unidades) * 1.08;
    const maxY = Math.max(...d.platos.map((p) => p.margen), d.mediana_margen) * 1.1;
    const puntos = ["Estrella", "Vaca", "Puzzle", "Perro"].map((clase) => ({
      label: clase, backgroundColor: COLORES[clase], borderColor: COLORES[clase], pointRadius: 7, pointHoverRadius: 11,
      data: d.platos.filter((p) => p.clasificacion === clase).map((p) => ({ x: p.unidades, y: p.margen, p })),
    }));
    const medianas = [
      { label: "Mediana de popularidad", data: [{ x: d.mediana_unidades, y: 0 }, { x: d.mediana_unidades, y: maxY }] },
      { label: "Mediana de margen", data: [{ x: 0, y: d.mediana_margen }, { x: maxX, y: d.mediana_margen }] },
    ].map((m) => ({ ...m, showLine: true, pointRadius: 0, pointHoverRadius: 0, borderColor: c.texto, borderDash: [6, 4], borderWidth: 1.5 }));

    const ctx = $("c-matriz").getContext("2d");
    gMatriz = new Chart(ctx, { type: "scatter", data: { datasets: [...puntos, ...medianas] },
      options: { ...base(), scales: { ...ejes(c, "Unidades vendidas", "Margen de ganancia (S/)"),
          x: { ...ejes(c).x, max: maxX, title: { display: true, text: "Unidades vendidas", color: c.texto } },
          y: { ...ejes(c).y, max: maxY, title: { display: true, text: "Margen de ganancia (S/)", color: c.texto } } },
        plugins: { legend: { labels: { color: c.texto, usePointStyle: true } },
          tooltip: { callbacks: {
            title: (items) => (items[0].raw.p ? items[0].raw.p.plato : items[0].dataset.label),
            label: (x) => { const p = x.raw.p; return p ? [`${p.clasificacion}`, `${p.unidades} unidades`, `Margen ${soles(p.margen)}`, `Ingresos ${soles(p.ingresos)}`] : ""; },
          } } } } });
  }

  async function cargarMatriz() {
    const q = new URLSearchParams();
    if ($("f-dias").value) q.set("dias", $("f-dias").value);
    if ($("f-categoria").value) q.set("categoria", $("f-categoria").value);
    try {
      datosMatriz = await pedir(`/admin/api/analisis/matriz?${q}`);
      llenarSelect($("f-categoria"), datosMatriz.categorias, "Todas");
      pintarMatriz(datosMatriz);
    } catch (e) { $("m-estado").textContent = "No se pudieron cargar los datos de la matriz."; }
  }

  // ------------------------------------------------------------ prediccion de demanda
  function pintarPrediccion(d) {
    if (gPred) { gPred.destroy(); gPred = null; }
    $("p-estado").textContent = d.plato ? "" : "Todavía no hay ventas suficientes para predecir.";
    $("t-pred").replaceChildren();
    $("t-total").textContent = "";
    if (!d.plato) return;

    const c = colores();
    const n = d.historial.length;
    const fechas = [...d.historial.map((h) => h.fecha), ...d.prediccion.map((p) => p.fecha)];
    const real = [...d.historial.map((h) => h.unidades), ...d.prediccion.map(() => null)];
    // la proyeccion arranca en el ultimo dia real para que la linea quede unida
    const proy = fechas.map((_, i) => (i === n - 1 ? d.historial[n - 1].unidades : i >= n ? d.prediccion[i - n].unidades : null));

    gPred = new Chart($("c-pred").getContext("2d"), { type: "line",
      data: { labels: fechas.map(ddmm), datasets: [
        { label: "Ventas reales", data: real, borderColor: c.linea, backgroundColor: c.linea, borderWidth: 3, tension: .25, pointRadius: 3 },
        { label: "Proyección (7 días)", data: proy, borderColor: c.linea, backgroundColor: c.linea, borderWidth: 3, borderDash: [8, 5], tension: .25, pointRadius: 3 },
      ] },
      options: { ...base(), interaction: { mode: "index", intersect: false },
        scales: { ...ejes(c, "", "Unidades vendidas"), x: { ...ejes(c).x, beginAtZero: false, ticks: { color: c.texto, maxRotation: 0, autoSkipPadding: 14 }, grid: { display: false } } },
        plugins: { legend: { labels: { color: c.texto, usePointStyle: true } },
          tooltip: { callbacks: { label: (x) => (x.parsed.y == null ? "" : `${x.dataset.label}: ${x.parsed.y} uds`) } } } } });

    const filas = d.prediccion.map((p) => {
      const tr = document.createElement("tr");
      const dia = DIAS[new Date(p.fecha + "T00:00:00").getDay()];
      [[`${dia} ${ddmm(p.fecha)}`, "Día"], [`${p.unidades} unidades`, "Previsto"]].forEach(([txt, etiqueta]) => {
        const td = document.createElement("td"); td.textContent = txt; td.dataset.label = etiqueta; tr.appendChild(td);
      });
      return tr;
    });
    $("t-pred").replaceChildren(...filas);
    $("t-total").textContent = `Total previsto para ${d.plato} en 7 días: ${d.prediccion.reduce((s, p) => s + p.unidades, 0)} unidades.`;
  }

  async function cargarPrediccion() {
    const q = new URLSearchParams();
    if ($("f-plato").value) q.set("plato", $("f-plato").value);
    try {
      datosPred = await pedir(`/admin/api/analisis/prediccion?${q}`);
      llenarSelect($("f-plato"), datosPred.platos, "Plato más vendido");
      pintarPrediccion(datosPred);
    } catch (e) { $("p-estado").textContent = "No se pudieron cargar los datos de la predicción."; }
  }

  $("f-dias").addEventListener("change", cargarMatriz);
  $("f-categoria").addEventListener("change", cargarMatriz);
  $("f-plato").addEventListener("change", cargarPrediccion);
  if (window.SM && SM.alCambiarTema) {                    // al cambiar claro/oscuro se vuelven a pintar
    SM.alCambiarTema(() => { if (datosMatriz) pintarMatriz(datosMatriz); if (datosPred) pintarPrediccion(datosPred); });
  }
  cargarMatriz();
  cargarPrediccion();
})();
