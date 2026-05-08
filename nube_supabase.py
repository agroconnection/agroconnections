# -*- coding: utf-8 -*-
"""Cliente base para Fase 3: sincronizacion con Supabase."""

from __future__ import annotations

import json
import mimetypes
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError
from urllib.parse import urlencode


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config_nube.json"


@dataclass
class CloudConfig:
    supabase_url: str
    anon_key: str
    organization_id: str
    bucket: str = "financial-documents"
    sync_access_token: str = ""
    service_role_key: str = ""


def load_config(path: Path = CONFIG_PATH) -> CloudConfig:
    data: dict[str, Any] = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    env_data = {
        "supabase_url": os.environ.get("SUPABASE_URL", ""),
        "anon_key": os.environ.get("SUPABASE_ANON_KEY", ""),
        "organization_id": os.environ.get("SUPABASE_ORGANIZATION_ID", ""),
        "bucket": os.environ.get("SUPABASE_BUCKET", ""),
        "sync_access_token": os.environ.get("SUPABASE_SYNC_ACCESS_TOKEN", ""),
        "service_role_key": os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
    }
    for key, value in env_data.items():
        if value:
            data[key] = value
    if not data:
        raise FileNotFoundError(
            f"No existe {path.name}. Copia config_nube.example.json o configura variables de entorno de Supabase."
        )
    missing = [key for key in ("supabase_url", "anon_key", "organization_id") if not data.get(key)]
    if missing:
        raise FileNotFoundError(f"Falta configurar en Supabase: {', '.join(missing)}")
    return CloudConfig(
        supabase_url=str(data["supabase_url"]).rstrip("/"),
        anon_key=str(data["anon_key"]),
        organization_id=str(data["organization_id"]),
        bucket=str(data.get("bucket", "financial-documents")),
        sync_access_token=str(data.get("sync_access_token", "")),
        service_role_key=str(data.get("service_role_key", "")),
    )


