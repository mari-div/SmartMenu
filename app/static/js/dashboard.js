// Dashboard: numeros que cuentan hacia su valor y graficos que siguen el tema claro/oscuro.
(() => {
  const { contar, temaOscuro } = SM;

  const FORMATOS = {
    entero: (n) => Math.round(n).toLocaleString("en-US"),
    dinero: (n) => "$" + n.toFixed(2),
    dinero0: (n) => "$" + Math.round(n).toLocaleString("en-US"),
    min: (n) => n.toFixed(1) + " min",
  };

  // KPIs: cuentan cuando la tarjeta aparece en pantalla
  const observador = "IntersectionObserver" in window && new IntersectionObserver((entradas) => {
    entradas.forEach((e) => {
      if (!e.isIntersecting) return;
      const v = e.target;
      contar(v, Number(v.dataset.valor), FORMATOS[v.dataset.formato] || FORMATOS.entero, 1100);
      observador.unobserve(v);
    });
  }, { threshold: 0.4 });

  document.querySelectorAll(".kpi-valor").forEach((v) => {
    const formato = FORMATOS[v.dataset.formato] || FORMATOS.entero;
    v.textContent = formato(0);
    observador ? observador.observe(v) : (v.textContent = formato(Number(v.dataset.valor)));
  });

  // Graficos: PNG generado por el servidor con el tema actual; se recarga al cambiar de tema
  const imgs = [...document.querySelectorAll(".grafico img")];
  function cargarGraficos() {
    const tema = temaOscuro() ? "oscuro" : "claro";
    imgs.forEach((img) => {
      const marco = img.closest(".grafico-marco");
      marco.classList.add("cargando");
      img.onload = () => marco.classList.remove("cargando");
      img.onerror = () => { marco.classList.remove("cargando"); img.alt = "No se pudo cargar el gráfico"; };
      img.src = `/dashboard/grafico/${img.dataset.g}.png?tema=${tema}`;
    });
  }
  cargarGraficos();
  SM.alCambiarTema(cargarGraficos);
})();
