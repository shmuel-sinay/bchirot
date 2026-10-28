"""תחזית משוקללת: משלימה יישובים/קלפיות שטרם נספרו לפי יישובים דומים (kNN על פרופיל הצבעה בבחירות קודמות),
ומוסיפה מעטפות חיצוניות בלי רשימות ערביות.
שימוש: python3 -I scripts/forecast.py <prev_expb.csv> <now_expb.csv> [out_dir]"""
import sys, json, numpy as np, pandas as pd

META = ['סמל ועדה','ברזל','שם ישוב','סמל ישוב','קלפי','ריכוז','שופט','בזב','מצביעים','פסולים','כשרים','חיצוניות','קלפי אחרת']
OLD_ARAB = ['ום', 'עם', 'ד']
NEW_ARAB = ['ודם', 'עם', 'ד']
THRESH = 0.0325
# גושים לפי אותיות הפתק (ועדת הבחירות, 27.09.26)
BLOCS = {
    'קואליציה': ['מחל', 'ב', 'ט', 'שס', 'ג', 'ני', 'נר', 'זך'],           # הליכוד, עוצמה יהודית, ציונות דתית+זהות, ש"ס, יהדות התורה, נעם
    'אופוזיציה יהודית': ['רק', 'דרך', 'ל', 'אמת', 'די', 'כן'],            # בנט, איזנקוט, ליברמן, הדמוקרטים, המילואימניקים, כחול לבן
    'ערבים': ['ודם', 'עם', 'ד', 'בד'],                                     # המשותפת, רע"ם, השותפות לכולם, ביחד נצליח
}
NAMES = {'מחל': 'הליכוד', 'ב': 'עוצמה יהודית', 'ט': 'הציונות הדתית וזהות', 'שס': 'ש"ס', 'ג': 'יהדות התורה', 'ני': 'נעם',
         'רק': 'ביחד – בנט', 'דרך': 'איזנקוט', 'ל': 'ישראל ביתנו', 'אמת': 'הדמוקרטים', 'די': 'המילואימניקים', 'כן': 'כחול לבן',
         'ודם': 'הרשימה המשותפת', 'עם': 'רע"ם', 'ך': 'עמך ישראל', 'זך': 'הציבור החרדי', 'ד': 'השותפות לכולם', 'בד': 'ביחד נצליח',
         'נר': 'צבע שחור', 'פה': 'אני ואתה', 'בי': 'צומת בית ישראל', 'צדק': 'שרשר לאהבה', 'ה': 'גן עדן', 'י': 'ישראל תחילה'}
DISQUALIFIED = 'ודם'                                                         # אושרה על תנאי עד הכרעת העליון
K = 8
ENV_CODE = 9999

def dhondt(votes, seats=120):
    flat = sorted(((v / (i + 1), p) for p, v in votes.items() for i in range(seats)), reverse=True)[:seats]
    out = dict.fromkeys(votes, 0)
    for _, p in flat: out[p] += 1
    return out

def seats_for(totals):
    tot = sum(totals.values())
    return dhondt({p: v for p, v in totals.items() if v / tot >= THRESH})

def load(path):
    b = pd.read_csv(path, encoding='utf-8-sig').dropna(axis=1, how='all')
    return b, [c for c in b.columns if c not in META]

def knn_predict(F, Y, w, idx_train, x, k=K):
    d = np.sqrt(((F[idx_train] - x) ** 2).sum(axis=1))
    o = np.argsort(d)[:k]
    wt = w[idx_train][o] / (d[o] + 0.03)
    return (Y[idx_train][o] * wt[:, None]).sum(axis=0) / wt.sum()

