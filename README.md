# yeffrimic.github.io

Portafolio y CV de Yeffri J. Salazar en cuatro idiomas:
español (`/`), inglés (`/en/`), alemán (`/de/`) y chino (`/zh/`).

## Cómo actualizar el contenido

1. Edita `content/site.json`. Cada proyecto, charla o puesto es **una sola entrada**
   con los textos en los cuatro idiomas (`es`, `en`, `de`, `zh`).
   - Fechas: `"2026-09"`, `"2026-08-28"`, rangos `"2026-03..2026-07"`, `"2025-06..now"`.
     El script las escribe en el formato de cada idioma.
   - Si un texto no tiene traducción, se usa el español.
2. Regenera las páginas desde la raíz del repo:

   ```bash
   python tools/build.py
   ```

3. Haz commit de `content/site.json` **y** de los `index.html` generados.

No edites los `index.html` a mano: el script los sobrescribe.

## Ruta en bici (`/ruta/`)

Bitácora del viaje Guatemala → Costa Rica. Cada historia es una entrada en
`entries` de `content/ruta.json`:

```json
{
  "slug": "dia-3-frontera",
  "date": "2026-10-24",
  "from": { "es": "Escuintla" },
  "place": { "es": "La Hachadura" },
  "country": "sv",
  "km": 120,
  "coords": [13.86, -90.08],
  "title": { "es": "…", "en": "…", "de": "…", "zh": "…" },
  "body": { "es": ["Párrafo 1", "Párrafo 2"], "en": ["…"] },
  "photos": [{ "src": "images/ruta/frontera.jpg", "alt": { "es": "…" }, "caption": { "es": "…" } }],
  "videos": ["https://www.tiktok.com/@joserivasgt/video/…", "https://www.instagram.com/reel/…"]
}
```

- Cada entrada es un capítulo con su propia página: `ruta/<slug>/` (y `en/ruta/<slug>/`, etc.).
- `km` son los km recorridos en la etapa.
- `coords` es el punto donde terminó la etapa; el mapa une los puntos en orden de fecha.
- Fotos y videos con `"after": n` se insertan después del párrafo `n`; un video puede ser solo el enlace
  o `{ "url": "…", "after": 3 }`. Las fotos van reducidas en `images/ruta/` (los originales, fuera del repo).
- `cover`: imagen de 1200×630 para la vista previa al compartir en Facebook/LinkedIn.
- `events`: próximas fechas (`date`, `title`, `place`, `country`, `url`); las pasadas se ocultan al regenerar.
- `start` (lugar y `coords` de salida) y `start_date` (para numerar los días) van en la raíz del archivo.
- `country`: `gt`, `sv`, `hn`, `ni` o `cr`.
- Los enlaces de TikTok/Instagram se insertan como publicaciones; no hace falta subir los videos.
- Después: `python tools/build.py`.

## Archivos

| Ruta | Qué es |
|---|---|
| `content/site.json` | Todo el contenido, en los cuatro idiomas |
| `tools/build.py` | Genera `index.html`, `en/`, `de/`, `zh/` (solo usa la biblioteca estándar de Python) |
| `assets/css/site.css` | Estilos compartidos |
| `assets/js/site.js` | Tema claro/oscuro, filtros, selector y sugerencia de idioma |
| `assets/js/chip-intro.js` | Animación de entrada (viaje dentro del chip) |
| `content/ruta.json` | Historias del viaje en bici, en los cuatro idiomas |
| `assets/js/ruta.js` | Mapa del recorrido (Leaflet + OpenStreetMap) |
