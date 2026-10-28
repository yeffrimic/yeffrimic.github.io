"""Genera las páginas del sitio en cada idioma a partir de content/site.json.

Uso (desde la raíz del repo):
    python tools/build.py

Salida: index.html (español), en/index.html, de/index.html, zh/index.html.
Para agregar un proyecto, charla o puesto: edita content/site.json y vuelve a correr
este script. No edites los index.html a mano; se sobrescriben.
"""
import html
import json
import os
import re
import urllib.parse
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MONTHS = {
    "es": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "de": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
}
PRESENT = {"es": "actualidad", "en": "present", "de": "heute", "zh": "至今"}


# ---------- utilidades ----------
def tr(value, lang):
    """Devuelve el texto en el idioma pedido; si el valor no está traducido, lo usa tal cual."""
    if isinstance(value, dict):
        return value.get(lang) or value["es"]
    return value


def esc(text):
    return html.escape(text, quote=False)


def attr(text):
    return html.escape(text, quote=True)


def parse_point(p):
    if p == "now":
        return None
    parts = [int(x) for x in p.split("-")]
    return parts + [None] * (3 - len(parts))  # [año, mes, día]


def fmt_point(p, lang):
    if p is None:
        return PRESENT[lang]
    y, m, d = p
    if lang == "zh":
        return f"{y}年" + (f"{m}月" if m else "") + (f"{d}日" if d else "")
    if not m:
        return str(y)
    mon = MONTHS[lang][m - 1]
    if d:
        return f"{d}. {mon} {y}" if lang == "de" else f"{d} {mon} {y}"
    return f"{mon} {y}"


def fmt_date(spec, lang):
    """'2026-09', '2026-08-28', '2026-03..2026-07', '2025-06..now', '2019..2022'."""
    if ".." not in spec:
        return fmt_point(parse_point(spec), lang)
    a, b = (parse_point(x) for x in spec.split(".."))
    if a and b and a[0] == b[0] and a[1] and b[1]:
        y = a[0]
        if a[1] == b[1] and a[2] and b[2]:  # mismo mes: 9–11 Sep 2026
            if lang == "zh":
                return f"{y}年{a[1]}月{a[2]}日–{b[2]}日"
            mon = MONTHS[lang][a[1] - 1]
            return f"{a[2]}.–{b[2]}. {mon} {y}" if lang == "de" else f"{a[2]}–{b[2]} {mon} {y}"
        if not a[2] and not b[2]:  # mismo año: Mar – Jul 2026
            if lang == "zh":
                return f"{y}年{a[1]}月 – {b[1]}月"
            return f"{MONTHS[lang][a[1] - 1]} – {MONTHS[lang][b[1] - 1]} {y}"
    return f"{fmt_point(a, lang)} – {fmt_point(b, lang)}"


def href(url, root):
    return url if url.startswith(("http://", "https://", "mailto:", "tel:")) else root + url


# ---------- bloques ----------
def render_tags(tags, lang):
    return "".join(f'<span class="tag">{esc(tr(t, lang))}</span>' for t in tags)


def render_links(links, ui, lang, root):
    if not links:
        return ""
    out = []
    for l in links:
        label = l["label"]
        text = tr(ui[label], lang) if isinstance(label, str) else tr(label, lang)
        out.append(f'<a class="more" href="{attr(href(l["url"], root))}">{esc(text)} →</a>')
    return f'\n        <div class="links-row">{"".join(out)}</div>'


def render_card(item, ui, lang, root, with_cat):
    cat = f' data-cat="{attr(item["cat"])}"' if with_cat else ""
    badge = f'\n        <span class="badge">{esc(tr(item["badge"], lang))}</span>' if item.get("badge") else ""
    org = f'\n        <div class="org">{esc(tr(item["org"], lang))}</div>' if item.get("org") else ""
    tags = f'\n        <div class="tags">{render_tags(item["tags"], lang)}</div>' if item.get("tags") else ""
    return f"""      <article class="card"{cat}>{badge}
        <span class="date">{esc(fmt_date(item["date"], lang))}</span>
        <h3>{esc(tr(item["title"], lang))}</h3>{org}
        <p>{esc(tr(item["text"], lang))}</p>{tags}{render_links(item.get("links"), ui, lang, root)}
      </article>
"""


