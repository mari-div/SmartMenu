// Gráficos interactivos: consumen el JSON calculado con pandas/numpy.
(() => {
  const cMatriz = document.getElementById("c-matriz");
  const cPred = document.getElementById("c-pred");
  if (!cMatriz || !cPred) return;

  const COLOR = { Estrella: "#16a34a", Vaca: "#2563eb", Puzzle: "#f59e0b", Perro: "#dc2626" };
  let gMatriz, gPred;

  async function pedir(url) {
    const r = await fetch(url);
    return r.json();
  }

  function temaSelects() {
  const oscuro = SM.temaOscuro();
  document.querySelectorAll(".interactivos select").forEach((s) => {
    s.classList.toggle("sel-oscuro", oscuro);
    s.classList.toggle("sel-claro", !oscuro);
  });
}
temaSelects();
SM.alCambiarTema(temaSelects);

  async function dibujarMatriz() {
    const cat = document.getElementById("f-cat").value;
    const d = await pedir("/admin/api/analisis/matriz" + (cat ? `?categoria=${encodeURIComponent(cat)}` : ""));

    // Llenar el selector solo la primera vez
    const sel = document.getElementById("f-cat");
    if (sel.options.length === 1) d.categorias.forEach((c) => sel.add(new Option(c, c)));

    const grupos = Object.keys(COLOR).map((k) => ({
      label: k,
      backgroundColor: COLOR[k],
      data: d.platos.filter((p) => p.clasificacion === k)
        .map((p) => ({ x: p.unidades, y: p.margen, nombre: p.plato })),
    }));

    gMatriz?.destroy();
    gMatriz = new Chart(cMatriz, {
      type: "scatter",
      data: { datasets: grupos },
      options: {
        plugins: { tooltip: { callbacks: { label: (c) => `${c.raw.nombre}: ${c.raw.x} uds, margen ${c.raw.y}` } } },
        scales: { x: { title: { display: true, text: "Unidades vendidas" } },
                  y: { title: { display: true, text: "Margen" } } },
      },
    });
  }

  async function dibujarPred() {
    const sel = document.getElementById("f-plato");
    const d = await pedir("/admin/api/analisis/prediccion" + (sel.value ? `?plato=${encodeURIComponent(sel.value)}` : ""));
    if (!d.plato) return;

    if (!sel.options.length) d.platos.forEach((p) => sel.add(new Option(p, p)));
    sel.value = d.plato;

    const fecha = (r) => r.fecha ?? r.dia ?? r[0];
    const valor = (r) => r.unidades ?? r.cantidad ?? r.valor ?? r[1];
    const etiquetas = [...d.historial.map(fecha), ...d.prediccion.map(fecha)];

    gPred?.destroy();
    gPred = new Chart(cPred, {
      type: "line",
      data: {
        labels: etiquetas,
        datasets: [
          { label: "Historial", data: d.historial.map(valor), borderColor: "#2563eb" },
          { label: "Predicción 7 días",
            data: [...Array(d.historial.length).fill(null), ...d.prediccion.map(valor)],
            borderColor: "#f59e0b", borderDash: [6, 4] },
        ],
      },
    });
  }

  document.getElementById("f-cat").addEventListener("change", dibujarMatriz);
  document.getElementById("f-plato").addEventListener("change", dibujarPred);
  dibujarMatriz();
  dibujarPred();
})();