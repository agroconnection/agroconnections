# -*- coding: utf-8 -*-
"""Web movil Fase 3: captura en nube con login Supabase."""

from __future__ import annotations

import tempfile
import csv
import io
import json
import os
import re
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, Response, flash, redirect, render_template_string, request, session, url_for
from werkzeug.utils import secure_filename

from nube_supabase import SupabaseClient, load_config, make_cloud_path, new_upload_id


APP_NAME = "Control Financiero Nube"
APP_SHORT_NAME = "Finanzas Nube"
APP_VERSION = "2026-05-08-reports-integrated"
THEME_COLOR = "#12324a"
INTERNAL_TRANSFER_NATURE = "Transferencia entre cuentas propias"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}
SESSION_REFRESH_MARGIN_SECONDS = 300

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "control-financiero-nube-local")


@app.after_request
def prevent_browser_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


BASE_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <link rel="manifest" href="{{ url_for('manifest') }}">
  <link rel="icon" href="{{ url_for('app_icon') }}" type="image/svg+xml">
  <meta name="theme-color" content="{{ theme_color }}">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="{{ short_name }}">
  <style>
    body { margin: 0; background: #f6f7f9; color: #182230; font-family: Arial, sans-serif; }
    header { background: #12324a; color: white; padding: 18px 16px; }
    header h1 { margin: 0; font-size: 20px; }
    main { max-width: 780px; margin: 0 auto; padding: 16px; }
    form, section { background: white; border: 1px solid #d7dee8; border-radius: 8px; padding: 14px; margin-bottom: 14px; }
    label { display: block; margin: 12px 0 6px; font-weight: 700; font-size: 14px; }
    input, select, textarea { width: 100%; box-sizing: border-box; padding: 11px; border: 1px solid #b8c4d2; border-radius: 7px; font-size: 16px; }
    textarea { min-height: 80px; }
    summary { cursor: pointer; font-weight: 800; color: #17324d; padding: 10px 0; }
    button, a.button { display: inline-block; border: 0; border-radius: 7px; padding: 11px 14px; background: #1f4e78; color: white; font-weight: 700; text-decoration: none; margin-top: 12px; }
    button:disabled { opacity: .62; cursor: not-allowed; }
    a.secondary { background: #edf2f7; color: #17324d; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .messages { padding: 0; list-style: none; }
    .messages li { background: #e9f7ef; border: 1px solid #bce4ca; color: #155724; padding: 10px; border-radius: 7px; margin-bottom: 8px; }
    .messages li.error { background: #fdecea; border-color: #f5c2c0; color: #8a1f17; }
    .messages li.warning { background: #fff7e6; border-color: #ffd58a; color: #8a5a00; }
    .muted { color: #667085; font-size: 13px; }
    nav { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    nav a.button { margin-top: 0; }
    table { width: 100%; border-collapse: collapse; background: white; font-size: 14px; }
    th, td { padding: 9px; border-bottom: 1px solid #e2e8f0; text-align: left; vertical-align: top; }
    th { background: #edf2f7; }
    .amount { text-align: right; white-space: nowrap; }
    .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
    .card { background: white; border: 1px solid #d7dee8; border-radius: 8px; padding: 12px; }
    .card strong { display: block; color: #667085; font-size: 13px; margin-bottom: 6px; }
    .card span { display: block; color: #12324a; font-size: 20px; font-weight: 800; }
    .table-scroll { overflow-x: auto; }
    .install-box { background: #eef6ff; border-color: #b8d9ff; }
    .install-steps li { margin-bottom: 8px; }
    .install-button { width: 100%; font-size: 16px; margin-bottom: 12px; }
    .status-pill { display: inline-block; padding: 4px 8px; border-radius: 999px; background: #fff7e6; color: #8a5a00; font-weight: 700; font-size: 12px; }
    .status-ok { background: #e9f7ef; color: #155724; }
    .hint { background: #eef6ff; border: 1px solid #b8d9ff; border-radius: 7px; padding: 9px; color: #17324d; font-size: 13px; margin-top: 8px; }
    .quick-form { padding: 0; overflow: hidden; }
    .quick-head { background: #ffffff; padding: 16px; border-bottom: 1px solid #e2e8f0; }
    .quick-head h2 { margin: 0 0 6px; font-size: 22px; color: #12324a; }
    .quick-body { padding: 16px; }
    .file-input { position: absolute; inline-size: 1px; block-size: 1px; opacity: 0; overflow: hidden; }
    .file-picker { display: flex; align-items: center; justify-content: center; min-height: 104px; border: 2px dashed #93adc3; border-radius: 8px; background: #f8fafc; color: #17324d; font-weight: 800; text-align: center; padding: 18px; margin-top: 8px; }
    .file-picker:focus-within, .file-picker:hover { border-color: #1f4e78; background: #eef6ff; }
    .selected-file { margin-top: 8px; color: #475467; font-size: 13px; overflow-wrap: anywhere; }
    .send-button { width: 100%; font-size: 17px; padding: 13px 16px; }
    .sent-panel { border-color: #bce4ca; background: #e9f7ef; color: #155724; }
    .sent-panel h2 { margin: 0 0 8px; font-size: 20px; }
    .recent-list { display: grid; gap: 8px; }
    .recent-item { border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; background: #ffffff; }
    .recent-top { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
    .recent-title { font-weight: 800; color: #17324d; }
    .optional-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 680px) { .grid, .cards, .optional-grid { grid-template-columns: 1fr; } main { padding: 12px; } nav a.button { flex: 1 1 auto; text-align: center; } }
  </style>
</head>
<body>
  <header><h1>{{ title }}</h1></header>
  <main>
    {% if logged_in %}
      <nav>
        <a class="button" href="{{ url_for('index') }}">Capturar</a>
        <a class="button secondary" href="{{ url_for('reports') }}">Reportes</a>
        <a class="button secondary" href="{{ url_for('install') }}">Instalar</a>
        <a class="button secondary" href="{{ url_for('logout') }}">Salir</a>
      </nav>
    {% endif %}
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <ul class="messages">{% for category, message in messages %}<li class="{{ category }}">{{ message }}</li>{% endfor %}</ul>
      {% endif %}
    {% endwith %}
    {{ body|safe }}
  </main>
  <script>
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("{{ url_for('service_worker') }}").catch(() => {});
      });
    }
    let deferredInstallPrompt = null;
    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      deferredInstallPrompt = event;
      const button = document.getElementById("installAppButton");
      if (button) button.hidden = false;
    });
    async function installApp() {
      if (!deferredInstallPrompt) return;
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null;
      const button = document.getElementById("installAppButton");
      if (button) button.hidden = true;
    }
    function updateSelectedFiles(input) {
      const target = document.getElementById("selectedFileName");
      const submit = document.getElementById("sendUploadButton");
      if (!target) return;
      const files = Array.from(input.files || []);
      if (!files.length) {
        target.textContent = "Ningún archivo seleccionado";
        if (submit) submit.disabled = true;
        return;
      }
      const names = files.slice(0, 3).map((file) => file.name).join(", ");
      target.textContent = files.length > 3 ? `${names} y ${files.length - 3} más` : names;
      if (submit) submit.disabled = false;
    }
    function markUploading(form) {
      const button = document.getElementById("sendUploadButton");
      if (button) {
        button.disabled = true;
        button.textContent = "Enviando...";
      }
      return true;
    }
  </script>
</body>
</html>
"""


LOGIN_BODY = """
<form method="post" action="{{ url_for('login') }}" autocomplete="on">
  <label>Correo</label>
  <input type="email" name="email" autocomplete="username" required>
  <label>Contraseña</label>
  <input type="password" name="password" autocomplete="current-password" required>
  <button type="submit">Entrar</button>
</form>
"""


UPLOAD_BODY = """
{% if last_uploads %}
<section class="sent-panel">
  <h2>Información enviada</h2>
  <p>Se guardó en la nube y aparecerá en revisión al sincronizar la computadora.</p>
  {% for row in last_uploads %}
    <div class="recent-item">
      <div class="recent-top">
        <span class="recent-title">{{ upload_type_label(row.upload_type) }}</span>
        <span class="status-pill">{{ status_label(row.status) }}</span>
      </div>
      <div class="muted">{{ row.created_at or row.document_date or 'Recibido' }}</div>
    </div>
  {% endfor %}
</section>
{% endif %}

<form class="quick-form" method="post" enctype="multipart/form-data" onsubmit="return markUploading(this)">
  <div class="quick-head">
    <h2>Enviar documento</h2>
    <p class="muted">Usuario: {{ email }}</p>
  </div>
  <div class="quick-body">
    <label>Tipo</label>
    <select name="upload_type" required>
      <option value="ticket">Ticket / comprobante</option>
      <option value="estado_cuenta">Estado de cuenta</option>
      <option value="factura">Factura</option>
      <option value="otro">Otro</option>
    </select>

    <label>Archivo o foto</label>
    <label class="file-picker" for="documentInput">Seleccionar desde galería, cámara o archivos</label>
    <input id="documentInput" class="file-input" type="file" name="document" accept=".pdf,image/*,.png,.jpg,.jpeg,.webp,.heic,.heif" multiple required onchange="updateSelectedFiles(this)">
    <div id="selectedFileName" class="selected-file">Ningún archivo seleccionado</div>

    <details>
      <summary>Datos opcionales</summary>
      <div class="optional-grid">
        <div>
          <label>Fecha</label>
          <input type="text" name="document_date" placeholder="AAAA-MM-DD" inputmode="numeric" pattern="\\d{4}-\\d{2}-\\d{2}">
        </div>
        <div>
          <label>Ingreso / Egreso</label>
          <select name="movement_type">
            <option value="">Detectar automáticamente</option>
            <option value="Egreso">Egreso</option>
            <option value="Ingreso">Ingreso</option>
          </select>
        </div>
        <div>
          <label>Monto</label>
          <input type="number" name="amount" min="0.01" step="0.01" inputmode="decimal">
        </div>
        <div>
          <label>Moneda</label>
          <select name="currency">
            <option>MXN</option>
            <option>USD</option>
          </select>
        </div>
        <div>
          <label>Banco</label>
          <input name="bank" placeholder="Ej. BBVA">
        </div>
        <div>
          <label>Cuenta</label>
          <input name="account_name" placeholder="Ej. BBVA Empresa">
        </div>
      </div>
      <label>Concepto</label>
      <input name="concept" placeholder="Ej. gasolina, hospedaje, venta">
      <label>Personal / Empresa / Mixto</label>
      <select name="nature">
        <option>Pendiente de clasificar</option>
        <option>Personal</option>
        <option>Empresarial</option>
        <option>Mixto</option>
      </select>
    </details>

    <label>Nota breve</label>
    <textarea name="notes" placeholder="Opcional"></textarea>
    <button id="sendUploadButton" class="send-button" type="submit" disabled>Enviar a revisión</button>
  </div>
</form>
<section>
  <h2>Últimos envíos</h2>
  <div class="recent-list">
    {% for row in analysis_uploads[:8] %}
      <div class="recent-item">
        <div class="recent-top">
          <span class="recent-title">{{ upload_type_label(row.upload_type) }}</span>
          <span class="status-pill {% if row.status != 'pendiente' %}status-ok{% endif %}">{{ status_label(row.status) }}</span>
        </div>
        <div>{{ row.concept or row.notes or 'Pendiente de OCR' }}</div>
        <div class="muted">{{ row.document_date or row.created_at or 'Fecha pendiente' }}</div>
      </div>
    {% else %}
      <p>Todavía no hay archivos enviados.</p>
    {% endfor %}
  </div>
</section>
"""


INSTALL_BODY = """
<section class="install-box">
  <h2>Instalar en el celular</h2>
  <button id="installAppButton" class="install-button" type="button" onclick="installApp()" hidden>Instalar aplicación</button>
  <p>Dirección de la app privada: <strong>{{ app_url }}</strong></p>
  <ol class="install-steps">
    <li>Abre esta página en Huawei Browser, Chrome o Edge.</li>
    <li>Si aparece el botón Instalar aplicación, tócalo.</li>
    <li>Si no aparece, toca el menú del navegador.</li>
    <li>Elige Agregar a pantalla principal o Añadir a pantalla de inicio.</li>
    <li>Nombre sugerido: Control Financiero Nube.</li>
    <li>Confirma con Agregar.</li>
  </ol>
  <p class="muted">El icono queda como app instalada, pero seguirá pidiendo usuario y contraseña. Solo entran las cuentas que autorices.</p>
</section>
"""


REPORT_BODY = """
<form method="get" action="{{ url_for('reports') }}">
  <input type="hidden" name="submitted" value="1">
  <div class="grid">
    <div>
      <label>Periodo</label>
      <select name="period">
        {% for option in period_options %}
          <option value="{{ option }}" {% if option == period_filter %}selected{% endif %}>{{ option }}</option>
        {% endfor %}
      </select>
    </div>
    <div>
      <label>Fecha base</label>
      <input type="date" name="base_date" value="{{ base_date }}" required>
    </div>
  </div>
  <div class="grid">
    <div>
      <label>Desde</label>
      <input type="date" name="start_date" value="{{ start_date }}" required>
    </div>
    <div>
      <label>Hasta</label>
      <input type="date" name="end_date" value="{{ end_date }}" required>
    </div>
  </div>
  <div class="grid">
    <div>
      <label>Tipo</label>
      <select name="type">
        {% for option in type_options %}
          <option value="{{ option }}" {% if option == type_filter %}selected{% endif %}>{{ option }}</option>
        {% endfor %}
      </select>
    </div>
    <div>
      <label>Ámbito</label>
      <select name="scope">
        {% for option in scope_options %}
          <option value="{{ option }}" {% if option == scope_filter %}selected{% endif %}>{{ option }}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <div class="grid">
    <div>
      <label>Cuenta contiene</label>
      <input name="account_name" value="{{ account_name }}" placeholder="Ej. BBVA Empresa">
    </div>
  </div>
  <label><input type="checkbox" name="exclude_internal" value="1" {% if exclude_internal %}checked{% endif %}> No contar transferencias entre cuentas propias como ingreso/egreso</label>
  <label><input type="checkbox" name="include_pending" value="1" {% if include_pending %}checked{% endif %}> Incluir capturas pendientes del celular</label>
  <button type="submit">Generar reporte</button>
  <a class="button secondary" href="{{ csv_url }}">Descargar CSV</a>
</form>

<div class="cards">
  <div class="card"><strong>Ingresos</strong><span>{{ money(total_income) }}</span></div>
  <div class="card"><strong>Egresos</strong><span>{{ money(total_expense) }}</span></div>
  <div class="card"><strong>Resultado</strong><span>{{ money(total_income - total_expense) }}</span></div>
  <div class="card"><strong>Ingreso nacional</strong><span>{{ money(scope_totals.Nacional.income) }}</span></div>
  <div class="card"><strong>Ingreso internacional</strong><span>{{ money(scope_totals.Internacional.income) }}</span></div>
  <div class="card"><strong>Egreso nacional</strong><span>{{ money(scope_totals.Nacional.expense) }}</span></div>
  <div class="card"><strong>Egreso internacional</strong><span>{{ money(scope_totals.Internacional.expense) }}</span></div>
  <div class="card"><strong>Transferencias propias</strong><span>{{ money(transfer_total) }}</span></div>
</div>

<section>
  <h2>Resumen nacional / internacional</h2>
  <div class="table-scroll">
    <table>
      <thead><tr><th>Ámbito</th><th class="amount">Ingresos</th><th class="amount">Egresos</th><th class="amount">Resultado</th></tr></thead>
      <tbody>
        {% for row in scope_summary %}
          <tr><td>{{ row.scope }}</td><td class="amount">{{ money(row.income) }}</td><td class="amount">{{ money(row.expense) }}</td><td class="amount">{{ money(row.income - row.expense) }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>Resumen por cuenta</h2>
  <div class="table-scroll">
    <table>
      <thead><tr><th>Cuenta</th><th class="amount">Ingresos</th><th class="amount">Egresos</th><th class="amount">Resultado</th></tr></thead>
      <tbody>
        {% for row in account_summary %}
          <tr><td>{{ row.account }}</td><td class="amount">{{ money(row.income) }}</td><td class="amount">{{ money(row.expense) }}</td><td class="amount">{{ money(row.income - row.expense) }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>Resumen por categoría</h2>
  <div class="table-scroll">
    <table>
      <thead><tr><th>Tipo</th><th>Ámbito</th><th>Categoría</th><th class="amount">Total</th></tr></thead>
      <tbody>
        {% for row in category_summary %}
          <tr><td>{{ row.movement_type }}</td><td>{{ row.scope }}</td><td>{{ row.category }}</td><td class="amount">{{ money(row.total) }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>Movimientos nube</h2>
  <div class="table-scroll">
    <table>
      <thead><tr><th>Fecha</th><th>Estado</th><th>Tipo</th><th>Ámbito</th><th>Cuenta</th><th>Categoria</th><th>Concepto</th><th class="amount">Monto</th></tr></thead>
      <tbody>
        {% for row in rows %}
          <tr><td>{{ row.record_date }}</td><td>{{ row.status }}</td><td>{{ row.movement_type }}</td><td>{{ row.scope }}</td><td>{{ row.account }}</td><td>{{ row.category }}</td><td>{{ row.concept }}</td><td class="amount">{{ money(row.amount_mxn) }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
"""


def money(value: float | int | None) -> str:
    return f"${float(value or 0):,.2f}"


def status_label(status: str | None) -> str:
    labels = {
        "pendiente": "Pendiente",
        "en_revision": "En revisión",
        "confirmado": "Guardado",
        "descartado": "Descartado",
        "duplicado": "Duplicado",
    }
    return labels.get(str(status or "").lower(), str(status or "Pendiente"))


def upload_type_label(upload_type: str | None) -> str:
    labels = {
        "ticket": "Ticket / comprobante",
        "estado_cuenta": "Estado de cuenta",
        "factura": "Factura",
        "movimiento_manual": "Movimiento manual",
        "otro": "Otro",
    }
    return labels.get(str(upload_type or ""), str(upload_type or "Archivo"))


def normalize_token(value) -> str:
    text = str(value or "").upper()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


CATEGORY_RULES = [
    ("Combustible", ("GASOLINA", "GASOLINERA", "COMBUSTIBLE", "DIESEL", "PEMEX", "MAGNA", "PREMIUM", "G500", "SHELL", "MOBIL")),
    ("Hospedaje", ("HOTEL", "HOSPEDAJE", "MOTEL", "POSADA", "AIRBNB")),
    ("Peajes", ("PEAJE", "CASETA", "CAPUFE", "AUTOPISTA", "CUOTA")),
    ("Transporte", ("UBER", "DIDI", "TAXI", "AUTOBUS", "VUELO", "AEROMEXICO")),
    ("Alimentación operativa", ("RESTAURANTE", "RESTAURANT", "COMIDA", "ALIMENTOS", "OXXO", "SEVEN", "STARBUCKS", "TOKS", "VIPS", "WENDY", "BURGER", "PIZZA")),
    ("Mantenimiento", ("REFACCION", "TALLER", "LLANTA", "MANTENIMIENTO", "ACEITE")),
    ("Servicios administrativos", ("PAPELERIA", "IMPRESION", "CFE", "TELMEX", "INTERNET", "FACTURACION")),
    ("Viáticos", ("VIATICO", "VIATICOS")),
]


def infer_scope(concept: str, currency: str) -> str:
    text = normalize_token(concept)
    international_words = (
        "INTERNACIONAL", "EXTRANJERO", "EXTERIOR", "FOREIGN", "INTERNATIONAL",
        "SWIFT", "WIRE", "WISE", "PAYPAL", "PAYONEER", "WESTERN UNION",
        "USD", "DOLAR", "DOLARES", "EUR", "EURO", "IBAN", "USA",
        "ESTADOS UNIDOS", "CANADA", "CHINA", "EUROPA",
    )
    if normalize_token(currency or "MXN") != "MXN":
        return "Internacional"
    return "Internacional" if any(word in text for word in international_words) else "Nacional"


def infer_category(upload_type: str, movement_type: str | None, text: str, scope: str) -> str:
    normalized = normalize_token(text)
    if movement_type == "Ingreso":
        return f"Ingreso {scope.lower()}"
    for category, keywords in CATEGORY_RULES:
        if any(keyword in normalized for keyword in keywords):
            return category
    if movement_type == "Egreso":
        return f"Egreso {scope.lower()}"
    if upload_type == "estado_cuenta":
        return "Estado de cuenta"
    return "Pendiente de clasificar"


def infer_movement_type(upload_type: str, concept: str, amount: str | None) -> str | None:
    text = normalize_token(concept)
    income_words = ("INGRESO", "VENTA", "COBRO", "DEPOSITO", "DEPOSITO", "ABONO", "PAGO RECIBIDO", "TRANSFERENCIA RECIBIDA")
    expense_words = ("EGRESO", "GASTO", "COMPRA", "PAGO", "RETIRO", "CARGO", "TICKET", "FACTURA")
    if any(word in text for word in income_words):
        return "Ingreso"
    if any(word in text for word in expense_words):
        return "Egreso"
    if upload_type in {"ticket", "factura"} and amount:
        return "Egreso"
    return None


def infer_nature(form_nature: str, upload_type: str, movement_type: str | None, text: str) -> str:
    if form_nature and form_nature != "Pendiente de clasificar":
        return form_nature
    normalized = normalize_token(text)
    personal_words = ("PERSONAL", "FARMACIA", "COLEGIATURA", "CASA", "NETFLIX", "SPOTIFY", "ROPA")
    business_words = ("EMPRESA", "EMPRESARIAL", "FACTURA", "CLIENTE", "PROVEEDOR", "COMBUSTIBLE", "VIATICO", "HOSPEDAJE", "PEAJE")
    if any(word in normalized for word in personal_words):
        return "Personal"
    if any(word in normalized for word in business_words):
        return "Empresarial"
    if upload_type in {"ticket", "factura"} or movement_type == "Ingreso":
        return "Empresarial"
    return "Pendiente de clasificar"


def classify_mobile_upload(upload_type: str, form_data) -> dict:
    concept = (form_data.get("concept") or "").strip()
    notes = (form_data.get("notes") or "").strip()
    bank = (form_data.get("bank") or "").strip()
    account_name = (form_data.get("account_name") or "").strip()
    currency = (form_data.get("currency") or "MXN").strip().upper() or "MXN"
    full_text = " ".join([concept, notes, bank, account_name, upload_type])
    movement_type = (form_data.get("movement_type") or "").strip() or infer_movement_type(upload_type, full_text, form_data.get("amount"))
    scope = infer_scope(full_text, currency)
    category = infer_category(upload_type, movement_type, full_text, scope)
    nature = infer_nature((form_data.get("nature") or "Pendiente de clasificar").strip(), upload_type, movement_type, full_text)
    confidence = 0.82
    if movement_type:
        confidence += 0.02
    if category != "Pendiente de clasificar":
        confidence += 0.03
    if nature != "Pendiente de clasificar":
        confidence += 0.02
    confidence = min(confidence, 0.89)
    return {
        "movement_type": movement_type,
        "scope": scope,
        "category": category,
        "nature": nature,
        "confidence": confidence,
    }


def suggestion_note(classification: dict) -> str:
    return (
        "Sugerencia nube: "
        f"categoria={classification['category']}; "
        f"ambito={classification['scope']}; "
        f"confianza={int(round(classification['confidence'] * 100))}%."
    )


def suggested_category_from_notes(notes: str | None) -> str:
    match = re.search(r"Sugerencia nube:\s*categoria=([^;]+);", str(notes or ""), re.IGNORECASE)
    return match.group(1).strip() if match else ""


def suggested_scope_from_notes(notes: str | None) -> str:
    match = re.search(r"ambito=([^;]+);", str(notes or ""), re.IGNORECASE)
    return match.group(1).strip() if match else ""


def suggested_summary(row: dict) -> str:
    category = suggested_category_from_notes(row.get("notes"))
    scope = suggested_scope_from_notes(row.get("notes"))
    movement_type = row.get("movement_type") or "Pendiente"
    nature = row.get("nature") or "Pendiente de clasificar"
    pieces = [str(movement_type)]
    if category:
        pieces.append(category)
    if scope:
        pieces.append(scope)
    if nature:
        pieces.append(nature)
    return " / ".join(piece for piece in pieces if piece)


def load_analysis_uploads() -> list[dict]:
    try:
        return cloud_client().list_cloud_uploads(limit=30)
    except Exception:
        # Sesiones viejas, creadas antes de guardar refresh_token, pueden seguir subiendo
        # con el backend aunque no puedan listar hasta volver a iniciar sesion.
        return []


def parse_report_date(value: str | None, fallback: date) -> date:
    try:
        return date.fromisoformat(value or "")
    except ValueError:
        return fallback


def report_period_range(period: str, base: date) -> tuple[date, date]:
    if period == "Semanal":
        start = base - timedelta(days=base.weekday())
        return start, start + timedelta(days=6)
    if period == "Mensual":
        start = base.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, next_month - timedelta(days=1)
    if period == "Trimestral":
        first_month = ((base.month - 1) // 3) * 3 + 1
        start = date(base.year, first_month, 1)
        next_quarter_month = first_month + 3
        if next_quarter_month > 12:
            next_quarter = date(base.year + 1, 1, 1)
        else:
            next_quarter = date(base.year, next_quarter_month, 1)
        return start, next_quarter - timedelta(days=1)
    if period == "Anual":
        return date(base.year, 1, 1), date(base.year, 12, 31)
    return base - timedelta(days=30), base


def report_scope(category: str, nature: str, concept: str, currency: str, notes: str = "") -> str:
    suggested = suggested_scope_from_notes(notes)
    if suggested in {"Nacional", "Internacional"}:
        return suggested
    return infer_scope(" ".join([category or "", nature or "", concept or "", notes or ""]), currency or "MXN")


def is_internal_transfer_report_row(row: dict) -> bool:
    text = normalize_token(" ".join([
        str(row.get("nature") or ""),
        str(row.get("category") or ""),
        str(row.get("concept") or ""),
    ]))
    markers = (
        "TRANSFERENCIA ENTRE CUENTAS PROPIAS",
        "TRASPASO ENTRE CUENTAS",
        "CUENTAS PROPIAS",
        "MIS CUENTAS",
        "MISMA TITULARIDAD",
    )
    return any(marker in text for marker in markers)


def normalize_cloud_report_row(row: dict, pending: bool = False) -> dict:
    if pending:
        amount = float(row.get("amount") or 0)
        category = suggested_category_from_notes(row.get("notes")) or upload_type_label(row.get("upload_type"))
        scope = report_scope(category, row.get("nature") or "", row.get("concept") or "", row.get("currency") or "MXN", row.get("notes") or "")
        return {
            "record_date": row.get("document_date") or "",
            "status": f"Pendiente: {row.get('status', '')}",
            "movement_type": row.get("movement_type") or "",
            "scope": scope,
            "account": row.get("account_name") or "Sin cuenta",
            "category": category,
            "nature": row.get("nature") or "",
            "concept": row.get("concept") or "",
            "amount_mxn": amount,
            "currency": row.get("currency") or "MXN",
        }
    category = row.get("category_name") or ""
    scope = report_scope(category, row.get("nature") or "", row.get("concept") or "", row.get("currency") or "MXN")
    return {
        "record_date": row.get("movement_date") or "",
        "status": row.get("status") or "guardado",
        "movement_type": row.get("movement_type") or "",
        "scope": scope,
        "account": row.get("account_name") or "Sin cuenta",
        "category": category,
        "nature": row.get("nature") or "",
        "concept": row.get("concept") or "",
        "amount_mxn": float(row.get("amount_mxn") or 0),
        "currency": row.get("currency") or "MXN",
    }


def load_cloud_report_context() -> dict:
    today = date.today()
    period_options = ["Semanal", "Mensual", "Trimestral", "Anual", "Personalizado"]
    period_filter = request.args.get("period", "Mensual")
    if period_filter not in period_options:
        period_filter = "Mensual"
    base_date = parse_report_date(request.args.get("base_date"), today)
    if period_filter == "Personalizado":
        start = parse_report_date(request.args.get("start_date"), today - timedelta(days=30))
        end = parse_report_date(request.args.get("end_date"), today)
    else:
        start, end = report_period_range(period_filter, base_date)
    if start > end:
        start, end = end, start
    type_filter = request.args.get("type", "Todos")
    if type_filter not in ("Todos", "Ingreso", "Egreso"):
        type_filter = "Todos"
    movement_type = "" if type_filter == "Todos" else type_filter
    scope_filter = request.args.get("scope", "Todos")
    if scope_filter not in ("Todos", "Nacional", "Internacional"):
        scope_filter = "Todos"
    account_name = request.args.get("account_name", "").strip()
    raw_exclude = request.args.get("exclude_internal")
    exclude_internal = True if raw_exclude is None and not request.args.get("submitted") else raw_exclude == "1"
    include_pending = request.args.get("include_pending", "1") == "1"

    client = cloud_client()
    saved_rows = client.list_cloud_movements(
        start.isoformat(),
        end.isoformat(),
        movement_type=movement_type,
        account_name=account_name,
        exclude_internal=False,
    )
    rows = [normalize_cloud_report_row(row) for row in saved_rows]
    if include_pending:
        pending_rows = client.list_cloud_upload_report_rows(
            start.isoformat(),
            end.isoformat(),
            movement_type=movement_type,
            account_name=account_name,
            exclude_internal=False,
        )
        rows.extend(normalize_cloud_report_row(row, pending=True) for row in pending_rows)
    transfer_rows = [row for row in rows if is_internal_transfer_report_row(row)]
    transfer_total = sum(float(row["amount_mxn"]) for row in transfer_rows)
    if exclude_internal:
        rows = [row for row in rows if not is_internal_transfer_report_row(row)]
    if scope_filter != "Todos":
        rows = [row for row in rows if row["scope"] == scope_filter]

    total_income = sum(float(row["amount_mxn"]) for row in rows if row["movement_type"] == "Ingreso")
    total_expense = sum(float(row["amount_mxn"]) for row in rows if row["movement_type"] == "Egreso")
    by_scope: dict[str, dict[str, float]] = {
        "Nacional": {"income": 0.0, "expense": 0.0},
        "Internacional": {"income": 0.0, "expense": 0.0},
    }
    by_account: dict[str, dict[str, float]] = {}
    by_category: dict[tuple[str, str, str], float] = {}
    for row in rows:
        scope = row["scope"] if row["scope"] in by_scope else "Nacional"
        by_scope.setdefault(scope, {"income": 0.0, "expense": 0.0})
        account = row["account"]
        by_account.setdefault(account, {"income": 0.0, "expense": 0.0})
        if row["movement_type"] == "Ingreso":
            by_account[account]["income"] += float(row["amount_mxn"])
            by_scope[scope]["income"] += float(row["amount_mxn"])
        elif row["movement_type"] == "Egreso":
            by_account[account]["expense"] += float(row["amount_mxn"])
            by_scope[scope]["expense"] += float(row["amount_mxn"])
        key = (row["movement_type"] or "Pendiente", scope, row["category"] or "Sin categoria")
        by_category[key] = by_category.get(key, 0.0) + float(row["amount_mxn"])
    scope_summary = [
        {"scope": scope, "income": values["income"], "expense": values["expense"]}
        for scope, values in by_scope.items()
    ]
    account_summary = [
        {"account": account, "income": values["income"], "expense": values["expense"]}
        for account, values in sorted(by_account.items())
    ]
    category_summary = [
        {"movement_type": key[0], "scope": key[1], "category": key[2], "total": total}
        for key, total in sorted(by_category.items())
    ]
    csv_url = url_for(
        "reports_csv",
        period=period_filter,
        base_date=base_date.isoformat(),
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        type=type_filter,
        scope=scope_filter,
        account_name=account_name,
        exclude_internal="1" if exclude_internal else "0",
        include_pending="1" if include_pending else "0",
    )
    return {
        "period_options": period_options,
        "period_filter": period_filter,
        "base_date": base_date.isoformat(),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "type_filter": type_filter,
        "type_options": ["Todos", "Ingreso", "Egreso"],
        "scope_filter": scope_filter,
        "scope_options": ["Todos", "Nacional", "Internacional"],
        "account_name": account_name,
        "exclude_internal": exclude_internal,
        "include_pending": include_pending,
        "rows": rows,
        "scope_totals": by_scope,
        "scope_summary": scope_summary,
        "account_summary": account_summary,
        "category_summary": category_summary,
        "transfer_total": transfer_total,
        "total_income": total_income,
        "total_expense": total_expense,
        "csv_url": csv_url,
        "money": money,
    }


def page(body_template: str, **context):
    body = render_template_string(body_template, **context)
    return render_template_string(
        BASE_TEMPLATE,
        title=APP_NAME,
        short_name=APP_SHORT_NAME,
        theme_color=THEME_COLOR,
        logged_in=bool(session.get("access_token")),
        body=body,
    )


def set_single_flash(message: str, category: str = "success") -> None:
    session["_flashes"] = [(category, message)]


def store_auth_session(result: dict, email: str | None = None) -> None:
    session["access_token"] = result["access_token"]
    if result.get("refresh_token"):
        session["refresh_token"] = result["refresh_token"]
    if result.get("user", {}).get("id"):
        session["user_id"] = result["user"]["id"]
    if email:
        session["email"] = email
    expires_at = result.get("expires_at")
    if expires_at:
        session["token_expires_at"] = int(expires_at)
    else:
        session["token_expires_at"] = int(time.time()) + int(result.get("expires_in") or 3600)


def refresh_user_session(force: bool = False) -> bool:
    refresh_token = session.get("refresh_token")
    if not refresh_token:
        return False
    expires_at = int(session.get("token_expires_at") or 0)
    if not force and expires_at and expires_at - int(time.time()) > SESSION_REFRESH_MARGIN_SECONDS:
        return False
    config = load_config()
    client = SupabaseClient(config)
    result = client.refresh_session(refresh_token)
    store_auth_session(result)
    return True


def token_time_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "claim timestamp" in message
        or "jwt expired" in message
        or "invalid jwt" in message
        or "expired" in message
    )


def cloud_client(server: bool = False) -> SupabaseClient:
    config = load_config()
    if server and config.service_role_key:
        return SupabaseClient(config, access_token=config.service_role_key)
    refresh_user_session()
    token = session.get("access_token")
    return SupabaseClient(config, access_token=token)


def save_cloud_upload(file, upload_type: str, form_data) -> tuple[dict, str]:
    if not file or not file.filename:
        raise ValueError("Selecciona un archivo PDF o imagen.")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato no permitido. Usa PDF o imagen.")
    document_date = (form_data.get("document_date") or "").strip()
    if document_date:
        try:
            document_date = date.fromisoformat(document_date).isoformat()
        except ValueError as exc:
            raise ValueError("Fecha inválida. Usa el formato AAAA-MM-DD o deja la fecha vacía para OCR.") from exc
    else:
        document_date = None
    client = cloud_client(server=True)
    upload_id = new_upload_id()
    safe_name = secure_filename(file.filename) or f"documento{suffix}"
    cloud_path = make_cloud_path(client.config.organization_id, session["user_id"], upload_id, safe_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / safe_name
        file.save(local_path)
        try:
            client.upload_file(local_path, cloud_path)
        except RuntimeError as exc:
            if not token_time_error(exc):
                raise
            refresh_user_session(force=True)
            client = cloud_client(server=True)
            client.upload_file(local_path, cloud_path)
    amount = form_data.get("amount")
    classification = classify_mobile_upload(upload_type, form_data)
    movement_type = classification["movement_type"] or None
    notes = form_data.get("notes", "").strip()
    enriched_notes = " ".join(part for part in [notes, suggestion_note(classification)] if part).strip()
    nature = classification["nature"]
    record = client.create_upload_record(
        {
            "id": upload_id,
            "uploaded_by": session["user_id"],
            "upload_type": upload_type,
            "movement_type": movement_type,
            "document_date": document_date,
            "concept": form_data.get("concept", "").strip(),
            "amount": float(amount) if amount else None,
            "currency": form_data.get("currency", "MXN"),
            "bank": form_data.get("bank", "").strip(),
            "account_name": form_data.get("account_name", "").strip(),
            "nature": nature,
            "storage_path": cloud_path,
            "notes": enriched_notes,
            "status": "pendiente",
        }
    )
    return record, upload_id


@app.get("/manifest.webmanifest")
def manifest():
    payload = {
        "name": APP_NAME,
        "short_name": APP_SHORT_NAME,
        "start_url": url_for("index"),
        "scope": "/",
        "id": url_for("index"),
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "background_color": "#f6f7f9",
        "theme_color": THEME_COLOR,
        "description": "Captura privada de tickets, estados de cuenta y reportes financieros.",
        "categories": ["finance", "business", "productivity"],
        "icons": [
            {"src": url_for("app_icon"), "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"},
        ],
    }
    return Response(json.dumps(payload, ensure_ascii=False), mimetype="application/manifest+json")


@app.get("/icon.svg")
def app_icon():
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 128'>
<rect width='128' height='128' rx='24' fill='{THEME_COLOR}'/>
<path d='M28 42h72v12H28zM28 62h72v12H28zM28 82h46v12H28z' fill='#ffffff' opacity='.95'/>
<circle cx='92' cy='88' r='14' fill='#64d2a6'/>
<path d='M86 88l5 5 10-12' fill='none' stroke='#12324a' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")


@app.get("/sw.js")
def service_worker():
    script = """
const CACHE_NAME = "control-financiero-nube-v4";
const STATIC_ASSETS = ["/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const acceptsHtml = request.headers.get("accept")?.includes("text/html");

  if (request.mode === "navigate" || acceptsHtml) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response("<!doctype html><title>Sin conexión</title><p>Sin conexión. Intenta de nuevo cuando tengas internet.</p>", {
          headers: { "Content-Type": "text/html; charset=utf-8" }
        })
      )
    );
    return;
  }

  if (isSameOrigin && STATIC_ASSETS.includes(url.pathname)) {
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
    return;
  }

  event.respondWith(fetch(request));
});
"""
    return Response(script, mimetype="application/javascript", headers={"Service-Worker-Allowed": "/"})


@app.get("/salud")
def health():
    try:
        config = load_config()
        payload = {
            "ok": True,
            "version": APP_VERSION,
            "supabase_url": bool(config.supabase_url),
            "organization_id": bool(config.organization_id),
            "bucket": config.bucket,
            "server_upload_enabled": bool(config.service_role_key),
        }
        status = 200
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        status = 500
    return Response(json.dumps(payload, ensure_ascii=False), status=status, mimetype="application/json")


@app.get("/instalar")
def install():
    if not session.get("access_token"):
        return redirect(url_for("login"))
    return page(INSTALL_BODY, app_url=request.url_root.rstrip("/"))


@app.get("/reportes")
def reports():
    if not session.get("access_token"):
        return redirect(url_for("login"))
    try:
        return page(REPORT_BODY, **load_cloud_report_context())
    except Exception as exc:
        flash(f"No se pudo generar el reporte: {exc}", "error")
        return redirect(url_for("index"))


@app.get("/reportes.csv")
def reports_csv():
    if not session.get("access_token"):
        return redirect(url_for("login"))
    try:
        context = load_cloud_report_context()
    except Exception as exc:
        flash(f"No se pudo generar CSV: {exc}", "error")
        return redirect(url_for("reports"))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Estado", "Tipo", "Ambito", "Cuenta", "Categoria", "Naturaleza", "Concepto", "Monto MXN"])
    for row in context["rows"]:
        writer.writerow(
            [
                row["record_date"],
                row["status"],
                row["movement_type"],
                row["scope"],
                row["account"],
                row["category"],
                row["nature"],
                row["concept"],
                f'{float(row["amount_mxn"]):.2f}',
            ]
        )
    filename = f"reporte_nube_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/")
def index():
    if not session.get("access_token"):
        return redirect(url_for("login"))
    analysis_uploads = load_analysis_uploads()
    sent_ids = {value for value in request.args.get("enviados", "").split(",") if value}
    last_uploads = [row for row in analysis_uploads if row.get("id") in sent_ids]
    return page(
        UPLOAD_BODY,
        email=session.get("email", ""),
        analysis_uploads=analysis_uploads,
        last_uploads=last_uploads,
        status_label=status_label,
        upload_type_label=upload_type_label,
        suggested_summary=suggested_summary,
    )


@app.get("/analisis")
def analysis():
    if not session.get("access_token"):
        return redirect(url_for("login"))
    return redirect(url_for("index"))


@app.post("/analisis")
def upload_for_analysis():
    if not session.get("access_token"):
        return redirect(url_for("login"))
    return upload()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return page(LOGIN_BODY)
    try:
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        if not email or not password:
            set_single_flash("Escribe tu correo y contraseña para entrar.", "error")
            return redirect(url_for("login"))
        config = load_config()
        client = SupabaseClient(config)
        result = client.sign_in_with_password(email, password)
        store_auth_session(result, email)
        set_single_flash("Sesion iniciada.", "success")
        return redirect(url_for("index"))
    except Exception as exc:
        message = str(exc)
        if "invalid login credentials" in message.lower() or "invalid_credentials" in message.lower():
            message = "Correo o contraseña no válidos. Revisa que sean los mismos que registraste."
        elif "400 bad request" in message.lower():
            message = "El navegador envió una sesión incompleta. Escribe de nuevo tu correo y contraseña."
        else:
            message = f"No se pudo iniciar sesion: {message}"
        set_single_flash(message, "error")
        return redirect(url_for("login"))


@app.get("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada.", "success")
    return redirect(url_for("login"))


@app.post("/")
def upload():
    if not session.get("access_token"):
        return redirect(url_for("login"))
    try:
        upload_type = request.form.get("upload_type") or request.form.get("analysis_type") or "ticket"
        files = [file for file in request.files.getlist("document") if file and file.filename]
        if not files:
            raise ValueError("Selecciona una foto, imagen, PDF o archivo.")
        upload_ids: list[str] = []
        for file in files:
            record, upload_id = save_cloud_upload(file, upload_type, request.form)
            upload_ids.append(upload_id)
        if len(upload_ids) == 1:
            set_single_flash("Listo. Información enviada a revisión.", "success")
        else:
            set_single_flash(f"Listo. Se enviaron {len(upload_ids)} archivos a revisión.", "success")
        return redirect(url_for("index", enviados=",".join(upload_ids[:8])))
    except Exception as exc:
        set_single_flash(f"No se pudo subir: {exc}", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5050")), debug=False)