def render_job(job, lang):
    cls = ' class="minor"' if job.get("minor") else ""
    bullets = ""
    if job.get("bullets"):
        items = "".join(f"<li>{esc(tr(b, lang))}</li>" for b in job["bullets"])
        bullets = f"\n        <ul>{items}</ul>"
    return f"""      <li{cls}>
        <span class="when">{esc(fmt_date(job["date"], lang))}</span>
        <h3>{esc(tr(job["title"], lang))}</h3>
        <div class="where">{esc(tr(job["where"], lang))}</div>{bullets}
      </li>
"""


def raw_list(items, lang):
    # Estas listas ya vienen en HTML (con <b>, <br />) desde site.json
    return "".join(f"\n          <li>{tr(i, lang)}</li>" for i in items)


# ---------- página ----------
def render_page(data, L):
    lang = L["code"]
    ui = data["ui"]
    u = lambda k: tr(ui[k], lang)  # noqa: E731
    root = "../" * L["path"].count("/")
    site = data["site_url"]

    # Selector de idioma: rutas relativas desde esta página
    switch = []
    alternates = []
    for o in data["langs"]:
        rel = root + o["path"] if o["path"] else (root or "./")
        current = ' aria-current="true"' if o["code"] == lang else ""
        switch.append(
            f'<a href="{attr(rel)}" hreflang="{o["html_lang"]}" lang="{o["html_lang"]}" data-lang="{o["code"]}"'
            f' data-suggest="{attr(tr(ui["suggest"], o["code"]))}" data-suggest-btn="{attr(tr(ui["suggest_btn"], o["code"]))}"'
            f"{current}>{esc(o['label'])}</a>"
        )
        alternates.append(f'<link rel="alternate" hreflang="{o["html_lang"]}" href="{site}{o["path"]}" />')
    alternates.append(f'<link rel="alternate" hreflang="x-default" href="{site}" />')

    # Solo la portada en español redirige a la versión que el visitante eligió antes
    lang_map = {o["code"]: o["path"] for o in data["langs"] if o["path"]}
    redirect = ""
    if lang == "es":
        redirect = (
            "    try { var L = localStorage.getItem('lang'), M = " + json.dumps(lang_map) + ";\n"
            "      if (L && M[L]) { location.replace(M[L] + location.search + location.hash); return; } } catch (e) {}\n"
        )

    projects = "".join(render_card(p, ui, lang, root, True) for p in data["projects"])
    talks = "".join(render_card(t, ui, lang, root, False) for t in data["talks"])
    jobs = "".join(render_job(j, lang) for j in data["jobs"])
    stats = "".join(
        f'\n      <div class="stat"><b>{esc(tr(s["value"], lang))}</b><span>{esc(tr(s["label"], lang))}</span></div>'
        for s in data["stats"]
    )
    filters = "".join(
        f'\n      <button data-filter="{f}" aria-pressed="{"true" if f == "all" else "false"}">{esc(u("f_" + f))}</button>'
        for f in ["all", "robotica", "edu", "hardware", "software"]
    )
    captions = attr(json.dumps(tr(ui["intro_captions"], lang), ensure_ascii=False))

    return f"""<!doctype html>
<!-- Generado por tools/build.py desde content/site.json. No editar a mano. -->
<html lang="{L["html_lang"]}" data-lang="{lang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(u("title"))}</title>
<meta name="description" content="{attr(u("meta_desc"))}" />
<meta property="og:title" content="{attr(u("title"))}" />
<meta property="og:description" content="{attr(u("og_desc"))}" />
<meta property="og:image" content="{site}images/yo.jpg" />
<meta property="og:locale" content="{L["og_locale"]}" />
<link rel="canonical" href="{site}{L["path"]}" />
{chr(10).join(alternates)}
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
<script>
  (function () {{
{redirect}    // Intro del chip: una vez por sesión; ?intro la fuerza; con movimiento reducido va en versión suave
    var d = document.documentElement, force = /[?&]intro(?:[=&]|$)/.test(location.search), reduce = false, seen = false;
    try {{ reduce = matchMedia('(prefers-reduced-motion: reduce)').matches; }} catch (e) {{}}
    try {{ seen = sessionStorage.getItem('introSeen') === '1'; }} catch (e) {{}}
    if (force || !seen) {{ d.classList.add('intro-on'); if (reduce) d.classList.add('intro-soft'); }}
  }})();
</script>
<link rel="stylesheet" href="{root}assets/css/site.css" />
</head>
<body>

<div id="chipIntro" data-captions="{captions}">
  <canvas aria-hidden="true"></canvas>
  <div class="intro-caption" aria-hidden="true"><b>{esc(tr(ui["intro_captions"], lang)[0])}</b><span>×1</span></div>
  <button class="intro-skip" type="button">{esc(u("intro_skip"))}</button>
</div>

<nav class="top">
  <div class="wrap">
    <a class="brand" href="#inicio">Yeffri J. Salazar</a>
    <div class="links">
      <a href="#proyectos">{esc(u("nav_projects"))}</a>
      <a href="#charlas">{esc(u("nav_talks"))}</a>
      <a href="#experiencia">{esc(u("nav_experience"))}</a>
      <a href="#formacion">{esc(u("nav_education"))}</a>
      <a href="#contacto">{esc(u("nav_contact"))}</a>
      <a href="ruta/">{esc(u("nav_ride"))}</a>
    </div>
    <div class="lang-switch" role="group" aria-label="{attr(u("lang_label"))}">{"".join(switch)}</div>
    <button id="themeToggle" aria-label="{attr(u("theme_label"))}" title="{attr(u("theme_label"))}">◐</button>
  </div>
</nav>

<header class="hero" id="inicio">
  <div class="wrap">
    <div class="hero-grid">
      <div>
        <h1>Yeffri J. Salazar</h1>
        <p class="role">{esc(u("role"))}</p>
        <p class="lead">{esc(u("lead"))}</p>
        <div class="contact-row">
          <a class="chip-link primary" href="https://www.linkedin.com/in/yeffrimic/">in · LinkedIn</a>
          <a class="chip-link" href="https://github.com/yeffrimic">GitHub</a>
          <a class="chip-link" href="https://themicrofcontrol.wordpress.com">{esc(u("blog"))}</a>
          <button class="chip-link print-btn" onclick="window.print()">{esc(u("print_cv"))}</button>
        </div>
      </div>
      <img src="{root}images/yo.jpg" alt="{attr(u("photo_alt"))}" />
    </div>

    <div class="stats">{stats}
    </div>
  </div>
</header>

<section class="block" id="proyectos">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">{esc(u("projects_kicker"))}</span>
      <h2>{esc(u("projects_title"))}</h2>
      <p>{esc(u("projects_desc"))}</p>
    </div>

    <div class="filters" role="group" aria-label="{attr(u("filters_label"))}">{filters}
    </div>

    <div class="grid" id="projectGrid">
{projects}    </div>
    <p class="all-repos"><a class="more" href="https://github.com/yeffrimic?tab=repositories">{esc(u("all_repos"))} →</a></p>
  </div>
</section>

<section class="block" id="charlas">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">{esc(u("talks_kicker"))}</span>
      <h2>{esc(u("talks_title"))}</h2>
      <p>{esc(u("talks_desc"))}</p>
    </div>

    <div class="grid">
{talks}    </div>

    <div class="cols" style="margin-top:16px">
      <div class="panel">
        <h3>{esc(u("topics_title"))}</h3>
        <ul>{raw_list(data["topics"], lang)}
        </ul>
      </div>
    </div>
  </div>
</section>

<section class="block" id="experiencia">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">{esc(u("exp_kicker"))}</span>
      <h2>{esc(u("exp_title"))}</h2>
    </div>

    <ul class="timeline">
{jobs}    </ul>
  </div>
</section>

<section class="block" id="formacion">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">{esc(u("base_kicker"))}</span>
      <h2>{esc(u("base_title"))}</h2>
    </div>

    <div class="cols">
      <div class="panel">
        <h3>{esc(u("p_education"))}</h3>
        <ul>{raw_list(data["education"], lang)}
        </ul>
      </div>
      <div class="panel">
        <h3>{esc(u("p_skills"))}</h3>
        <ul>{raw_list(data["skills"], lang)}
        </ul>
      </div>
      <div class="panel">
        <h3>{esc(u("p_awards"))}</h3>
        <ul>{raw_list(data["awards"], lang)}
        </ul>
      </div>
      <div class="panel">
        <h3>{esc(u("p_communities"))}</h3>
        <ul>{raw_list(data["communities"], lang)}
        </ul>
      </div>
      <div class="panel">
        <h3>{esc(u("p_languages"))}</h3>
        <ul>{raw_list(data["languages"], lang)}
        </ul>
      </div>
    </div>
  </div>
</section>

<section class="block" id="contacto">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">{esc(u("contact_kicker"))}</span>
      <h2>{esc(u("contact_title"))}</h2>
      <p>{esc(u("contact_desc"))}</p>
    </div>
    <div class="contact-row">
      <a class="chip-link primary" href="https://www.linkedin.com/in/yeffrimic/">in · LinkedIn</a>
      <a class="chip-link" href="tel:+50241116553">☎ +502 4111-6553</a>
      <a class="chip-link" href="https://github.com/yeffrimic">GitHub</a>
      <a class="chip-link" href="https://twitter.com/yeffrimic">X / Twitter</a>
      <a class="chip-link" href="https://www.instagram.com/yeffrimic/">Instagram</a>
      <a class="chip-link" href="https://themicrofcontrol.wordpress.com">{esc(u("blog"))}</a>
    </div>
    <p class="no-print" style="color:var(--muted);margin-top:18px">{esc(u("location"))}</p>
  </div>
</section>

<footer>
  <div class="wrap">
    <span>© 2026 Yeffri J. Salazar</span>
    <span>{esc(u("motto"))} · <a href="?intro">{esc(u("replay"))}</a></span>
  </div>
</footer>

<script src="{root}assets/js/site.js"></script>
<script src="{root}assets/js/chip-intro.js"></script>
</body>
</html>
"""


