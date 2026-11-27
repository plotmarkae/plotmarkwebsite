"""Fetch Dubai Land Department open data and write market-data/data.json.
Runs weekly in GitHub Actions. Polite: one request at a time, with pauses."""
import json, os, sys, time, statistics, urllib.request, datetime as dt

GATE = 'https://gateway.dubailand.gov.ae/open-data/'
HEAD = {'User-Agent': 'Mozilla/5.0 (compatible; plotmark.ae market page; weekly)',
        'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json',
        'Origin': 'https://dubailand.gov.ae', 'Referer': 'https://dubailand.gov.ae/'}
SQM_TO_SQFT = 10.7639
COMMUNITIES = {  # display name -> DLD area names (lower case)
    'Dubai Marina': ['dubai marina', 'marsa dubai'],
    'Palm Jumeirah': ['palm jumeirah', 'nakhlat jumeira'],
    'Jumeirah Village Circle': ['jumeirah village circle', 'al barsha south fourth'],
    'Dubai Hills Estate': ['dubai hills', 'dubai hills estate', 'hadaeq sheikh mohammed bin rashid'],
    'Downtown Dubai': ['burj khalifa', 'downtown dubai'],
    'Business Bay': ['business bay'],
    'Dubai Creek Harbour': ['dubai creek harbour', 'al khairan first'],
    'Dubai South': ['dubai south', 'madinat al mataar'],
}
LOOKUP = {a: c for c, names in COMMUNITIES.items() for a in names}

