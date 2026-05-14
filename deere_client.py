import os
from typing import Any

import requests
from requests import Response

from auth import get_valid_access_token


def _api_base_url() -> str:
    return os.environ.get(
        "DEERE_API_BASE_URL",
        "https://api.deere.com/platform",
    ).strip().rstrip("/")


def _isg_base_url() -> str:
    return "https://api.deere.com/isg"


def _http_timeout_seconds() -> int:
    return int(os.environ.get("HTTP_TIMEOUT_SECONDS", "20"))


def _platform_url(path: str) -> str:
    return f"{_api_base_url()}{path}"


def _isg_url(path: str) -> str:
    return f"{_isg_base_url()}{path}"


def _build_deere_url(path: str) -> str | None:
    if not path:
        return None
    normalized = str(path).strip()
    if not normalized:
        return None
    if normalized.startswith("https://api.deere.com/") or normalized.startswith("https://sandboxapi.deere.com/"):
        return normalized
    if "://" in normalized:
        return None
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return f"{_api_base_url()}{normalized}"


def _authorized_get(
    url: str,
    accept_header: str = "application/vnd.deere.axiom.v3+json",
    params: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[Response | None, tuple[dict, int] | None]:
    access_token = get_valid_access_token()
    if not access_token:
        return None, (
            {
                "error": "unauthorized",
                "message": "Realize o login em /auth/login antes de acessar este recurso.",
            },
            401,
        )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": accept_header,
    }
    if extra_headers:
        headers.update(extra_headers)

    try:
        response = requests.get(url, headers=headers, params=params, timeout=_http_timeout_seconds())
        if not response.ok:
            return None, (
                {
                    "error": "deere_api_error",
                    "message": "Falha na chamada da API John Deere.",
                    "status_code": response.status_code,
                    "url": response.url,
                    "details": response.text,
                },
                response.status_code,
            )
        return response, None
    except requests.RequestException as exc:
        return None, ({"error": "network_error", "message": str(exc), "url": url}, 502)


def _get_values(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        values = payload.get("values", [])
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
    return []


def _fetch_all_pages(
    url: str,
    params: dict | None = None,
    accept_header: str = "application/vnd.deere.axiom.v3+json",
    extra_headers: dict[str, str] | None = None,
) -> tuple[list[dict], tuple[dict, int] | None]:
    """Follows nextPage links and consolidates all values into a single list."""
    all_values: list[dict] = []
    current_url: str | None = url
    current_params = params

    while current_url:
        response, error = _authorized_get(current_url, accept_header=accept_header, params=current_params, extra_headers=extra_headers)
        if error:
            return [], error

        data = response.json()

        if isinstance(data, dict):
            values = data.get("values", [])
            if isinstance(values, list):
                all_values.extend(v for v in values if isinstance(v, dict))

            links = data.get("links", [])
            next_link = next(
                (lnk for lnk in links if isinstance(lnk, dict) and lnk.get("rel") == "nextPage"),
                None,
            )
            current_url = next_link.get("uri") if isinstance(next_link, dict) else None
        else:
            current_url = None

        current_params = None

    return all_values, None


def _date_params(start_date: str | None, end_date: str | None) -> dict | None:
    params: dict = {}
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    return params or None


def _extract_ids(payload: Any, source_path: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "id" in node:
                result: dict[str, Any] = {
                    "id": str(node.get("id")),
                    "type": node.get("@type"),
                    "name": node.get("name"),
                    "source_path": source_path,
                }
                links = node.get("links")
                if isinstance(links, list):
                    self_link = next(
                        (link for link in links if isinstance(link, dict) and link.get("rel") == "self"),
                        None,
                    )
                    if isinstance(self_link, dict):
                        result["self_uri"] = self_link.get("uri")
                results.append(result)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return results