# ---------- ruta en bici (content/ruta.json → ruta/ y un capítulo por historia) ----------
def embed(url, ru, lang, root=""):
    """Inserta una publicación de TikTok o Instagram a partir de su enlace, o un .mp4 propio."""
    if url.endswith(".mp4"):
        # Si junto al .mp4 hay un .webm (Firefox en Linux a veces no trae H.264) o un .jpg de portada, se usan.
        base = url[:-4]
        has = lambda ext: os.path.exists(os.path.join(ROOT, base + ext))
        poster = f' poster="{attr(root + base + ".jpg")}"' if has(".jpg") else ""
        webm = f'<source src="{attr(root + base + ".webm")}" type="video/webm" />' if has(".webm") else ""
        return (f'<video controls playsinline preload="metadata"{poster}>{webm}'
                f'<source src="{attr(root + url)}" type="video/mp4" /></video>')
    m = re.search(r"tiktok\.com/@[^/]+/video/(\d+)", url)
    if m:
        return (f'<blockquote class="tiktok-embed" cite="{attr(url)}" data-video-id="{m.group(1)}">'
                f'<section><a href="{attr(url)}">{esc(tr(ru["watch"], lang))} →</a></section></blockquote>')
    if re.search(r"instagram\.com/(p|reel|tv)/", url):
        return (f'<blockquote class="instagram-media" data-instgrm-permalink="{attr(url)}" data-instgrm-version="14">'
                f'<a href="{attr(url)}">{esc(tr(ru["watch"], lang))} →</a></blockquote>')
    return f'<a class="more" href="{attr(url)}">{esc(tr(ru["watch"], lang))} →</a>'


