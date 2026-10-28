(() => {
  const channels = ["חדשות 12", "חדשות 13", "כאן 11", "i24 / ערוץ 14"];
  const box = document.getElementById("channels");
  const save = k => { try { return localStorage.getItem(k) || ""; } catch { return ""; } };
  box.innerHTML = channels.map((c, i) =>
    `<label>${c}<textarea id="ch${i}" placeholder="הליכוד: 30">${save("ch" + i)}</textarea></label>`).join("");

  const parse = t => Object.fromEntries(t.split("\n").map(l => l.split(/[:：]/))
    .filter(p => p.length === 2 && !isNaN(+p[1])).map(p => [p[0].trim(), +p[1]]));

  document.getElementById("calc").onclick = () => {
    const polls = channels.map((_, i) => {
      const v = document.getElementById("ch" + i).value;
      try { localStorage.setItem("ch" + i, v); } catch {}
      return parse(v);
    });
    const parties = [...new Set(polls.flatMap(p => Object.keys(p)))];
    const rows = parties.map(name => {
      const vals = polls.map(p => p[name]);
      const have = vals.filter(v => v !== undefined);
      return { name, vals, avg: have.reduce((a, b) => a + b, 0) / have.length };
    }).sort((a, b) => b.avg - a.avg);
    document.getElementById("exitTable").innerHTML =
      `<thead><tr><th>מפלגה</th>${channels.map(c => `<th>${c}</th>`).join("")}<th>ממוצע</th></tr></thead><tbody>` +
      rows.map(r => `<tr><td>${r.name}</td>${r.vals.map(v => `<td>${v ?? "-"}</td>`).join("")}<td>${r.avg.toFixed(1)}</td></tr>`).join("") + "</tbody>";
  };
})();
