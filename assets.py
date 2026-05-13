from flask import Blueprint, jsonify, request

from deere_client import _authorized_get, _date_params, _fetch_all_pages, _platform_url

assets_bp = Blueprint("assets_bp", __name__)


def _normalize_asset(item: dict) -> dict:
    asset_type = item.get("assetType") if isinstance(item.get("assetType"), dict) else {}
    organization = item.get("organization") if isinstance(item.get("organization"), dict) else {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "asset_type_id": asset_type.get("id"),
        "asset_type_name": asset_type.get("name"),
        "organization_id": organization.get("id"),
        "serial_number": item.get("serialNumber"),
        "archived": item.get("archived"),
    }


def _normalize_asset_catalog_item(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "category": item.get("category"),
        "description": item.get("description"),
    }


def _normalize_asset_location(item: dict) -> dict:
    geometry = item.get("geometry") if isinstance(item.get("geometry"), dict) else {}
    coords = geometry.get("coordinates", [])
    lat = coords[1] if len(coords) >= 2 else None
    lon = coords[0] if len(coords) >= 1 else None
    return {
        "timestamp": item.get("timestamp"),
        "lat": lat,
        "lon": lon,
        "source": item.get("source"),
    }


# ============================================================
# ASSET CATALOG
# ============================================================

@assets_bp.get("/assetCatalog")
def get_asset_catalog():
    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url("/assetCatalog")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_asset_catalog_item(v) for v in values]}), 200


# ============================================================
# ASSET BY ID
# ============================================================

@assets_bp.get("/assets/<string:asset_id>")
def get_asset_by_id(asset_id: str):
    if not asset_id.strip():
        return jsonify({"error": "invalid_asset_id", "message": "asset_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/assets/{asset_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_asset(data)), 200


# ============================================================
# ORGANIZATION ASSETS
# ============================================================

@assets_bp.get("/organizations/<string:org_id>/assets")
def get_organization_assets(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/assets")

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
        "values": [_normalize_asset(v) for v in values],
    }), 200


# ============================================================
# ASSET LOCATIONS
# ============================================================

@assets_bp.get("/assets/<string:asset_id>/locations")
def get_asset_locations(asset_id: str):
    if not asset_id.strip():
        return jsonify({"error": "invalid_asset_id", "message": "asset_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url(f"/assets/{asset_id}/locations")

    if raw:
        response, error = _authorized_get(url, params=params)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "asset_id": asset_id,
        "total": len(values),
        "values": [_normalize_asset_location(v) for v in values],
    }), 200