def numbered(word, n):
    """'Capítulo' → 'Capítulo 3'; en chino la palabra trae {n}: '第{n}章' → '第3章'."""
    return word.replace("{n}", str(n)) if "{n}" in word else f"{word} {n}"


def chapter_meta(e, n, ruta, lang):
    """'Capítulo 1 · Día 1 · 25 Oct 2026' y 'Ciudad de Guatemala → El Cerinal · Guatemala · 25 km'."""
    ru = ruta["ui"]
    head = [numbered(tr(ru["chapter"], lang), n)]
    if ruta.get("start_date"):
        head.append(numbered(tr(ru["day"], lang), (date.fromisoformat(e["date"]) - date.fromisoformat(ruta["start_date"])).days + 1))
    head.append(fmt_date(e["date"], lang))
    place = tr(e["place"], lang)
    if e.get("from"):
        place = f'{tr(e["from"], lang)} → {place}'
    where = [place, tr(ruta["countries"][e["country"]], lang)]
    if e.get("km"):
        where.append(numbered(tr(ru["km"], lang), e["km"]))
    return " · ".join(head), " · ".join(where)


def excerpt(e, lang, size=200):
    text = tr(e["body"], lang)[0]
    if len(text) <= size:
        return text
    return text[:size].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def ruta_page(data, ruta, L, sub, title, desc, image, main, extra_js=""):
    """Esqueleto común de las páginas de la ruta. `sub` es la ruta bajo ruta/ ('' o 'slug/')."""
    lang = L["code"]
    ru = ruta["ui"]
    ui = data["ui"]
    site = data["site_url"]
    root = "../" * (L["path"].count("/") + 1 + sub.count("/"))
    page = "ruta/" + sub

    switch = []
    alternates = []
    for o in data["langs"]:
        current = ' aria-current="true"' if o["code"] == lang else ""
        switch.append(
            f'<a href="{attr(root + o["path"] + page)}" hreflang="{o["html_lang"]}" lang="{o["html_lang"]}" data-lang="{o["code"]}"'
            f' data-suggest="{attr(tr(ui["suggest"], o["code"]))}" data-suggest-btn="{attr(tr(ui["suggest_btn"], o["code"]))}"'
            f"{current}>{esc(o['label'])}</a>"
        )
        alternates.append(f'<link rel="alternate" hreflang="{o["html_lang"]}" href="{site}{o["path"]}{page}" />')
    alternates.append(f'<link rel="alternate" hreflang="x-default" href="{site}{page}" />')

    redirect = ""
    if lang == "es":
        lang_map = {o["code"]: root + o["path"] + page for o in data["langs"] if o["path"]}
        redirect = (
            "<script>\n  try { var L = localStorage.getItem('lang'), M = " + json.dumps(lang_map) + ";\n"
            "    if (L && M[L]) location.replace(M[L] + location.search + location.hash); } catch (e) {}\n</script>\n"
        )

    index = root + L["path"] + "ruta/"
    return f"""<!doctype html>
<!-- Generado por tools/build.py desde content/ruta.json. No editar a mano. -->
<html lang="{L["html_lang"]}" data-lang="{lang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(title)}</title>
<meta name="description" content="{attr(desc)}" />
<meta property="og:type" content="{"article" if sub else "website"}" />
<meta property="og:site_name" content="Yeffri J. Salazar" />
<meta property="og:title" content="{attr(title)}" />
<meta property="og:description" content="{attr(desc)}" />
<meta property="og:image" content="{site}{image}" />
<meta property="og:url" content="{site}{L["path"]}{page}" />
<meta property="og:locale" content="{L["og_locale"]}" />
<meta name="twitter:card" content="summary_large_image" />
<link rel="canonical" href="{site}{L["path"]}{page}" />
{chr(10).join(alternates)}
{redirect}<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
<link rel="stylesheet" href="{root}assets/css/site.css" />
</head>
<body>

<nav class="top">
  <div class="wrap">
    <a class="brand" href="{root}{L["path"]}">Yeffri J. Salazar</a>
    <div class="links">
      <a href="{root}{L["path"]}">← {esc(tr(ru["nav_home"], lang))}</a>
      <a href="{index}#capitulos">{esc(tr(ru["nav_chapters"], lang))}</a>
      <a href="{index}viaje/">{esc(tr(ru["nav_about"], lang))}</a>
    </div>
    <div class="lang-switch" role="group" aria-label="{attr(tr(ui["lang_label"], lang))}">{"".join(switch)}</div>
    <button id="themeToggle" aria-label="{attr(tr(ui["theme_label"], lang))}" title="{attr(tr(ui["theme_label"], lang))}">◐</button>
  </div>
</nav>
{main}
<footer>
  <div class="wrap">
    <span>© 2026 Yeffri J. Salazar</span>
    <span>{esc(tr(ui["motto"], lang))}</span>
  </div>
</footer>

<script src="{root}assets/js/site.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script src="{root}assets/js/ruta.js"></script>
{extra_js}</body>
</html>
"""


