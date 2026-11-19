# scottluntz.com

Personal site for Scott Luntz's sports analytics work. Served by GitHub Pages
from the `docs/` folder of this repository.

| Path | What it is | Built from |
| --- | --- | --- |
| `/` | Home page | `src/index.html`, filled in by `build.py` |
| `/modern-pitch/` | *The Shape of the Modern Pitch* (paper) | `velo-vs-spin/site/` |
| `/pitch-shape-explorer/` | Pitch Shape Explorer (dashboard) | `velo-vs-spin/site-dashboard/` |

Those paths are permanent. Links to them are already in posts, the paper and
the README of the code repo, so add new paths rather than renaming these.

## Rebuilding

The paper and dashboard are built in the sibling
[modern-pitcher-evaluation](https://github.com/scobobo/modern-pitcher-evaluation)
checkout (`../velo-vs-spin`). Rebuild them there first, then:

```bash
python3 build.py
```

`build.py` copies them into `docs/`, renders the home page and its link-preview
card, and stops if anything would publish a `netlify.app` link or an email
address. Every number on the home page — the crossover chart, the
pitcher-season count, the backtest record — is read from the analysis output,
not typed. The preview card is rendered with headless Google Chrome.

Commit `docs/` and push; GitHub Pages republishes within a minute or two.

## Old addresses

The paper and dashboard used to live at
`the-shape-of-the-modern-pitch.netlify.app` and `pitch-shape-explorer.netlify.app`.
Those Netlify sites are kept alive as permanent redirects so links already
shared keep working. Their contents are in `netlify-redirects/`, one folder per
site, deployed by dragging the folder onto that site's Deploys page in Netlify.
Do not delete those Netlify sites.

## Licence

Paper text and figures: CC BY 4.0. Code: MIT. See the code repository.
