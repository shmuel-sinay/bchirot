(() => {
  const blocs = ["ימין", "שמאל", "חרדים", "ערבים"];
  const $ = id => document.getElementById(id);
  $("ratios").innerHTML = "<p>אחוז הצבעה במעוזי כל גוש (היום / בבחירות הקודמות):</p>" + blocs.map(b =>
    `<label>${b}: <input type="number" step="0.1" id="now_${b}" value="60"> / <input type="number" step="0.1" id="prev_${b}" value="60"></label><br>`).join("");

  $("project").onclick = () => {
    const parties = $("polls").value.split("\n").map(l => l.split(/[:：]/).map(x => x.trim()))
      .filter(p => p.length === 3 && !isNaN(+p[1]) && blocs.includes(p[2])).map(p => ({ name: p[0], seats: +p[1], bloc: p[2] }));
    if (!parties.length) return ($("projOut").textContent = "לא הוזנו סקרים בפורמט תקין.");
    const factor = {};
    for (const b of blocs) factor[b] = +$("now_" + b).value / +$("prev_" + b).value;
    const w = parties.map(p => ({ ...p, w: p.seats * factor[p.bloc] }));
    const total = w.reduce((a, p) => a + p.w, 0);
    // חלוקה לפי שארית הגדולה כך שהסכום יהיה 120
    w.forEach(p => { p.exact = p.w / total * 120; p.out = Math.floor(p.exact); });
    let left = 120 - w.reduce((a, p) => a + p.out, 0);
    [...w].sort((a, b) => (b.exact - b.out) - (a.exact - a.out)).slice(0, left).forEach(p => p.out++);
    const sum = b => w.filter(p => p.bloc === b).reduce((a, p) => a + p.out, 0);
    const base = b => parties.filter(p => p.bloc === b).reduce((a, p) => a + p.seats, 0);
    const lines = blocs.filter(b => base(b)).map(b => {
      const f = factor[b], d = sum(b) - Math.round(base(b) / parties.reduce((a, p) => a + p.seats, 0) * 120);
      return `במעוזי ${b} ההצבעה היא ${(f * 100).toFixed(0)}% מהרגיל, ולכן הגוש מקבל בהערכה ${sum(b)} מנדטים (${d >= 0 ? "+" : ""}${d} ביחס לסקר).`;
    });
    $("projOut").innerHTML = "<ul>" + lines.map(l => `<li>${l}</li>`).join("") + "</ul><table><thead><tr><th>מפלגה</th><th>סקר</th><th>הערכה</th></tr></thead><tbody>" +
      w.sort((a, b) => b.out - a.out).map(p => `<tr><td>${p.name}</td><td>${p.seats}</td><td>${p.out}</td></tr>`).join("") + "</tbody></table>";
  };
})();
