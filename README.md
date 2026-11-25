# plotmark.ae

Website for Plotmark Real Estate L.L.C, a boutique real estate brokerage in Dubai.

- `index.html` — the home page (brand: Plotmark Brand Book); `mortgages/` and `insights/` hold the other pages.
- `scripts/market/` — fetches Dubai Land Department open data and renders the market trends page.
- `.github/workflows/pages.yml` — publishes the site with GitHub Pages on every push to `main`,
  and refreshes the market data every Monday (or when a commit message contains `[market]`).

To update the site, edit the pages, commit and push to `main`. GitHub Pages republishes it in a minute or two.
