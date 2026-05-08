# Control Financiero Movil Android

Aplicacion APK para Huawei/Android.

Version actual: 0.3.0

## Que hace

- Inicia sesion con usuario autorizado de Supabase.
- Permite elegir fotos, PDF o archivos desde el celular.
- Permite tomar foto y enviarla.
- Sube los documentos directo a Supabase Storage.
- Crea registros en `cloud_uploads` para que la PC los descargue y analice.
- Muestra ultimos envios.
- Guarda documentos pendientes en el celular si no se pueden enviar.
- Permite reintentar pendientes cuando vuelve internet.
- Muestra estados claros: pendiente, fallo o enviado.
- Reportes por semana, mes, trimestre o ano.
- Reportes concentrados, por cuenta y por categoria.
- Separa ingresos/egresos nacionales e internacionales.
- Separa transferencias entre cuentas propias para no contarlas como ingreso extra.

## Seguridad

La app solo incluye la llave publica de Supabase (`sb_publishable...`).
No incluye la llave secreta `service_role`.

Los permisos reales dependen de Supabase Auth y las politicas RLS ya configuradas:
admin, contador y capturista pueden subir documentos.

## Flujo de pendientes

Al presionar enviar, la app guarda primero cada documento en una cola local.
Despues intenta subirlos a Supabase. Si internet falla, el documento queda en
`Pendientes en este celular` y se puede reintentar con `Enviar pendientes`.

## Como generar el APK

En GitHub:

1. Abrir el repositorio `control-financiero-nube`.
2. Entrar a `Actions`.
3. Ejecutar `Build Android APK`.
4. Descargar el artefacto `control-financiero-android-apk`.
5. Instalar `app-debug.apk` en el Huawei.

Android puede avisar que el APK no viene de Play Store. Se permite instalar desde el navegador/archivos y se confirma la instalacion.