def share_links(url, title, ru, lang):
    q = urllib.parse.quote(url, safe="")
    return f"""<div class="share" data-url="{attr(url)}">
      <span>{esc(tr(ru["share"], lang))}</span>
      <a class="chip-link" href="https://www.facebook.com/sharer/sharer.php?u={q}">Facebook</a>
      <a class="chip-link" href="https://www.linkedin.com/sharing/share-offsite/?url={q}">LinkedIn</a>
      <a class="chip-link" href="https://wa.me/?text={urllib.parse.quote(title + " " + url, safe="")}">WhatsApp</a>
      <button class="chip-link copy-link" type="button" data-done="{attr(tr(ru["copied"], lang))}">{esc(tr(ru["copy"], lang))}</button>
    </div>"""


def entry_image(e, ruta):
    """Imagen al compartir: `cover` (1200×630) si existe; si no, la primera foto."""
    if e.get("cover"):
        return e["cover"]
    photos = e.get("photos") or []
    return photos[0]["src"] if photos else ruta["default_image"]


def map_points(ruta, entries, lang, prefix):
    points = []
    if ruta.get("start"):
        s = ruta["start"]
        points.append({"lat": s["coords"][0], "lng": s["coords"][1], "href": "", "title": "", "place": tr(s["place"], lang)})
    points += [{"lat": e["coords"][0], "lng": e["coords"][1], "href": prefix + e["slug"] + "/",
                "title": tr(e["title"], lang), "place": tr(e["place"], lang), "cta": tr(ruta["ui"]["read"], lang)}
               for e in entries if e.get("coords")]
    return attr(json.dumps(points, ensure_ascii=False))


