/* ZapClin marketing site — sem SW, sem API, sem vínculo com o app operacional */
(function () {
  "use strict";

  const nav = document.querySelector(".nav");
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");

  const onScroll = () => {
    if (!nav) return;
    nav.classList.toggle("scrolled", window.scrollY > 12);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", () => {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Reveal on scroll
  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -8% 0px" }
    );
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("in"));
  }

  // Education tabs
  const tabs = Array.from(document.querySelectorAll(".edu-tab"));
  const panel = document.querySelector(".edu-panel");
  const panelTitle = document.querySelector("[data-edu-title]");
  const panelTag = document.querySelector("[data-edu-tag]");
  const panelLead = document.querySelector("[data-edu-lead]");
  const panelList = document.querySelector("[data-edu-list]");
  const panelNote = document.querySelector("[data-edu-note]");

  const copy = {
    higienizar: {
      tone: "green",
      tag: "Elimina germes e odores",
      title: "Higienizar",
      lead: "Ação bactericida e desodorizante. Ideal quando o capacete está aparentemente limpo, mas com cheiro ou uso frequente.",
      items: [
        "Ozônio, UV e sanitizantes específicos",
        "Remove até 99,9% dos micro-organismos",
        "Não substitui limpeza de sujeira visível",
        "Perfeito para manutenção periódica"
      ],
      note: "Escolha quando o problema é odor/bactérias — não manchas profundas."
    },
    limpar: {
      tone: "gold",
      tag: "Remove sujeira leve",
      title: "Limpar",
      lead: "Cuida da superfície: poeira, suor e oleosidade leve, com acabamento de brilho e proteção.",
      items: [
        "Microfibra + bactericidas e finalizadores",
        "Deixa o casco com aspecto cuidado",
        "Ajuda a preservar materiais por mais tempo",
        "Não remove manchas profundas de tecido"
      ],
      note: "Escolha quando há sujeira leve, sem odor forte nem forro muito impregnado."
    },
    lavar: {
      tone: "blue",
      tag: "Remove sujeira profunda",
      title: "Lavar",
      lead: "Limpeza profunda de tecidos e forros: manchas, suor acumulado e sujeira pesada.",
      items: [
        "Produtos têxteis + escovação controlada",
        "Enxágue e secagem profissional",
        "Devolve aparência renovada ao interior",
        "Combinar com higienização = proteção completa"
      ],
      note: "Escolha quando o capacete está muito sujo, manchado ou há tempos sem cuidado."
    }
  };

  function renderEdu(key) {
    const data = copy[key];
    if (!data || !panel) return;
    tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.edu === key));
    panel.dataset.tone = data.tone;
    if (panelTag) panelTag.textContent = data.tag;
    if (panelTitle) panelTitle.textContent = data.title;
    if (panelLead) panelLead.textContent = data.lead;
    if (panelList) {
      panelList.innerHTML = data.items.map((item) => `<li>${item}</li>`).join("");
    }
    if (panelNote) panelNote.textContent = data.note;
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => renderEdu(tab.dataset.edu));
  });
  if (tabs.length) renderEdu(tabs[0].dataset.edu || "higienizar");

  // Preferência de serviço → WhatsApp
  document.querySelectorAll("[data-wa-service]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const service = btn.getAttribute("data-wa-service");
      const msg = encodeURIComponent(
        `Olá, ZapClin! Quero agendar: ${service}. Estou no Golden Shopping Calhau.`
      );
      btn.setAttribute("href", `https://wa.me/5598981479616?text=${msg}`);
    });
  });
})();
