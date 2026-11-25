"""Render market/index.html from DLD data. Runs on every deploy.
Data comes from this pipeline's fetch job if it ran, otherwise from the live site's last data.json."""
import json, os, re, html, urllib.request, datetime as dt

def load():
    if os.path.exists('market-data/data.json'):
        return json.load(open('market-data/data.json')), 'fresh'
    try:
        with urllib.request.urlopen('https://plotmark.ae/market/data.json', timeout=30) as f:
            return json.load(f), 'previous'
    except Exception as e:
        print('no previous data:', e); return None, 'none'

def aed(n): return 'AED ' + f'{n:,.0f}' if n is not None else '–'
def num(n): return f'{n:,.0f}' if n is not None else '–'
def pct(n): return f'{n}%' if n is not None else '–'
def bn(n):
    if n is None: return '–'
    return f'AED {n/1e9:,.1f}bn' if n >= 1e9 else f'AED {n/1e6:,.0f}m'
def dlong(iso): return dt.date.fromisoformat(iso[:10]).strftime('%-d %B %Y')

def columns(months):
    W, H, L, B, T = 960, 300, 56, 34, 24
    vals = [m['sales'] for m in months]
    mx = max(vals) if vals else 1
    step = 5000 if mx > 15000 else (2000 if mx > 6000 else 1000)
    top = ((mx // step) + 1) * step
    n = len(months); slot = (W - L - 10) / max(n, 1); bw = min(24, slot * .45)
    y = lambda v: T + (H - T - B) * (1 - v / top)
    g = []
    for k in range(0, top + 1, step):
        yy = y(k); lab = f'{k//1000}K' if top >= 10000 and k else f'{k:,}'
        g.append(f'<line x1="{L}" x2="{W}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#E6E0D7" stroke-width="1"/><text x="{L-10}" y="{yy+4:.1f}" text-anchor="end" font-size="12" fill="#6B6259">{lab}</text>')
    imax = vals.index(mx) if vals else -1
    for i, m in enumerate(months):
        cx = L + slot * i + slot / 2; x = cx - bw / 2; yy = y(m['sales']); h = (H - B) - yy
        col = '#D2C5B3' if m.get('partial') else '#94590C'
        r = min(4, h)
        path = f'M{x:.1f},{H-B} V{yy+r:.1f} Q{x:.1f},{yy:.1f} {x+r:.1f},{yy:.1f} H{x+bw-r:.1f} Q{x+bw:.1f},{yy:.1f} {x+bw:.1f},{yy+r:.1f} V{H-B}Z' if h > 0 else ''
        tip = f"{m['label']}: {m['sales']:,} sales" + (' (month to date)' if m.get('partial') else '')
        g.append(f'<g class="bar"><title>{tip}</title><rect x="{cx-slot/2:.1f}" y="{T}" width="{slot:.1f}" height="{H-B-T}" fill="transparent"/><path d="{path}" fill="{col}"/></g>')
        g.append(f'<text x="{cx:.1f}" y="{H-B+20}" text-anchor="middle" font-size="12" fill="#6B6259">{m["label"]}</text>')
        if i in (imax, n - 1):
            g.append(f'<text x="{cx:.1f}" y="{yy-8:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="#2F2A25">{m["sales"]:,}</text>')
    g.append(f'<line x1="{L}" x2="{W}" y1="{H-B}" y2="{H-B}" stroke="#BDB3A7" stroke-width="1"/>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Registered property sales in Dubai by month this year" class="chart">{"".join(g)}</svg>'

def comm_rows(comm):
    mx = max([c['median_psf'] for c in comm if c['median_psf']] or [1])
    out = []
    for c in comm:
        w = 100 * (c['median_psf'] or 0) / mx
        bar = f'<span class="ib"><span style="width:{w:.0f}%"></span></span>' if c['median_psf'] else ''
        out.append(f'<tr><th scope="row">{html.escape(c["name"])}</th><td>{num(c["sales"])}</td><td class="psf">{bar}<b>{aed(c["median_psf"])}</b></td><td>{pct(c["offplan_share"])}</td><td>{aed(c["median_rent_flat"])}</td></tr>')
    return ''.join(out)

CSS = '''
.kpis5{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px}
.kpi{background:rgba(255,255,255,.82);border-radius:22px;padding:22px 22px 20px;box-shadow:0 18px 50px rgba(47,42,37,.06)}
.kpi dt{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--saffron-text);font-weight:600}
.kpi dd{margin:10px 0 0;font-size:clamp(1.5rem,2.4vw,2rem);font-weight:800;letter-spacing:-.04em;line-height:1.05}
.kpi small{display:block;margin-top:8px;font-size:12.5px;color:var(--muted);font-weight:400;letter-spacing:0}
.chart-card{background:rgba(255,255,255,.82);border-radius:28px;padding:clamp(20px,3vw,34px);box-shadow:0 18px 50px rgba(47,42,37,.06)}
.chart-card h2{font-size:clamp(1.4rem,2.4vw,1.8rem);letter-spacing:-.035em}
.chart-card .sub{color:var(--muted);font-size:14px;margin:6px 0 18px}
.chart{width:100%;height:auto;font-family:Sora,Arial,sans-serif}
.chart .bar:hover path{opacity:.8}
.legend-note{display:flex;flex-wrap:wrap;gap:16px;font-size:12.5px;color:var(--muted);margin-top:10px}
.legend-note i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.mtable{width:100%;border-collapse:collapse;font-size:15px}
.mtable th,.mtable td{padding:14px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.mtable th[scope=row],.mtable thead th:first-child{text-align:left;font-weight:600}
.mtable thead th{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--saffron-text);font-weight:600;white-space:normal;vertical-align:bottom}
.mtable .psf{display:flex;align-items:center;gap:10px;justify-content:flex-end}
.ib{display:inline-block;width:90px;height:8px;background:#EDE7DF;border-radius:4px;overflow:hidden}
.ib span{display:block;height:100%;background:#94590C;border-radius:0 4px 4px 0}
.scroll{overflow-x:auto}
.method{font-size:13.5px;color:var(--muted);line-height:1.7;max-width:56rem}
.method a{color:var(--charcoal)}
@media (max-width:1000px){.kpis5{grid-template-columns:repeat(2,minmax(0,1fr))}.kpis5 .kpi:first-child{grid-column:1/-1}}
@media (max-width:520px){.ib{width:50px}.mtable{font-size:14px}}
'''

def main():
    data, state = load()
    src = open('insights/index.html').read()
    head_tpl = src[:src.index('</head>')]
    style = re.search(r'<style>.*?</style>', head_tpl, flags=re.S).group(0).replace('</style>', CSS + '</style>')
    body = src[src.index('</head>'):]
    defs = re.search(r'<svg width="0" height="0".*?</svg>\n', body, flags=re.S).group(0)
    topbar = re.search(r'<div class="topbar">.*?</div>\n</div>\n', body, flags=re.S).group(0)
    header = re.search(r'<header class="site">.*?</header>', body, flags=re.S).group(0).replace('<a href="/market/">', '<a href="/market/" aria-current="page">')
    footer = re.search(r'<footer class="site">.*?</footer>', body, flags=re.S).group(0)
    menu_js = re.search(r"<script>\n\(function\(\)\{\n  var t=document.getElementById\('menu-toggle'\).*?</script>", body, flags=re.S).group(0)

    title = 'Dubai Property Market Trends (Updated Weekly) | Plotmark Real Estate'
    desc = 'Dubai property market trends from Dubai Land Department data, updated weekly: sales volumes, off-plan share, price per sq ft and rents in Dubai Marina, Downtown, Business Bay, JVC and more.'
    if data:
        d = data['dubai']; upd = dlong(data['generated_at'])
        p1 = f"{dlong(d['period_sales'][0])} – {dlong(d['period_sales'][1])}"
        p2 = f"{dlong(d['period_rents'][0])} – {dlong(d['period_rents'][1])}"
        ld = [{"@context": "https://schema.org", "@type": "Dataset", "name": "Dubai property market trends", "description": desc,
               "url": "https://plotmark.ae/market/", "dateModified": data['generated_at'][:10], "creator": {"@id": "https://plotmark.ae/#agency"},
               "isBasedOn": "https://dubailand.gov.ae/en/open-data/real-estate-data/", "spatialCoverage": "Dubai, United Arab Emirates", "license": "Dubai Land Department open data"},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://plotmark.ae/"}, {"@type": "ListItem", "position": 2, "name": "Market trends", "item": "https://plotmark.ae/market/"}]}]
        ym = [m for m in data['months']]
        tbl_months = ''.join(f"<tr><th scope='row'>{m['label']}{' (to date)' if m.get('partial') else ''}</th><td>{m['sales']:,}</td><td>{pct(round(100*m['offplan']/m['sales'])) if m.get('offplan') and m['sales'] else '–'}</td></tr>" for m in ym)
        content = f'''
<section class="block" style="padding-top:0" aria-label="Headline figures">
  <div class="wrap">
    <dl class="kpis5">
      <div class="kpi"><dt>Sales, last 90 days</dt><dd>{num(d['sales_count'])}</dd><small>registered sale transactions</small></div>
      <div class="kpi"><dt>Sales value</dt><dd>{bn(d['sales_value'])}</dd><small>last 90 days</small></div>
      <div class="kpi"><dt>Off-plan share</dt><dd>{pct(d['offplan_share'])}</dd><small>of sales, last 90 days</small></div>
      <div class="kpi"><dt>Price per sq ft</dt><dd>{aed(d['median_psf_units'])}</dd><small>median, apartments and units</small></div>
      <div class="kpi"><dt>Annual rent</dt><dd>{aed(d['median_rent_flats'])}</dd><small>median, flats, last 30 days</small></div>
    </dl>
  </div>
</section>
<section class="block" style="padding-top:0" aria-labelledby="c1">
  <div class="wrap">
    <div class="chart-card">
      <h2 id="c1">Registered sales by month, {data['months'][0]['month'][:4]}</h2>
      <p class="sub">All property sale transactions registered with the Dubai Land Department.</p>
      {columns(ym)}
      <p class="legend-note"><span><i style="background:#94590C"></i>Full month</span><span><i style="background:#D2C5B3"></i>Month to date</span></p>
      <details style="margin-top:14px"><summary style="cursor:pointer;font-size:14px;font-weight:600">View as table</summary>
        <div class="scroll"><table class="mtable" style="margin-top:10px"><thead><tr><th>Month</th><th>Sales</th><th>Off-plan share</th></tr></thead><tbody>{tbl_months}</tbody></table></div>
      </details>
    </div>
  </div>
</section>
<section class="block" style="padding-top:0" aria-labelledby="c2">
  <div class="wrap">
    <div class="chart-card">
      <h2 id="c2">Communities we cover</h2>
      <p class="sub">Sales and prices: {p1}. Rents: {p2}. Medians shown where there are at least 10 records.</p>
      <div class="scroll"><table class="mtable">
        <thead><tr><th>Community</th><th>Sales</th><th>Median price per sq ft (units)</th><th>Off-plan share</th><th>Median annual rent (flats)</th></tr></thead>
        <tbody>{comm_rows(data['communities'])}</tbody>
      </table></div>
    </div>
  </div>
</section>'''
        status = f'Updated {upd}. Refreshed every week from Dubai Land Department open data.'
    else:
        ld = []; content = '<section class="block" style="padding-top:0"><div class="wrap"><div class="chart-card"><h2>Market data is being updated.</h2><p class="sub">Please check back shortly.</p></div></div></section>'
        status = 'Refreshed every week from Dubai Land Department open data.'

    ldt = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in ld)
    head = re.sub(r'<title>.*?</title>', f'<title>{html.escape(title)}</title>', head_tpl, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{html.escape(desc)}">', head)
    head = head.replace('https://plotmark.ae/insights/"', 'https://plotmark.ae/market/"')
    head = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="Dubai property market trends, updated weekly | Plotmark">', head)
    head = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{html.escape(desc)}">', head)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>\n', '', head, flags=re.S)
    head = re.sub(r'<style>.*?</style>', lambda m: style, head, flags=re.S)
    head = head.replace('<link rel="preconnect" href="https://fonts.googleapis.com">', ldt + '<link rel="preconnect" href="https://fonts.googleapis.com">', 1)

    main_html = f'''<main id="top">
<div class="wrap crumbs"><a href="/">Home</a> / Market trends</div>
<section class="m-hero" aria-labelledby="mk-title">
  <div class="wrap">
    <h1 class="eyebrow" id="mk-title">Dubai property market trends</h1>
    <p class="display">The market, <span class="l">in numbers</span><span style="color:var(--saffron)">.</span></p>
    <p class="lead">Sales, prices and rents across Dubai and the communities Plotmark covers, from official Dubai Land Department records. {status}</p>
  </div>
</section>
{content}
<section class="block" style="padding-top:0" aria-labelledby="mm">
  <div class="wrap">
    <h2 id="mm" class="eyebrow" style="margin-bottom:14px">How these figures are made</h2>
    <p class="method">Source: <a href="https://dubailand.gov.ae/en/open-data/real-estate-data/" rel="noopener">Dubai Land Department open data</a>, which DLD publishes for the current calendar year. Sales are registered sale transactions (ready and off-plan); prices per square foot use the registered value and actual area of units, and medians reduce the effect of unusual deals. Rents are annual amounts on Ejari-registered tenancy contracts for flats, new and renewed. Communities follow DLD area names (for example Marsa Dubai for Dubai Marina, Burj Khalifa for Downtown Dubai, and Al Barsha South Fourth for Jumeirah Village Circle), so boundaries can differ from marketing names. Recent records can still be added after publication. Figures are for general information only and are not a valuation or investment advice.</p>
  </div>
</section>
<section class="block" style="padding-top:0" aria-label="Next step">
  <div class="wrap"><div class="cta-line"><h2>Want the numbers for a specific building? <span style="font-weight:300">Ask us.</span></h2><a class="btn btn-ink" href="/#contact">Send an enquiry</a></div></div>
</section>
</main>'''
    page = head + '</head>\n<body>\n\n' + defs + topbar + '\n' + header + '\n\n' + main_html + '\n\n' + footer + '\n\n' + menu_js + '\n</body>\n</html>\n'
    os.makedirs('market', exist_ok=True)
    open('market/index.html', 'w').write(page)
    if data: json.dump(data, open('market/data.json', 'w'))
    print('rendered market page from', state, 'data')

if __name__ == '__main__':
    main()
