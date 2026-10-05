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
          <a class="chip-link primary" href="mailto:yeffri@protonmail.com">✉ yeffri@protonmail.com</a>
          <a class="chip-link" href="https://www.linkedin.com/in/yeffrimic/">LinkedIn</a>
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
      <a class="chip-link primary" href="mailto:yeffri@protonmail.com">✉ yeffri@protonmail.com</a>
      <a class="chip-link" href="tel:+50241116553">☎ +502 4111-6553</a>
      <a class="chip-link" href="https://www.linkedin.com/in/yeffrimic/">LinkedIn</a>
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


def main():
    with open(os.path.join(ROOT, "content", "site.json"), encoding="utf-8") as f:
        data = json.load(f)
    for L in data["langs"]:
        out = os.path.join(ROOT, L["path"], "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(render_page(data, L))
        print("ok", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
