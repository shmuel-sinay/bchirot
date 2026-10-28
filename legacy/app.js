let data;
const $ = id => document.getElementById(id);

function leadingBloc(n) {
  const totals = {};
  if (!Object.keys(n.votes).length) return "-";
  for (const [party, v] of Object.entries(n.votes)) {
    const bloc = data.parties[party];
    totals[bloc] = (totals[bloc] || 0) + v;
  }
  return Object.entries(totals).sort((a, b) => b[1] - a[1])[0][0];
}

function render() {
  const dir = $("sort").value === "desc" ? -1 : 1;
  const rows = data.cities[$("city").value]
    .map(n => ({ ...n, pct: n.voted / n.eligible * 100, bloc: leadingBloc(n) }))
    .sort((a, b) => dir * (a.pct - b.pct));
  $("rows").innerHTML = rows.map((n, i) => `<tr>
    <td>${i + 1}</td><td>${n.name}</td>
    <td>${n.pct.toFixed(1)}%<span class="bar" style="width:${n.pct}px"></span></td>
    <td>${n.eligible.toLocaleString("he-IL")}</td><td>${n.voted.toLocaleString("he-IL")}</td>
    <td><span class="tag ${n.bloc}">${n.bloc}</span></td></tr>`).join("");
}

fetch("data/elections.json").then(r => r.json()).then(d => {
  data = d;
  $("note").textContent = d._note;
  $("city").innerHTML = Object.keys(d.cities).map(c => `<option>${c}</option>`).join("");
  $("city").onchange = $("sort").onchange = render;
  render();
});

// טעינת CSV: מזהה עמודות לפי שם בעברית; שורות של אותה שכונה (קלפיות) מסוכמות.
$("file").onchange = async e => {
  const text = await e.target.files[0].text();
  const [head, ...lines] = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/).map(l => l.split(/[,\t;]/).map(x => x.trim().replace(/^"|"$/g, "")));
  const col = re => head.findIndex(h => re.test(h));
  const [ci, ni, ei, vi] = [/עיר|ישוב|יישוב/, /שכונה|אזור/, /זכאי|זכות|בעלי/, /הצביע|מצביעים|כשרים/].map(col);
  if ([ci, ni, ei, vi].includes(-1)) return alert("לא זוהו העמודות: עיר, שכונה, בעלי זכות בחירה, מצביעים");
  const cities = {};
  for (const r of lines) {
    const n = (cities[r[ci]] ||= {});
    const x = (n[r[ni]] ||= { name: r[ni], eligible: 0, voted: 0, votes: {} });
    x.eligible += +r[ei]; x.voted += +r[vi];
  }
  for (const c in cities) cities[c] = Object.values(cities[c]);
  data = { ...data, _note: "נתונים מהקובץ שנטען", cities };
  $("note").textContent = data._note;
  $("city").innerHTML = Object.keys(cities).map(c => `<option>${c}</option>`).join("");
  render();
};
