package com.agroconnections.finanzas;

import android.app.Activity;
import android.content.ClipData;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.text.InputType;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.NumberFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

public class MainActivity extends Activity {
    private static final int PICK_FILES = 100;
    private static final int TAKE_PHOTO = 101;
    private static final String PREF_PENDING_UPLOADS = "pending_uploads";
    private static final String PREF_LAST_NOTICE = "last_notice";

    private final List<Uri> selectedUris = new ArrayList<>();
    private SharedPreferences prefs;
    private LinearLayout root;
    private TextView statusText;
    private TextView selectedText;
    private Uri pendingCameraUri;
    private int reportContentStart = -1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("control_financiero", MODE_PRIVATE);
        if (getAccessToken().isEmpty()) {
            showLogin();
        } else {
            showCapture();
        }
    }

    private void setScreen() {
        ScrollView scrollView = new ScrollView(this);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(16), dp(16), dp(24));
        root.setBackgroundColor(Color.rgb(246, 247, 249));
        scrollView.addView(root);
        setContentView(scrollView);
    }

    private void showLogin() {
        setScreen();
        addHeader("Control Financiero");
        addMuted("Aplicacion instalada. Entra con tu usuario autorizado de Supabase.");

        EditText email = input("Correo");
        email.setInputType(InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText password = input("Contrasena");
        password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);

        Button button = primaryButton("Entrar");
        button.setOnClickListener(v -> runWithStatus("Iniciando sesion...", () -> {
            signIn(email.getText().toString().trim(), password.getText().toString());
            runOnUiThread(this::showCapture);
        }));
        root.addView(button);
        statusText = addStatus();
    }

    private void showShell(String active) {
        setScreen();
        addHeader("Control Financiero");
        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(0, dp(8), 0, dp(8));

        Button capture = navButton("Capturar", "Capturar".equals(active));
        capture.setOnClickListener(v -> showCapture());
        Button reports = navButton("Reportes", "Reportes".equals(active));
        reports.setOnClickListener(v -> showReports());
        Button logout = navButton("Salir", false);
        logout.setOnClickListener(v -> {
            prefs.edit().clear().apply();
            showLogin();
        });

        nav.addView(capture);
        nav.addView(reports);
        nav.addView(logout);
        root.addView(nav);
    }

    private void showCapture() {
        showShell("Capturar");
        addSectionTitle("Enviar documento");
        addMuted("Selecciona fotos, PDF o archivos del celular. La computadora los analizara y los mostrara en revision.");

        Spinner typeSpinner = new Spinner(this);
        String[] types = {"Ticket / comprobante", "Estado de cuenta", "Factura", "Otro"};
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, types);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        typeSpinner.setAdapter(adapter);
        root.addView(typeSpinner);

        Button pick = secondaryButton("Elegir galeria o archivos");
        pick.setOnClickListener(v -> openFilePicker());
        root.addView(pick);

        Button photo = secondaryButton("Tomar foto");
        photo.setOnClickListener(v -> openCamera());
        root.addView(photo);

        selectedText = addMuted("Sin archivos seleccionados");

        EditText notes = input("Nota opcional");
        notes.setSingleLine(false);
        notes.setMinLines(2);

        Button upload = primaryButton("Enviar a revision");
        upload.setOnClickListener(v -> {
            if (selectedUris.isEmpty()) {
                toast("Selecciona una foto, PDF o archivo.");
                return;
            }
            String uploadType = uploadTypeFromSpinner(typeSpinner.getSelectedItemPosition());
            runWithStatus("Guardando pendientes y enviando...", () -> {
                int queued = enqueueSelectedUploads(uploadType, notes.getText().toString());
                int[] result = processPendingQueue();
                runOnUiThread(() -> {
                    selectedUris.clear();
                    updateSelectedText();
                    notes.setText("");
                    saveNotice(buildQueueMessage(queued, result[0], result[1]));
                    showCapture();
                });
            });
        });
        root.addView(upload);

        Button retry = secondaryButton("Enviar pendientes");
        retry.setOnClickListener(v -> runWithStatus("Reintentando pendientes...", () -> {
            int[] result = processPendingQueue();
            runOnUiThread(() -> {
                saveNotice(buildQueueMessage(0, result[0], result[1]));
                showCapture();
            });
        }));
        root.addView(retry);

        statusText = addStatus();
        showLastNotice();
        addPendingSummary();
        addSectionTitle("Ultimos envios");
        loadRecentUploads();
    }

    private String buildQueueMessage(int queued, int sent, int failed) {
        if (sent > 0 && failed == 0) {
            return sent == 1
                    ? "Informacion enviada. Aparecera en revision en la computadora."
                    : "Se enviaron " + sent + " archivos. Apareceran en revision en la computadora.";
        }
        if (failed > 0) {
            return "Se guardaron pendientes. Enviados: " + sent + ". Pendientes por reintentar: " + failed + ".";
        }
        if (queued > 0) {
            return "Se guardaron " + queued + " pendientes para enviar cuando haya internet.";
        }
        return "No hay pendientes por enviar.";
    }

    private void addPendingSummary() {
        JSONArray pending = getPendingUploads();
        int count = pending.length();
        addSectionTitle("Pendientes en este celular");
        if (count == 0) {
            addMuted("No hay documentos pendientes.");
            return;
        }
        addMuted(count == 1
                ? "Hay 1 documento guardado en el celular esperando envio."
                : "Hay " + count + " documentos guardados en el celular esperando envio.");
        for (int i = 0; i < pending.length(); i++) {
            JSONObject row = pending.optJSONObject(i);
            if (row == null) {
                continue;
            }
            addSmallItem(
                    row.optString("status", "Pendiente") + " - " + uploadTypeLabel(row.optString("upload_type")),
                    row.optString("file_name", "Documento"),
                    row.optString("error", row.optString("created_at", ""))
            );
        }
    }

    private int enqueueSelectedUploads(String uploadType, String notes) throws Exception {
        JSONArray pending = getPendingUploads();
        String createdAt = new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(new Date());
        for (Uri uri : new ArrayList<>(selectedUris)) {
            JSONObject item = new JSONObject();
            item.put("id", UUID.randomUUID().toString());
            item.put("uri", uri.toString());
            item.put("file_name", sanitizeFileName(getDisplayName(uri)));
            item.put("upload_type", uploadType);
            item.put("notes", notes == null ? "" : notes.trim());
            item.put("status", "Pendiente");
            item.put("attempts", 0);
            item.put("error", "");
            item.put("created_at", createdAt);
            pending.put(item);
        }
        savePendingUploads(pending);
        return selectedUris.size();
    }

    private int[] processPendingQueue() throws Exception {
        JSONArray pending = getPendingUploads();
        JSONArray remaining = new JSONArray();
        int sent = 0;
        int failed = 0;
        for (int i = 0; i < pending.length(); i++) {
            JSONObject item = pending.optJSONObject(i);
            if (item == null) {
                continue;
            }
            try {
                uploadPendingItem(item);
                sent++;
            } catch (Exception exc) {
                item.put("attempts", item.optInt("attempts", 0) + 1);
                item.put("status", "Fallo");
                item.put("error", shortError(exc.getMessage()));
                remaining.put(item);
                failed++;
            }
        }
        savePendingUploads(remaining);
        return new int[]{sent, failed};
    }

    private void uploadPendingItem(JSONObject item) throws Exception {
        refreshIfNeeded();
        String uploadId = item.getString("id");
        Uri uri = Uri.parse(item.getString("uri"));
        String fileName = sanitizeFileName(item.optString("file_name", getDisplayName(uri)));
        String uploadType = item.optString("upload_type", "ticket");
        String notes = item.optString("notes", "");
        String storagePath = SupabaseConfig.ORGANIZATION_ID + "/" + prefs.getString("user_id", "") + "/" + uploadId + "/" + fileName;
        byte[] bytes = readBytes(uri);
        String mime = getContentResolver().getType(uri);
        if (mime == null || mime.trim().isEmpty()) {
            mime = "application/octet-stream";
        }
        storageUpload(storagePath, bytes, mime);

        JSONObject record = new JSONObject();
        record.put("id", uploadId);
        record.put("organization_id", SupabaseConfig.ORGANIZATION_ID);
        record.put("uploaded_by", prefs.getString("user_id", ""));
        record.put("upload_type", uploadType);
        record.put("concept", "");
        record.put("currency", "MXN");
        record.put("bank", "");
        record.put("account_name", "");
        record.put("nature", "Pendiente de clasificar");
        record.put("storage_path", storagePath);
        record.put("notes", notes);
        record.put("status", "pendiente");
        JSONArray payload = new JSONArray();
        payload.put(record);
        restPost("/rest/v1/cloud_uploads?on_conflict=id", payload.toString());
    }

    private JSONArray getPendingUploads() {
        String raw = prefs.getString(PREF_PENDING_UPLOADS, "[]");
        try {
            return new JSONArray(raw == null || raw.trim().isEmpty() ? "[]" : raw);
        } catch (Exception ignored) {
            return new JSONArray();
        }
    }

    private void savePendingUploads(JSONArray pending) {
        prefs.edit().putString(PREF_PENDING_UPLOADS, pending.toString()).apply();
    }

    private void saveNotice(String message) {
        prefs.edit().putString(PREF_LAST_NOTICE, message == null ? "" : message).apply();
    }

    private void showLastNotice() {
        String message = prefs.getString(PREF_LAST_NOTICE, "");
        if (message == null || message.trim().isEmpty()) {
            return;
        }
        prefs.edit().remove(PREF_LAST_NOTICE).apply();
        addNotice(message);
    }

    private String shortError(String message) {
        String value = message == null ? "Sin detalle" : message.trim();
        if (value.length() > 120) {
            value = value.substring(0, 120) + "...";
        }
        return value;
    }

    private void showReports() {
        showShell("Reportes");
        addSectionTitle("Reportes");
        addMuted("Consulta los movimientos guardados y sincronizados desde la computadora.");

        Spinner periodSpinner = new Spinner(this);
        String[] periods = {"Semana actual", "Mes actual", "Trimestre actual", "Ano actual"};
        ArrayAdapter<String> periodAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, periods);
        periodAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        periodSpinner.setAdapter(periodAdapter);
        periodSpinner.setSelection(1);
        root.addView(periodSpinner);

        EditText accountFilter = input("Cuenta contiene (opcional)");

        Button generate = primaryButton("Generar reporte");
        generate.setOnClickListener(v -> runWithStatus("Generando reporte...", () ->
                loadReport(periodSpinner.getSelectedItemPosition(), accountFilter.getText().toString())
        ));
        root.addView(generate);

        statusText = addStatus();
        reportContentStart = root.getChildCount();
        runWithStatus("Cargando reporte...", () -> loadReport(1, ""));
    }

    private void loadReport(int periodIndex, String accountFilter) throws Exception {
        String[] range = reportRange(periodIndex);
        String filter = accountFilter == null ? "" : accountFilter.trim();
        String query = "organization_id=eq." + SupabaseConfig.ORGANIZATION_ID
                + "&movement_date=gte." + range[0]
                + "&movement_date=lte." + range[1]
                + "&select=movement_date,movement_type,account_name,account_owner_type,category_name,nature,concept,amount_mxn,currency"
                + "&order=movement_date.desc";
        if (!filter.isEmpty()) {
            query += "&account_name=ilike.*" + urlParam(filter) + "*";
        }
        JSONArray rows = new JSONArray(restGet("/rest/v1/cloud_movements?" + query));

        Totals total = new Totals();
        Totals national = new Totals();
        Totals international = new Totals();
        Totals transfers = new Totals();
        Map<String, Totals> byAccount = new LinkedHashMap<>();
        Map<String, Totals> byCategory = new LinkedHashMap<>();

        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.getJSONObject(i);
            String type = row.optString("movement_type");
            double amount = row.optDouble("amount_mxn", 0);
            if (isOwnTransfer(row)) {
                transfers.add(type, amount);
                continue;
            }
            total.add(type, amount);
            if (isInternationalMovement(row)) {
                international.add(type, amount);
            } else {
                national.add(type, amount);
            }
            totalsFor(byAccount, cleanLabel(row.optString("account_name"), "Sin cuenta")).add(type, amount);
            totalsFor(byCategory, cleanLabel(row.optString("category_name"), "Sin categoria")).add(type, amount);
        }

        runOnUiThread(() -> {
            statusText.setText("");
            clearReportArea();
            addMuted(range[2] + " | " + range[0] + " a " + range[1]
                    + (filter.isEmpty() ? "" : " | Cuenta: " + filter));
            addSectionTitle("Concentrado");
            addCard("Ingresos", money(total.income));
            addCard("Egresos", money(total.expense));
            addCard("Resultado", money(total.result()));
            addCard("Ingresos nacionales", money(national.income));
            addCard("Egresos nacionales", money(national.expense));
            addCard("Ingresos internacionales", money(international.income));
            addCard("Egresos internacionales", money(international.expense));
            if (transfers.totalMovement() > 0) {
                addCard("Transferencias propias",
                        "Entradas: " + money(transfers.income) + "\nSalidas: " + money(transfers.expense));
            }

            addSectionTitle("Por cuenta");
            if (byAccount.isEmpty()) {
                addMuted("No hay movimientos en el periodo seleccionado.");
            } else {
                for (Map.Entry<String, Totals> entry : byAccount.entrySet()) {
                    Totals item = entry.getValue();
                    addSmallItem(
                            entry.getKey(),
                            "Ingresos: " + money(item.income) + " | Egresos: " + money(item.expense),
                            "Resultado: " + money(item.result())
                    );
                }
            }

            addSectionTitle("Por categoria");
            if (byCategory.isEmpty()) {
                addMuted("No hay categorias en el periodo seleccionado.");
            } else {
                int shown = 0;
                for (Map.Entry<String, Totals> entry : byCategory.entrySet()) {
                    if (shown >= 20) {
                        addMuted("Se muestran las primeras 20 categorias del periodo.");
                        break;
                    }
                    Totals item = entry.getValue();
                    addSmallItem(
                            entry.getKey(),
                            "Ingresos: " + money(item.income) + " | Egresos: " + money(item.expense),
                            "Resultado: " + money(item.result())
                    );
                    shown++;
                }
            }

            addSectionTitle("Movimientos recientes");
            for (int i = 0; i < Math.min(rows.length(), 15); i++) {
                try {
                    JSONObject row = rows.getJSONObject(i);
                    String scope = isOwnTransfer(row)
                            ? "Transferencia propia"
                            : (isInternationalMovement(row) ? "Internacional" : "Nacional");
                    addSmallItem(
                            row.optString("movement_date") + " - " + row.optString("movement_type") + " - " + scope,
                            row.optString("concept", "Sin concepto"),
                            cleanLabel(row.optString("account_name"), "Sin cuenta")
                                    + " | " + cleanLabel(row.optString("category_name"), "Sin categoria")
                                    + " | " + money(row.optDouble("amount_mxn", 0))
                    );
                } catch (Exception ignored) {
                }
            }
            if (rows.length() == 0) {
                addMuted("Todavia no hay movimientos sincronizados en este periodo.");
            }
        });
    }

    private void clearReportArea() {
        if (reportContentStart < 0) {
            return;
        }
        while (root.getChildCount() > reportContentStart) {
            root.removeViewAt(reportContentStart);
        }
    }

    private String[] reportRange(int periodIndex) {
        Calendar start = Calendar.getInstance();
        Calendar end = Calendar.getInstance();
        clearTime(start);
        clearTime(end);
        String label;
        if (periodIndex == 0) {
            start.setFirstDayOfWeek(Calendar.MONDAY);
            start.set(Calendar.DAY_OF_WEEK, Calendar.MONDAY);
            label = "Semana actual";
        } else if (periodIndex == 2) {
            int month = start.get(Calendar.MONTH);
            start.set(Calendar.MONTH, (month / 3) * 3);
            start.set(Calendar.DAY_OF_MONTH, 1);
            label = "Trimestre actual";
        } else if (periodIndex == 3) {
            start.set(Calendar.MONTH, Calendar.JANUARY);
            start.set(Calendar.DAY_OF_MONTH, 1);
            label = "Ano actual";
        } else {
            start.set(Calendar.DAY_OF_MONTH, 1);
            label = "Mes actual";
        }
        return new String[]{dateOnly(start.getTime()), dateOnly(end.getTime()), label};
    }

    private void clearTime(Calendar calendar) {
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
    }

    private String dateOnly(Date date) {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(date);
    }

    private Totals totalsFor(Map<String, Totals> map, String key) {
        Totals totals = map.get(key);
        if (totals == null) {
            totals = new Totals();
            map.put(key, totals);
        }
        return totals;
    }

    private boolean isOwnTransfer(JSONObject row) {
        String text = (row.optString("nature") + " " + row.optString("category_name") + " " + row.optString("concept"))
                .toUpperCase(Locale.ROOT);
        return text.contains("TRANSFERENCIA ENTRE CUENTAS PROPIAS")
                || text.contains("TRASPASO ENTRE CUENTAS")
                || text.contains("CUENTAS PROPIAS")
                || text.contains("MIS CUENTAS")
                || text.contains("MISMA TITULARIDAD");
    }

    private boolean isInternationalMovement(JSONObject row) {
        String currency = row.optString("currency", "MXN").trim().toUpperCase(Locale.ROOT);
        if (!currency.isEmpty() && !"MXN".equals(currency) && !"PESOS".equals(currency)) {
            return true;
        }
        String text = (row.optString("category_name") + " " + row.optString("nature") + " " + row.optString("concept"))
                .toUpperCase(Locale.ROOT);
        String[] markers = {
                "INTERNACIONAL", "EXTRANJERO", "EXTERIOR", "FOREIGN", "INTERNATIONAL",
                "SWIFT", "WIRE", "WISE", "PAYPAL", "PAYONEER", "WESTERN UNION",
                "USD", "DOLAR", "DOLARES", "EUR", "EURO", "IBAN",
                "USA", "ESTADOS UNIDOS", "CANADA", "CHINA", "EUROPA"
        };
        for (String marker : markers) {
            if (text.contains(marker)) {
                return true;
            }
        }
        return false;
    }

    private String cleanLabel(String value, String fallback) {
        String clean = value == null ? "" : value.trim();
        return clean.isEmpty() ? fallback : clean;
    }

    private String urlParam(String value) throws Exception {
        return URLEncoder.encode(value, "UTF-8").replace("+", "%20");
    }

    private void loadRecentUploads() {
        runWithStatus("Actualizando ultimos envios...", () -> {
            String query = "organization_id=eq." + SupabaseConfig.ORGANIZATION_ID
                    + "&select=id,created_at,upload_type,status,concept,notes"
                    + "&order=created_at.desc&limit=8";
            JSONArray rows = new JSONArray(restGet("/rest/v1/cloud_uploads?" + query));
            runOnUiThread(() -> {
                statusText.setText("");
                for (int i = 0; i < rows.length(); i++) {
                    try {
                        JSONObject row = rows.getJSONObject(i);
                        addSmallItem(
                                uploadTypeLabel(row.optString("upload_type")) + " - " + row.optString("status"),
                                row.optString("concept", "").isEmpty() ? row.optString("notes", "Pendiente de OCR") : row.optString("concept"),
                                row.optString("created_at", "")
                        );
                    } catch (Exception ignored) {
                    }
                }
                if (rows.length() == 0) {
                    addMuted("Todavia no hay archivos enviados.");
                }
            });
        });
    }

    private void signIn(String email, String password) throws Exception {
        if (email.isEmpty() || password.isEmpty()) {
            throw new IllegalArgumentException("Escribe correo y contrasena.");
        }
        JSONObject payload = new JSONObject();
        payload.put("email", email);
        payload.put("password", password);
        JSONObject result = new JSONObject(authPost("/auth/v1/token?grant_type=password", payload));
        JSONObject user = result.getJSONObject("user");
        long expiresAt = System.currentTimeMillis() + (result.optLong("expires_in", 3600) * 1000L);
        prefs.edit()
                .putString("email", email)
                .putString("access_token", result.getString("access_token"))
                .putString("refresh_token", result.optString("refresh_token", ""))
                .putString("user_id", user.getString("id"))
                .putLong("expires_at", expiresAt)
                .apply();
    }

    private void refreshIfNeeded() throws Exception {
        String refresh = prefs.getString("refresh_token", "");
        if (refresh == null || refresh.isEmpty()) {
            return;
        }
        long expiresAt = prefs.getLong("expires_at", 0);
        if (expiresAt - System.currentTimeMillis() > 300000) {
            return;
        }
        JSONObject payload = new JSONObject();
        payload.put("refresh_token", refresh);
        JSONObject result = new JSONObject(authPost("/auth/v1/token?grant_type=refresh_token", payload));
        long newExpiresAt = System.currentTimeMillis() + (result.optLong("expires_in", 3600) * 1000L);
        prefs.edit()
                .putString("access_token", result.getString("access_token"))
                .putString("refresh_token", result.optString("refresh_token", refresh))
                .putLong("expires_at", newExpiresAt)
                .apply();
    }

    private void uploadDocument(Uri uri, String uploadType, String notes) throws Exception {
        refreshIfNeeded();
        String uploadId = UUID.randomUUID().toString();
        String fileName = sanitizeFileName(getDisplayName(uri));
        String storagePath = SupabaseConfig.ORGANIZATION_ID + "/" + prefs.getString("user_id", "") + "/" + uploadId + "/" + fileName;
        byte[] bytes = readBytes(uri);
        String mime = getContentResolver().getType(uri);
        if (mime == null || mime.trim().isEmpty()) {
            mime = "application/octet-stream";
        }
        storageUpload(storagePath, bytes, mime);

        JSONObject record = new JSONObject();
        record.put("id", uploadId);
        record.put("organization_id", SupabaseConfig.ORGANIZATION_ID);
        record.put("uploaded_by", prefs.getString("user_id", ""));
        record.put("upload_type", uploadType);
        record.put("concept", "");
        record.put("currency", "MXN");
        record.put("bank", "");
        record.put("account_name", "");
        record.put("nature", "Pendiente de clasificar");
        record.put("storage_path", storagePath);
        record.put("notes", notes == null ? "" : notes.trim());
        record.put("status", "pendiente");
        JSONArray payload = new JSONArray();
        payload.put(record);
        restPost("/rest/v1/cloud_uploads?on_conflict=id", payload.toString());
    }

    private String authPost(String path, JSONObject payload) throws Exception {
        return request("POST", SupabaseConfig.SUPABASE_URL + path, payload.toString(), false, "application/json");
    }

    private String restGet(String path) throws Exception {
        refreshIfNeeded();
        return request("GET", SupabaseConfig.SUPABASE_URL + path, null, true, "application/json");
    }

    private String restPost(String path, String payload) throws Exception {
        refreshIfNeeded();
        return request("POST", SupabaseConfig.SUPABASE_URL + path, payload, true, "application/json");
    }

    private String request(String method, String urlText, String payload, boolean authenticated, String contentType) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(urlText).openConnection();
        conn.setRequestMethod(method);
        conn.setConnectTimeout(30000);
        conn.setReadTimeout(60000);
        conn.setRequestProperty("apikey", SupabaseConfig.ANON_KEY);
        conn.setRequestProperty("Content-Type", contentType);
        String prefer = "return=representation";
        if ("POST".equals(method) && urlText.contains("/rest/v1/")) {
            prefer = "resolution=merge-duplicates,return=representation";
        }
        conn.setRequestProperty("Prefer", prefer);
        if (authenticated) {
            conn.setRequestProperty("Authorization", "Bearer " + getAccessToken());
        }
        if (payload != null) {
            conn.setDoOutput(true);
            try (OutputStream out = conn.getOutputStream()) {
                out.write(payload.getBytes(StandardCharsets.UTF_8));
            }
        }
        int code = conn.getResponseCode();
        String body = readResponse(conn, code);
        if (code < 200 || code >= 300) {
            throw new IllegalStateException("HTTP " + code + ": " + body);
        }
        return body;
    }

    private void storageUpload(String storagePath, byte[] bytes, String mime) throws Exception {
        String url = SupabaseConfig.SUPABASE_URL + "/storage/v1/object/" + SupabaseConfig.BUCKET + "/" + encodePath(storagePath);
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(30000);
        conn.setReadTimeout(120000);
        conn.setDoOutput(true);
        conn.setRequestProperty("apikey", SupabaseConfig.ANON_KEY);
        conn.setRequestProperty("Authorization", "Bearer " + getAccessToken());
        conn.setRequestProperty("Content-Type", mime);
        conn.setRequestProperty("x-upsert", "true");
        try (OutputStream out = conn.getOutputStream()) {
            out.write(bytes);
        }
        int code = conn.getResponseCode();
        String body = readResponse(conn, code);
        if (code < 200 || code >= 300) {
            throw new IllegalStateException("Storage HTTP " + code + ": " + body);
        }
    }

    private String readResponse(HttpURLConnection conn, int code) throws Exception {
        InputStream in = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
        if (in == null) {
            return "";
        }
        return new String(readAll(in), StandardCharsets.UTF_8);
    }

    private byte[] readBytes(Uri uri) throws Exception {
        try (InputStream in = getContentResolver().openInputStream(uri)) {
            if (in == null) {
                throw new IllegalArgumentException("No se pudo abrir el archivo.");
            }
            return readAll(in);
        }
    }

    private byte[] readAll(InputStream in) throws Exception {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] data = new byte[8192];
        int read;
        while ((read = in.read(data)) != -1) {
            buffer.write(data, 0, read);
        }
        return buffer.toByteArray();
    }

    private void openFilePicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"image/*", "application/pdf"});
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        startActivityForResult(intent, PICK_FILES);
    }

    private void openCamera() {
        try {
            ContentValues values = new ContentValues();
            values.put(MediaStore.Images.Media.DISPLAY_NAME, "ticket_" + System.currentTimeMillis() + ".jpg");
            values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
            values.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/ControlFinanciero");
            pendingCameraUri = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
            Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            intent.putExtra(MediaStore.EXTRA_OUTPUT, pendingCameraUri);
            startActivityForResult(intent, TAKE_PHOTO);
        } catch (Exception exc) {
            toast("No se pudo abrir la camara: " + exc.getMessage());
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK) {
            return;
        }
        if (requestCode == PICK_FILES && data != null) {
            ClipData clipData = data.getClipData();
            if (clipData != null) {
                for (int i = 0; i < clipData.getItemCount(); i++) {
                    addUri(clipData.getItemAt(i).getUri(), data.getFlags());
                }
            } else if (data.getData() != null) {
                addUri(data.getData(), data.getFlags());
            }
        } else if (requestCode == TAKE_PHOTO && pendingCameraUri != null) {
            selectedUris.add(pendingCameraUri);
        }
        updateSelectedText();
    }

    private void addUri(Uri uri, int flags) {
        try {
            int takeFlags = flags & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            getContentResolver().takePersistableUriPermission(uri, takeFlags);
        } catch (Exception ignored) {
        }
        selectedUris.add(uri);
    }

    private void updateSelectedText() {
        if (selectedText == null) {
            return;
        }
        if (selectedUris.isEmpty()) {
            selectedText.setText("Sin archivos seleccionados");
            return;
        }
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < selectedUris.size(); i++) {
            if (i > 0) {
                builder.append("\n");
            }
            builder.append(i + 1).append(". ").append(getDisplayName(selectedUris.get(i)));
        }
        selectedText.setText(builder.toString());
    }

    private String getDisplayName(Uri uri) {
        ContentResolver resolver = getContentResolver();
        try (Cursor cursor = resolver.query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) {
                    String name = cursor.getString(index);
                    if (name != null && !name.trim().isEmpty()) {
                        return name;
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return "documento_" + System.currentTimeMillis() + ".jpg";
    }

    private String uploadTypeFromSpinner(int index) {
        if (index == 1) return "estado_cuenta";
        if (index == 2) return "factura";
        if (index == 3) return "otro";
        return "ticket";
    }

    private String uploadTypeLabel(String value) {
        if ("estado_cuenta".equals(value)) return "Estado de cuenta";
        if ("factura".equals(value)) return "Factura";
        if ("otro".equals(value)) return "Otro";
        return "Ticket";
    }

    private String getAccessToken() {
        String token = prefs == null ? "" : prefs.getString("access_token", "");
        return token == null ? "" : token;
    }

    private String sanitizeFileName(String value) {
        String clean = value == null ? "documento" : value.trim();
        clean = clean.replaceAll("[^A-Za-z0-9._-]", "_");
        return clean.isEmpty() ? "documento" : clean;
    }

    private String encodePath(String value) throws Exception {
        String[] parts = value.split("/");
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < parts.length; i++) {
            if (i > 0) builder.append("/");
            builder.append(URLEncoder.encode(parts[i], "UTF-8").replace("+", "%20"));
        }
        return builder.toString();
    }

    private void runWithStatus(String message, Task task) {
        if (statusText != null) {
            statusText.setText(message);
        }
        new Thread(() -> {
            try {
                task.run();
            } catch (Exception exc) {
                runOnUiThread(() -> {
                    if (statusText != null) {
                        statusText.setText("Error: " + exc.getMessage());
                    }
                    toast("Error: " + exc.getMessage());
                });
            }
        }).start();
    }

    private TextView addHeader(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(24);
        view.setTextColor(Color.rgb(18, 50, 74));
        view.setTypeface(null, 1);
        view.setPadding(0, 0, 0, dp(10));
        root.addView(view);
        return view;
    }

    private TextView addSectionTitle(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(20);
        view.setTextColor(Color.rgb(24, 34, 48));
        view.setTypeface(null, 1);
        view.setPadding(0, dp(16), 0, dp(8));
        root.addView(view);
        return view;
    }

    private TextView addMuted(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(14);
        view.setTextColor(Color.rgb(102, 112, 133));
        view.setPadding(0, dp(4), 0, dp(8));
        root.addView(view);
        return view;
    }

    private TextView addStatus() {
        TextView view = new TextView(this);
        view.setText("");
        view.setTextSize(14);
        view.setTextColor(Color.rgb(21, 87, 36));
        view.setPadding(0, dp(8), 0, dp(8));
        root.addView(view);
        return view;
    }

    private void addNotice(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(15);
        view.setTextColor(Color.rgb(21, 87, 36));
        view.setPadding(dp(12), dp(10), dp(12), dp(10));
        view.setBackgroundColor(Color.rgb(233, 247, 239));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, dp(6), 0, dp(6));
        view.setLayoutParams(params);
        root.addView(view);
    }

    private EditText input(String hint) {
        EditText editText = new EditText(this);
        editText.setHint(hint);
        editText.setTextSize(16);
        editText.setSingleLine(true);
        editText.setPadding(dp(12), dp(10), dp(12), dp(10));
        root.addView(editText);
        return editText;
    }

    private Button primaryButton(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setAllCaps(false);
        button.setTextColor(Color.WHITE);
        button.setBackgroundColor(Color.rgb(31, 78, 120));
        button.setPadding(dp(8), dp(8), dp(8), dp(8));
        return button;
    }

    private Button secondaryButton(String text) {
        Button button = primaryButton(text);
        button.setTextColor(Color.rgb(18, 50, 74));
        button.setBackgroundColor(Color.rgb(237, 242, 247));
        return button;
    }

    private Button navButton(String text, boolean active) {
        Button button = active ? primaryButton(text) : secondaryButton(text);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1);
        params.setMargins(dp(2), 0, dp(2), 0);
        button.setLayoutParams(params);
        return button;
    }

    private void addCard(String title, String value) {
        TextView view = new TextView(this);
        view.setText(title + "\n" + value);
        view.setTextSize(18);
        view.setTextColor(Color.rgb(18, 50, 74));
        view.setTypeface(null, 1);
        view.setPadding(dp(12), dp(12), dp(12), dp(12));
        view.setBackgroundColor(Color.WHITE);
        root.addView(view);
    }

    private void addSmallItem(String title, String subtitle, String right) {
        TextView view = new TextView(this);
        view.setText(title + "\n" + subtitle + "\n" + right);
        view.setTextSize(14);
        view.setTextColor(Color.rgb(24, 34, 48));
        view.setPadding(dp(10), dp(10), dp(10), dp(10));
        view.setBackgroundColor(Color.WHITE);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, dp(4), 0, dp(4));
        view.setLayoutParams(params);
        root.addView(view);
    }

    private String money(double value) {
        NumberFormat format = NumberFormat.getCurrencyInstance(new Locale("es", "MX"));
        return format.format(value);
    }

    private static class Totals {
        double income;
        double expense;

        void add(String type, double amount) {
            double safeAmount = Math.abs(amount);
            if ("Ingreso".equals(type)) {
                income += safeAmount;
            } else if ("Egreso".equals(type)) {
                expense += safeAmount;
            }
        }

        double result() {
            return income - expense;
        }

        double totalMovement() {
            return income + expense;
        }
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }

    private interface Task {
        void run() throws Exception;
    }
}
