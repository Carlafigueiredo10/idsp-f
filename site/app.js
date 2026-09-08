/* IDSP-F — site estático. Sem build, sem backend. Dados: data/*.json gerados pelo pipeline. */
(function () {
  "use strict";

  const REPO = "https://github.com/Carlafigueiredo10/idsp-f";
  const CLASSES = {
    deserto_critico:      { nome: "Deserto crítico",      cor: "#9b2226", pat: "critico", desc: "pouca presença e muita gente já podendo sair" },
    presenca_em_risco:    { nome: "Presença em risco",    cor: "#5c4a99", pat: "risco",   desc: "presença alta, mas muita gente já podendo sair" },
    deserto_estavel:      { nome: "Deserto estável",      cor: "#d98b2b", pat: "estavel", desc: "pouca presença, evasão iminente baixa" },
    presenca_consolidada: { nome: "Presença consolidada", cor: "#2f7d5b", pat: "plano",   desc: "presença alta e evasão iminente baixa" },
  };
  const PREP = { BA: "Na", PB: "Na", MG: "Em", SP: "Em", SC: "Em", PE: "Em", AL: "Em", SE: "Em", RR: "Em", RO: "Em", GO: "Em", MT: "Em", MS: "Em" };
  const LENTE_DESC = {
    nucleo: "INSS, Receita Federal, Institutos Federais, universidades e IBGE — os serviços federais que a população encontra no território.",
    total: "Todos os servidores civis ativos do Executivo Federal com cargo efetivo (SIAPE).",
  };
  const LENTE_ROTULO = { nucleo: "do núcleo de serviços", total: "do Executivo Federal" };

  const st = { lente: "nucleo", uf: null, dados: null, grupos: null, meta: null, geo: null };
  const $ = (s) => document.querySelector(s);
  const fmtInt = (v) => (typeof v === "number" ? v.toLocaleString("pt-BR") : v);
  const fmtNum = (v, d = 2) => (v == null ? "—" : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const fmtPct = (v) => (v == null ? "—" : fmtNum(v * 100, 1) + "%");
  const mesBR = (s) => { if (!s) return "—"; const [a, m] = s.split("-"); const n = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]; return `${n[+m - 1] || m}/${a}`; };

  // ---------------------------------------------------------------- padrões (acessibilidade: nunca só cor)
  function defs(svg) {
    const d = svg.append("defs");
    const mk = (id, cor, draw) => {
      const p = d.append("pattern").attr("id", "pat-" + id).attr("width", 8).attr("height", 8).attr("patternUnits", "userSpaceOnUse");
      p.append("rect").attr("width", 8).attr("height", 8).attr("fill", cor);
      draw(p);
    };
    mk("critico", CLASSES.deserto_critico.cor, (p) => {
      p.append("path").attr("d", "M0,8 L8,0 M-2,2 L2,-2 M6,10 L10,6").attr("stroke", "rgba(255,255,255,.55)").attr("stroke-width", 1.4);
      p.append("path").attr("d", "M0,0 L8,8 M-2,6 L2,10 M6,-2 L10,2").attr("stroke", "rgba(255,255,255,.55)").attr("stroke-width", 1.4);
    });
    mk("estavel", CLASSES.deserto_estavel.cor, (p) => {
      p.append("path").attr("d", "M0,8 L8,0 M-2,2 L2,-2 M6,10 L10,6").attr("stroke", "rgba(255,255,255,.6)").attr("stroke-width", 1.4);
    });
    mk("risco", CLASSES.presenca_em_risco.cor, (p) => {
      p.append("circle").attr("cx", 2).attr("cy", 2).attr("r", 1.3).attr("fill", "rgba(255,255,255,.7)");
      p.append("circle").attr("cx", 6).attr("cy", 6).attr("r", 1.3).attr("fill", "rgba(255,255,255,.7)");
    });
    mk("plano", CLASSES.presenca_consolidada.cor, () => {});
    mk("nd", "#c9c2b8", () => {});
  }
  const fillDe = (q) => `url(#pat-${(CLASSES[q] || { pat: "nd" }).pat})`;
  function swatch(q, w = 26, h = 18) {
    const svg = d3.create("svg").attr("viewBox", `0 0 ${w} ${h}`).attr("aria-hidden", "true");
    defs(svg);
    svg.append("rect").attr("width", w).attr("height", h).attr("fill", fillDe(q));
    return svg.node();
  }

  // ---------------------------------------------------------------- dados
  const linhas = () => st.dados[st.lente];
  const porUF = (uf) => linhas().find((r) => r.uf === uf);

  async function carregar() {
    const [dados, grupos, meta, geo] = await Promise.all(
      ["data/idspf_uf.json", "data/idspf_uf_grupo.json", "data/metadata.json", "data/uf.geojson"].map((u) =>
        fetch(u).then((r) => { if (!r.ok) throw new Error(u + ": " + r.status); return r.json(); })
      )
    );
    Object.assign(st, { dados, grupos, meta, geo });
  }

  // ---------------------------------------------------------------- hash
  function lerHash() {
    const h = new URLSearchParams(location.hash.replace(/^#/, ""));
    const lente = h.get("lente");
    // sem lente no link, volta ao padrão: um link compartilhado precisa mostrar
    // sempre a mesma coisa, e não herdar a lente que o visitante usou antes
    st.lente = lente && st.dados[lente] ? lente : "nucleo";
    const uf = (h.get("uf") || "").toUpperCase();
    if (uf && porUF(uf)) st.uf = uf;
  }
  function gravarHash(scroll) {
    const p = new URLSearchParams();
    if (st.uf) p.set("uf", st.uf);
    if (st.lente !== "nucleo") p.set("lente", st.lente);
    const novo = "#" + p.toString();
    if (location.hash !== novo) history.replaceState(null, "", novo || location.pathname);
    if (scroll) $("#painel").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function selecionar(uf, scroll) {
    st.uf = uf;
    gravarHash(scroll);
    atualizarSelecao();
    renderPainel();
  }

  // ---------------------------------------------------------------- cabeçalho
  function renderCabecalho() {
    const m = st.meta;
    $("#ref").textContent = `Cadastro SIAPE ${mesBR(m.mes_ref_f1)} · Abono de permanência ${mesBR(m.mes_ref_f2)} · População IBGE ${m.ano_pop} · gerado em ${(m.gerado_em || "").slice(0, 10)}`;
    $("#versao").textContent = "v" + m.versao;
    $("#lnk-repo").href = REPO;
    $("#lnk-metodologia").href = REPO + "/blob/main/METODOLOGIA.md";
    $("#lnk-privacidade").href = REPO + "/blob/main/PRIVACIDADE.md";
    $("#aviso-ficticio").hidden = !m.ficticio;
    $("#citacao").textContent = `IDSP-F — Índice de Deserto de Serviço Público Federal, v${m.versao} (${(m.gerado_em || "").slice(0, 7)}). ${REPO}`;
    document.querySelectorAll(".lente button").forEach((b) => {
      const on = b.dataset.lente === st.lente;
      b.classList.toggle("ativo", on);
      b.setAttribute("aria-pressed", String(on));
    });
    $("#lente-desc").textContent = LENTE_DESC[st.lente];
  }

  // ---------------------------------------------------------------- legenda
  function renderLegenda() {
    const ul = $("#legenda");
    ul.innerHTML = "";
    const cont = d3.rollup(linhas(), (v) => v.length, (r) => r.quadrante);
    for (const [q, c] of Object.entries(CLASSES)) {
      const li = document.createElement("li");
      li.appendChild(swatch(q));
      const t = document.createElement("span");
      t.innerHTML = `<strong>${c.nome}</strong> (${cont.get(q) || 0} UFs)<small>${c.desc}</small>`;
      li.appendChild(t);
      ul.appendChild(li);
    }
  }

  // ---------------------------------------------------------------- mapa
  function renderMapa() {
    const box = $(".mapa-box");
    const w = Math.max(280, box.clientWidth - 16);
    const h = Math.round(w * 0.98);
    const svg = d3.select("#svg-mapa").attr("viewBox", `0 0 ${w} ${h}`).attr("width", w).attr("height", h);
    svg.selectAll("*").remove();
    defs(svg);
    const proj = d3.geoMercator().fitSize([w, h], st.geo);
    const path = d3.geoPath(proj);
    const tip = $("#tooltip");

    const g = svg.append("g");
    g.selectAll("path")
      .data(st.geo.features)
      .join("path")
      .attr("class", "uf")
      .attr("d", path)
      .attr("fill", (f) => fillDe((porUF(f.properties.sigla) || {}).quadrante))
      .attr("tabindex", 0)
      .attr("role", "button")
      .attr("aria-label", (f) => { const r = porUF(f.properties.sigla); return `${f.properties.nome}: ${r ? r.classe : "sem dado"}`; })
      .on("click", (e, f) => selecionar(f.properties.sigla, true))
      .on("keydown", (e, f) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selecionar(f.properties.sigla, true); } })
      .on("mousemove", (e, f) => {
        const r = porUF(f.properties.sigla);
        tip.hidden = false;
        tip.innerHTML = `<strong>${f.properties.nome}</strong><br>${r ? r.classe : "—"}<br>${r ? fmtNum(r.A_raw) + " serv./10 mil · " + fmtPct(r.B_raw) + " elegíveis" : ""}`;
        const rect = box.getBoundingClientRect();
        tip.style.left = Math.min(e.clientX - rect.left + 12, rect.width - 250) + "px";
        tip.style.top = e.clientY - rect.top + 12 + "px";
      })
      .on("mouseleave", () => { tip.hidden = true; });

    if (w >= 420) {
      g.selectAll("text")
        .data(st.geo.features)
        .join("text")
        .attr("class", "sigla")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("transform", (f) => `translate(${path.centroid(f)})`)
        .text((f) => f.properties.sigla);
    }
    atualizarSelecao();
  }

  function atualizarSelecao() {
    d3.selectAll("#svg-mapa path.uf").classed("sel", (f) => f.properties.sigla === st.uf);
    d3.selectAll("#svg-matriz .ponto").classed("sel", (r) => r.uf === st.uf);
    const sel = $("#sel-uf");
    if (sel.value !== (st.uf || "")) sel.value = st.uf || "";
  }

  // ---------------------------------------------------------------- matriz
  function renderMatriz() {
    const box = $(".matriz-box");
    const w = Math.max(280, box.clientWidth - 16);
    const h = Math.round(Math.min(w * 0.85, 520));
    const m = { t: 24, r: 16, b: 44, l: 44 };
    const svg = d3.select("#svg-matriz").attr("viewBox", `0 0 ${w} ${h}`).attr("width", w).attr("height", h);
    svg.selectAll("*").remove();
    const x = d3.scaleLinear().domain([-4, 104]).range([m.l, w - m.r]);
    const y = d3.scaleLinear().domain([-4, 104]).range([h - m.b, m.t]);
    const c = st.meta.parametros.cortes[st.lente];

    svg.append("rect").attr("class", "quad-critico").attr("x", x(-4)).attr("y", y(104)).attr("width", x(c.A_pct_lim) - x(-4)).attr("height", y(c.B_pct_lim) - y(104));
    svg.append("g").attr("class", "eixo").attr("transform", `translate(0,${h - m.b})`).call(d3.axisBottom(x).ticks(5).tickValues([0, 25, 50, 75, 100]));
    svg.append("g").attr("class", "eixo").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues([0, 25, 50, 75, 100]));
    svg.append("line").attr("class", "corte").attr("x1", x(c.A_pct_lim)).attr("x2", x(c.A_pct_lim)).attr("y1", y(-4)).attr("y2", y(104));
    svg.append("line").attr("class", "corte").attr("x1", x(-4)).attr("x2", x(104)).attr("y1", y(c.B_pct_lim)).attr("y2", y(c.B_pct_lim));
    svg.append("text").attr("class", "eixo").attr("x", (x(0) + x(100)) / 2).attr("y", h - 8).attr("text-anchor", "middle").style("font-size", "11px").style("fill", "#6f6962").text("← menos presença · percentil de presença (A) · mais presença →");
    svg.append("text").attr("class", "eixo").attr("transform", `translate(12,${(y(0) + y(100)) / 2}) rotate(-90)`).attr("text-anchor", "middle").style("font-size", "11px").style("fill", "#6f6962").text("percentil de fragilidade (B) →");
    const rot = [["Deserto crítico", 2, 100, "start"], ["Presença em risco", 100, 100, "end"], ["Deserto estável", 2, 0, "start"], ["Presença consolidada", 100, 0, "end"]];
    rot.forEach(([t, px, py, a]) => svg.append("text").attr("class", "rotulo-quad").attr("x", x(px)).attr("y", y(py) + (py ? -6 : 14)).attr("text-anchor", a).text(t));

    const pts = svg.append("g").selectAll("g").data(linhas().filter((r) => r.A_pct != null && r.B_pct != null)).join("g")
      .attr("class", "ponto").attr("transform", (r) => `translate(${x(r.A_pct)},${y(r.B_pct)})`)
      .attr("tabindex", 0).attr("role", "button").attr("aria-label", (r) => `${r.nome}: ${r.classe}`)
      .on("click", (e, r) => selecionar(r.uf, true))
      .on("keydown", (e, r) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selecionar(r.uf, true); } });
    pts.append("circle").attr("r", w < 480 ? 9 : 11).attr("fill", (r) => (CLASSES[r.quadrante] || {}).cor || "#c9c2b8");
    pts.append("text").attr("text-anchor", "middle").attr("dy", "0.35em").text((r) => r.uf);
    atualizarSelecao();
  }

  function renderTabela() {
    const tb = $("#tabela tbody");
    tb.innerHTML = "";
    for (const r of linhas()) {
      const tr = document.createElement("tr");
      tr.dataset.uf = r.uf;
      tr.innerHTML = `<td class="num">${r.posicao}</td><td><strong>${r.uf}</strong> ${r.nome}</td><td>${r.classe}</td><td class="num">${fmtNum(r.A_raw)}</td><td class="num">${fmtPct(r.B_raw)}</td><td class="num">${fmtNum(r.gravidade, 1)}</td>`;
      tr.addEventListener("click", () => selecionar(r.uf, true));
      tb.appendChild(tr);
    }
  }

  // ---------------------------------------------------------------- painel
  function renderSelect() {
    const sel = $("#sel-uf");
    sel.innerHTML = '<option value="">— escolha —</option>' +
      [...linhas()].sort((a, b) => a.nome.localeCompare(b.nome)).map((r) => `<option value="${r.uf}">${r.nome} (${r.uf})</option>`).join("");
    sel.value = st.uf || "";
  }

  function renderPainel() {
    const el = $("#cartao");
    const r = st.uf && porUF(st.uf);
    if (!r) {
      el.innerHTML = `<p class="sub">Escolha um estado acima, toque no mapa ou na matriz. Exemplo: <a href="#uf=AP">Amapá</a>.</p>`;
      return;
    }
    const c = CLASSES[r.quadrante] || { nome: "—", cor: "#c9c2b8" };
    const prep = PREP[r.uf] || "No";
    const cortes = st.meta.parametros.cortes[st.lente];
    const A = fmtNum(r.A_raw, 1);
    const B = r.B_raw == null ? "—" : fmtNum(r.B_raw * 100, 1);
    const sint = r.A_raw == null
      ? `${prep} ${r.nome}, os números desta lente foram suprimidos por serem inferiores ao limite de publicação.`
      : `${prep} ${r.nome}, <strong>${A}</strong> servidores federais ${LENTE_ROTULO[st.lente]} por 10 mil habitantes (percentil ${fmtNum(r.A_pct, 0)}); <strong>${B}%</strong> já podem se aposentar hoje.`;

    const grupos = st.grupos.filter((g) => g.uf === r.uf);
    const maxB = d3.max(st.grupos, (g) => g.B_raw) || 1;
    const barras = st.lente === "nucleo" ? `
      <div class="barras">
        <h4 style="margin:.5rem 0 .2rem;font-size:.95rem">Fragilidade por grupo do núcleo</h4>
        ${grupos.map((g) => `
          <div class="barra">
            <span>${g.nome_grupo}</span>
            <div class="trilho" role="img" aria-label="${g.nome_grupo}: ${g.B_raw == null ? "suprimido ou sem dado" : fmtPct(g.B_raw) + " elegíveis"}"><div class="fill" style="width:${g.B_raw == null ? 0 : Math.round((g.B_raw / maxB) * 100)}%"></div></div>
            <span class="n">${g.B_raw == null ? (g.n_ativos === "0" ? "sem ativos" : "&lt;5 / suprimido") : fmtPct(g.B_raw)} · ${fmtInt(isNaN(+g.n_abono) ? g.n_abono : +g.n_abono)} de ${fmtInt(isNaN(+g.n_ativos) ? g.n_ativos : +g.n_ativos)}</span>
          </div>`).join("")}
      </div>` : "";

    const flags = (r.flags || []).map((f) => ({
      ativos_suprimidos: "ativos suprimidos (n < 5)", abono_suprimido: "abono suprimido (n < 5)",
      sem_abono_registrado: "nenhum abono registrado na UF nesta lente", B_indisponivel: "fragilidade indisponível",
    }[f] || f));

    el.innerHTML = `
      <div class="cab">
        <h3>${r.nome} <span class="regiao">· ${r.uf} · ${r.regiao}</span></h3>
        <span class="badge" style="background:${c.cor}">${swatch(r.quadrante, 16, 16).outerHTML} ${c.nome}</span>
      </div>
      <p class="sintese">${sint}</p>
      <div class="kpis">
        <div class="kpi"><div class="v">${A}</div><div class="l">servidores por 10 mil hab.</div><div class="p">percentil ${fmtNum(r.A_pct, 0)} · corte ${fmtNum(cortes.A_raw_lim, 1)}</div></div>
        <div class="kpi"><div class="v">${B}%</div><div class="l">já elegíveis à aposentadoria</div><div class="p">${fmtInt(isNaN(+r.n_abono) ? r.n_abono : +r.n_abono)} de ${fmtInt(isNaN(+r.n_ativos_base_b) ? r.n_ativos_base_b : +r.n_ativos_base_b)} em órgãos comparáveis · percentil ${fmtNum(r.B_pct, 0)}</div></div>
        <div class="kpi"><div class="v">${r.posicao}º</div><div class="l">de 27 em gravidade</div><div class="p">gravidade ${fmtNum(r.gravidade, 1)} / 100</div></div>
        <div class="kpi"><div class="v">${fmtInt(isNaN(+r.n_ativos) ? r.n_ativos : +r.n_ativos)}</div><div class="l">servidores ativos</div><div class="p">população ${fmtInt(r.populacao)}</div></div>
      </div>
      ${barras}
      ${flags.length ? `<p class="flags">Observações: ${flags.join("; ")}.</p>` : ""}
      <p class="rastro">Lente: ${st.lente === "nucleo" ? "núcleo de serviços" : "Executivo Federal total"} · Cadastro SIAPE ${mesBR(st.meta.mes_ref_f1)} · Abono ${mesBR(st.meta.mes_ref_f2)} · População IBGE ${st.meta.ano_pop} · corte: ${st.meta.parametros.corte} · supressão n &lt; ${st.meta.parametros.supressao_min} · <a href="data/metadata.json">metadata.json</a> · link: <a href="#uf=${r.uf}${st.lente !== "nucleo" ? "&lente=" + st.lente : ""}">#uf=${r.uf}</a></p>`;
  }

  // ---------------------------------------------------------------- metodologia / fontes
  function renderMeta() {
    const m = st.meta;
    const cob = m.cobertura_crosswalk || {};
    const terr = m.fontes?.f1?.territorializacao || {};
    const totTerr = Object.values(terr).reduce((a, b) => a + b, 0) || 1;
    const porMetodo = Object.entries(terr).filter(([k]) => k !== "sem_uf")
      .sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k.replace(/_/g, " ")} ${fmtPct(v / totTerr)}`).join(", ");
    const lim = [
      `<strong>Meses de referência:</strong> cadastro de servidores de ${mesBR(m.mes_ref_f1)} e abono de permanência de ${mesBR(m.mes_ref_f2)}. Os dois meses são deliberadamente iguais: a fragilidade é uma razão entre as duas bases e só faz sentido no mesmo instante. O conjunto de abono no dados.gov.br está desatualizado, o que fixa o mês de todo o índice.`,
      `<strong>Territorialização:</strong> o campo de UF do cadastro traz <code>-1</code> quando não informado. A UF é recuperada por uma cadeia de regras (${porMetodo}); ${fmtPct((terr.sem_uf || 0) / totTerr)} dos vínculos permanecem sem UF, em sua maioria administração central de ministérios, e ficam fora do índice. Nenhum é atribuído ao Distrito Federal por conveniência.`,
      `<strong>Eixo B restrito:</strong> a fragilidade só usa órgãos presentes nas duas bases e bem territorializados no cadastro. Sem isso, o numerador cobre um universo maior que o denominador e aparecem estados com "mais de 100% dos servidores já elegíveis". Por isso o painel mostra o denominador efetivo ao lado do percentual.`,
      `<strong>Fora do universo:</strong> governos de ex-territórios (Amapá, Roraima e Rondônia). São pessoal pago pela União que serve funções estaduais: aparecem no abono e praticamente não aparecem no cadastro de servidores civis.`,
      `<strong>Receita Federal:</strong> não é um órgão próprio no cadastro e suas unidades não se identificam pelo nome. O grupo é o Ministério da Fazenda inteiro, do qual a Receita é a maior parte.`,
      `<strong>Eixo B pela UF de residência</strong>, não pela UPAG, que é unidade pagadora e se concentra em sedes. Divergência entre as duas: ${m.divergencia_upag_residencia == null ? "—" : fmtPct(m.divergencia_upag_residencia)}. Preenchimento da residência no abono: ${fmtPct(m.fontes?.f2?.preenchimento_uf_residencia)}.`,
      `<strong>Casamento de nomes de órgão:</strong> cobertura ${fmtPct(cob.nucleo)} no núcleo e ${fmtPct(cob.total)} no total (${Object.entries(cob.por_metodo || {}).map(([k, v]) => `${v} ${k}`).join(", ")}).`,
      `<strong>Corte da matriz:</strong> ${m.parametros.corte} nacional (A: ${fmtNum(m.parametros.cortes.nucleo.A_raw_lim, 2)} servidores por 10 mil no núcleo; B: ${fmtPct(m.parametros.cortes.nucleo.B_raw_lim)}).`,
      `<strong>Fora do escopo:</strong> ${(m.fora_do_escopo || []).join(", ")}.`,
    ];
    $("#limitacoes").innerHTML = lim.map((l) => `<li>${l}</li>`).join("");

    const f = m.fontes || {};
    const cards = [
      { t: "F1 · Cadastro de Servidores", o: "CGU — Portal da Transparência (fonte SIAPE) · espelho MGI no dados.gov.br",
        u: [["Portal da Transparência — download", "https://portaldatransparencia.gov.br/download-de-dados/servidores"], ["dados.gov.br — Servidores do Executivo Federal", "https://dados.gov.br/dados/conjuntos-dados/servidores-do-executivo-federal"]],
        meta: `mês ${mesBR(m.mes_ref_f1)} · arquivo <code>${f.f1?.arquivo || "—"}</code><br>SHA-256 <code>${(f.f1?.sha256 || "").slice(0, 16)}…</code> · ${fmtInt(f.f1?.ativos)} ativos após filtro` },
      { t: "F2 · Abono de Permanência", o: "MGI — Gestão de Pessoas (Executivo Federal) · dados.gov.br",
        u: [["dados.gov.br — Abono Permanência", "https://dados.gov.br/dados/conjuntos-dados/gastos-pessoal-abono-permanencia"]],
        meta: `mês ${mesBR(m.mes_ref_f2)} · arquivo <code>${f.f2?.arquivo || "—"}</code><br>SHA-256 <code>${(f.f2?.sha256 || "").slice(0, 16)}…</code> · ${fmtInt(f.f2?.abonos)} abonos` },
      { t: "F3 · População residente", o: "IBGE — Estimativas da população, por UF",
        u: [["API SIDRA, tabela 6579", "https://sidra.ibge.gov.br/tabela/6579"], ["ibge.gov.br", "https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html"]],
        meta: `referência ${m.ano_pop}` },
      { t: "F4 · Malha territorial", o: "IBGE — API de malhas geográficas", u: [["servicodados.ibge.gov.br", "https://servicodados.ibge.gov.br/api/docs/malhas?versao=3"]], meta: "GeoJSON simplificado, versionado no repositório" },
    ];
    $("#cards-fontes").innerHTML = cards.map((c) => `
      <div class="card"><h4>${c.t}</h4><div>${c.o}</div>
        <div>${c.u.map(([n, u]) => `<a href="${u}" target="_blank" rel="noopener">${n}</a>`).join(" · ")}</div>
        <p class="meta">${c.meta}</p></div>`).join("");
  }

  // ---------------------------------------------------------------- eventos
  function ligarEventos() {
    document.querySelectorAll(".lente button").forEach((b) => b.addEventListener("click", () => {
      st.lente = b.dataset.lente;
      gravarHash(false);
      renderTudo();
    }));
    $("#sel-uf").addEventListener("change", (e) => selecionar(e.target.value || null, false));
    $("#btn-print").addEventListener("click", () => { if (!st.uf) selecionar(linhas()[0].uf, false); window.print(); });
    $("#btn-share").addEventListener("click", async () => {
      if (!st.uf) return;
      const url = location.href;
      try { await navigator.clipboard.writeText(url); $("#btn-share").textContent = "Link copiado ✓"; }
      catch { prompt("Copie o link:", url); }
      setTimeout(() => { $("#btn-share").textContent = "Copiar link"; }, 2000);
    });
    window.addEventListener("hashchange", () => { lerHash(); renderTudo(); });
    let t;
    window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => { renderMapa(); renderMatriz(); }, 150); });
  }

  function renderTudo() {
    renderCabecalho();
    renderLegenda();
    renderMapa();
    renderMatriz();
    renderTabela();
    renderSelect();
    renderPainel();
  }

  carregar().then(() => {
    lerHash();
    renderMeta();
    ligarEventos();
    renderTudo();
    if (st.uf) $("#painel").scrollIntoView({ block: "start" });
  }).catch((e) => {
    $("#cartao").innerHTML = `<p><strong>Não foi possível carregar os dados.</strong> ${e.message}</p>`;
    console.error(e);
  });
})();
