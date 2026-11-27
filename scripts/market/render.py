"""Render market/index.html and valuation/index.html from DLD data. Runs on every deploy.
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

def columns(months, W=960, H=300, cls='chart'):
    L, B, T = (56, 34, 24) if W > 600 else (40, 30, 22)
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
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Registered property sales in Dubai by month this year" class="{cls}">{"".join(g)}</svg>'

def comm_rows(comm):
    mx = max([c['median_psf'] for c in comm if c['median_psf']] or [1])
    out = []
    for c in comm:
        w = 100 * (c['median_psf'] or 0) / mx
        bar = f'<span class="ib"><span style="width:{w:.0f}%"></span></span>' if c['median_psf'] else ''
        out.append(f'<tr><th scope="row">{html.escape(c["name"])}</th><td data-l="Sales">{num(c["sales"])}</td><td class="psf" data-l="Price per sq ft">{bar}<b>{aed(c["median_psf"])}</b></td><td data-l="Off-plan">{pct(c["offplan_share"])}</td><td data-l="Annual rent (flat)">{aed(c["median_rent_flat"])}</td></tr>')
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
.chart-m{display:none}
@media (max-width:640px){.chart:not(.chart-m){display:none}.chart-m{display:block}
.mtable.cm thead{display:none}.mtable.cm,.mtable.cm tbody,.mtable.cm tr{display:block}
.mtable.cm tr{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px;padding:16px 0;border-bottom:1px solid var(--line)}
.mtable.cm th[scope=row]{grid-column:1/-1;border:0;padding:0;font-size:16px}
.mtable.cm td{border:0;padding:0;text-align:left;white-space:normal;display:block;font-size:15px;font-weight:600}
.mtable.cm td::before{content:attr(data-l);display:block;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--saffron-text);font-weight:600;margin-bottom:3px}
.mtable.cm .psf{display:block}.mtable.cm .ib{display:none}}
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
    desc = 'Dubai property sales, prices per sq ft and rents by community, updated weekly from Dubai Land Department data: Dubai Marina, Downtown, Business Bay, JVC and more.'
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
      {columns(ym)}{columns(ym, 380, 260, 'chart chart-m')}
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
      <div class="scroll"><table class="mtable cm">
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
    try:
        valuation_page(data)
    except Exception as e:
        print('valuation page skipped:', e)
    try:
        homepage(data)
    except Exception as e:
        print('homepage market band skipped:', e)

# ====================== Valuation page: "What's my property worth?" ======================
VCSS = '''
.v-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:22px;align-items:start}
.v-card{background:rgba(255,255,255,.86);border-radius:28px;padding:clamp(20px,3vw,32px);box-shadow:0 18px 50px rgba(47,42,37,.06)}
.v-card h2{font-size:clamp(1.3rem,2.2vw,1.7rem);letter-spacing:-.035em;margin:0 0 4px}
.v-card .sub{color:var(--muted);font-size:14px;margin:0 0 18px}
.vf{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.vf label{display:flex;flex-direction:column;gap:6px;font-size:13px;font-weight:600;color:var(--charcoal)}
.vf .full{grid-column:1/-1}
.vf input,.vf select{font:inherit;font-weight:400;font-size:15.5px;padding:13px 14px;border:1px solid var(--line);border-radius:14px;background:#fff;color:var(--charcoal);width:100%}
.vf input:focus,.vf select:focus{outline:2px solid var(--saffron);outline-offset:1px}
.seg2{display:flex;gap:6px;flex-wrap:wrap}
.seg2 button{font:inherit;font-size:14px;padding:10px 14px;border-radius:999px;border:1px solid var(--line);background:#fff;cursor:pointer;color:var(--charcoal)}
.seg2 button[aria-pressed=true]{background:var(--charcoal);color:var(--paper);border-color:var(--charcoal)}
.v-est .range{font-size:clamp(1.9rem,4vw,2.8rem);font-weight:800;letter-spacing:-.045em;line-height:1.05;margin:6px 0 4px}
.v-est .mid{font-size:15px;color:var(--muted)}
.v-bar{position:relative;height:10px;border-radius:6px;background:linear-gradient(90deg,#EDE7DF,#D2C5B3 35%,#E8A33D 50%,#D2C5B3 65%,#EDE7DF);margin:18px 0 6px}
.v-bar i{position:absolute;top:-5px;width:4px;height:20px;border-radius:2px;background:var(--charcoal);left:50%}
.v-scale{display:flex;justify-content:space-between;font-size:12px;color:var(--muted)}
.v-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:20px 0 0;padding:0}
.v-facts div{background:var(--paper);border-radius:16px;padding:12px 14px}
.v-facts dt{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--saffron-text);font-weight:600}
.v-facts dd{margin:4px 0 0;font-weight:700;font-size:15.5px}
.v-basis{font-size:13px;color:var(--muted);margin:14px 0 0;line-height:1.6}
.v-empty{color:var(--muted);font-size:15px;line-height:1.7}
.v-lead{margin-top:22px;padding-top:20px;border-top:1px solid var(--line)}
.v-lead h3{font-size:17px;margin:0 0 4px;letter-spacing:-.02em}
.v-lead p{font-size:14px;color:var(--muted);margin:0 0 14px}
.v-note{font-size:13.5px;min-height:1.2em;color:var(--muted)}
.v-thanks{background:var(--paper);border-radius:16px;padding:16px;font-size:15px}
.method{font-size:13.5px;color:var(--muted);line-height:1.7;max-width:56rem}
.method a{color:var(--charcoal)}
@media (max-width:900px){.v-grid{grid-template-columns:1fr}}
@media (max-width:560px){.vf{grid-template-columns:1fr}.v-facts{grid-template-columns:1fr 1fr}}
'''

VJS = r'''
(function(){
  var D=JSON.parse(document.getElementById('vdata').textContent||'null');
  var CRM_URL='https://xkyxwfdgnkvmmwanegax.supabase.co',CRM_KEY='sb_publishable_haAnDdVKW9zlIZZa32TQHw_lWCAjMmF';
  var $=function(s){return document.querySelector(s)};
  var st={type:'Apartment',beds:'2',status:'ready'};
  function aed(n){return 'AED '+Math.round(n).toLocaleString('en-US')}
  function short(n){return n>=1e6?'AED '+(n/1e6).toFixed(2).replace(/\.?0+$/,'')+'M':'AED '+Math.round(n/1e3)+'K'}
  function fd(s){var m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],p=String(s).split('-');return +p[2]+' '+m[+p[1]-1]+' '+p[0]}
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  if(!D||!D.areas||!D.areas.length){$('#v-out').innerHTML='<p class="v-empty">The valuation figures are being refreshed from Dubai Land Department data. Please check back shortly, or send us your details below and we will prepare a valuation for you.</p>';}
  else{
    var sel=$('#v-area'),pop=[],rest=[];
    D.areas.forEach(function(a,i){(a.label.indexOf('(')>0||i<12?pop:rest).push(a)});
    rest.sort(function(a,b){return a.label.localeCompare(b.label)});
    function opts(list){return list.map(function(a){return '<option value="'+esc(a.name)+'">'+esc(a.label)+'</option>'}).join('')}
    sel.innerHTML='<option value="">Choose a community</option><optgroup label="Most traded">'+opts(pop)+'</optgroup><optgroup label="All areas, A to Z">'+opts(rest)+'</optgroup>';
  }
  document.querySelectorAll('.seg2').forEach(function(g){g.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
    g.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});st[g.dataset.k]=b.dataset.v;calc()})});
  ['#v-area','#v-size'].forEach(function(s){$(s).addEventListener('input',calc)});
  var last=null;
  function pick(a){
    var b=st.beds,t=st.type,s=st.status,g=a.g,tries=[[t,b,s,'similar '+(b==='Studio'?'studio':b+'-bedroom')+' '+t.toLowerCase()+'s'],[t,b,'all','similar '+(b==='Studio'?'studio':b+'-bedroom')+' '+t.toLowerCase()+'s (ready and off-plan)'],[t,'any',s,'all '+t.toLowerCase()+'s'],[t,'any','all','all '+t.toLowerCase()+'s (ready and off-plan)']];
    for(var i=0;i<tries.length;i++){var k=tries[i][0]+'|'+tries[i][1]+'|'+tries[i][2];if(g[k])return {q:g[k],what:tries[i][3],exact:i===0}}
    return null;
  }
  function calc(){
    if(!D||!D.areas)return;
    var a=D.areas.filter(function(x){return x.name===$('#v-area').value})[0],size=+$('#v-size').value,out=$('#v-out');
    if(!a){out.innerHTML='<p class="v-empty">Choose a community, property type, bedrooms and size to see what similar homes have actually sold for.</p>';last=null;return}
    var m=pick(a);
    if(!m){out.innerHTML='<p class="v-empty">Not enough recent '+st.type.toLowerCase()+' sales in '+esc(a.label)+' to give a fair range. Send us your details below and we will check the comparable sales for you.</p>';last=null;return}
    var q=m.q,sz=size>=150&&size<=50000?size:q.size,lo=q.p25*sz,mid=q.med*sz,hi=q.p75*sz;
    var r=a.r[st.type+'|'+st.beds]||null,yieldTxt='–';
    if(r&&st.status==='ready'&&q.price){yieldTxt=(100*r.med/q.price).toFixed(1)+'%'}
    last={area:a.label,type:st.type,beds:st.beds,status:st.status,size:sz,lo:lo,mid:mid,hi:hi};
    out.innerHTML='<div class="v-est"><p class="eyebrow">Estimated value</p><p class="range">'+short(lo)+' – '+short(hi)+'</p><p class="mid">Middle of the range: <b>'+aed(mid)+'</b>'+(size?'':' (for a typical '+Math.round(q.size).toLocaleString('en-US')+' sq ft)')+'</p>'+
      '<div class="v-bar" aria-hidden="true"><i></i></div><div class="v-scale"><span>Lower quarter of sales</span><span>Upper quarter</span></div>'+
      '<dl class="v-facts"><div><dt>Price per sq ft</dt><dd>'+aed(q.med)+'</dd></div><div><dt>Sales compared</dt><dd>'+q.n.toLocaleString('en-US')+'</dd></div><div><dt>'+(r?'Typical rent / year':'Typical size')+'</dt><dd>'+(r?aed(r.med):Math.round(q.size).toLocaleString('en-US')+' sq ft')+'</dd></div></dl>'+
      (r&&st.status==='ready'?'<p class="v-basis">Indicative gross rental yield: <b>'+yieldTxt+'</b> (typical annual rent of '+aed(r.med)+' from '+r.n+' Ejari contracts, against the typical sale price of '+aed(q.price)+').</p>':'')+
      '<p class="v-basis">Based on '+q.n+' registered sales of '+m.what+' in '+esc(a.label)+' between '+fd(D.period_sales[0])+' and '+fd(D.period_sales[1])+'. The range runs from the lower to the upper quarter of prices per sq ft, applied to your size.'+(m.exact?'':' There were too few exact matches, so the comparison is wider.')+'</p></div>';
  }
  calc();
  var f=$('#v-form');
  f.addEventListener('submit',function(e){
    e.preventDefault();var note=$('#v-note'),btn=f.querySelector('button[type=submit]');
    var fd=new FormData(f);if((fd.get('_gotcha')||'').trim())return;
    var name=(fd.get('name')||'').trim(),email=(fd.get('email')||'').trim();
    if(name.length<2||!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){note.textContent='Please add your name and a valid email.';return}
    var why=fd.get('goal')||'Sell';
    var det=last?('Valuation request: '+last.type+', '+(last.beds==='Studio'?'studio':last.beds+' bedrooms')+', '+Math.round(last.size)+' sq ft, '+last.status+', '+last.area+'. Online estimate '+aed(last.lo)+' – '+aed(last.hi)+' (middle '+aed(last.mid)+').'):('Valuation request: '+($('#v-area').value||'area not chosen')+'.');
    var msg=det+((fd.get('message')||'').trim()?'\n'+fd.get('message').trim():'');
    btn.disabled=true;btn.textContent='Sending…';note.textContent='';
    var mail=new FormData();mail.append('_subject','Valuation request from plotmark.ae');mail.append('name',name);mail.append('email',email);mail.append('phone',fd.get('phone')||'');mail.append('interest',why==='Let'?'Letting my property':(why==='Sell'?'Selling my property':'Valuation only'));mail.append('message',msg);
    var p1=fetch('https://formspree.io/f/xvkadeey',{method:'POST',body:mail,headers:{'Accept':'application/json'}}).then(function(r){return r.ok}).catch(function(){return false});
    var p2=fetch(CRM_URL+'/rest/v1/rpc/submit_website_lead',{method:'POST',headers:{'Content-Type':'application/json','apikey':CRM_KEY,'Authorization':'Bearer '+CRM_KEY},
      body:JSON.stringify({p_name:name,p_email:email,p_phone:fd.get('phone')||null,p_interest:why==='Let'?'Let':'Sell',p_message:msg,p_page:location.pathname})}).then(function(r){return r.ok}).catch(function(){return false});
    Promise.all([p1,p2]).then(function(r){
      if(r[0]||r[1]){f.outerHTML='<div class="v-thanks"><b>Thank you.</b> We have your request and will reply by email with a valuation based on the latest comparable sales.</div>'}
      else{btn.disabled=false;btn.textContent='Request my valuation';note.textContent='Sorry, that did not send. Please email enquiries@plotmark.ae.'}
    });
  });
})();
'''

def load_valuation(market):
    if os.path.exists('market-data/valuation.json'):
        return json.load(open('market-data/valuation.json')), 'fresh'
    try:
        with urllib.request.urlopen('https://plotmark.ae/valuation/data.json', timeout=30) as f:
            return json.load(f), 'previous'
    except Exception as e:
        print('no previous valuation data:', e)
    if market and market.get('communities'):   # fallback: community medians only
        areas = [{'name': c['name'], 'label': c['name'], 'sales': c['sales'],
                  'g': {'Apartment|any|all': {'n': c['sales'], 'p25': round(c['median_psf'] * .9), 'med': c['median_psf'],
                                              'p75': round(c['median_psf'] * 1.1), 'size': 900, 'price': 0}}, 'r': {}}
                 for c in market['communities'] if c.get('median_psf')]
        return {'period_sales': market['dubai']['period_sales'], 'areas': areas, 'fallback': True}, 'fallback'
    return None, 'none'

def valuation_page(market):
    data, state = load_valuation(market)
    src = open('insights/index.html').read()
    head_tpl = src[:src.index('</head>')]
    style = re.search(r'<style>.*?</style>', head_tpl, flags=re.S).group(0).replace('</style>', VCSS + '</style>')
    body = src[src.index('</head>'):]
    defs = re.search(r'<svg width="0" height="0".*?</svg>\n', body, flags=re.S).group(0)
    topbar = re.search(r'<div class="topbar">.*?</div>\n</div>\n', body, flags=re.S).group(0)
    header = re.search(r'<header class="site">.*?</header>', body, flags=re.S).group(0).replace('<a href="/valuation/">', '<a href="/valuation/" aria-current="page">')
    footer = re.search(r'<footer class="site">.*?</footer>', body, flags=re.S).group(0)
    menu_js = re.search(r"<script>\n\(function\(\)\{\n  var t=document.getElementById\('menu-toggle'\).*?</script>", body, flags=re.S).group(0)
    title = "What's My Property Worth? Dubai Valuation from DLD Sales | Plotmark"
    desc = 'Free, instant estimate of your Dubai property value from real Dubai Land Department sales: price per sq ft, comparable sales and rental yield by community and bedrooms.'
    ld = [{"@context": "https://schema.org", "@type": "WebApplication", "name": "Plotmark property valuation", "url": "https://plotmark.ae/valuation/",
           "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "description": desc, "isAccessibleForFree": True,
           "provider": {"@id": "https://plotmark.ae/#agency"}, "isBasedOn": "https://dubailand.gov.ae/en/open-data/real-estate-data/"},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://plotmark.ae/"}, {"@type": "ListItem", "position": 2, "name": "Property valuation", "item": "https://plotmark.ae/valuation/"}]}]
    ldt = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in ld)
    head = re.sub(r'<title>.*?</title>', f'<title>{html.escape(title)}</title>', head_tpl, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{html.escape(desc)}">', head)
    head = head.replace('https://plotmark.ae/insights/"', 'https://plotmark.ae/valuation/"')
    head = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="What is my Dubai property worth? | Plotmark">', head)
    head = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{html.escape(desc)}">', head)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>\n', '', head, flags=re.S)
    head = re.sub(r'<style>.*?</style>', lambda m: style, head, flags=re.S)
    head = head.replace('<link rel="preconnect" href="https://fonts.googleapis.com">', ldt + '<link rel="preconnect" href="https://fonts.googleapis.com">', 1)
    upd = f"Figures updated {dlong(data['generated_at'])} from Dubai Land Department data." if data and data.get('generated_at') else 'Figures from Dubai Land Department data, refreshed weekly.'
    vjson = json.dumps(data or None, separators=(',', ':')).replace('<', '\\u003c')
    bed_btns = ''.join(f'<button type="button" data-v="{b}" aria-pressed="{"true" if b == "2" else "false"}">{b if b != "Studio" else "Studio"}</button>' for b in ['Studio', '1', '2', '3', '4', '5+'])
    main_html = f'''<main id="top">
<div class="wrap crumbs"><a href="/">Home</a> / Property valuation</div>
<section class="m-hero" aria-labelledby="v-title">
  <div class="wrap">
    <h1 class="eyebrow" id="v-title">Dubai property valuation</h1>
    <p class="display">What is your home <span class="l">really worth</span><span style="color:var(--saffron)">?</span></p>
    <p class="lead">An instant estimate from what similar homes actually sold for, using registered Dubai Land Department sales, not asking prices. {upd}</p>
  </div>
</section>
<section class="block" style="padding-top:0" aria-label="Valuation calculator">
  <div class="wrap v-grid">
    <div class="v-card">
      <h2>Your property</h2><p class="sub">Four details. No sign-up.</p>
      <div class="vf">
        <label class="full">Community<select id="v-area"><option value="">Loading…</option></select></label>
        <div class="full"><span style="font-size:13px;font-weight:600">Type</span><div class="seg2" data-k="type" style="margin-top:6px"><button type="button" data-v="Apartment" aria-pressed="true">Apartment</button><button type="button" data-v="Villa" aria-pressed="false">Villa / townhouse</button></div></div>
        <div class="full"><span style="font-size:13px;font-weight:600">Bedrooms</span><div class="seg2" data-k="beds" style="margin-top:6px">{bed_btns}</div></div>
        <label>Size (sq ft)<input id="v-size" type="number" inputmode="numeric" min="150" max="50000" placeholder="e.g. 1,250"></label>
        <div><span style="font-size:13px;font-weight:600">Status</span><div class="seg2" data-k="status" style="margin-top:6px"><button type="button" data-v="ready" aria-pressed="true">Ready</button><button type="button" data-v="offplan" aria-pressed="false">Off-plan</button></div></div>
      </div>
    </div>
    <div class="v-card" aria-live="polite">
      <div id="v-out"><p class="v-empty">Choose a community, property type, bedrooms and size to see what similar homes have actually sold for.</p></div>
      <div class="v-lead">
        <h3>Want a precise valuation?</h3>
        <p>We check the exact building, floor, view and recent comparable sales, and reply by email.</p>
        <form id="v-form" class="vf" novalidate>
          <p hidden><label>Leave this empty<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label></p>
          <label>Full name<input name="name" autocomplete="name" required></label>
          <label>Email<input name="email" type="email" autocomplete="email" required></label>
          <label>Phone (optional)<input name="phone" type="tel" autocomplete="tel"></label>
          <label>I'm thinking of<select name="goal"><option value="Sell">Selling</option><option value="Let">Letting</option><option value="Value">Just knowing the value</option></select></label>
          <label class="full">Building or anything else (optional)<input name="message" placeholder="e.g. Marina Gate 1, high floor, sea view"></label>
          <div class="full" style="display:flex;flex-wrap:wrap;align-items:center;gap:14px"><button class="btn btn-ink" type="submit">Request my valuation</button><span class="v-note" id="v-note" role="status"></span></div>
        </form>
      </div>
    </div>
  </div>
</section>
<section class="block" style="padding-top:0" aria-labelledby="vm">
  <div class="wrap">
    <h2 id="vm" class="eyebrow" style="margin-bottom:14px">How this estimate is made</h2>
    <p class="method">Source: <a href="https://dubailand.gov.ae/en/open-data/real-estate-data/" rel="noopener">Dubai Land Department open data</a>, registered sales over the last 90 days and Ejari rental contracts over the last 30 days, refreshed every week. We compare homes of the same type and bedrooms in the same DLD area (ready or off-plan); the range is the lower to upper quarter of prices per square foot, applied to your size. Where there are too few matches, the comparison widens and says so. Areas follow DLD names, so boundaries can differ from marketing names. This is an indicative estimate for general information, not a formal valuation or investment advice; formal valuations are carried out by RERA-certified valuers.</p>
  </div>
</section>
</main>
<script type="application/json" id="vdata">{vjson}</script>
<script>{VJS}</script>'''
    page = head + '</head>\n<body>\n\n' + defs + topbar + '\n' + header + '\n\n' + main_html + '\n\n' + footer + '\n\n' + menu_js + '\n</body>\n</html>\n'
    os.makedirs('valuation', exist_ok=True)
    open('valuation/index.html', 'w').write(page)
    if data and not data.get('fallback'): json.dump(data, open('valuation/data.json', 'w'), separators=(',', ':'))
    print('rendered valuation page from', state, 'data')

# ====================== Homepage: live market band and price ticker ======================
def spark(months, W=320, H=110):
    vals = [m['sales'] for m in months] or [0]
    mx = max(vals) or 1; n = len(months); slot = W / max(n, 1); bw = min(16, slot * .55)
    g = []
    for i, m in enumerate(months):
        h = (H - 22) * m['sales'] / mx; x = slot * i + (slot - bw) / 2; y = H - 18 - h
        col = '#D2C5B3' if m.get('partial') else ('#E8A33D' if i == n - 1 or (i == n - 2 and months[-1].get('partial')) else '#94590C')
        g.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="{col}"><title>{m["label"]}: {m["sales"]:,} sales</title></rect>')
        g.append(f'<text x="{x + bw / 2:.1f}" y="{H - 4}" text-anchor="middle" font-size="10" fill="#6B6259">{m["label"][0]}</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Registered sales in Dubai by month this year">{"".join(g)}</svg>'

def homepage(data):
    if not data or not os.path.exists('index.html'): return
    s = open('index.html').read()
    if '<!--PULSE-->' not in s: return
    d = data['dubai']; months = data.get('months') or []
    full = [m for m in months if not m.get('partial')]
    chg = ''
    if len(full) >= 2 and full[-2]['sales']:
        pc = 100 * (full[-1]['sales'] - full[-2]['sales']) / full[-2]['sales']
        cls = 'up' if pc >= 0 else 'down'; arrow = '▲' if pc >= 0 else '▼'
        chg = f'<p class="chg"><b>{full[-1]["sales"]:,}</b> sales in {dt.date.fromisoformat(full[-1]["month"] + "-01").strftime("%B")} <span class="{cls}">{arrow} {abs(pc):.0f}%</span> vs {dt.date.fromisoformat(full[-2]["month"] + "-01").strftime("%B")}</p>'
    ytd = sum(m['sales'] for m in months)
    upd = dlong(data['generated_at'])
    block = f'''<!--PULSE-->
<section class="pulse" aria-labelledby="pulse-title">
  <div class="wrap">
    <div class="pulse-card">
      <div class="pulse-top"><div><p class="eyebrow pulse-live">Dubai market this week</p><h2 id="pulse-title">Every sale and rent, from the Land Department.</h2></div><span class="src">Updated {upd} · Source: Dubai Land Department</span></div>
      <div class="pulse-grid">
        <dl class="pulse-stats">
          <div><dt>Sales</dt><dd>{num(d['sales_count'])}</dd><small>last 90 days</small></div>
          <div><dt>Value</dt><dd>{bn(d['sales_value'])}</dd><small>last 90 days</small></div>
          <div><dt>Off-plan</dt><dd>{pct(d['offplan_share'])}</dd><small>of sales</small></div>
          <div><dt>Price / sq ft</dt><dd>{aed(d['median_psf_units'])}</dd><small>median, apartments</small></div>
          <div><dt>Rent / year</dt><dd>{aed(d['median_rent_flats'])}</dd><small>median flat, new contracts</small></div>
          <div><dt>Sales this year</dt><dd>{num(ytd)}</dd><small>since 1 January</small></div>
        </dl>
        <div class="pulse-chart"><span class="lbl">Sales by month</span>{chg}{spark(months)}</div>
      </div>
      <div class="pulse-links"><a href="/market/">Prices and rents by community →</a><a href="/valuation/">What is your home worth? →</a></div>
    </div>
  </div>
</section>
<!--/PULSE-->'''
    s = re.sub(r'<!--PULSE-->.*?<!--/PULSE-->', lambda m: block, s, flags=re.S)
    comm = [c for c in data.get('communities', []) if c.get('median_psf')]
    if comm and '<!--TICKER-->' in s:
        pin = '<svg width="18" height="18" viewBox="0 0 34 34" aria-hidden="true"><use href="#pin" fill="#E8A33D"/></svg>'
        items = ''.join(f'<span><b>{html.escape(c["name"].split(" ")[0])}</b> {html.escape(" ".join(c["name"].split(" ")[1:]))} <small style="font-size:.6em;font-weight:600;color:var(--saffron-text);letter-spacing:0">AED {c["median_psf"]:,}/sq ft</small>{pin}</span>' for c in comm)
        s = re.sub(r'<!--TICKER-->.*?<!--/TICKER-->', lambda m: '<!--TICKER-->' + items + items + '<!--/TICKER-->', s, flags=re.S)
    open('index.html', 'w').write(s)
    print('homepage market band updated')

if __name__ == '__main__':
    main()
