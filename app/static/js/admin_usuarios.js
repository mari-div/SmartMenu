// Admin > Usuarios: crear, activar/desactivar y cambiar claves.
(() => {
  const { toast } = SM;
  const cabeceras = { "Content-Type": "application/json" };

  document.getElementById("form-usuario").addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = document.getElementById("error-usuario");
    error.hidden = true;
    const r = await fetch("/admin/api/usuarios", { method: "POST", headers: cabeceras, body: JSON.stringify({
      nombre: document.getElementById("n-nombre").value, username: document.getElementById("n-user").value,
      password: document.getElementById("n-pass").value, rol: document.getElementById("n-rol").value }) });
    const d = await r.json();
    if (!r.ok) { error.textContent = d.error; error.hidden = false; return; }
    toast(`Usuario ${d.username} creado`, "ok");
    setTimeout(() => location.reload(), 700);
  });

  document.querySelectorAll(".sw-activo").forEach((sw) => sw.addEventListener("change", async () => {
    const fila = sw.closest("tr");
    const r = await fetch(`/admin/api/usuarios/${fila.dataset.id}`, { method: "PATCH", headers: cabeceras, body: JSON.stringify({ activo: sw.checked }) });
    if (!r.ok) { sw.checked = !sw.checked; toast((await r.json()).error, "error"); return; }
    toast(`${fila.dataset.user}: ${sw.checked ? "activado" : "desactivado"}`, "ok");
  }));

  document.querySelectorAll(".reset-clave").forEach((b) => b.addEventListener("click", async () => {
    const fila = b.closest("tr");
    const nueva = prompt(`Nueva contraseña para ${fila.dataset.user} (mínimo 6 caracteres):`);
    if (!nueva) return;
    const r = await fetch(`/admin/api/usuarios/${fila.dataset.id}`, { method: "PATCH", headers: cabeceras, body: JSON.stringify({ password: nueva }) });
    toast(r.ok ? "Contraseña actualizada" : (await r.json()).error, r.ok ? "ok" : "error");
  }));
})();
