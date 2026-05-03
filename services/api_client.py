import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import requests
import streamlit as st


DEFAULT_SERVICE_URLS = {
    "auth": "http://localhost:8001",
    "ledger": "http://localhost:8004",
    "ocr": "http://localhost:8005",
    "onboarding": "http://localhost:8007",
}


class APIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except Exception:
        return {}


def init_api_config() -> None:
    st.session_state.setdefault("service_urls", DEFAULT_SERVICE_URLS.copy())


def set_auth_session(access_token: str) -> None:
    claims = decode_jwt_payload(access_token)
    st.session_state["access_token"] = access_token
    st.session_state["company_id"] = claims.get("company_id", "")
    st.session_state["user_id"] = claims.get("sub", "")
    st.session_state["roles"] = claims.get("roles", [])


def clear_auth_session() -> None:
    for key in ["access_token", "company_id", "user_id", "roles"]:
        st.session_state.pop(key, None)


@dataclass
class APIClient:
    service: str
    timeout: int = 20
    retries: int = 2

    @property
    def base_url(self) -> str:
        init_api_config()
        return st.session_state["service_urls"].get(self.service, "").rstrip("/")

    def headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        token = st.session_state.get("access_token")
        company_id = st.session_state.get("company_id")
        user_id = st.session_state.get("user_id")
        roles = st.session_state.get("roles", [])

        if token:
            headers["Authorization"] = f"Bearer {token}"
        if company_id:
            headers["X-Tenant-ID"] = company_id
        if user_id:
            headers["X-User-ID"] = user_id
        if roles:
            headers["X-User-Roles"] = ",".join(roles)
        if extra:
            headers.update(extra)
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        retries: int | None = None,
    ) -> Any:
        if not self.base_url:
            raise APIError(f"No base URL configured for {self.service} service")

        attempts = (self.retries if retries is None else retries) + 1
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: APIError | None = None

        for attempt in range(attempts):
            try:
                response = requests.request(
                    method,
                    url,
                    json=json_data,
                    params={k: v for k, v in (params or {}).items() if v not in (None, "")},
                    files=files,
                    headers=self.headers(headers),
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    raise self._to_error(response)
                if not response.content:
                    return None
                return response.json()
            except requests.RequestException as exc:
                last_error = APIError(f"{self.service} API is unreachable: {exc}")
            except APIError as exc:
                last_error = exc
                if exc.status_code and exc.status_code < 500:
                    break

            if attempt < attempts - 1:
                time.sleep(0.4 * (attempt + 1))

        raise last_error or APIError("API request failed")

    def _to_error(self, response: requests.Response) -> APIError:
        try:
            payload = response.json()
            detail = payload.get("detail", payload)
        except ValueError:
            payload = response.text
            detail = response.text
        return APIError(str(detail), status_code=response.status_code, payload=payload)


def login(email: str, password: str) -> dict[str, Any]:
    return APIClient("auth").request(
        "POST",
        "/auth/login",
        json_data={"email": email, "password": password},
        retries=1,
    )


def onboarding_status() -> dict[str, Any]:
    return APIClient("onboarding").request("GET", "/onboarding/status")


def api_prefill(payload: dict[str, Any]) -> dict[str, Any]:
    return APIClient("onboarding").request("POST", "/onboarding/api-prefill", json_data=payload)


def upload_kyc_document(document_type: str, uploaded_file: Any) -> dict[str, Any]:
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }
    return APIClient("onboarding").request(
        "POST",
        "/onboarding/ocr-upload",
        params={"document_type": document_type},
        files=files,
    )


def onboarding_job(job_id: str) -> dict[str, Any]:
    return APIClient("onboarding").request("GET", f"/onboarding/job/{job_id}")


def confirm_onboarding(company_data: dict[str, Any], kyc_document_ids: list[str]) -> dict[str, Any]:
    return APIClient("onboarding").request(
        "POST",
        "/onboarding/confirm",
        json_data={"company_data": company_data, "kyc_document_ids": kyc_document_ids},
    )


def ledger_entries(account_id: str | None = None, start_date: Any = None, end_date: Any = None) -> list[dict[str, Any]]:
    params = {
        "account_id": account_id,
        "start_date": start_date.isoformat() if hasattr(start_date, "isoformat") else start_date,
        "end_date": end_date.isoformat() if hasattr(end_date, "isoformat") else end_date,
    }
    return APIClient("ledger").request("GET", "/ledger/entries", params=params)


def create_journal(payload: dict[str, Any]) -> dict[str, Any]:
    return APIClient("ledger").request(
        "POST",
        "/ledger/journals",
        json_data=payload,
        headers={"Idempotency-Key": str(uuid4())},
    )


def chart_of_accounts() -> list[dict[str, Any]]:
    path = st.session_state.get("chart_accounts_path", "/ledger/accounts")
    return APIClient("ledger").request("GET", path)
