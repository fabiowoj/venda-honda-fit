// Honda New Fit 2009 — animações de scroll, comparação com a FIPE e galeria.
// Sem dependências. Todo o conteúdo já está no HTML; este arquivo só anima e atualiza.
(() => {
  "use strict";
  document.documentElement.classList.add("js");

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const calmo = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const brl = (n) => "R$ " + Math.round(n).toLocaleString("pt-BR");
  const limitar = (v, a, b) => Math.min(b, Math.max(a, v));

  document.addEventListener("DOMContentLoaded", () => {
    const secPreco = $("#preco");
    const preco = Number(secPreco.dataset.preco);
    let fipe = Number(secPreco.dataset.fipeValor);
    let barrasLigadas = false;

    // ---------- Preço x FIPE ----------
    function mostrarFipe(valor, mes, aoVivo) {
      fipe = valor;
      const dif = fipe - preco;
      $$("[data-preco-fmt]").forEach((el) => (el.textContent = brl(preco) + ",00"));
      $("[data-fipe-fmt]").textContent = brl(fipe) + ",00";
      $("[data-fipe-mes-txt]").textContent = mes;
      $("[data-fipe-origem]").textContent = aoVivo ? "Valor consultado agora na tabela FIPE" : "Valor de referência da tabela FIPE";
      $("[data-fipe-titulo]").textContent = dif > 0 ? "Abaixo da tabela FIPE" : "Preço de tabela FIPE";
      $("[data-dif-rot]").textContent = dif >= 0 ? "Economia em relação à FIPE" : "Diferença para a FIPE";
      $("[data-dif-fmt]").textContent = brl(Math.abs(dif));
      $("[data-dif-pct]").textContent =
        (Math.abs(dif) / fipe * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "% " +
        (dif >= 0 ? "abaixo" : "acima") + " do valor da tabela";
      desenharBarras();
    }
    function desenharBarras() {
      if (!barrasLigadas) return;
      const max = Math.max(fipe, preco);
      $('[data-barra="fipe"] i').style.width = (fipe / max) * 100 + "%";
      $('[data-barra="preco"] i').style.width = (preco / max) * 100 + "%";
    }

    async function buscarFipe() {
      const codigo = secPreco.dataset.fipeCodigo;
      const ano = Number(secPreco.dataset.fipeAno);
      const chave = "fipe:" + codigo;
      try {
        const salvo = JSON.parse(localStorage.getItem(chave) || "null");
        if (salvo && Date.now() - salvo.em < 12 * 3600e3) return mostrarFipe(salvo.valor, salvo.mes, true);
      } catch {}
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 8000);
      try {
        const r = await fetch("https://brasilapi.com.br/api/fipe/preco/v1/" + encodeURIComponent(codigo), {
          signal: ctrl.signal, referrerPolicy: "no-referrer", credentials: "omit",
        });
        if (!r.ok) return;
        const lista = await r.json();
        const linha = Array.isArray(lista) ? lista.find((x) => x && Number(x.anoModelo) === ano) : null;
        if (!linha) return;
        const valor = Number(String(linha.valor).replace(/[^\d,]/g, "").replace(",", "."));
        // Só aceita um valor plausível; qualquer resposta estranha mantém o valor de referência.
        if (!(valor > 5000 && valor < 300000)) return;
        const mes = String(linha.mesReferencia || "").trim().slice(0, 40) || secPreco.dataset.fipeMes;
        mostrarFipe(Math.round(valor), mes, true);
        try { localStorage.setItem(chave, JSON.stringify({ valor: Math.round(valor), mes, em: Date.now() })); } catch {}
      } catch {
        /* sem internet ou API fora do ar: fica o valor de referência */
      } finally {
        clearTimeout(t);
      }
    }
    mostrarFipe(fipe, secPreco.dataset.fipeMes, false);
    buscarFipe();

    // ---------- Contadores ----------
    function contar() {
      const els = $$("[data-conta]");
      const fim = els.map((el) => Number(el.dataset.conta));
      const ini = els.map((el) => Number(el.dataset.contaDe || 0));
      const t0 = performance.now();
      const passo = (agora) => {
        const k = limitar((agora - t0) / 1800, 0, 1);
        const e = 1 - Math.pow(1 - k, 3);
        els.forEach((el, i) => {
          const v = Math.round(ini[i] + (fim[i] - ini[i]) * e);
          el.textContent = el.hasAttribute("data-milhar") ? v.toLocaleString("pt-BR") : String(v);
        });
        if (k < 1) requestAnimationFrame(passo);
      };
      requestAnimationFrame(passo);
    }

    // ---------- Entradas ao aparecer na tela ----------
    const observador = new IntersectionObserver((entradas) => {
      for (const e of entradas) {
        if (!e.isIntersecting) continue;
        const el = e.target;
        if (el.hasAttribute("data-revelar")) el.classList.add("visivel");
        if (el.matches('[data-barra="fipe"]')) { barrasLigadas = true; desenharBarras(); }
        if (el.hasAttribute("data-contador") && !calmo) contar();
        observador.unobserve(el);
      }
    }, { threshold: 0.15 });
    $$("[data-revelar]").forEach((el) => observador.observe(el));
    observador.observe($('[data-barra="fipe"]'));
    if (!calmo) {
      $$("[data-conta]").forEach((el) => (el.textContent = el.dataset.contaDe || "0"));
      observador.observe($("[data-contador]"));
    }

    // ---------- Vídeo da abertura acompanhando o scroll ----------
    const abertura = $(".abertura");
    const video = $(".abertura-video");
    const titulo = $(".abertura-titulo");
    const info = $(".abertura-info");
    const barra = $(".abertura-barra i");
    const flutuante = $(".flutuante");
    let duracao = 0, atual = 0, alvo = 0;

    if (video && !calmo) {
      const pronto = () => {
        duracao = video.duration || 0;
        // iOS só libera o avanço quadro a quadro depois de um play().
        const p = video.play();
        if (p) p.then(() => video.pause()).catch(() => {});
        pedirQuadro();
      };
      video.addEventListener("loadedmetadata", pronto);
      if (video.readyState >= 1) pronto();
    }

    // ---------- Laço de animação (só roda quando algo mudou) ----------
    const paralaxes = calmo ? [] : $$("[data-paralaxe]");
    let pedido = 0;
    const pedirQuadro = () => { if (!pedido) pedido = requestAnimationFrame(quadro); };

    // ---------- Galeria horizontal ----------
    const galeria = $(".galeria");
    const trilho = $(".galeria-trilho");
    $$(".galeria-item img").forEach((img) => {
      const w = img.getAttribute("width"), h = img.getAttribute("height");
      if (w && h) img.closest(".galeria-item").style.setProperty("--ar", w + "/" + h);
    });
    // Prende a galeria e move as fotos com o scroll só em telas largas o bastante e sem "reduzir movimento".
    const modoFixo = matchMedia("(min-width: 700px) and (min-height: 500px)");
    function ajustarGaleria() {
      const fixo = !calmo && modoFixo.matches;
      galeria.classList.toggle("fixa", fixo);
      $("[data-galeria-dica]").textContent = fixo ? "Role para ver · clique para ampliar" : "Arraste para o lado · toque para ampliar";
      if (fixo) {
        const sobra = Math.max(0, trilho.scrollWidth - innerWidth);
        galeria.style.height = `calc(100vh + ${sobra}px)`;
      } else {
        galeria.style.height = "";
        trilho.style.transform = "";
      }
      pedirQuadro();
    }
    modoFixo.addEventListener("change", ajustarGaleria);
    addEventListener("resize", ajustarGaleria);
    addEventListener("load", ajustarGaleria);
    ajustarGaleria();

    function quadro() {
      pedido = 0;
      const vh = innerHeight;
      const ra = abertura.getBoundingClientRect();
      if (!calmo) {
        const p = limitar(-ra.top / (abertura.offsetHeight - vh), 0, 1);
        alvo = p * duracao;
        barra.style.width = p * 100 + "%";
        titulo.style.transform = `translateY(${-p * 30}vh) scale(${1 - p * 0.25})`;
        titulo.style.opacity = String(Math.max(0, 1 - p * 2.2));
        info.style.opacity = String(p > 0.85 ? Math.max(0, 1 - (p - 0.85) * 6) : 1);
      }
      const mostrar = ra.bottom < vh * 0.9;
      flutuante.classList.toggle("visivel", mostrar);

      let continuar = false;
      if (duracao && ra.bottom > 0) {
        atual += (alvo - atual) * 0.12;
        if (Math.abs(alvo - atual) < 0.005) atual = alvo; else continuar = true;
        if (Math.abs(video.currentTime - atual) > 0.02 && !video.seeking) video.currentTime = atual;
        if (video.seeking) continuar = true;
      }

      for (const el of paralaxes) {
        const r = el.parentElement.getBoundingClientRect();
        if (r.bottom < -200 || r.top > vh + 200) continue;
        el.style.transform = `translate3d(0,${(r.top + r.height / 2 - vh / 2) * Number(el.dataset.paralaxe)}px,0)`;
      }

      if (galeria.classList.contains("fixa")) {
        const rg = galeria.getBoundingClientRect();
        const p = limitar(-rg.top / (galeria.offsetHeight - vh), 0, 1);
        const sobra = Math.max(0, trilho.scrollWidth - innerWidth);
        trilho.style.transform = `translate3d(${-p * sobra}px,0,0)`;
      }
      if (continuar) pedirQuadro();
    }
    addEventListener("scroll", pedirQuadro, { passive: true });
    pedirQuadro();

    // ---------- Foto ampliada ----------
    const dialogo = $(".ampliar");
    const botoes = $$(".galeria-abrir");
    let indice = 0;
    function abrir(i) {
      indice = (i + botoes.length) % botoes.length;
      const b = botoes[indice];
      const img = $("img", dialogo);
      img.src = b.dataset.foto;
      img.alt = $("img", b).alt;
      $("p", dialogo).textContent = `${b.closest("figure").querySelector("figcaption").textContent} · ${indice + 1}/${botoes.length}`;
      if (!dialogo.open) dialogo.showModal();
    }
    botoes.forEach((b, i) => b.addEventListener("click", () => abrir(i)));
    $(".fechar", dialogo).addEventListener("click", () => dialogo.close());
    $(".ant", dialogo).addEventListener("click", () => abrir(indice - 1));
    $(".prox", dialogo).addEventListener("click", () => abrir(indice + 1));
    dialogo.addEventListener("click", (e) => { if (e.target === dialogo) dialogo.close(); });
    dialogo.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") abrir(indice - 1);
      if (e.key === "ArrowRight") abrir(indice + 1);
    });
    let toqueX = null;
    dialogo.addEventListener("touchstart", (e) => (toqueX = e.touches[0].clientX), { passive: true });
    dialogo.addEventListener("touchend", (e) => {
      if (toqueX === null) return;
      const dx = e.changedTouches[0].clientX - toqueX;
      if (Math.abs(dx) > 50) abrir(indice + (dx < 0 ? 1 : -1));
      toqueX = null;
    });
  });
})();
