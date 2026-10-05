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

## Archivos

| Ruta | Qué es |
|---|---|
| `content/site.json` | Todo el contenido, en los cuatro idiomas |
| `tools/build.py` | Genera `index.html`, `en/`, `de/`, `zh/` (solo usa la biblioteca estándar de Python) |
| `assets/css/site.css` | Estilos compartidos |
| `assets/js/site.js` | Tema claro/oscuro, filtros, selector y sugerencia de idioma |
| `assets/js/chip-intro.js` | Animación de entrada (viaje dentro del chip) |
