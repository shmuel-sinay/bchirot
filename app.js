let data;
const $ = id => document.getElementById(id);

function leadingBloc(n) {
  const totals = {};
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
