(() => {
  const $ = (id) => document.getElementById(id);
  const fmt = new Intl.NumberFormat('he-IL');
  const pct = (x, d = 1) => (x * 100).toFixed(d) + '%';
  const COLORS = {
    'מחל': '#2f6bff', 'ב': '#123fa8', 'ט': '#7f98ff', 'שס': '#2e9cc9', 'ג': '#7a5af0', 'ני': '#9aa9d6',
    'דרך': '#f08a1c', 'רק': '#ffc23d', 'ל': '#d9503a', 'אמת': '#e0508f', 'די': '#b5702f', 'כן': '#9a8f7a',
    'ודם': '#19a46f', 'עם': '#72d6ac',
  };
  const BLOC_ORDER = ['קואליציה', 'אופוזיציה יהודית', 'ערבים'];
  let D, state = { env: 9.6, turn: 100, disq: false };

  // חלוקת מנדטים: אחוז חסימה ואז חלוקה לפי מנה (שקול לבדר-עופר ללא הסכמי עודפים)
  function allocate(votes, thr, n = 120) {
    const total = Object.values(votes).reduce((a, b) => a + b, 0);
    const pass = Object.entries(votes).filter(([, v]) => v / total >= thr);
    const seats = Object.fromEntries(Object.keys(votes).map((k) => [k, 0]));
    const q = pass.map(([k, v]) => ({ k, v, s: 0 }));
    for (let i = 0; i < n; i++) {
      let best = q[0];
      for (const x of q) if (x.v / (x.s + 1) > best.v / (best.s + 1)) best = x;
      best.s++; seats[best.k]++;
    }
    return seats;
  }

  function compute() {
    const m = D.meta, e = state.env / 100, t = state.turn / 100;
    const base = D.parties.map((p) => p.votes_now + p.votes_missing * t);
    const baseTotal = base.reduce((a, b) => a + b, 0);
    const envVotes = baseTotal * e / (1 - e);
    const votes = {};
    D.parties.forEach((p, i) => {
      if (state.disq && p.letter === 'ודם') return;
      votes[p.letter] = base[i] + p.env_share * envVotes;
    });
    const seats = allocate(votes, m.threshold);
    const total = Object.values(votes).reduce((a, b) => a + b, 0);
    return { votes, seats, total };
  }

  function seatPositions(n = 120) {
    const rows = 7, r0 = 0.46, r1 = 1, radii = Array.from({ length: rows }, (_, i) => r0 + (r1 - r0) * i / (rows - 1));
    const sum = radii.reduce((a, b) => a + b, 0);
    const counts = radii.map((r) => Math.round(n * r / sum));
    let diff = n - counts.reduce((a, b) => a + b, 0);
    for (let i = rows - 1; diff !== 0; i = (i + rows - 1) % rows) { counts[i] += Math.sign(diff); diff -= Math.sign(diff); }
    const pts = [];
    radii.forEach((r, i) => {
      for (let j = 0; j < counts[i]; j++) {
        const a = counts[i] === 1 ? Math.PI / 2 : (j / (counts[i] - 1)) * Math.PI;
        pts.push({ a, x: 320 + Math.cos(a) * r * 290, y: 320 - Math.sin(a) * r * 290 });
      }
    });
    return pts.sort((p, q) => p.a - q.a);                // מימין (זווית 0) לשמאל
  }
  const POS = seatPositions();

  function drawHemi(res) {
    const order = [];
    for (const b of BLOC_ORDER) D.parties.filter((p) => p.bloc === b && res.seats[p.letter]).sort((x, y) => res.seats[y.letter] - res.seats[x.letter]).forEach((p) => order.push(p));
    D.parties.filter((p) => !BLOC_ORDER.includes(p.bloc) && res.seats[p.letter]).forEach((p) => order.push(p));
    const colorOf = [];
    order.forEach((p) => { for (let i = 0; i < res.seats[p.letter]; i++) colorOf.push({ c: COLORS[p.letter] || '#8b97a6', l: p.name }); });
    const svg = $('hemi');
    if (!svg.childElementCount) {
      POS.forEach((p) => { const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); c.setAttribute('cx', p.x.toFixed(1)); c.setAttribute('cy', p.y.toFixed(1)); c.setAttribute('r', 11); c.setAttribute('class', 'seat'); svg.appendChild(c); });
    }
    if (!$('hemiLabel')) {
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g'); g.id = 'hemiLabel';
      g.innerHTML = '<text x="320" y="290" text-anchor="middle" font-size="64" font-weight="900" style="font-family:var(--font-d)" fill="var(--ink)">120</text><text x="320" y="318" text-anchor="middle" font-size="16" fill="var(--mute)">מנדטים</text>';
      svg.appendChild(g);
    }
    [...svg.querySelectorAll('circle')].forEach((c, i) => {
      const s = colorOf[i];
      c.setAttribute('fill', s ? s.c : 'var(--line)');
      c.innerHTML = s ? `<title>${s.l}</title>` : '';
    });
    $('legend').innerHTML = order.map((p) => `<span><i style="background:${COLORS[p.letter] || '#8b97a6'}"></i>${p.name} <b>${res.seats[p.letter]}</b></span>`).join('');
  }

  function blocSeats(res) {
    const out = {};
    for (const b of BLOC_ORDER) out[b] = D.parties.filter((p) => p.bloc === b).reduce((a, p) => a + (res.seats[p.letter] || 0), 0);
    return out;
  }

  function render() {
    const res = compute(), bs = blocSeats(res);
    $('oEnv').textContent = state.env.toFixed(1) + '%';
    $('oTurn').textContent = state.turn + '%';
    drawHemi(res);
    $('b0').textContent = bs['קואליציה']; $('b1').textContent = bs['אופוזיציה יהודית']; $('b2').textContent = bs['ערבים'];
    $('mC').style.width = bs['קואליציה'] / 120 * 100 + '%'; $('mO').style.width = bs['אופוזיציה יהודית'] / 120 * 100 + '%'; $('mA').style.width = bs['ערבים'] / 120 * 100 + '%';
    const co = bs['קואליציה'], oa = bs['אופוזיציה יהודית'] + bs['ערבים'];
    const top = D.parties.slice().sort((a, b) => (res.seats[b.letter] || 0) - (res.seats[a.letter] || 0))[0];
    $('headline').textContent = co >= 61 ? `לקואליציה יש רוב של ${co} מנדטים` : `לקואליציה ${co} מנדטים, בלי רוב`;
    $('lede').textContent = `${top.name} הרשימה הגדולה עם ${res.seats[top.letter]} מנדטים. ` + (co >= 61 ? `המתחרים מגיעים ל‑${oa}.` : `לאופוזיציה עם הרשימות הערביות יש ${oa}.`);
    $('meterNote').textContent = `הקו הוא רוב של 61. קואליציה ${co}, אופוזיציה יהודית ${bs['אופוזיציה יהודית']}, רשימות ערביות ${bs['ערבים']}.`;
    $('stamp').textContent = state.disq ? 'תרחיש: הרשימה המשותפת נפסלת' : 'תחזית משוקללת, הערכה ראשית';
    const tb = $('tbl').tBodies[0];
    tb.innerHTML = D.parties.filter((p) => p.votes_now > 20000).sort((a, b) => ((res.seats[b.letter] || 0) - (res.seats[a.letter] || 0)) || (b.votes_now - a.votes_now)).map((p) => {
      const v = res.votes[p.letter] || 0, s = res.seats[p.letter] || 0;
      const col = COLORS[p.letter] || '#8b97a6';
      return `<tr><td><span class="pill" style="--c:${col}"><i></i>${p.name} <small>${p.letter}</small></span></td><td>${fmt.format(p.votes_now)}</td><td>${v ? fmt.format(Math.round(v)) : '—'}</td><td>${v ? pct(v / res.total) : '—'}</td><td><span class="bar" style="--c:${col};width:${s * 5}px"></span><b>${s}</b></td><td>${p.p10 === p.p90 ? p.p10 : p.p10 + '–' + p.p90}</td><td>${(p.entry_prob * 100).toFixed(0)}%</td></tr>`;
    }).join('');
  }

  function static_() {
    const m = D.meta;
    $('missingLede').textContent = `${m.settlements_missing} יישובים לא נספרו בכלל ועוד ${m.settlements_partial} נספרו חלקית. חסרים כ‑${fmt.format(Math.round(m.missing_voters / 1000))} אלף מצביעים צפויים, מול ${fmt.format(Math.round(m.valid_counted / 1000))} אלף קולות כשרים שנספרו.`;
    $('mtbl').tBodies[0].innerHTML = D.missing.map((r) => `<tr><td>${r.name}</td><td>${r.sector}</td><td>${(r.counted * 100).toFixed(0)}%</td><td>${fmt.format(r.missing_eligible)}</td><td>${fmt.format(r.expected_voters)}</td></tr>`).join('');
    const nm = Object.fromEntries(D.parties.map((p) => [p.letter, p.name]));
    $('ctbl').tBodies[0].innerHTML = D.cities.map((c) => `<tr><td>${c.city}</td><td>${pct(c.voted / c.eligible)}</td><td>${nm[c.top] || c.top}</td></tr>`).join('');
    $('valid').innerHTML = `<span>בבדיקה על יישובים מוסתרים: שגיאה ממוצעת ${pct(m.cv_error, 2)} באחוזי הקולות הארציים</span>` +
      D.validation.slice(0, 8).map((v) => `<span>${nm[v.party] || v.party}: בפועל ${pct(v.actual)}, נחזה ${pct(v.predicted)}</span>`).join('');
  }

  function init() {
    $('env').value = state.env; $('turn').value = state.turn;
    $('env').oninput = (e) => { state.env = +e.target.value; render(); };
    $('turn').oninput = (e) => { state.turn = +e.target.value; render(); };
    $('disq').onchange = (e) => { state.disq = e.target.checked; render(); };
    $('reset').onclick = () => { state = { env: Math.round(D.meta.env_share * 1000) / 10, turn: 100, disq: false }; $('env').value = state.env; $('turn').value = 100; $('disq').checked = false; render(); };
    $('theme').onclick = () => {
      const cur = document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      const next = cur === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch (e) {}
    };
    try { const t = localStorage.getItem('theme'); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
    state.env = Math.round(D.meta.env_share * 1000) / 10; $('env').value = state.env;
    static_(); render();
  }

  fetch('data/forecast.json').then((r) => r.json()).then((d) => { D = d; init(); })
    .catch(() => { $('headline').textContent = 'לא ניתן לטעון את הנתונים'; $('lede').textContent = 'פתח את האתר דרך שרת (למשל python3 -m http.server).'; });
})();
