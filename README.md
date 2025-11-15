# Agro Connections — Sitio web

Este repositorio contiene el código del sitio estático de **Agro Connections S.A. de C.V.**

## Estructura

- `index.html` — página principal.
- `css/style.css` — estilos.
- `js/app.js` — comportamiento (navegación, galería local, formulario multipaso).
- `assets/logo.png` — logotipo.
- `aviso-legal.html` y `privacidad.html` — páginas legales.
- `404.html` — página de error.
- `CNAME` — dominio personalizado (agroconnections.mx).
- `robots.txt` y `sitemap.xml` — soporte SEO.
- `LICENSE.txt`, `LEGAL.txt`, `SECURITY.md` — licencias y seguridad.

## Despliegue

El sitio está pensado para GitHub Pages:

1. Subir todos los archivos a la rama `main`.
2. En **Settings → Pages**, elegir:
   - Source: `Deploy from a branch`
   - Branch: `main` / `(root)`

Si se usa dominio propio (`agroconnections.mx`), apuntar los DNS a GitHub Pages
y mantener el archivo `CNAME` con el mismo dominio.
