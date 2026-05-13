from flask import Blueprint, jsonify, request

from deere_client import _authorized_get, _fetch_all_pages, _isg_url, _platform_url

equipment_bp = Blueprint("equipment_bp", __name__)


def _normalize_equipment_type(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
    }


def _normalize_equipment_model(item: dict) -> dict:
    make = item.get("make") if isinstance(item.get("make"), dict) else {}
    eq_type = item.get("type") if isinstance(item.get("type"), dict) else {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "make_id": make.get("id"),
        "make_name": make.get("name"),
        "type_id": eq_type.get("id"),
        "type_name": eq_type.get("name"),
        "model_year": item.get("modelYear"),
    }


def _normalize_equipment(item: dict) -> dict:
    make = item.get("make") if isinstance(item.get("make"), dict) else {}
    model = item.get("model") if isinstance(item.get("model"), dict) else {}
    eq_type = item.get("type") if isinstance(item.get("type"), dict) else {}
    isg_type = item.get("isgType") if isinstance(item.get("isgType"), dict) else {}
    organization = item.get("organization") if isinstance(item.get("organization"), dict) else {}
    return {
        "id": item.get("id"),
        "principal_id": item.get("principalId"),
        "erid": item.get("ERID"),
        "name": item.get("name"),
        "serial_number": item.get("serialNumber"),
        "engine_serial_number": item.get("engineSerialNumber"),
        "model_year": item.get("modelYear"),
        "archived": item.get("archived"),
        "telematics_capable": item.get("telematicsCapable"),
        "is_serial_number_certified": item.get("isSerialNumberCertified"),
        "make_id": make.get("id"),
        "make_name": make.get("name"),
        "model_id": model.get("id"),
        "model_name": model.get("name"),
        "type_id": eq_type.get("id"),
        "type_name": eq_type.get("name"),
        "isg_type_id": isg_type.get("id"),
        "isg_type_name": isg_type.get("name"),
        "organization_id": organization.get("id"),
    }


# ============================================================
# EQUIPMENT TYPES
# ============================================================

@equipment_bp.get("/equipmentTypes")
def get_equipment_types():
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url("/equipmentTypes")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_equipment_type(v) for v in values]}), 200


# ============================================================
# EQUIPMENT ISG TYPES
# ============================================================

@equipment_bp.get("/equipmentISGTypes")
def get_equipment_isg_types():
    raw = request.args.get("raw", "false").lower() == "true"
    url = _isg_url("/equipmentISGTypes")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_equipment_type(v) for v in values]}), 200


# ============================================================
# EQUIPMENT MODELS
# ============================================================

@equipment_bp.get("/equipmentModels/<string:serial_number>")
def get_equipment_model_by_serial(serial_number: str):
    if not serial_number.strip():
        return jsonify({"error": "invalid_serial_number", "message": "serial_number nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/equipmentModels/{serial_number}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_equipment_model(data)), 200


@equipment_bp.get("/equipmentMakes/<string:make_id>/equipmentTypes/<string:type_id>/equipmentModels/<string:model_id>")
def get_equipment_model_by_make_type(make_id: str, type_id: str, model_id: str):
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/equipmentMakes/{make_id}/equipmentTypes/{type_id}/equipmentModels/{model_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_equipment_model(data)), 200


# ============================================================
# EQUIPMENT BY ID (ISG)
# ============================================================

@equipment_bp.get("/equipment/<string:equipment_id>")
def get_equipment_by_id(equipment_id: str):
    if not equipment_id.strip():
        return jsonify({"error": "invalid_equipment_id", "message": "equipment_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _isg_url(f"/equipment/{equipment_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_equipment(data)), 200
