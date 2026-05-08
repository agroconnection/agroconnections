# Despliegue nube para usar la app movil con la PC apagada

Servicio activo:

```text
https://control-financiero-nube.onrender.com
```

Panel de Render:

```text
https://dashboard.render.com/web/srv-d7tc6u3eo5us73eicmh0
```

Esta guia publica `app_web_nube.py` en Render para que el celular pueda abrir la app desde internet aunque la computadora este apagada.

## Que queda funcionando

- El celular entra a una URL publica tipo `https://control-financiero-nube.onrender.com`.
- Puedes subir tickets, facturas, estados de cuenta, PDFs o imagenes desde cualquier lugar.
- Los archivos se guardan en Supabase Storage y los registros en `cloud_uploads`.
- La PC, cuando se encienda, sincroniza lo pendiente y hace el OCR/revision local.
- Los reportes nube muestran movimientos ya sincronizados y tambien pendientes capturados.

## Importante

La app movil en nube no debe guardar secretos en el codigo. Las llaves se ponen como variables de entorno en Render.

No publiques ni compartas:

- `config_nube.json`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`
- cualquier token de usuario

El archivo `.gitignore` ya excluye `config_nube.json`, `data/`, `comprobantes/` y `exports/`.

## Archivos preparados

- `app_web_nube.py`: app Flask movil/nube.
- `nube_supabase.py`: cliente Supabase.
- `requirements_web.txt`: dependencias ligeras para web.
- `Procfile`: comando para iniciar con Gunicorn.
- `render.yaml`: configuracion opcional para Render Blueprint.

## Variables de entorno en Render

Configura estas variables en el servicio web:

| Variable | Valor |
| --- | --- |
| `FLASK_SECRET_KEY` | Generar valor seguro automatico o texto aleatorio largo |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_ANON_KEY` | Publishable/anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret/service role key, solo en servidor |
| `SUPABASE_ORGANIZATION_ID` | ID de la organizacion creada en Supabase |
| `SUPABASE_BUCKET` | `financial-documents` |

## Opcion A: Render Blueprint

1. Sube esta carpeta a GitHub.
2. En Render, crea un Blueprint usando el repositorio.
3. Render leera `render.yaml`.
4. Llena las variables marcadas como secretas.
5. Espera el deploy.

## Opcion B: Web Service manual

1. En Render crea `New > Web Service`.
2. Conecta el repositorio.
3. Usa:
   - Runtime: Python
   - Build Command: `pip install -r requirements_web.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT app_web_nube:app`
   - Health Check Path: `/salud`
4. Agrega las variables de entorno.
5. Haz deploy.

## Verificacion

Cuando Render termine, abre:

```text
https://control-financiero-nube.onrender.com/salud
```

Debe responder algo como:

```json
{"ok": true, "supabase_url": true, "organization_id": true, "bucket": "financial-documents", "server_upload_enabled": true}
```

Si `server_upload_enabled` sale `false`, falta `SUPABASE_SERVICE_ROLE_KEY`.

## Uso diario

1. Desde el celular abre la URL publica de Render.
2. Inicia sesion.
3. Entra a `Instalar` y agrega la app a la pantalla de inicio.
4. Abre el icono instalado.
5. Sube tickets o documentos.
6. Si la PC esta apagada, los archivos quedan en Supabase como pendientes.
7. Al encender la PC, abre la app de escritorio y usa `Traer capturas del celular`.

Guia de instalacion en celular: `INSTALAR_APP_CELULAR.md`.

## Limitacion actual

La subida funciona con la PC apagada. El OCR y la clasificacion completa se hacen cuando la PC sincroniza. Si despues quieres OCR completo tambien en nube, se requiere agregar un worker/servicio OCR en servidor.
