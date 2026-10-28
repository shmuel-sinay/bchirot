"""ניתוח תוצאות לפי קלפי (CSV ועדת הבחירות) + תחזית למעטפות כפולות ללא מצביעים לרשימות ערביות.
שימוש: python3 -I scripts/analyze.py <expb.csv>"""
import sys, numpy as np, pandas as pd

META = ['סמל ועדה','ברזל','שם ישוב','סמל ישוב','קלפי','ריכוז','שופט','בזב','מצביעים','פסולים','כשרים','חיצוניות','קלפי אחרת']
THRESH = 0.0325
ARAB = ['ודם', 'עם', 'ד']          # רשימות שזוהו כערביות לפי עוצמה ביישובים ערביים; ד קטנה ושייכת לאותו מגזר
# יישובים ערביים (>60% מהקולות לרשימות ערביות) מזוהים אוטומטית ומשמשים להפרדת מגזר

def dhondt(votes, seats=120):
    q = {p: [v / (i + 1) for i in range(seats)] for p, v in votes.items()}
    flat = sorted(((x, p) for p, l in q.items() for x in l), reverse=True)[:seats]
    out = dict.fromkeys(votes, 0)
    for _, p in flat: out[p] += 1
    return out

def seats_for(totals):
    tot = sum(totals.values())
    passed = {p: v for p, v in totals.items() if v / tot >= THRESH}
    return dhondt(passed)

def main(path):
    b = pd.read_csv(path, encoding='utf-8-sig').dropna(axis=1, how='all')
    parties = [c for c in b.columns if c not in META]
    tot = b[parties].sum()
    valid = tot.sum()
    print(f"בזב {b['בזב'].sum():,}  מצביעים {b['מצביעים'].sum():,}  כשרים {int(valid):,}  הצבעה {b['מצביעים'].sum()/b['בזב'].sum():.1%}")
    s = seats_for(tot.to_dict())
    print("\n== תוצאות (קלפיות שנספרו) ==")
    for p in tot.sort_values(ascending=False).index[:16]:
        print(f"{p:5s} {int(tot[p]):>9,} {tot[p]/valid:6.2%}  מנדטים: {s.get(p,0)}")
    # מגזר ערבי: יישובים שבהם רשימות ערביות >60%
    city = b.groupby('שם ישוב')[parties].sum()
    arab_share = city[ARAB].sum(axis=1) / city.sum(axis=1)
    arab_cities = arab_share[arab_share > .6].index
    jew = b[~b['שם ישוב'].isin(arab_cities)][parties].sum()
    print(f"\nיישובים ערביים (>60% לרשימות ערביות): {len(arab_cities)}, הצבעה שם "
          f"{b[b['שם ישוב'].isin(arab_cities)]['מצביעים'].sum()/b[b['שם ישוב'].isin(arab_cities)]['בזב'].sum():.1%}")

    # תחזית: מעטפות כפולות (חיילים, נציגויות, אסירים, מאושפזים) - ללא רשימות ערביות
    print("\n== תחזית אחרי מעטפות כפולות (0 לרשימות ערביות) ==")
    base = jew.drop(ARAB, errors='ignore')
    shares = (base / base.sum()).reindex(tot.index, fill_value=0)
    rng = np.random.default_rng(1)
    for pct in (0.03, 0.05, 0.08):
        add = valid * pct
        t = tot + shares * add
        s2 = seats_for(t.to_dict())
        print(f"\nמעטפות = {pct:.0%} מהכשרים (~{int(add):,}):")
        print("  " + ", ".join(f"{p}:{s2[p]}" for p in sorted(s2, key=s2.get, reverse=True)))
    # סימולציה: גודל 3-8%, ותנודה בהרכב (Dirichlet) סביב חלוקת המגזר היהודי
    runs = {}
    N = 4000
    for _ in range(N):
        pct = rng.uniform(.03, .08)
        sh = rng.dirichlet(shares.values * 300 + 1e-9)
        t = tot + pd.Series(sh, index=shares.index) * valid * pct
        for p, v in seats_for(t.to_dict()).items(): runs.setdefault(p, []).append(v)
    print("\n== סימולציה (4000 הרצות) - טווח 10%-90% ==")
    for p, v in sorted(runs.items(), key=lambda kv: -np.mean(kv[1])):
        v = v + [0] * (N - len(v))
        print(f"{p:5s} ממוצע {np.mean(v):5.1f}  טווח {np.percentile(v,10):.0f}-{np.percentile(v,90):.0f}  סיכוי כניסה {np.mean(np.array(v)>0):.0%}")
    # מי קרובה לאחוז החסימה
    print("\nקרובות לאחוז החסימה:", {p: f"{tot[p]/valid:.2%}" for p in tot.index if .02 < tot[p]/valid < .045})
    # הצבעה לפי עיר גדולה
    c = b.groupby('שם ישוב')[['בזב','מצביעים']].sum()
    c['pct'] = c['מצביעים'] / c['בזב']
    print("\nהצבעה בערים הגדולות:")
    print(c.sort_values('בזב', ascending=False).head(10)['pct'].map('{:.1%}'.format).to_string())

if __name__ == '__main__':
    main(sys.argv[1])
