// Admin > Menu e inventario: editar platos y reponer stock sin recargar la pagina.
(() => {
  const { toast } = SM;

  async function enviar(url, metodo, cuerpo) {
    const r = await fetch(url, { method: metodo, headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "No se pudo guardar");
    return d;
  }

  document.querySelectorAll(".guardar-plato").forEach((boton) => boton.addEventListener("click", async () => {
    const fila = boton.closest("tr");
    const campo = (n) => fila.querySelector(`[name="${n}"]`);
    boton.disabled = true;
    try {
      const d = await enviar(`/admin/api/platos/${fila.dataset.id}`, "PATCH", {
        precio: campo("precio").value, costo: campo("costo").value,
        disponible: campo("disponible").checked, imagen_url: campo("imagen_url").value,
      });
      // refresca la miniatura con la foto nueva
      const marco = fila.querySelector(".mini-foto");
      marco.replaceChildren();
      if (d.imagen_url) {
        const img = Object.assign(document.createElement("img"), { src: d.imagen_url, alt: "", loading: "lazy", referrerPolicy: "no-referrer" });
        img.onerror = () => img.remove();
        marco.append(img);
      }
      toast(`“${d.nombre}” guardado`, "ok");
    } catch (e) { toast(e.message, "error"); }
    boton.disabled = false;
  }));

  document.querySelectorAll("#tabla-stock .reponer button").forEach((boton) => boton.addEventListener("click", async () => {
    const fila = boton.closest("tr");
    const cantidad = fila.querySelector(".reponer input").value;
    boton.disabled = true;
    try {
      const d = await enviar(`/admin/api/ingredientes/${fila.dataset.id}/reponer`, "POST", { cantidad });
      const unidad = fila.querySelector(".stock-val").textContent.split(" ").pop();
      fila.querySelector(".stock-val").textContent = `${d.stock.toFixed(1)} ${unidad}`;
      fila.classList.toggle("stock-bajo", d.bajo);
      const estado = fila.querySelector(".estado-stock");
      estado.textContent = d.bajo ? "Stock bajo" : "Normal";
      estado.className = `badge ${d.bajo ? "b-cancelado" : "b-entregado"} estado-stock`;
      toast(`${d.nombre}: stock actualizado`, "ok");
    } catch (e) { toast(e.message, "error"); }
    boton.disabled = false;
  }));
})();