def render_ruta(data, ruta, L):
    """Portada de la ruta: corta a propósito (capítulos y mapa); el resto vive en ruta/viaje/."""
    lang = L["code"]
    ru = ruta["ui"]
    u = lambda k: tr(ru[k], lang)  # noqa: E731
    entries = sorted(ruta["entries"], key=lambda e: e["date"])

    total_km = sum(e.get("km") or 0 for e in entries)
    countries = {e["country"] for e in entries}
    days = ""
    if entries and ruta.get("start_date"):
        days = str((date.fromisoformat(entries[-1]["date"]) - date.fromisoformat(ruta["start_date"])).days + 1)
    stats = [(f"{total_km:,}".replace(",", " "), "stat_km"), (days or "–", "stat_days"),
             (str(len(countries)) if countries else "–", "stat_countries"), (str(len(entries)), "stat_chapters")]
    stats_html = "".join(f'\n      <div class="stat"><b>{v}</b><span>{esc(u(k))}</span></div>' for v, k in stats)

    cards = []
    for n, e in enumerate(entries, 1):
        head, where = chapter_meta(e, n, ruta, lang)
        cards.append(f"""      <a class="chapter-card" href="{attr(e["slug"])}/">
        <span class="date">{esc(head)}</span>
        <h3>{esc(tr(e["title"], lang))}</h3>
        <div class="where">{esc(where)}</div>
        <p>{esc(excerpt(e, lang))}</p>
        <span class="more">{esc(u("read"))} →</span>
      </a>
""")
    chapters = "".join(cards) or f'      <p class="empty">{esc(u("empty"))}</p>\n'
    latest = f'\n      <a class="chip-link primary" href="{attr(entries[-1]["slug"])}/">{esc(u("latest"))} →</a>' if entries else ""

    main = f"""
<header class="hero">
  <div class="wrap">
    <span class="kicker">{esc(u("kicker"))} · <span class="hashtag">{esc(ruta["hashtag"])}</span></span>
    <h1>{esc(u("heading"))}</h1>
    <p class="lead">{esc(u("lead"))}</p>
    <div class="contact-row">{latest}
      <a class="chip-link" href="viaje/">{esc(u("nav_about"))} →</a>
    </div>
    <div class="stats">{stats_html}
    </div>
  </div>
</header>

<section class="block" id="capitulos">
  <div class="wrap">
    <div class="sec-head">
      <h2>{esc(u("nav_chapters"))}</h2>
    </div>
    <div class="chapters">
{chapters}    </div>
  </div>
</section>

<section class="block" id="mapa">
  <div class="wrap">
    <p class="map-hint">{esc(u("map_hint"))}</p>
    <div id="routeMap" role="region" aria-label="{attr(u("map_label"))}" data-points="{map_points(ruta, entries, lang, "")}"></div>
  </div>
</section>
"""
    return ruta_page(data, ruta, L, "", u("title"), u("meta_desc"), ruta["default_image"], main)