def main(prev_path, now_path, out_dir=None):
    pb, PP = load(prev_path)
    nb, NP = load(now_path)
    env = pb[pb['סמל ישוב'] == ENV_CODE]
    reg = pb[pb['סמל ישוב'] != ENV_CODE]
    env_share_of_valid = env['כשרים'].sum() / pb['כשרים'].sum()

    s22 = reg.groupby('סמל ישוב').agg(name=('שם ישוב', 'first'), elig=('בזב', 'sum'), voted=('מצביעים', 'sum'), valid=('כשרים', 'sum'))
    v22 = reg.groupby('סמל ישוב')[PP].sum()
    s26 = nb.groupby('סמל ישוב').agg(name=('שם ישוב', 'first'), elig=('בזב', 'sum'), voted=('מצביעים', 'sum'), valid=('כשרים', 'sum'))
    v26 = nb.groupby('סמל ישוב')[NP].sum()

    arab_sh = v22[[c for c in OLD_ARAB if c in v22]].sum(axis=1) / s22['valid']
    har_sh = v22[['שס', 'ג']].sum(axis=1) / s22['valid']
    s22['sector'] = np.where(arab_sh > .5, 'ערבי', np.where(har_sh > .5, 'חרדי', 'כללי'))

    J = s22.join(s26, rsuffix='26', how='left').fillna({'elig26': 0, 'voted26': 0, 'valid26': 0})
    J['r'] = J['elig26'] / J['elig']
    growth = {sec: J[(J.sector == sec) & (J.r >= 0.97) & (J.r < 1.5)]['r'].median() for sec in ['ערבי', 'חרדי', 'כללי']}
    J['g'] = J['sector'].map(growth)
    J['c'] = J['elig26'] / (J['elig'] * J['g'])               # שיעור הנספר מתוך הצפוי
    complete = J['c'] >= 0.93
    J['turn22'] = J['voted'] / J['elig']
    k_turn = {sec: (J[complete & (J.sector == sec)]['voted26'] / J[complete & (J.sector == sec)]['elig26']).median() /
                   J[complete & (J.sector == sec)]['turn22'].median() for sec in growth}

    # יישובים חדשים שלא היו בבחירות הקודמות: נחשבים שלמים
    new_codes = [c for c in s26.index if c not in s22.index]

    # --- מודל: רגרסיית ריג' (פרופיל הצבעה ב‑2022 + השתתפות) -> חלוקת הקולות היום, מאומנת על יישובים שנספרו במלואם
    top_old = [p for p in v22.sum().sort_values(ascending=False).index[:14]]
    oth = (v22.sum(axis=1) - v22[top_old].sum(axis=1)).values
    F_all = np.c_[np.sqrt(np.c_[v22[top_old].values, oth] / s22['valid'].values[:, None]), J['turn22'].values, np.ones(len(J))]
    comp_idx = np.where(complete.values)[0]
    Y = np.zeros((len(J), len(NP)))
    for i, code in enumerate(J.index):
        if code in v26.index and v26.loc[code].sum() > 0:
            Y[i] = (v26.loc[code] / v26.loc[code].sum()).values
    w = np.sqrt(J['voted26'].values + 1)
    LAM = 10.0

    def fit(idx):
        W = w[idx][:, None]
        A = F_all[idx] * W
        return np.linalg.solve(A.T @ A + LAM * np.eye(F_all.shape[1]), A.T @ (Y[idx] * W))

    def predict(B, rows):
        p_ = np.clip(F_all[rows] @ B, 0, None)
        return p_ / p_.sum(axis=1, keepdims=True)

    # ולידציה: 20% מהיישובים השלמים מוסתרים ומנובאים (חוזר 20 פעמים)
    rng = np.random.default_rng(7)
    errs = []
    for _ in range(20):
        hold = rng.choice(comp_idx, size=len(comp_idx) // 5, replace=False)
        train = np.setdiff1d(comp_idx, hold)
        pr = predict(fit(train), hold)
        wts = J['voted26'].values[hold]
        act = (Y[hold] * wts[:, None]).sum(axis=0); prt = (pr * wts[:, None]).sum(axis=0)
        errs.append(np.c_[act / act.sum(), prt / prt.sum()])
    e = np.mean(errs, axis=0)
    cv = pd.DataFrame({'actual': e[:, 0], 'predicted': e[:, 1]}, index=NP)
    cv['abs_err'] = (cv.actual - cv.predicted).abs()
    top_new = pd.Series((Y * J['voted26'].values[:, None]).sum(axis=0), index=NP).sort_values(ascending=False).index[:12]
    print("== ולידציה (20% מהיישובים השלמים הוסתרו ונוחשו, ממוצע 20 חזרות) ==")
    print(cv.loc[top_new].round(4).to_string())
    print("שגיאה מוחלטת ממוצעת באחוזי קולות ארציים:", f"{cv.loc[top_new,'abs_err'].mean():.2%}")

    B = fit(comp_idx)
    resid = Y[comp_idx] - predict(B, comp_idx)            # שאריות לדגימה בסימולציה
    size_c = J['voted26'].values[comp_idx]

    # --- השלמת חסרים
    miss_rows = []
    miss_votes = np.zeros(len(NP))
    miss_items = []                                       # (קולות, חלוקה צפויה) לכל יישוב חסר
    for i, code in enumerate(J.index):
        if J.c.iloc[i] >= 0.93: continue
        U = max(J['elig'].iloc[i] * J['g'].iloc[i] - J['elig26'].iloc[i], 0)
        if J['c'].iloc[i] > 0.3 and J['elig26'].iloc[i] > 0:
            turn = J['voted26'].iloc[i] / J['elig26'].iloc[i]
        else:
            turn = min(J['turn22'].iloc[i] * k_turn[J['sector'].iloc[i]], 0.95)
        votes = U * turn * 0.995
        sh = predict(B, [i])[0]
        miss_votes += votes * sh
        miss_items.append((votes, sh))
        miss_rows.append((J['name'].iloc[i], J['sector'].iloc[i], round(J['c'].iloc[i], 2), int(U), int(votes)))
    miss = pd.DataFrame(miss_rows, columns=['שם', 'מגזר', 'נספר', 'בעלי זכות חסרים', 'מצביעים צפויים'])

    counted = pd.Series(nb[NP].sum(), index=NP)
    print(f"\nגידול בעלי זכות לפי מגזר: { {k: round(v,3) for k,v in growth.items()} }")
    print(f"יישובים חסרים לגמרי: {(J.c<0.02).sum()}, חלקיים: {((J.c>=0.02)&(J.c<0.93)).sum()}")
    print(f"מצביעים צפויים בחסר: {int(miss['מצביעים צפויים'].sum()):,}  (נספרו {int(counted.sum()):,})")
    print(miss.sort_values('מצביעים צפויים', ascending=False).head(15).to_string(index=False))

    # --- מעטפות חיצוניות: מערבבים יישובים שדומים לפרופיל המעטפות ב‑2022, בלי רשימות ערביות
    ep = env[PP].sum()
    ep = ep.drop([c for c in OLD_ARAB if c in ep.index])
    ep = ep / ep.sum()
    jewish_idx = [i for i in comp_idx if J['sector'].iloc[i] != 'ערבי' and J['voted26'].iloc[i] > 1500]
    A = np.c_[(v22[PP].drop(columns=[c for c in OLD_ARAB if c in v22]).iloc[jewish_idx].div(
        v22[PP].drop(columns=[c for c in OLD_ARAB if c in v22]).iloc[jewish_idx].sum(axis=1), axis=0)).values.T]
    # NNLS פשוט באמצעות גרדיאנט מוקרן
    x = np.ones(A.shape[1]) / A.shape[1]
    t = ep.reindex([c for c in PP if c not in OLD_ARAB]).fillna(0).values
    for _ in range(4000):
        g = A.T @ (A @ x - t)
        x = np.maximum(x - 0.5 * g, 0)
        x = x / x.sum()
    env_new = (Y[jewish_idx] * x[:, None]).sum(axis=0)
    for c in NEW_ARAB:
        if c in NP: env_new[NP.index(c)] = 0
    env_new = pd.Series(env_new / env_new.sum(), index=NP)
    print("\nהרכב מעטפות צפוי (ללא ערביים):", env_new.sort_values(ascending=False).head(8).round(3).to_dict())

    # --- סימולציה
    base_now = counted + pd.Series(miss_votes, index=NP)
    total_est = base_now.sum()
    runs = {p: [] for p in NP}; runs2 = {p: [] for p in NP}
    bloc_runs = {b_: [] for b_ in BLOCS}; bloc_runs2 = {b_: [] for b_ in BLOCS}
    N = 4000
    mv_votes = np.array([v for v, _ in miss_items]); mv_sh = np.array([h for _, h in miss_items])
    for _ in range(N):
        # לכל יישוב חסר: נותנים שארית של יישוב שלם בגודל דומה (דגימה), ומעט שונות בהשתתפות
        pick = rng.integers(0, len(comp_idx), len(mv_votes))
        sh = np.clip(mv_sh + resid[pick], 0, None); sh /= sh.sum(axis=1, keepdims=True)
        turn_noise = rng.normal(1, 0.03)
        mv = pd.Series((mv_votes[:, None] * sh).sum(axis=0) * turn_noise, index=NP)
        env_size = total_est / (1 - env_share_of_valid) * env_share_of_valid * rng.uniform(0.85, 1.12)
        d = rng.dirichlet(env_new.values * 400 + 1e-9)
        t_ = counted + mv + pd.Series(d, index=NP) * env_size
        s = seats_for(t_.to_dict())
        for p in NP: runs[p].append(s.get(p, 0))
        s2 = seats_for({k: v for k, v in t_.items() if k != DISQUALIFIED})
        for b_, ps in BLOCS.items():
            bloc_runs[b_].append(sum(s.get(q, 0) for q in ps)); bloc_runs2[b_].append(sum(s2.get(q, 0) for q in ps))
        for q in NP: runs2[q].append(s2.get(q, 0))
    print(f"\nמעטפות חיצוניות ב‑2022: {env_share_of_valid:.1%} מהכשרים")
    rows = []
    final_mean = counted + pd.Series(miss_votes, index=NP) + env_new * (total_est / (1 - env_share_of_valid) * env_share_of_valid)
    for p in final_mean.sort_values(ascending=False).index[:14]:
        v = np.array(runs[p])
        rows.append(dict(party=p, votes_now=int(counted[p]), votes_forecast=int(final_mean[p]), share_forecast=round(final_mean[p] / final_mean.sum(), 4),
                         seats_mean=round(v.mean(), 1), p10=int(np.percentile(v, 10)), p90=int(np.percentile(v, 90)), entry_prob=round((v > 0).mean(), 2)))
    res = pd.DataFrame(rows)
    print(res.to_string(index=False))
    brow = []
    for label, br, rr in (('כל הרשימות מתמודדות', bloc_runs, runs), ('המשותפת נפסלת', bloc_runs2, runs2)):
        co = np.array(br['קואליציה']); op = np.array(br['אופוזיציה יהודית']); ar = np.array(br['ערבים'])
        brow.append(dict(scenario=label, coalition=round(co.mean(), 1), opposition=round(op.mean(), 1), arab=round(ar.mean(), 1),
                         p_coalition_61=round((co >= 61).mean(), 2), p_opp_arab_61=round(((op + ar) >= 61).mean(), 2),
                         p_opp_only_61=round((op >= 61).mean(), 2), p_none_61=round(((co < 61) & ((op + ar) < 61)).mean(), 2)))
    bl = pd.DataFrame(brow); print(bl.T.to_string())
    d2 = pd.DataFrame({q: [np.mean(runs2[q])] for q in NP}).T.rename(columns={0: 'seats_if_disqualified'})
    print(d2.sort_values('seats_if_disqualified', ascending=False).head(12).round(1).T.to_string())
    if out_dir:
        bloc_of = {q: b_ for b_, ps in BLOCS.items() for q in ps}
        c_ = J.copy()
        city = nb.groupby('שם ישוב')[['בזב', 'מצביעים']].sum().sort_values('בזב', ascending=False).head(15)
        city['top'] = nb.groupby('שם ישוב')[NP].sum().loc[city.index].idxmax(axis=1)
        out = dict(
            meta=dict(valid_counted=int(counted.sum()), eligible_counted=int(nb['בזב'].sum()), voted_counted=int(nb['מצביעים'].sum()),
                      missing_voters=int(miss_votes.sum()), env_share=round(float(env_share_of_valid), 4),
                      env_votes=int(total_est / (1 - env_share_of_valid) * env_share_of_valid), threshold=THRESH,
                      settlements_missing=int((J.c < 0.02).sum()), settlements_partial=int(((J.c >= 0.02) & (J.c < 0.93)).sum()),
                      cv_error=round(float(cv.loc[top_new, 'abs_err'].mean()), 4)),
            parties=[dict(letter=p, name=NAMES.get(p, p), bloc=bloc_of.get(p, 'אחר'), votes_now=int(counted[p]), votes_missing=int(miss_votes[NP.index(p)]),
                          env_share=round(float(env_new[p]), 4), seats_mean=round(float(np.mean(runs[p])), 1), p10=int(np.percentile(runs[p], 10)),
                          p90=int(np.percentile(runs[p], 90)), entry_prob=round(float((np.array(runs[p]) > 0).mean()), 2),
                          seats_if_disq=round(float(np.mean(runs2[p])), 1)) for p in counted.sort_values(ascending=False).index[:20]],
            blocs=bl.to_dict('records'),
            missing=miss.sort_values('מצביעים צפויים', ascending=False).head(15).rename(columns={'שם': 'name', 'מגזר': 'sector', 'נספר': 'counted', 'בעלי זכות חסרים': 'missing_eligible', 'מצביעים צפויים': 'expected_voters'}).to_dict('records'),
            cities=[dict(city=i, eligible=int(r['בזב']), voted=int(r['מצביעים']), top=r['top']) for i, r in city.iterrows()],
            validation=[dict(party=p, actual=round(float(cv.loc[p, 'actual']), 4), predicted=round(float(cv.loc[p, 'predicted']), 4)) for p in top_new],
        )
        json.dump(out, open(f"{out_dir}/forecast.json", 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        bl.to_csv(f"{out_dir}/blocs.csv", index=False, encoding='utf-8')
        res.to_csv(f"{out_dir}/forecast.csv", index=False, encoding='utf-8')
        miss.sort_values('מצביעים צפויים', ascending=False).head(40).to_csv(f"{out_dir}/missing.csv", index=False, encoding='utf-8')
        cv.loc[top_new].reset_index().rename(columns={'index': 'party'}).to_csv(f"{out_dir}/validation.csv", index=False, encoding='utf-8')

if __name__ == '__main__':
    main(*sys.argv[1:4])
