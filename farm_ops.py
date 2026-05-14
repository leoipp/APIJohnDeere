from flask import Blueprint, jsonify, request

from deere_client import _authorized_get, _date_params, _fetch_all_pages, _platform_url

farm_ops_bp = Blueprint("farm_ops_bp", __name__)


def _normalize_field_operation(item: dict) -> dict:
    machine = item.get("machine") if isinstance(item.get("machine"), dict) else {}
    field = item.get("field") if isinstance(item.get("field"), dict) else {}
    farm = item.get("farm") if isinstance(item.get("farm"), dict) else {}
    client = item.get("client") if isinstance(item.get("client"), dict) else {}
    quantities = item.get("quantities") if isinstance(item.get("quantities"), list) else []

    normalized_quantities = []
    for q in quantities:
        if not isinstance(q, dict):
            continue
        measurement = q.get("measurement") if isinstance(q.get("measurement"), dict) else {}
        normalized_quantities.append({
            "type": q.get("@type"),
            "value": measurement.get("asDouble"),
            "unit": measurement.get("unit"),
        })

    return {
        "id": item.get("id"),
        "type": item.get("@type"),
        "start_date": item.get("startDate"),
        "end_date": item.get("endDate"),
        "last_modified": item.get("lastModifiedDate"),
        "machine_id": machine.get("id"),
        "machine_name": machine.get("name"),
        "field_id": field.get("id"),
        "field_name": field.get("name"),
        "farm_id": farm.get("id"),
        "farm_name": farm.get("name"),
        "client_id": client.get("id"),
        "client_name": client.get("name"),
        "quantities": normalized_quantities,
    }


def _normalize_operator(item: dict) -> dict:
    return {
        "erid": item.get("ERID") or item.get("erid"),
        "first_name": item.get("firstName"),
        "last_name": item.get("lastName"),
        "email": item.get("email"),
        "resource_type": item.get("@type"),
        "license_number": item.get("licenseNumber"),
        "archived": item.get("archived"),
    }


def _normalize_farm(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "archived": item.get("archived"),
        "organization_id": (item.get("organization") or {}).get("id"),
        "client_id": (item.get("client") or {}).get("id"),
        "client_name": (item.get("client") or {}).get("name"),
    }


def _normalize_client(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "archived": item.get("archived"),
    }


# ============================================================
# OPERATORS
# ============================================================

@farm_ops_bp.get("/organizations/<string:org_id>/operators")
def get_organization_operators(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/operators")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "organization_id": org_id,
        "total": len(values),
        "values": [_normalize_operator(v) for v in values],
    }), 200


@farm_ops_bp.get("/organizations/<string:org_id>/operators/<string:operator_erid>")
def get_operator_by_erid(org_id: str, operator_erid: str):
    if not org_id.strip() or not operator_erid.strip():
        return jsonify({"error": "invalid_params", "message": "org_id e operator_erid nao podem ser vazios."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/operators/{operator_erid}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_operator(data)), 200


# ============================================================
# FARMS
# ============================================================

@farm_ops_bp.get("/organizations/<string:org_id>/farms")
def get_organization_farms(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/farms")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "organization_id": org_id,
        "total": len(values),
        "values": [_normalize_farm(v) for v in values],
    }), 200


@farm_ops_bp.get("/organizations/<string:org_id>/farms/<string:farm_id>")
def get_farm_by_id(org_id: str, farm_id: str):
    if not org_id.strip() or not farm_id.strip():
        return jsonify({"error": "invalid_params", "message": "org_id e farm_id nao podem ser vazios."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/farms/{farm_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_farm(data)), 200


@farm_ops_bp.get("/organizations/<string:org_id>/farms/<string:farm_id>/clients")
def get_farm_clients(org_id: str, farm_id: str):
    if not org_id.strip() or not farm_id.strip():
        return jsonify({"error": "invalid_params", "message": "org_id e farm_id nao podem ser vazios."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/farms/{farm_id}/clients")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "organization_id": org_id,
        "farm_id": farm_id,
        "total": len(values),
        "values": [_normalize_client(v) for v in values],
    }), 200


# ============================================================
# FIELD OPERATIONS
# ============================================================

@farm_ops_bp.get("/organizations/<string:org_id>/fieldOperations")
def get_field_operations(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    params: dict = {}
    date_p = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    if date_p:
        params.update(date_p)
    op_type = request.args.get("type")
    if op_type:
        params["fieldOperationType"] = op_type

    url = _platform_url(f"/organizations/{org_id}/fieldOperations")

    if raw:
        response, error = _authorized_get(url, params=params or None)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params or None)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "organization_id": org_id,
        "total": len(values),
        "values": [_normalize_field_operation(v) for v in values],
    }), 200


@farm_ops_bp.get("/organizations/<string:org_id>/fieldOperations/harvest")
def get_harvest_operations(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    params: dict = {"fieldOperationType": "HarvestActivity"}
    date_p = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    if date_p:
        params.update(date_p)

    url = _platform_url(f"/organizations/{org_id}/fieldOperations")
    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "organization_id": org_id,
        "total": len(values),
        "values": [_normalize_field_operation(v) for v in values],
    }), 200


@farm_ops_bp.get("/organizations/<string:org_id>/fieldOperations/<string:operation_id>")
def get_field_operation_by_id(org_id: str, operation_id: str):
    if not org_id.strip() or not operation_id.strip():
        return jsonify({"error": "invalid_params", "message": "org_id e operation_id nao podem ser vazios."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/fieldOperations/{operation_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_field_operation(data)), 200
