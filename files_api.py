from flask import Blueprint, Response, jsonify, request

from deere_client import _authorized_get, _date_params, _fetch_all_pages, _platform_url

files_bp = Blueprint("files_bp", __name__)


def _normalize_file(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "resource_type": item.get("@type"),
        "content_type": item.get("contentType"),
        "size": item.get("size"),
        "created": item.get("created"),
        "modified": item.get("modified"),
        "status": item.get("status"),
        "organization_id": (item.get("organization") or {}).get("id"),
    }


# ============================================================
# FILES LIST
# ============================================================

@files_bp.get("/files")
def get_files():
    raw = request.args.get("raw", "false").lower() == "true"
    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url("/files")

    if raw:
        response, error = _authorized_get(url, params=params)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"total": len(values), "values": [_normalize_file(v) for v in values]}), 200


# ============================================================
# FILE BY ID
# ============================================================

@files_bp.get("/files/<string:file_id>")
def get_file_by_id(file_id: str):
    if not file_id.strip():
        return jsonify({"error": "invalid_file_id", "message": "file_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/files/{file_id}")

    response, error = _authorized_get(url)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    if raw:
        return jsonify(data), 200

    return jsonify(_normalize_file(data)), 200


# ============================================================
# ORGANIZATION FILES
# ============================================================

@files_bp.get("/organizations/<string:org_id>/files")
def get_organization_files(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url(f"/organizations/{org_id}/files")

    if raw:
        response, error = _authorized_get(url, params=params)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "organization_id": org_id,
        "total": len(values),
        "values": [_normalize_file(v) for v in values],
    }), 200


# ============================================================
# HPR FILES
# ============================================================

@files_bp.get("/organizations/<string:org_id>/files/hpr")
def get_organization_hpr_files(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url(f"/organizations/{org_id}/files")

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    hpr_files = [
        _normalize_file(v) for v in values
        if "hpr" in str(v.get("contentType", "")).lower()
        or str(v.get("name", "")).lower().endswith(".hpr")
    ]

    return jsonify({
        "organization_id": org_id,
        "total": len(hpr_files),
        "values": hpr_files,
    }), 200


# ============================================================
# FILE DOWNLOAD (binário)
# ============================================================

@files_bp.get("/files/<string:file_id>/download")
def download_file(file_id: str):
    if not file_id.strip():
        return jsonify({"error": "invalid_file_id", "message": "file_id nao pode ser vazio."}), 400

    # Primeiro busca metadados para obter nome e contentType
    meta_response, error = _authorized_get(_platform_url(f"/files/{file_id}"))
    if error:
        return jsonify(error[0]), error[1]

    meta = meta_response.json()
    filename = meta.get("name") or file_id
    content_type = meta.get("contentType") or "application/octet-stream"

    # Baixa o binário usando o contentType do arquivo como Accept
    bin_response, error = _authorized_get(
        _platform_url(f"/files/{file_id}"),
        accept_header=content_type,
    )
    if error:
        return jsonify(error[0]), error[1]

    return Response(
        bin_response.content,
        status=200,
        headers={
            "Content-Type": content_type,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
