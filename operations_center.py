import os
from typing import Any

import requests
from flask import Blueprint, jsonify, request
from requests import Response

from auth import get_valid_access_token

operations_center_bp = Blueprint("operations_center_bp", __name__)


# ============================================================
# CONFIG
# ============================================================

def _api_base_url() -> str:
    return os.environ.get(
        "DEERE_API_BASE_URL",
        "https://api.deere.com/platform",
    ).strip().rstrip("/")


def _http_timeout_seconds() -> int:
    return int(os.environ.get("HTTP_TIMEOUT_SECONDS", "20"))


def _organizations_endpoint() -> str:
    return f"{_api_base_url()}/organizations"


def _organization_endpoint(organization_id: str) -> str:
    return f"{_api_base_url()}/organizations/{organization_id}"


def _organization_settings_endpoint(organization_id: str) -> str:
    return f"{_api_base_url()}/organizations/{organization_id}/settings"


def _isg_equipment_endpoint() -> str:
    return "https://api.deere.com/isg/equipment"


def _machine_engine_hours_endpoint(machine_id: str) -> str:
    return f"https://api.deere.com/platform/machines/{machine_id}/engineHours"


# ============================================================
# HTTP JOHN DEERE
# ============================================================

def _build_deere_url(path: str) -> str | None:
    if not path:
        return None

    normalized = str(path).strip()

    if not normalized:
        return None

    if normalized.startswith("https://api.deere.com/"):
        return normalized

    if normalized.startswith("https://sandboxapi.deere.com/"):
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

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=_http_timeout_seconds(),
        )

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
        return None, (
            {
                "error": "network_error",
                "message": str(exc),
                "url": url,
            },
            502,
        )


# ============================================================
# HELPERS
# ============================================================

