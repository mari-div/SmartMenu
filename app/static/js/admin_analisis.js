// Admin > Analisis avanzado: graficos de matplotlib que siguen el tema claro/oscuro.
(() => {
  const imgs = [...document.querySelectorAll(".grafico img")];
  function cargarGraficos() {
    const tema = SM.temaOscuro() ? "oscuro" : "claro";
    imgs.forEach((img) => {
      const marco = img.closest(".grafico-marco");
      marco.classList.add("cargando");
      img.onload = () => marco.classList.remove("cargando");
      img.onerror = () => { marco.classList.remove("cargando"); img.alt = "No se pudo cargar el gráfico"; };
      img.src = `/admin/grafico/${img.dataset.g}.png?tema=${tema}`;
    });
  }
  cargarGraficos();
  SM.alCambiarTema(cargarGraficos);
})();