def render_about(data, ruta, L):
    """ruta/viaje/: por qué, destino, contacto para emprendedores, próximas fechas y redes."""
    lang = L["code"]
    ru = ruta["ui"]
    u = lambda k: tr(ru[k], lang)  # noqa: E731
    why = ruta["purpose"]
    why_cards = "".join(f"""
      <article class="card">
        <h3>{esc(tr(it["title"], lang))}</h3>
        <p>{esc(tr(it["text"], lang))}</p>
      </article>""" for it in why["items"])
    contact = ruta["contact"]
    contact_btns = "".join(f'\n      <a class="chip-link{" primary" if i == 0 else ""}" href="{attr(b["url"])}">{esc(tr(b["label"], lang))}</a>'
                           for i, b in enumerate(contact["buttons"]))
    socials = "".join(f'\n      <a class="chip-link" href="{attr(s["url"])}">{esc(s["label"])}</a>' for s in ruta["socials"])
    ev = ruta["events_ui"]
    # Solo las fechas que aún no pasan (al momento de generar el sitio)
    upcoming = sorted((e for e in ruta["events"] if e["date"] >= date.today().isoformat()), key=lambda e: e["date"])
    events = "".join(f"""
      <li>
        <span class="when">{esc(fmt_date(e["date"], lang))}</span>
        <h3>{esc(tr(e["title"], lang))}</h3>
        <div class="where">{esc(tr(e["place"], lang))} · {esc(tr(ruta["countries"][e["country"]], lang))}</div>{
        f'{chr(10)}        <a class="more" href="{attr(e["url"])}">{esc(tr(ev["more"], lang))} →</a>' if e.get("url") else ""}
      </li>""" for e in upcoming)
    events_html = f'<ul class="timeline">{events}\n    </ul>' if events else f'<p class="empty">{esc(tr(ev["empty"], lang))}</p>'

    main = f"""
<header class="hero">
  <div class="wrap">
    <span class="kicker">{esc(u("kicker"))} · <span class="hashtag">{esc(ruta["hashtag"])}</span></span>
    <h1>{esc(tr(why["heading"], lang))}</h1>
    <p class="lead">{esc(tr(why["intro"], lang))}</p>
    <p class="why-destination">{esc(tr(why["destination"], lang))}</p>
  </div>
</header>

<section class="block" id="por-que">
  <div class="wrap">
    <div class="grid why-grid">{why_cards}
    </div>
    <p class="why-closing">{esc(tr(why["closing"], lang))}</p>
    <div class="embeds why-videos">{"".join(f'<div class="embed">{embed(v, ru, lang)}</div>' for v in why["videos"])}</div>
  </div>
</section>

<section class="block" id="contacto">
  <div class="wrap">
    <div class="sec-head">
      <h2>{esc(tr(contact["heading"], lang))}</h2>
      <p>{esc(tr(contact["text"], lang))}</p>
    </div>
    <div class="contact-row">{contact_btns}
    </div>
  </div>
</section>

<section class="block" id="fechas">
  <div class="wrap">
    <div class="sec-head">
      <h2>{esc(tr(ev["heading"], lang))}</h2>
    </div>
    {events_html}
  </div>
</section>

<section class="block" id="redes">
  <div class="wrap">
    <div class="sec-head">
      <h2>{esc(u("follow"))}</h2>
      <p>{esc(u("hashtag_text"))} <b>{esc(ruta["hashtag"])}</b></p>
    </div>
    <div class="contact-row">{socials}
    </div>
  </div>
</section>
"""
    tiktok_js = '<script async src="https://www.tiktok.com/embed.js"></script>\n' if why["videos"] else ""
    title = f'{tr(why["heading"], lang)} · {u("short_title")}'
    return ruta_page(data, ruta, L, "viaje/", title, tr(why["destination"], lang), ruta["default_image"], main, tiktok_js)