def _get_values(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        values = payload.get("values", [])
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
    return []


def _latest_engine_hours(payload: Any) -> dict[str, Any]:
    """
    Extrai somente a leitura mais recente de horímetro.
    A Deere retorna uma lista em payload["values"], ordenada da mais recente
    para a mais antiga.
    """
    result = {
        "engine_hours": None,
        "engine_hours_unit": None,
        "engine_hours_timestamp": None,
        "engine_hours_total_records": None,
    }

    if not isinstance(payload, dict):
        return result

    result["engine_hours_total_records"] = payload.get("total")

    values = payload.get("values", [])

    if not isinstance(values, list) or not values:
        return result

    latest = values[0]

    if not isinstance(latest, dict):
        return result

    reading = latest.get("reading", {})

    if isinstance(reading, dict):
        result["engine_hours"] = reading.get("valueAsDouble")
        result["engine_hours_unit"] = reading.get("unit")

    result["engine_hours_timestamp"] = latest.get("reportTime")

    return result


def _equipment_to_summary_row(item: dict[str, Any]) -> dict[str, Any]:
    organization = item.get("organization") if isinstance(item.get("organization"), dict) else {}
    organization_role = item.get("organizationRole") if isinstance(item.get("organizationRole"), dict) else {}
    make = item.get("make") if isinstance(item.get("make"), dict) else {}
    model = item.get("model") if isinstance(item.get("model"), dict) else {}
    equipment_type = item.get("type") if isinstance(item.get("type"), dict) else {}
    isg_type = item.get("isgType") if isinstance(item.get("isgType"), dict) else {}

    return {
        "resource_type": item.get("@type"),
        "id": item.get("id"),
        "principal_id": item.get("principalId"),
        "erid": item.get("ERID"),
        "name": item.get("name"),
        "serial_number": item.get("serialNumber"),
        "engine_serial_number": item.get("engineSerialNumber"),
        "organization_id": organization.get("id"),
        "archived": item.get("archived"),
        "archived_timestamp": item.get("archivedTimestamp"),
        "telematics_capable": item.get("telematicsCapable"),
        "is_serial_number_certified": item.get("isSerialNumberCertified"),
        "model_year": item.get("modelYear"),
        "make_id": make.get("id"),
        "make_name": make.get("name"),
        "model_id": model.get("id"),
        "model_name": model.get("name"),
        "type_id": equipment_type.get("id"),
        "type_name": equipment_type.get("name"),
        "isg_type_id": isg_type.get("id"),
        "isg_type_name": isg_type.get("name"),
        "role_type": organization_role.get("type"),
        "role_event": organization_role.get("event"),
        "in_possession": organization_role.get("inPossession"),
        "role_effective_ts": organization_role.get("effectiveTS"),
    }


def _extract_ids(payload: Any, source_path: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "id" in node:
                result = {
                    "id": str(node.get("id")),
                    "type": node.get("@type"),
                    "name": node.get("name"),
                    "source_path": source_path,
                }

                links = node.get("links")

                if isinstance(links, list):
                    self_link = next(
                        (
                            link
                            for link in links
                            if isinstance(link, dict) and link.get("rel") == "self"
                        ),
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


# ============================================================
# ORGANIZATIONS
# ============================================================

@operations_center_bp.get("/organizations")
def get_organizations():
    response, error = _authorized_get(_organizations_endpoint())

    if error:
        return jsonify(error[0]), error[1]

    return jsonify(response.json()), 200


@operations_center_bp.get("/organizations/<string:organization_id>")
def get_organization_by_id(organization_id: str):
    if not organization_id.strip():
        return jsonify({
            "error": "invalid_organization_id",
            "message": "organization_id nao pode ser vazio.",
        }), 400

    response, error = _authorized_get(_organization_endpoint(organization_id))

    if error:
        return jsonify(error[0]), error[1]

    return jsonify(response.json()), 200


@operations_center_bp.get("/organizations/<string:organization_id>/settings")
def get_organization_settings(organization_id: str):
    if not organization_id.strip():
        return jsonify({
            "error": "invalid_organization_id",
            "message": "organization_id nao pode ser vazio.",
        }), 400

    response, error = _authorized_get(_organization_settings_endpoint(organization_id))

    if error:
        return jsonify(error[0]), error[1]

    return jsonify(response.json()), 200


# ============================================================
# EQUIPMENT / FLEET
# ============================================================

@operations_center_bp.get("/organizations/<string:organization_id>/equipment")
def get_organization_equipment(organization_id: str):
    if not organization_id.strip():
        return jsonify({
            "error": "invalid_organization_id",
            "message": "organization_id nao pode ser vazio.",
        }), 400

    response, error = _authorized_get(
        _isg_equipment_endpoint(),
        params={"organizationIds": organization_id},
    )

    if error:
        return jsonify(error[0]), error[1]

    return jsonify(response.json()), 200


@operations_center_bp.get("/organizations/<string:organization_id>/equipment-summary")
def get_organization_equipment_summary(organization_id: str):
    if not organization_id.strip():
        return jsonify({
            "error": "invalid_organization_id",
            "message": "organization_id nao pode ser vazio.",
        }), 400

    include_archived = request.args.get("include_archived", "false").lower() == "true"
    only_telematics = request.args.get("only_telematics", "false").lower() == "true"

    response, error = _authorized_get(
        _isg_equipment_endpoint(),
        params={"organizationIds": organization_id},
    )

    if error:
        return jsonify(error[0]), error[1]

    values = _get_values(response.json())
    rows = [_equipment_to_summary_row(item) for item in values]

    if not include_archived:
        rows = [row for row in rows if row.get("archived") is not True]

    if only_telematics:
        rows = [row for row in rows if row.get("telematics_capable") is True]

    return jsonify({
        "organization_id": organization_id,
        "total": len(rows),
        "include_archived": include_archived,
        "only_telematics": only_telematics,
        "values": rows,
    }), 200


@operations_center_bp.get("/organizations/<string:organization_id>/machines")
def get_organization_machines(organization_id: str):
    return get_organization_equipment(organization_id)


@operations_center_bp.get("/organizations/<string:organization_id>/machines-summary")
def get_organization_machines_summary(organization_id: str):
    if not organization_id.strip():
        return jsonify({
            "error": "invalid_organization_id",
            "message": "organization_id nao pode ser vazio.",
        }), 400

    include_archived = request.args.get("include_archived", "false").lower() == "true"

    response, error = _authorized_get(
        _isg_equipment_endpoint(),
        params={"organizationIds": organization_id},
    )

    if error:
        return jsonify(error[0]), error[1]

    values = _get_values(response.json())

    rows = [
        _equipment_to_summary_row(item)
        for item in values
        if item.get("@type") == "Machine"
    ]

    if not include_archived:
        rows = [row for row in rows if row.get("archived") is not True]

    return jsonify({
        "organization_id": organization_id,
        "total": len(rows),
        "include_archived": include_archived,
        "values": rows,
    }), 200


# ============================================================
# ENGINE HOURS
# ============================================================

@operations_center_bp.get("/machines/<string:machine_id>/engineHours")
def get_machine_engine_hours(machine_id: str):
    if not machine_id.strip():
        return jsonify({
            "error": "invalid_machine_id",
            "message": "machine_id nao pode ser vazio.",
        }), 400

    response, error = _authorized_get(_machine_engine_hours_endpoint(machine_id))

    if error:
        return jsonify(error[0]), error[1]

    return jsonify(response.json()), 200


@operations_center_bp.get("/machines/<string:machine_id>/engineHours/latest")
def get_machine_latest_engine_hours(machine_id: str):
    if not machine_id.strip():
        return jsonify({
            "error": "invalid_machine_id",
            "message": "machine_id nao pode ser vazio.",
        }), 400

    response, error = _authorized_get(_machine_engine_hours_endpoint(machine_id))

    if error:
        return jsonify(error[0]), error[1]

    latest = _latest_engine_hours(response.json())

    return jsonify({
        "machine_id": machine_id,
        **latest,
    }), 200


@operations_center_bp.get("/organizations/<string:organization_id>/engine-hours")
def get_organization_engine_hours(organization_id: str):
    if not organization_id.strip():
        return jsonify({
            "error": "invalid_organization_id",
            "message": "organization_id nao pode ser vazio.",
        }), 400

    include_archived = request.args.get("include_archived", "false").lower() == "true"

    equipment_response, equipment_error = _authorized_get(
        _isg_equipment_endpoint(),
        params={"organizationIds": organization_id},
    )

    if equipment_error:
        return jsonify(equipment_error[0]), equipment_error[1]

    equipment_values = _get_values(equipment_response.json())

    machines = [
        item
        for item in equipment_values
        if item.get("@type") == "Machine"
        and item.get("telematicsCapable") is True
        and (include_archived or item.get("archived") is not True)
    ]

    rows = []

    for machine in machines:
        machine_id = str(machine.get("id", "")).strip()

        if not machine_id:
            continue

        row = _equipment_to_summary_row(machine)

        # ============================================================
        # PRIMEIRA TENTATIVA -> machine_id
        # ============================================================

        response, error = _authorized_get(
            _machine_engine_hours_endpoint(machine_id)
        )

        # ============================================================
        # SEGUNDA TENTATIVA -> principal_id
        # Algumas maquinas novas/transferidas funcionam apenas assim
        # ============================================================

        if error and error[1] == 404:

            principal_id = str(machine.get("principalId", "")).strip()

            if principal_id and principal_id != machine_id:
                response, error = _authorized_get(
                    _machine_engine_hours_endpoint(principal_id)
                )

        # ============================================================
        # ERRO FINAL
        # ============================================================

        if error:
            row["engine_hours_ok"] = False
            row["engine_hours_error"] = error[0]
            row["engine_hours"] = None
            row["engine_hours_unit"] = None
            row["engine_hours_timestamp"] = None
            row["engine_hours_total_records"] = None

            rows.append(row)
            continue

        latest = _latest_engine_hours(response.json())

        row["engine_hours_ok"] = True
        row.update(latest)

        rows.append(row)

    return jsonify({
        "organization_id": organization_id,
        "total": len(rows),
        "include_archived": include_archived,
        "values": rows,
    }), 200


# ============================================================
# PROXY / DISCOVERY
# ============================================================

@operations_center_bp.get("/proxy")
def proxy_platform_get():
    path = request.args.get("path")

    if not path:
        return jsonify({
            "error": "missing_path",
            "message": "Informe o query param `path`.",
        }), 400

    url = _build_deere_url(path)

    if not url:
        return jsonify({
            "error": "invalid_path",
            "message": f"path invalido: {path}",
        }), 400

    params = request.args.to_dict(flat=True)
    params.pop("path", None)

    response, error = _authorized_get(url, params=params)

    if error:
        return jsonify(error[0]), error[1]

    return jsonify(response.json()), 200


@operations_center_bp.get("/discovery/ids")
def discover_ids():
    paths = request.args.getlist("path")

    if not paths:
        return jsonify({
            "error": "missing_path",
            "message": "Informe ao menos um query param `path`.",
        }), 400

    discovery: list[dict[str, Any]] = []
    all_ids: list[dict[str, Any]] = []

    for path in paths:
        url = _build_deere_url(path)

        if not url:
            discovery.append({
                "path": path,
                "ok": False,
                "status_code": 400,
                "error": "invalid_path",
            })
            continue

        response, error = _authorized_get(url)

        if error:
            discovery.append({
                "path": path,
                "ok": False,
                "status_code": error[1],
                "error": error[0],
            })
            continue

        payload = response.json()
        ids = _extract_ids(payload, source_path=path)
        all_ids.extend(ids)

        discovery.append({
            "path": path,
            "ok": True,
            "status_code": 200,
            "id_count": len(ids),
        })

    unique_index: dict[tuple[str, str], dict[str, Any]] = {}

    for item in all_ids:
        key = (item.get("source_path", ""), item.get("id", ""))

        if key not in unique_index:
            unique_index[key] = item

    return jsonify({
        "paths_checked": discovery,
        "total_ids": len(unique_index),
        "ids": list(unique_index.values()),
    }), 200