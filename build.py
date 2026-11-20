"""Build scottluntz.com into docs/, which GitHub Pages serves.

The paper and dashboard are built in the sibling velo-vs-spin project and
copied in here. Every number on the home page is read from that project's
output files rather than typed, so the page cannot drift from the work:

    velo-vs-spin/output/paper/sample_size_crossover.csv    the hero chart
    velo-vs-spin/output/dashboard/pitcher_seasons.json     pitcher-season count
    velo-vs-spin/output/leaderboard/backtest_FF_whiff_rate.csv   backtest record

Run after rebuilding the paper (build_standalone.py) and the dashboard
(build_dashboard.py) over there:

    python3 build.py
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DOCS = ROOT / "docs"
WORK = ROOT.parent / "velo-vs-spin"

DOMAIN = "scottluntz.com"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Built folder in velo-vs-spin -> path on the site. Changing a path breaks
# every link already shared, so add new ones rather than renaming these.
SECTIONS = {
    "site": "modern-pitch",
    "site-dashboard": "pitch-shape-explorer",
}

# Shown in the "Now" line and the footer. Set by hand when the page's content
# changes, so rebuilding without changes leaves the page byte-identical.
UPDATED = "November 2026"

LINKEDIN = "https://www.linkedin.com/in/scott-luntz-a1b3a6142/"
GITHUB = "https://github.com/scobobo"
PAPER_DOI = "10.5281/zenodo.22037431"


def crossover() -> tuple[str, int]:
    """The hero chart as inline SVG, and the crossover point in pitches."""
    path = WORK / "output" / "paper" / "sample_size_crossover.csv"
    with path.open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["target"] == "whiff rate"]
    # Up to 500 pitches, matching the one-pager's published figure. The
    # 1,000-pitch bucket has only 380 pitcher pairs.
    rows = [r for r in rows if int(r["min_pitches"]) <= 500]
    rows.sort(key=lambda r: int(r["min_pitches"]))
    n = [int(r["min_pitches"]) for r in rows]
    shape = [float(r["shape_r2"]) for r in rows]
    results = [float(r["past_results_r2"]) for r in rows]

    # Where results overtake ball flight, interpolated on the log scale the
    # chart is drawn on.
    cross_n = None
    for i in range(len(n) - 1):
        d0, d1 = shape[i] - results[i], shape[i + 1] - results[i + 1]
        if d0 > 0 >= d1:
            frac = d0 / (d0 - d1)
            lx = math.log2(n[i]) + frac * (math.log2(n[i + 1]) - math.log2(n[i]))
            cross_n = 2 ** lx
            break
    if cross_n is None:
        raise SystemExit("no crossover in the data -- the hero chart would be wrong")
    cross_label = int(round(cross_n / 10) * 10)

    W, H = 600, 330
    l, r, t, b = 44, 16, 40, 56
    w, h = W - l - r, H - t - b
    ymax = 0.40
    lo, hi = math.log2(n[0]), math.log2(n[-1])

    def X(v: float) -> float:
        return l + (math.log2(v) - lo) / (hi - lo) * w

    def Y(v: float) -> float:
        return t + h * (1 - v / ymax)

    def path(vals: list[float]) -> str:
        return " ".join(("M" if i == 0 else "L") + f"{X(a):.1f} {Y(v):.1f}"
                        for i, (a, v) in enumerate(zip(n, vals)))

    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" '
           'aria-labelledby="xo-title xo-desc">',
           '<title id="xo-title">Ball flight against results, by pitches seen</title>',
           f'<desc id="xo-desc">Predicting next-season whiff rate, ball flight stays near '
           f'{min(shape):.2f} to {max(shape):.2f} from {n[0]} to {n[-1]} pitches, while past '
           f'results rise from {results[0]:.2f} to {results[-1]:.2f}, overtaking ball flight '
           f'at about {cross_label} pitches.</desc>']

    for v in (0.1, 0.2, 0.3, 0.4):
        out.append(f'<line class="grid" x1="{l}" x2="{l + w}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
    out.append(f'<line class="baseline" x1="{l}" x2="{l + w}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/>')
    for v in (0, 0.1, 0.2, 0.3, 0.4):
        label = "0" if v == 0 else f"{v:.2f}".lstrip("0")
        # Hidden at phone width: the in-between ticks crowd, and "0" collides
        # with the first x label in the corner.
        cls = ' class="tick-mid"' if v in (0, 0.1, 0.3) else ""
        out.append(f'<text{cls} x="{l - 8}" y="{Y(v):.1f}" dy="0.35em" text-anchor="end">{label}</text>')
    out.append(f'<text x="{l}" y="{t - 18}">Predictive power, R²</text>')
    for v in n:
        out.append(f'<text x="{X(v):.1f}" y="{t + h + 24}" text-anchor="middle">{v}</text>')
    out.append(f'<text x="{l + w / 2:.1f}" y="{H - 4}" text-anchor="middle">Four-seam fastballs seen</text>')

    xc = X(cross_n)
    out.append(f'<line class="cross late" x1="{xc:.1f}" x2="{xc:.1f}" y1="{t}" y2="{t + h}"/>')
    out.append(f'<text class="lbl lbl-cross late" x="{xc + 8:.1f}" y="{t + 14}">About {cross_label} pitches</text>')

    out.append(f'<path class="line shape" pathLength="1" d="{path(shape)}"/>')
    out.append(f'<path class="line results" pathLength="1" d="{path(results)}"/>')
    out.append(f'<circle class="dot-shape late" cx="{X(n[-1]):.1f}" cy="{Y(shape[-1]):.1f}" r="5"/>')
    out.append(f'<circle class="dot-results late" cx="{X(n[-1]):.1f}" cy="{Y(results[-1]):.1f}" r="5"/>')
    out.append(f'<text class="lbl lbl-shape late" x="{X(n[-1]):.1f}" y="{Y(shape[-1]) - 16:.1f}" '
               'text-anchor="end">Ball flight</text>')
    # Both labels sit above their line's end, clear of the line itself.
    out.append(f'<text class="lbl lbl-results late" x="{X(n[-1]):.1f}" y="{Y(results[-1]) - 16:.1f}" '
               'text-anchor="end">Results</text>')
    out.append("</svg>")
    return "\n".join(out), cross_label


def dashboard_facts() -> dict[str, str]:
    meta = json.loads((WORK / "output" / "dashboard" / "pitcher_seasons.json")
                      .read_text(encoding="utf-8"))["meta"]
    with (WORK / "output" / "leaderboard" / "backtest_FF_whiff_rate.csv").open(newline="") as fh:
        seasons = list(csv.DictReader(fh))
    positive = sum(float(s["shape_lift"]) > 0 for s in seasons)
    first, last = meta["seasons"]
    verdicts = [v["verdict"] for v in meta["validation"].values()]
    return {
        "N_PITCHER_SEASONS": f"{meta['n_rows']:,}",
        "SEASONS": f"{first}–{last}",
        "BACKTEST_POS": str(positive),
        "BACKTEST_N": str(len(seasons)),
        "VALIDATED_N": str(verdicts.count("validated")),
        "PITCH_TYPES_N": str(len(verdicts)),
    }


def fill(template: str, values: dict[str, str]) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", val)
    left = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if left:
        raise SystemExit(f"unfilled placeholders: {sorted(set(left))}")
    return out


def render_card(html: str) -> None:
    """Screenshot the preview card with headless Chrome, then save as JPEG."""
    if not Path(CHROME).exists():
        if (DOCS / "card.jpg").exists():
            print("  Chrome not found; keeping the existing card.jpg")
            return
        raise SystemExit("Chrome not found and no card.jpg to fall back on")
    with tempfile.TemporaryDirectory() as tmp:
        page, png = Path(tmp) / "card.html", Path(tmp) / "card.png"
        page.write_text(html, encoding="utf-8")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", "--window-size=1200,630",
                        f"--screenshot={png}", page.as_uri()],
                       check=True, capture_output=True)
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "88",
                        str(png), "--out", str(DOCS / "card.jpg")],
                       check=True, capture_output=True)


def structured_data() -> str:
    """schema.org data for search engines: who the site is about, and what he made."""
    site = f"https://{DOMAIN}/"
    me = {"@id": f"{site}#scott"}
    graph = [
        {"@type": "Person", **me, "name": "Scott Luntz", "url": site,
         "jobTitle": "Independent sports analytics researcher",
         "sameAs": [LINKEDIN, GITHUB],
         "knowsAbout": ["Sports analytics", "Baseball", "Pitcher evaluation", "Statcast"]},
        {"@type": "WebSite", "@id": f"{site}#site", "url": site, "name": "Scott Luntz", "author": me},
        {"@type": "ScholarlyArticle", "headline": "The Shape of the Modern Pitch",
         "url": f"{site}modern-pitch/", "author": me, "datePublished": "2026-08",
         "identifier": {"@type": "PropertyValue", "propertyID": "DOI", "value": PAPER_DOI},
         "sameAs": f"https://doi.org/{PAPER_DOI}",
         "license": "https://creativecommons.org/licenses/by/4.0/"},
        {"@type": "WebApplication", "name": "Pitch Shape Explorer", "url": f"{site}pitch-shape-explorer/",
         "author": me, "applicationCategory": "Sports analytics", "operatingSystem": "Any web browser",
         "isAccessibleForFree": True},
    ]
    # "</" cannot appear inside a script element; escape it so a URL never ends it early.
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=1).replace("</", "<\\/")


def optional_extras() -> dict[str, str]:
    """Pieces that appear only once Scott supplies the file for them.

    Drop src/headshot.jpg (any size, roughly square) or src/resume.pdf into the
    source folder and rebuild; nothing else needs editing.
    """
    out = {"HEADSHOT": "", "RESUME_NAV": "", "RESUME_BUTTON": ""}
    if (SRC / "headshot.jpg").exists():
        out["HEADSHOT"] = ('\n        <figure class="headshot"><img src="/img/headshot.jpg" '
                           'alt="Scott Luntz" width="400" height="400"></figure>')
    if (SRC / "resume.pdf").exists():
        out["RESUME_NAV"] = '\n      <a href="/resume.pdf">Résumé</a>'
        out["RESUME_BUTTON"] = '\n        <a class="btn" href="/resume.pdf">Résumé (PDF)</a>'
    return out


def sips(src: Path, dst: Path, longest: int, quality: int = 80) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality), "-Z", str(longest),
                    str(src), "--out", str(dst)], check=True, capture_output=True)


def images() -> None:
    """Home-page thumbnails, the touch icon, and the headshot if there is one.

    The project panels show their preview at about 600px wide, so they get
    1200px copies (sharp on a retina screen) instead of the 2400px link-preview
    originals, which are kept for the link previews themselves.
    """
    sips(DOCS / "modern-pitch" / "social-card-v2.jpg", DOCS / "img" / "modern-pitch.jpg", 1200)
    sips(DOCS / "pitch-shape-explorer" / "dashboard-card.jpg", DOCS / "img" / "pitch-shape-explorer.jpg", 1200)
    if (SRC / "headshot.jpg").exists():
        sips(SRC / "headshot.jpg", DOCS / "img" / "headshot.jpg", 400, quality=85)

    # Apple touch icon: the favicon drawn square, since iOS rounds the corners itself.
    if not Path(CHROME).exists():
        print("  Chrome not found; keeping any existing apple-touch-icon.png")
        return
    square = (SRC / "favicon.svg").read_text(encoding="utf-8").replace(' rx="7"', "")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "icon.html"
        page.write_text("<html><body style='margin:0'>" + square.replace(
            "<svg ", "<svg width='180' height='180' style='display:block' ", 1) + "</body></html>", encoding="utf-8")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--window-size=180,180", f"--screenshot={DOCS / 'apple-touch-icon.png'}", page.as_uri()],
                       check=True, capture_output=True)


def crawl_files() -> None:
    site = f"https://{DOMAIN}/"
    (DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site}sitemap.xml\n", encoding="utf-8")
    urls = [site] + [f"{site}{dest}/" for dest in SECTIONS.values()]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n",
        encoding="utf-8")


def main() -> None:
    svg, cross_label = crossover()
    values = {"CROSSOVER_SVG": svg, "CROSSOVER_PITCHES": str(cross_label), **dashboard_facts(),
              "JSON_LD": structured_data(), "UPDATED": UPDATED, **optional_extras()}

    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(
        fill((SRC / "index.html").read_text(encoding="utf-8"), values), encoding="utf-8")
    shutil.copy2(SRC / "404.html", DOCS / "404.html")
    shutil.copy2(SRC / "site.css", DOCS / "site.css")
    shutil.copy2(SRC / "favicon.svg", DOCS / "favicon.svg")
    # Exactly as GitHub writes it from the Pages settings (no trailing newline),
    # so re-saving the domain there and rebuilding here never fight over it.
    (DOCS / "CNAME").write_text(DOMAIN, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    for built, dest in SECTIONS.items():
        src_dir, dst_dir = WORK / built, DOCS / dest
        page = (src_dir / "index.html").read_text(encoding="utf-8")
        # A stale build would still advertise the old Netlify address in its
        # preview tags, and every share would point at the wrong host.
        if f'og:url" content="https://{DOMAIN}/{dest}/' not in page:
            raise SystemExit(f"{built}/index.html is not built for {DOMAIN}/{dest}/ -- "
                             "rebuild it in velo-vs-spin first")
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns(".DS_Store"))

    images()
    crawl_files()
    if (SRC / "resume.pdf").exists():
        shutil.copy2(SRC / "resume.pdf", DOCS / "resume.pdf")

    render_card(fill((SRC / "card.html").read_text(encoding="utf-8"), {"CROSSOVER_SVG": svg}))

    # Checks on what will actually be published.
    problems = []
    for f in DOCS.rglob("*.html"):
        text = f.read_text(encoding="utf-8")
        if "netlify.app" in text:
            problems.append(f"{f.relative_to(DOCS)} still links to netlify.app")
        if re.search(r"[\w.+-]+@[\w-]+\.(com|net|org)\b", text):
            problems.append(f"{f.relative_to(DOCS)} contains an email address")
    if problems:
        raise SystemExit("not publishable:\n  " + "\n  ".join(problems))

    files = sorted(p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*") if p.is_file())
    size = sum((DOCS / p).stat().st_size for p in files) / 1e6
    print(f"built docs/ for {DOMAIN}: {len(files)} files, {size:.1f} MB")
    for p in files:
        print("  " + p)
    print(f"  crossover at about {cross_label} pitches; "
          f"{values['N_PITCHER_SEASONS']} pitcher-seasons; backtest "
          f"{values['BACKTEST_POS']} of {values['BACKTEST_N']}")


if __name__ == "__main__":
    sys.exit(main())