def post(ep, body, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(GATE + ep, data=json.dumps(body).encode(), headers=HEAD, method='POST')
            with urllib.request.urlopen(req, timeout=180) as f:
                return json.load(f)['response']['result'] or []
        except Exception as e:
            print('retry', ep, i, e, flush=True); time.sleep(5 * (i + 1))
    raise RuntimeError('DLD request failed: ' + ep)

def us(d): return d.strftime('%m/%d/%Y')

def tx_body(f, t, take, skip, offplan=''):
    return {"P_FROM_DATE": us(f), "P_TO_DATE": us(t), "P_GROUP_ID": "1", "P_IS_OFFPLAN": offplan, "P_IS_FREE_HOLD": "",
            "P_AREA_ID": "", "P_USAGE_ID": "", "P_PROP_TYPE_ID": "", "P_SORT": "TRANSACTION_NUMBER_ASC",
            "P_TAKE": str(take), "P_SKIP": str(skip)}

def rent_body(f, t, take, skip):
    return {"P_DATE_TYPE": "0", "P_FROM_DATE": us(f), "P_TO_DATE": us(t), "P_VERSION": "", "P_IS_FREE_HOLD": "",
            "P_USAGE_ID": "", "P_AREA_ID": "", "P_PROP_TYPE_ID": "", "P_SORT": "REGISTRATION_DATE_ASC",
            "P_TAKE": str(take), "P_SKIP": str(skip)}

def count(ep, body):
    r = post(ep, body); time.sleep(1.5)
    return int(r[0]['TOTAL']) if r else 0

def fetch_all(ep, mk, f, t, page=5000, max_pages=40):
    rows, seen, skip = [], set(), 0
    for _ in range(max_pages):
        r = post(ep, mk(f, t, page, skip)); time.sleep(1.5)
        if not r: break
        total = int(r[0]['TOTAL'])
        for x in r:
            k = (x.get('TRANSACTION_NUMBER') or x.get('REGISTRATION_DATE'), x.get('RN'), x.get('AREA_EN'), x.get('TRANS_VALUE') or x.get('ANNUAL_AMOUNT'), x.get('ACTUAL_AREA'))
            if k not in seen: seen.add(k); rows.append(x)
        skip += len(r)
        print(ep, skip, '/', total, flush=True)
        if skip >= total: break
    return rows

def med(v): return round(statistics.median(v)) if v else None

# ---------- valuation statistics (by area, type, bedrooms, ready/off-plan) ----------
def first(x, *keys):
    for k in keys:
        v = x.get(k)
        if v not in (None, ''): return v
    return None

def beds(x):
    r = str(first(x, 'ROOMS_EN', 'ROOMS', 'ROOMS_AR') or '').strip().lower()
    if not r: return None
    if 'studio' in r: return 'Studio'
    digits = ''.join(ch for ch in r if ch.isdigit())
    if not digits: return None
    n = int(digits)
    return None if n <= 0 or n > 9 else ('5+' if n >= 5 else str(n))

def kind(x):
    pt = (first(x, 'PROP_TYPE_EN') or '').lower()
    sub = (first(x, 'PROP_SB_TYPE_EN', 'PROP_SUB_TYPE_EN') or '').lower()
    use = (first(x, 'USAGE_EN') or '').lower()
    if use and 'resid' not in use: return None
    if 'villa' in pt or 'villa' in sub or 'town' in sub: return 'Villa'
    if 'flat' in sub or 'apartment' in sub or (pt == 'unit' and not sub): return 'Apartment'
    return None

def quart(v):
    v = sorted(v)
    if len(v) < 4: return None
    q = statistics.quantiles(v, n=4)
    return round(q[0]), round(statistics.median(v)), round(q[2])

def valuation(sales, rents, period):
    groups, rgroups, totals = {}, {}, {}
    for x in sales:
        area = (x.get('AREA_EN') or '').strip()
        k, b = kind(x), beds(x)
        a = x.get('ACTUAL_AREA') or x.get('PROCEDURE_AREA') or 0
        v = x.get('TRANS_VALUE') or 0
        if not area or not k or not a or a < 15 or v < 100000: continue
        sqft = a * SQM_TO_SQFT; psf = v / sqft
        if psf < 150 or psf > 20000: continue
        st = 'offplan' if x.get('IS_OFFPLAN') == 1 else 'ready'
        totals[area] = totals.get(area, 0) + 1
        for bb in (b or 'any', 'any') if b else ('any',):
            for ss in (st, 'all'):
                groups.setdefault((area, k, bb, ss), []).append((psf, sqft, v))
    for x in rents:
        area = (x.get('AREA_EN') or '').strip(); k, b = kind(x), beds(x)
        amt = x.get('ANNUAL_AMOUNT') or 0
        if not area or not k or amt < 5000 or amt > 5000000: continue
        for bb in (b, 'any') if b else ('any',):
            rgroups.setdefault((area, k, bb), []).append(amt)
    areas = {}
    for (area, k, b, st), rows in groups.items():
        if len(rows) < 5: continue
        q = quart([r[0] for r in rows])
        if not q: continue
        g = areas.setdefault(area, {'name': area, 'label': label(area), 'sales': totals.get(area, 0), 'g': {}, 'r': {}})
        g['g'][f'{k}|{b}|{st}'] = {'n': len(rows), 'p25': q[0], 'med': q[1], 'p75': q[2],
                                   'size': round(statistics.median([r[1] for r in rows])),
                                   'price': round(statistics.median([r[2] for r in rows]))}
    for (area, k, b), amts in rgroups.items():
        if area in areas and len(amts) >= 5:
            areas[area]['r'][f'{k}|{b}'] = {'n': len(amts), 'med': round(statistics.median(amts))}
    out = sorted((a for a in areas.values() if a['sales'] >= 10), key=lambda a: -a['sales'])
    return {'generated_at': dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
            'source': 'Dubai Land Department open data', 'period_sales': period[0], 'period_rents': period[1], 'areas': out}

def label(area):
    c = LOOKUP.get(area.lower())
    nice = area.title().replace(' Of ', ' of ').replace(' Al ', ' Al ')
    return f'{c} ({nice})' if c and c.lower() != area.lower() else (c or nice)

def main():
    today = dt.date.today()
    year = today.year
    out = {'generated_at': dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z', 'source': 'Dubai Land Department open data'}

    # 1) monthly sales counts, year to date (cheap: totals only)
    months = []
    for m in range(1, today.month + 1):
        f = dt.date(year, m, 1)
        t = (dt.date(year, m + 1, 1) - dt.timedelta(days=1)) if m < 12 else dt.date(year, 12, 31)
        t = min(t, today)
        allc = count('transactions', tx_body(f, t, 1, 0))
        offc = count('transactions', tx_body(f, t, 1, 0, offplan='1'))
        months.append({'month': f.strftime('%Y-%m'), 'label': f.strftime('%b'), 'sales': allc,
                       'offplan': offc if 0 < offc < allc else None, 'partial': t < (dt.date(year, m + 1, 1) - dt.timedelta(days=1) if m < 12 else dt.date(year, 12, 31))})
    out['months'] = months

    # 2) sales detail, last 90 days (within the current year, which is all DLD serves)
    f90 = max(today - dt.timedelta(days=90), dt.date(year, 1, 1))
    sales = fetch_all('transactions', tx_body, f90, today)
    # 3) rents, last 30 days
    f30 = max(today - dt.timedelta(days=30), dt.date(year, 1, 1))
    rents = fetch_all('rents', rent_body, f30, today + dt.timedelta(days=1), max_pages=30)

    def psf(x):
        a = x.get('ACTUAL_AREA') or x.get('PROCEDURE_AREA') or 0
        v = x.get('TRANS_VALUE') or 0
        return v / (a * SQM_TO_SQFT) if a and a > 15 and v > 100000 else None

    units = [x for x in sales if (x.get('PROP_TYPE_EN') or '').lower() == 'unit']
    out['dubai'] = {
        'period_sales': [f90.isoformat(), today.isoformat()],
        'sales_count': len(sales),
        'sales_value': round(sum(x.get('TRANS_VALUE') or 0 for x in sales)),
        'offplan_share': round(100 * sum(1 for x in sales if x.get('IS_OFFPLAN') == 1) / len(sales)) if sales else None,
        'median_psf_units': med([p for p in map(psf, units) if p]),
        'period_rents': [f30.isoformat(), today.isoformat()],
        'rent_contracts': len(rents),
        'median_rent_flats': med([x['ANNUAL_AMOUNT'] for x in rents if (x.get('PROP_SUB_TYPE_EN') or '').lower() == 'flat' and (x.get('ANNUAL_AMOUNT') or 0) > 5000]),
    }
    comm = []
    for c in COMMUNITIES:
        s = [x for x in sales if LOOKUP.get((x.get('AREA_EN') or '').strip().lower()) == c]
        u = [x for x in s if (x.get('PROP_TYPE_EN') or '').lower() == 'unit']
        r = [x for x in rents if LOOKUP.get((x.get('AREA_EN') or '').strip().lower()) == c]
        rf = [x['ANNUAL_AMOUNT'] for x in r if (x.get('PROP_SUB_TYPE_EN') or '').lower() == 'flat' and (x.get('ANNUAL_AMOUNT') or 0) > 5000]
        comm.append({'name': c, 'sales': len(s),
                     'median_psf': med([p for p in map(psf, u) if p]) if len(u) >= 10 else None,
                     'offplan_share': round(100 * sum(1 for x in s if x.get('IS_OFFPLAN') == 1) / len(s)) if len(s) >= 10 else None,
                     'median_rent_flat': med(rf) if len(rf) >= 10 else None, 'rent_contracts': len(r)})
    out['communities'] = comm
    os.makedirs('market-data', exist_ok=True)
    json.dump(out, open('market-data/data.json', 'w'), indent=1)
    # valuation figures: never allowed to break the market page
    try:
        if sales: print('sale record fields:', sorted(sales[0].keys()), flush=True)
        if rents: print('rent record fields:', sorted(rents[0].keys()), flush=True)
        val = valuation(sales, rents, ([f90.isoformat(), today.isoformat()], [f30.isoformat(), today.isoformat()]))
        json.dump(val, open('market-data/valuation.json', 'w'), separators=(',', ':'))
        print('valuation areas:', len(val['areas']), flush=True)
    except Exception as e:
        print('valuation stats skipped:', e, flush=True)
    print(json.dumps({k: out[k] for k in ('generated_at', 'dubai')}, indent=1))
    print(json.dumps(comm, indent=1))

if __name__ == '__main__':
    main()
