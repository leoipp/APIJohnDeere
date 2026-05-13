from flask import Blueprint, jsonify, request

from deere_client import _authorized_get, _fetch_all_pages, _platform_url

maps_bp = Blueprint("maps_bp", __name__)


def _normalize_file_resource(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "content_type": item.get("contentType"),
        "size": item.get("size"),
        "created": item.get("created"),
        "modified": item.get("modified"),
    }


def _normalize_map_layer_summary(item: dict) -> dict:
    field = item.get("field") if isinstance(item.get("field"), dict) else {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "layer_type": item.get("layerType"),
        "field_id": field.get("id"),
        "field_name": field.get("name"),
        "start_date": item.get("startDate"),
        "end_date": item.get("endDate"),
        "modified": item.get("modified"),
    }


def _normalize_map_layer(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "layer_type": item.get("layerType"),
        "start_date": item.get("startDate"),
        "end_date": item.get("endDate"),
        "modified": item.get("modified"),
        "record_count": item.get("recordCount"),
    }


# ============================================================
# FILE RESOURCES
# ============================================================

@maps_bp.get("/fileResources/<string:file_resource_id>")
def get_file_resource(file_resource_id: str):
    if not file_resource_id.strip():
        return jsonify({"error": "invalid_file_resource_id", "message": "file_resource_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/fileResources/{file_resource_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_file_resource(data)), 200


# ============================================================
# MAP LAYER SUMMARIES
# ============================================================

@maps_bp.get("/mapLayerSummaries/<string:summary_id>")
def get_map_layer_summary(summary_id: str):
    if not summary_id.strip():
        return jsonify({"error": "invalid_summary_id", "message": "summary_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/mapLayerSummaries/{summary_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_map_layer_summary(data)), 200


@maps_bp.get("/organizations/<string:org_id>/fields/<string:field_id>/mapLayerSummaries")
def get_field_map_layer_summaries(org_id: str, field_id: str):
    if not org_id.strip() or not field_id.strip():
        return jsonify({"error": "invalid_params", "message": "org_id e field_id nao podem ser vazios."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/organizations/{org_id}/fields/{field_id}/mapLayerSummaries")

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
        "field_id": field_id,
        "total": len(values),
        "values": [_normalize_map_layer_summary(v) for v in values],
    }), 200


# ============================================================
# MAP LAYERS
# ============================================================

@maps_bp.get("/mapLayers/<string:layer_id>")
def get_map_layer(layer_id: str):
    if not layer_id.strip():
        return jsonify({"error": "invalid_layer_id", "message": "layer_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/mapLayers/{layer_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_map_layer(data)), 200


@maps_bp.get("/mapLayers/<string:layer_id>/fileResources")
def get_map_layer_file_resources(layer_id: str):
    if not layer_id.strip():
        return jsonify({"error": "invalid_layer_id", "message": "layer_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/mapLayers/{layer_id}/fileResources")

    if raw:
        response, error = _authorized_get(url)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "map_layer_id": layer_id,
        "total": len(values),
        "values": [_normalize_file_resource(v) for v in values],
    }), 200