def render_chapter(data, ruta, L, entries, i):
    lang = L["code"]
    ru = ruta["ui"]
    u = lambda k: tr(ru[k], lang)  # noqa: E731
    e = entries[i]
    sub = e["slug"] + "/"
    root = "../" * (L["path"].count("/") + 2)
    url = f'{data["site_url"]}{L["path"]}ruta/{sub}'
    title = tr(e["title"], lang)
    head, where = chapter_meta(e, i + 1, ruta, lang)
    page_title = f'{head.split(" · ")[0]}: {title} · {u("short_title")}'

    def figure(p, cls=""):
        return (f'<figure{cls}><img src="{attr(root + p["src"])}" alt="{attr(tr(p.get("alt", ""), lang))}" loading="lazy" />'
                + (f'<figcaption>{esc(tr(p["caption"], lang))}</figcaption>' if p.get("caption") else "")
                + "</figure>")

    # Fotos y videos con "after": n van dentro del texto, después del párrafo n; los demás, al final.
    # Un video puede ser solo el enlace o {"url": ..., "after": n}.
    videos = [v if isinstance(v, dict) else {"url": v} for v in e.get("videos", [])]
    inline = {}
    for p in e.get("photos", []):
        if p.get("after"):
            inline.setdefault(p["after"], []).append(figure(p, ' class="inline"'))
    for v in videos:
        if v.get("after"):
            inline.setdefault(v["after"], []).append(f'<div class="embed inline">{embed(v["url"], ru, lang, root)}</div>')
    body = "".join(f"\n      <p>{esc(t)}</p>" + "".join(f"\n      {h}" for h in inline.get(n, []))
                   for n, t in enumerate(tr(e["body"], lang), 1))
    photos = "".join(figure(p) for p in e.get("photos", []) if not p.get("after"))
    embeds = "".join(f'<div class="embed">{embed(v["url"], ru, lang, root)}</div>' for v in videos if not v.get("after"))
    videos = [v["url"] for v in videos]

    pager = []
    if i > 0:
        p = entries[i - 1]
        pager.append(f'<a class="prev" href="../{attr(p["slug"])}/"><span>← {esc(u("prev"))}</span><b>{esc(tr(p["title"], lang))}</b></a>')
    if i + 1 < len(entries):
        n = entries[i + 1]
        pager.append(f'<a class="next" href="../{attr(n["slug"])}/"><span>{esc(u("next"))} →</span><b>{esc(tr(n["title"], lang))}</b></a>')
    else:
        pager.append(f'<div class="next soon"><span>{esc(u("next"))}</span><b>{esc(u("soon"))}</b></div>')

    extra_js = ""
    if any("tiktok.com" in v for v in videos):
        extra_js += '<script async src="https://www.tiktok.com/embed.js"></script>\n'
    if any("instagram.com" in v for v in videos):
        extra_js += '<script async src="https://www.instagram.com/embed.js"></script>\n'

    main = f"""
<article class="chapter">
  <div class="wrap">
    <header>
      <span class="date">{esc(head)}</span>
      <h1>{esc(title)}</h1>
      <div class="where">{esc(where)}</div>
    </header>{body}
    {f'<div class="photos">{photos}</div>' if photos else ""}
    {f'<div class="embeds">{embeds}</div>' if embeds else ""}
    {share_links(url, title, ru, lang)}
    <nav class="pager">{"".join(pager)}</nav>
    <p class="map-hint">{esc(u("map_hint"))}</p>
    <div id="routeMap" class="mini" role="region" aria-label="{attr(u("map_label"))}" data-points="{map_points(ruta, entries[: i + 1], lang, "../")}"></div>
    <p class="all"><a class="more" href="../#capitulos">{esc(u("all_chapters"))} →</a></p>
  </div>
</article>
"""
    return ruta_page(data, ruta, L, sub, page_title, excerpt(e, lang, 180), entry_image(e, ruta), main, extra_js)


def main():
    with open(os.path.join(ROOT, "content", "site.json"), encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(ROOT, "content", "ruta.json"), encoding="utf-8") as f:
        ruta = json.load(f)
    for L in data["langs"]:
        entries = sorted(ruta["entries"], key=lambda e: e["date"])
        pages = [("index.html", render_page(data, L)), (os.path.join("ruta", "index.html"), render_ruta(data, ruta, L))]
        pages.append((os.path.join("ruta", "viaje", "index.html"), render_about(data, ruta, L)))
        pages += [(os.path.join("ruta", e["slug"], "index.html"), render_chapter(data, ruta, L, entries, i))
                  for i, e in enumerate(entries)]
        for name, page in pages:
            out = os.path.join(ROOT, L["path"], name)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8", newline="\n") as f:
                f.write(page)
            print("ok", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
