import os
from typing import Any

import requests
from flask import Blueprint, jsonify, request
from requests import Response

from auth import get_valid_access_token

operations_center_bp = Blueprint("operations_center_bp", __name__)


def _api_base_url() -> str:
    return os.environ.get("DEERE_API_BASE_URL", "https://sandboxapi.deere.com/platform").strip()


def _organizations_endpoint() -> str:
    return f"{_api_base_url()}/organizations"


def _machine_engine_hour_endpoint(machine_id: str) -> str:
    return f"{_api_base_url()}/machines/{machine_id}/engineHour"


def _equipment_endpoint(equipment_id: str) -> str:
    return f"{_api_base_url()}/equipment/{equipment_id}"


def _equipment_model_endpoint(equipment_make_id: str, equipment_type_id: str, equipment_model_id: str) -> str:
    return (
        f"{_api_base_url()}/equipmentMakes/{equipment_make_id}"
        f"/equipmentTypes/{equipment_type_id}"
        f"/equipmentModels/{equipment_model_id}"
    )


def _equipment_makes_endpoint() -> str:
    return f"{_api_base_url()}/equipmentMakes"


def _equipment_types_endpoint(equipment_make_id: str) -> str:
    return f"{_api_base_url()}/equipmentMakes/{equipment_make_id}/equipmentTypes"


def _equipment_models_endpoint(equipment_make_id: str, equipment_type_id: str) -> str:
    return f"{_api_base_url()}/equipmentMakes/{equipment_make_id}/equipmentTypes/{equipment_type_id}/equipmentModels"


def _build_platform_url(path: str) -> str | None:
    normalized = path.strip()
    if not normalized:
        return None
    if "://" in normalized:
        return None
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return f"{_api_base_url()}{normalized}"


def _http_timeout_seconds() -> int:
    return int(os.environ.get("HTTP_TIMEOUT_SECONDS", "20"))


def _authorized_get(
    url: str, accept_header: str = "application/vnd.deere.axiom.v3+json", params: dict[str, str] | None = None
) -> tuple[Response | None, tuple[dict, int] | None]:
    access_token = get_valid_access_token()
    if not access_token:
        return (
            None,
            (
                {
                    "error": "unauthorized",
                    "message": "Realize o login em /auth/login antes de acessar este recurso.",
                },
                401,
            ),
        )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": accept_header,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=_http_timeout_seconds())
        response.raise_for_status()
        return response, None
    except requests.HTTPError as exc:
        details = exc.response.text if exc.response is not None else str(exc)
        status_code = exc.response.status_code if exc.response is not None else 502
        return None, (
            {"error": "deere_api_error", "message": "Falha na chamada da API John Deere.", "details": details},
            status_code,
        )
    except requests.RequestException as exc:
        return None, ({"error": "network_error", "message": str(exc)}, 502)


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
                    self_link = next((link for link in links if isinstance(link, dict) and link.get("rel") == "self"), None)
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


