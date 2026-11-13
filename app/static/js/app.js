// Utilidades compartidas por todas las paginas: tema, notificaciones, iconos y animaciones.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const raiz = document.documentElement;
  const reducido = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const SM = {
    reducido,
    dinero: (n) => "S/ " + Number(n).toFixed(2),

    // Crea un icono SVG del sprite:  SM.icono("check", "mi-clase")
    icono(nombre, clase = "") {
      const svg = document.createElementNS(NS, "svg");
      svg.setAttribute("class", ("ico " + clase).trim());
      svg.setAttribute("aria-hidden", "true");
      const uso = document.createElementNS(NS, "use");
      uso.setAttribute("href", "#i-" + nombre);
      svg.append(uso);
      return svg;
    },

    // Elemento rapido:  SM.el("div", {class: "x"}, hijo1, "texto")
    el(tag, attrs = {}, ...hijos) {
      const e = document.createElement(tag);
      for (const [k, v] of Object.entries(attrs)) {
        if (k === "class") e.className = v; else e.setAttribute(k, v);
      }
      e.append(...hijos.filter((h) => h !== null && h !== undefined));
      return e;
    },

    // Notificacion flotante (se lee en voz alta gracias a aria-live)
    toast(mensaje, tipo = "info", ms = 3800) {
      const icono = { ok: "check", error: "alert", info: "bell" }[tipo] || "bell";
      const t = SM.el("div", { class: `toast toast-${tipo}` }, SM.icono(icono), SM.el("span", {}, mensaje));
      document.getElementById("toasts").append(t);
      setTimeout(() => {
        t.classList.add("sale");
        setTimeout(() => t.remove(), reducido ? 0 : 250);
      }, ms);
    },

    // Anima un numero desde su valor actual hasta `hasta`
    contar(el, hasta, formato = (n) => String(Math.round(n)), duracion = 700) {
      const desde = Number(el._valor ?? 0);
      el._valor = hasta;
      if (reducido || desde === hasta) { el.textContent = formato(hasta); return; }
      const t0 = performance.now();
      cancelAnimationFrame(el._raf);
      const paso = (t) => {
        const p = Math.min(1, (t - t0) / duracion);
        const suave = 1 - Math.pow(1 - p, 3);                       // easeOutCubic
        el.textContent = formato(desde + (hasta - desde) * suave);
        if (p < 1) el._raf = requestAnimationFrame(paso);
      };
      el._raf = requestAnimationFrame(paso);
    },

    temaOscuro: () =>
      raiz.dataset.theme ? raiz.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches,

    // Ejecuta `fn` cuando cambia el tema (para el dashboard)
    alCambiarTema(fn) { addEventListener("sm-tema", fn); },
  };
  window.SM = SM;

  // ------------------------------------------------------------ sonido de alertas (Web Audio, sin archivos)
  let audio = null;
  const guardado = () => { try { return localStorage.getItem("sm-sonido") !== "off"; } catch (_) { return true; } };
  SM.sonidoActivo = guardado();

  // Los navegadores solo permiten sonar tras un gesto del usuario: el primer clic lo habilita
  addEventListener("pointerdown", () => {
    if (!audio) { try { audio = new (window.AudioContext || window.webkitAudioContext)(); } catch (_) {} }
    if (audio?.state === "suspended") audio.resume();
  }, { once: false });

  // tipo "nuevo": dos notas (pedido nuevo en cocina) · "listo": tres notas ascendentes (aviso al mozo)
  SM.beep = (tipo = "nuevo") => {
    if (!SM.sonidoActivo || !audio || audio.state !== "running") return;
    const notas = tipo === "listo" ? [660, 880, 1175] : [523, 784];
    notas.forEach((f, i) => {
      const o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime + i * 0.16;
      o.type = "sine"; o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.28);
      o.connect(g).connect(audio.destination); o.start(t); o.stop(t + 0.3);
    });
  };

  // Boton "Sonido activado/desactivado" (si la pagina lo tiene)
  const btnSonido = document.getElementById("btn-sonido");
  if (btnSonido) {
    const pintar = () => {
      btnSonido.setAttribute("aria-pressed", String(SM.sonidoActivo));
      btnSonido.querySelector("span").textContent = SM.sonidoActivo ? "Sonido activado" : "Sonido silenciado";
      btnSonido.querySelector("use").setAttribute("href", SM.sonidoActivo ? "#i-volume" : "#i-volume-off");
    };
    btnSonido.addEventListener("click", () => {
      SM.sonidoActivo = !SM.sonidoActivo;
      try { localStorage.setItem("sm-sonido", SM.sonidoActivo ? "on" : "off"); } catch (_) {}
      pintar();
      if (SM.sonidoActivo) setTimeout(() => SM.beep("nuevo"), 50);
    });
    pintar();
  }

  // Boton de tema claro / oscuro
  document.getElementById("btn-tema")?.addEventListener("click", () => {
    const nuevo = SM.temaOscuro() ? "light" : "dark";
    raiz.dataset.theme = nuevo;
    try { localStorage.setItem("sm-tema", nuevo); } catch (_) {}
    dispatchEvent(new Event("sm-tema"));
  });

  // Revela con animacion los elementos con data-revelar al entrar en pantalla
  if (!reducido && "IntersectionObserver" in window) {
    const obs = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("visto"); obs.unobserve(e.target); } });
    }, { threshold: 0.12 });
    document.querySelectorAll("[data-revelar]").forEach((el) => obs.observe(el));
  } else {
    document.querySelectorAll("[data-revelar]").forEach((el) => el.classList.add("visto"));
  }
})();
