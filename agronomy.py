from flask import Blueprint, jsonify, request

from deere_client import _authorized_get, _fetch_all_pages, _isg_url, _platform_url

agronomy_bp = Blueprint("agronomy_bp", __name__)


def _normalize_chemical(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "product_type": item.get("productType"),
        "epa_reg_number": item.get("epaRegNumber"),
        "company_name": (item.get("company") or {}).get("name"),
        "company_id": (item.get("company") or {}).get("id"),
        "archived": item.get("archived"),
    }


def _normalize_fertilizer(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "product_type": item.get("productType"),
        "form": item.get("form"),
        "company_name": (item.get("company") or {}).get("name"),
        "company_id": (item.get("company") or {}).get("id"),
        "archived": item.get("archived"),
    }


def _normalize_variety(item: dict) -> dict:
    crop = item.get("crop") if isinstance(item.get("crop"), dict) else {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "brand": item.get("brand"),
        "crop_id": crop.get("id"),
        "crop_name": crop.get("name"),
        "company_name": (item.get("company") or {}).get("name"),
        "company_id": (item.get("company") or {}).get("id"),
        "archived": item.get("archived"),
    }


def _normalize_tank_mix(item: dict) -> dict:
    components = item.get("components")
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "archived": item.get("archived"),
        "organization_id": (item.get("organization") or {}).get("id"),
        "components_count": len(components) if isinstance(components, list) else None,
    }


def _normalize_dry_blend(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "archived": item.get("archived"),
        "organization_id": (item.get("organization") or {}).get("id"),
    }


def _normalize_product_company(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
    }


def _normalize_active_ingredient(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "cas_number": item.get("casNumber"),
    }


# ============================================================
# CHEMICALS
# ============================================================

@agronomy_bp.get("/chemicals")
def get_chemicals():
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url("/chemicals")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_chemical(v) for v in values]}), 200


@agronomy_bp.get("/chemicals/<string:chemical_id>")
def get_chemical_by_id(chemical_id: str):
    if not chemical_id.strip():
        return jsonify({"error": "invalid_chemical_id", "message": "chemical_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/chemicals/{chemical_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_chemical(data)), 200


@agronomy_bp.get("/organizations/<string:org_id>/chemicals")
def get_organization_chemicals(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/chemicals")

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
        "values": [_normalize_chemical(v) for v in values],
    }), 200


@agronomy_bp.get("/organizations/<string:org_id>/chemicals/<string:chemical_id>")
def get_organization_chemical_by_id(org_id: str, chemical_id: str):
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/chemicals/{chemical_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_chemical(data)), 200


# ============================================================
# ACTIVE INGREDIENTS (ISG)
# ============================================================

@agronomy_bp.get("/activeIngredients")
def get_active_ingredients():
    raw = request.args.get("raw", "false").lower() == "true"
    url = _isg_url("/activeIngredients")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_active_ingredient(v) for v in values]}), 200


# ============================================================
# FERTILIZERS
# ============================================================

@agronomy_bp.get("/fertilizers")
def get_fertilizers():
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url("/fertilizers")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_fertilizer(v) for v in values]}), 200


@agronomy_bp.get("/fertilizers/<string:fertilizer_id>")
def get_fertilizer_by_id(fertilizer_id: str):
    if not fertilizer_id.strip():
        return jsonify({"error": "invalid_fertilizer_id", "message": "fertilizer_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/fertilizers/{fertilizer_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_fertilizer(data)), 200


@agronomy_bp.get("/organizations/<string:org_id>/fertilizers")
def get_organization_fertilizers(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/fertilizers")

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
        "values": [_normalize_fertilizer(v) for v in values],
    }), 200


@agronomy_bp.get("/organizations/<string:org_id>/fertilizers/<string:fertilizer_id>")
def get_organization_fertilizer_by_id(org_id: str, fertilizer_id: str):
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/fertilizers/{fertilizer_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_fertilizer(data)), 200


# ============================================================
# VARIETIES
# ============================================================

@agronomy_bp.get("/varieties")
def get_varieties():
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url("/varieties")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_variety(v) for v in values]}), 200


@agronomy_bp.get("/varieties/<string:variety_id>")
def get_variety_by_id(variety_id: str):
    if not variety_id.strip():
        return jsonify({"error": "invalid_variety_id", "message": "variety_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/varieties/{variety_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_variety(data)), 200


@agronomy_bp.get("/organizations/<string:org_id>/varieties")
def get_organization_varieties(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/varieties")

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
        "values": [_normalize_variety(v) for v in values],
    }), 200


@agronomy_bp.get("/organizations/<string:org_id>/varieties/<string:variety_id>")
def get_organization_variety_by_id(org_id: str, variety_id: str):
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/varieties/{variety_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_variety(data)), 200


# ============================================================
# TANK MIXES
# ============================================================

@agronomy_bp.get("/organizations/<string:org_id>/tankMixes")
def get_organization_tank_mixes(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/tankMixes")

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
        "values": [_normalize_tank_mix(v) for v in values],
    }), 200


@agronomy_bp.get("/organizations/<string:org_id>/tankMixes/<string:tank_mix_id>")
def get_organization_tank_mix_by_id(org_id: str, tank_mix_id: str):
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/tankMixes/{tank_mix_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_tank_mix(data)), 200


# ============================================================
# DRY BLENDS
# ============================================================

@agronomy_bp.get("/organizations/<string:org_id>/dryBlends")
def get_organization_dry_blends(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/dryBlends")

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
        "values": [_normalize_dry_blend(v) for v in values],
    }), 200


@agronomy_bp.get("/organizations/<string:org_id>/dryBlends/<string:dry_blend_id>")
def get_organization_dry_blend_by_id(org_id: str, dry_blend_id: str):
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/dryBlends/{dry_blend_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_dry_blend(data)), 200


# ============================================================
# PRODUCT COMPANIES
# ============================================================

@agronomy_bp.get("/organizations/<string:org_id>/productCompanies")
def get_organization_product_companies(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/productCompanies")

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
        "values": [_normalize_product_company(v) for v in values],
    }), 200