@operations_center_bp.get("/organizations")
def get_organizations():
    response, error = _authorized_get(_organizations_endpoint())
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/machines/<string:machine_id>/engineHour")
def get_machine_engine_hour(machine_id: str):
    if not machine_id.strip():
        return jsonify({"error": "invalid_machine_id", "message": "machine_id nao pode ser vazio."}), 400

    response, error = _authorized_get(_machine_engine_hour_endpoint(machine_id))
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/equipment/<string:equipment_id>")
def get_equipment_by_id(equipment_id: str):
    if not equipment_id.strip():
        return jsonify({"error": "invalid_equipment_id", "message": "equipment_id nao pode ser vazio."}), 400

    response, error = _authorized_get(_equipment_endpoint(equipment_id))
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/equipmentMakes")
def get_equipment_makes():
    response, error = _authorized_get(_equipment_makes_endpoint(), params=request.args.to_dict(flat=True))
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/equipmentMakes/<string:equipment_make_id>/equipmentTypes")
def get_equipment_types(equipment_make_id: str):
    if not equipment_make_id.strip():
        return jsonify({"error": "invalid_equipment_make_id", "message": "equipment_make_id nao pode ser vazio."}), 400

    response, error = _authorized_get(
        _equipment_types_endpoint(equipment_make_id), params=request.args.to_dict(flat=True)
    )
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/equipmentMakes/<string:equipment_make_id>/equipmentTypes/<string:equipment_type_id>/equipmentModels")
def get_equipment_models(equipment_make_id: str, equipment_type_id: str):
    if not equipment_make_id.strip():
        return jsonify({"error": "invalid_equipment_make_id", "message": "equipment_make_id nao pode ser vazio."}), 400
    if not equipment_type_id.strip():
        return jsonify({"error": "invalid_equipment_type_id", "message": "equipment_type_id nao pode ser vazio."}), 400

    response, error = _authorized_get(
        _equipment_models_endpoint(equipment_make_id, equipment_type_id), params=request.args.to_dict(flat=True)
    )
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get(
    "/equipmentMakes/<string:equipment_make_id>/equipmentTypes/<string:equipment_type_id>/equipmentModels/<string:equipment_model_id>"
)
def get_equipment_model_by_ids(equipment_make_id: str, equipment_type_id: str, equipment_model_id: str):
    if not equipment_make_id.strip():
        return jsonify({"error": "invalid_equipment_make_id", "message": "equipment_make_id nao pode ser vazio."}), 400
    if not equipment_type_id.strip():
        return jsonify({"error": "invalid_equipment_type_id", "message": "equipment_type_id nao pode ser vazio."}), 400
    if not equipment_model_id.strip():
        return jsonify({"error": "invalid_equipment_model_id", "message": "equipment_model_id nao pode ser vazio."}), 400

    response, error = _authorized_get(
        _equipment_model_endpoint(equipment_make_id, equipment_type_id, equipment_model_id)
    )
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/discovery/equipment-catalog")
def discover_equipment_catalog():
    makes_response, makes_error = _authorized_get(_equipment_makes_endpoint(), params=request.args.to_dict(flat=True))
    if makes_error:
        return jsonify(makes_error[0]), makes_error[1]

    makes_payload = makes_response.json()
    makes_values = makes_payload.get("values", []) if isinstance(makes_payload, dict) else []

    catalog: list[dict[str, Any]] = []
    for make in makes_values:
        make_id = str(make.get("id", "")).strip()
        if not make_id:
            continue

        types_response, types_error = _authorized_get(_equipment_types_endpoint(make_id))
        if types_error:
            catalog.append(
                {
                    "equipmentMakeId": make_id,
                    "equipmentMakeName": make.get("name"),
                    "types_error": types_error[0],
                    "types": [],
                }
            )
            continue

        types_payload = types_response.json()
        types_values = types_payload.get("values", []) if isinstance(types_payload, dict) else []
        types_result: list[dict[str, Any]] = []

        for equipment_type in types_values:
            type_id = str(equipment_type.get("id", "")).strip()
            if not type_id:
                continue

            models_response, models_error = _authorized_get(_equipment_models_endpoint(make_id, type_id))
            if models_error:
                types_result.append(
                    {
                        "equipmentTypeId": type_id,
                        "equipmentTypeName": equipment_type.get("name"),
                        "models_error": models_error[0],
                        "models": [],
                    }
                )
                continue

            models_payload = models_response.json()
            models_values = models_payload.get("values", []) if isinstance(models_payload, dict) else []
            types_result.append(
                {
                    "equipmentTypeId": type_id,
                    "equipmentTypeName": equipment_type.get("name"),
                    "models": [
                        {
                            "equipmentModelId": model.get("id"),
                            "equipmentModelName": model.get("name"),
                        }
                        for model in models_values
                        if isinstance(model, dict) and model.get("id") is not None
                    ],
                }
            )

        catalog.append(
            {
                "equipmentMakeId": make_id,
                "equipmentMakeName": make.get("name"),
                "types": types_result,
            }
        )

    return jsonify({"total_makes": len(catalog), "catalog": catalog}), 200


@operations_center_bp.get("/organizations/<string:organization_id>/machines")
def get_organization_machines(organization_id: str):
    if not organization_id.strip():
        return jsonify({"error": "invalid_organization_id", "message": "organization_id nao pode ser vazio."}), 400

    url = _build_platform_url(f"/organizations/{organization_id}/machines")
    if not url:
        return jsonify({"error": "invalid_path"}), 400

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/proxy")
def proxy_platform_get():
    path = request.args.get("path", "")
    url = _build_platform_url(path)
    if not url:
        return (
            jsonify(
                {
                    "error": "invalid_path",
                    "message": "Use o parametro query `path`, por exemplo: /organizations/413958/machines",
                }
            ),
            400,
        )

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]
    return jsonify(response.json()), 200


@operations_center_bp.get("/discovery/ids")
def discover_ids():
    paths = request.args.getlist("path")
    if not paths:
        return (
            jsonify(
                {
                    "error": "missing_path",
                    "message": "Informe ao menos um query param `path`. Exemplo: /api/oc/discovery/ids?path=/organizations",
                }
            ),
            400,
        )

    discovery: list[dict[str, Any]] = []
    all_ids: list[dict[str, Any]] = []

    for path in paths:
        url = _build_platform_url(path)
        if not url:
            discovery.append({"path": path, "ok": False, "status_code": 400, "error": "invalid_path"})
            continue

        response, error = _authorized_get(url)
        if error:
            discovery.append(
                {
                    "path": path,
                    "ok": False,
                    "status_code": error[1],
                    "error": error[0],
                }
            )
            continue

        payload = response.json()
        ids = _extract_ids(payload, source_path=path)
        all_ids.extend(ids)
        discovery.append(
            {
                "path": path,
                "ok": True,
                "status_code": 200,
                "id_count": len(ids),
            }
        )

    unique_index: dict[tuple[str, str], dict[str, Any]] = {}
    for item in all_ids:
        key = (item.get("source_path", ""), item.get("id", ""))
        if key not in unique_index:
            unique_index[key] = item

    return (
        jsonify(
            {
                "paths_checked": discovery,
                "total_ids": len(unique_index),
                "ids": list(unique_index.values()),
            }
        ),
        200,
    )