class SupabaseClient:
    def __init__(self, config: CloudConfig, access_token: str | None = None) -> None:
        self.config = config
        self.access_token = access_token or config.anon_key

    def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        token = self.access_token or self.config.anon_key
        if token.startswith("sb_"):
            headers = {"apikey": token}
        elif token == self.config.anon_key:
            headers = {"apikey": self.config.anon_key}
            if not self.config.anon_key.startswith("sb_"):
                headers["Authorization"] = f"Bearer {self.config.anon_key}"
        else:
            headers = {
                "apikey": self.config.anon_key,
                "Authorization": f"Bearer {token}",
            }
        if extra:
            headers.update(extra)
        return headers

    def request_json(
        self,
        method: str,
        url: str,
        payload: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = self.headers({"Content-Type": "application/json", "Prefer": "return=representation"})
        if extra_headers:
            headers.update(extra_headers)
        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase HTTP {exc.code}: {detail}") from exc

    def sign_in_with_password(self, email: str, password: str) -> dict[str, Any]:
        url = f"{self.config.supabase_url}/auth/v1/token?grant_type=password"
        payload = {"email": email, "password": password}
        result = self.request_json("POST", url, payload)
        if not isinstance(result, dict) or not result.get("access_token"):
            raise RuntimeError("No se pudo iniciar sesion en Supabase.")
        self.access_token = str(result["access_token"])
        return result

    def refresh_session(self, refresh_token: str) -> dict[str, Any]:
        url = f"{self.config.supabase_url}/auth/v1/token?grant_type=refresh_token"
        payload = {"refresh_token": refresh_token}
        result = self.request_json("POST", url, payload)
        if not isinstance(result, dict) or not result.get("access_token"):
            raise RuntimeError("No se pudo renovar la sesion en Supabase.")
        self.access_token = str(result["access_token"])
        return result

    def upload_file(self, local_path: Path, cloud_path: str) -> str:
        content_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
        url = f"{self.config.supabase_url}/storage/v1/object/{self.config.bucket}/{cloud_path}"
        headers = self.headers({"Content-Type": content_type, "x-upsert": "false"})
        req = request.Request(url, data=local_path.read_bytes(), headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=120) as response:
                response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Storage HTTP {exc.code}: {detail}") from exc
        return cloud_path

    def download_file(self, cloud_path: str, destination: Path) -> Path:
        url = f"{self.config.supabase_url}/storage/v1/object/{self.config.bucket}/{cloud_path}"
        req = request.Request(url, headers=self.headers(), method="GET")
        try:
            with request.urlopen(req, timeout=120) as response:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(response.read())
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Storage HTTP {exc.code}: {detail}") from exc
        return destination

    def create_upload_record(self, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.supabase_url}/rest/v1/cloud_uploads"
        payload = {
            "organization_id": self.config.organization_id,
            **data,
        }
        result = self.request_json("POST", url, [payload])
        return result[0] if isinstance(result, list) and result else {}

    def update_upload_record(self, upload_id: str, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.supabase_url}/rest/v1/cloud_uploads?id=eq.{upload_id}"
        result = self.request_json("PATCH", url, data)
        return result[0] if isinstance(result, list) and result else {}

    def list_pending_uploads(self) -> list[dict[str, Any]]:
        url = (
            f"{self.config.supabase_url}/rest/v1/cloud_uploads"
            f"?organization_id=eq.{self.config.organization_id}"
            f"&status=eq.pendiente"
            f"&select=*"
            f"&order=created_at.asc"
        )
        result = self.request_json("GET", url)
        return result if isinstance(result, list) else []

    def list_cloud_uploads(self, limit: int = 25) -> list[dict[str, Any]]:
        filters: list[tuple[str, str]] = [
            ("organization_id", f"eq.{self.config.organization_id}"),
            (
                "select",
                "id,created_at,document_date,upload_type,status,concept,amount,currency,bank,account_name,nature,notes",
            ),
            ("order", "created_at.desc"),
            ("limit", str(limit)),
        ]
        url = f"{self.config.supabase_url}/rest/v1/cloud_uploads?{urlencode(filters)}"
        result = self.request_json("GET", url)
        return result if isinstance(result, list) else []

    def upsert_cloud_movements(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        payload = [{"organization_id": self.config.organization_id, **row} for row in rows]
        query = urlencode({"on_conflict": "organization_id,source_device,local_movement_id"})
        url = f"{self.config.supabase_url}/rest/v1/cloud_movements?{query}"
        result = self.request_json(
            "POST",
            url,
            payload,
            {"Prefer": "resolution=merge-duplicates,return=representation"},
        )
        return len(result) if isinstance(result, list) else 0

    def list_cloud_movements(
        self,
        start_date: str,
        end_date: str,
        movement_type: str = "",
        account_name: str = "",
        exclude_internal: bool = True,
    ) -> list[dict[str, Any]]:
        filters: list[tuple[str, str]] = [
            ("organization_id", f"eq.{self.config.organization_id}"),
            ("movement_date", f"gte.{start_date}"),
            ("movement_date", f"lte.{end_date}"),
            (
                "select",
                "movement_date,movement_type,account_name,account_owner_type,category_name,nature,concept,amount_mxn,currency,status",
            ),
            ("order", "movement_date.desc"),
        ]
        if movement_type:
            filters.append(("movement_type", f"eq.{movement_type}"))
        if account_name:
            filters.append(("account_name", f"ilike.*{account_name}*"))
        if exclude_internal:
            filters.append(("nature", "neq.Transferencia entre cuentas propias"))
        url = f"{self.config.supabase_url}/rest/v1/cloud_movements?{urlencode(filters)}"
        result = self.request_json("GET", url)
        return result if isinstance(result, list) else []

    def list_cloud_upload_report_rows(
        self,
        start_date: str,
        end_date: str,
        movement_type: str = "",
        account_name: str = "",
        exclude_internal: bool = True,
    ) -> list[dict[str, Any]]:
        filters: list[tuple[str, str]] = [
            ("organization_id", f"eq.{self.config.organization_id}"),
            ("document_date", f"gte.{start_date}"),
            ("document_date", f"lte.{end_date}"),
            ("amount", "not.is.null"),
            ("movement_type", "not.is.null"),
            ("select", "document_date,movement_type,account_name,nature,concept,amount,currency,status,upload_type,notes"),
            ("order", "document_date.desc"),
        ]
        if movement_type:
            filters.append(("movement_type", f"eq.{movement_type}"))
        if account_name:
            filters.append(("account_name", f"ilike.*{account_name}*"))
        if exclude_internal:
            filters.append(("nature", "neq.Transferencia entre cuentas propias"))
        url = f"{self.config.supabase_url}/rest/v1/cloud_uploads?{urlencode(filters)}"
        result = self.request_json("GET", url)
        return result if isinstance(result, list) else []


def new_upload_id() -> str:
    return str(uuid.uuid4())


def make_cloud_path(organization_id: str, user_id: str, upload_id: str, filename: str) -> str:
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename)
    return f"{organization_id}/{user_id}/{upload_id}/{safe_name}"
