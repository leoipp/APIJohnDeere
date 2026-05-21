from flask import Blueprint, Response, jsonify, request

from deere_client import _authorized_get, _date_params, _fetch_all_pages, _platform_url

files_bp = Blueprint("files_bp", __name__)


def _extract_link(item: dict, rel: str) -> str | None:
    for link in item.get("links") or []:
        if isinstance(link, dict) and link.get("rel") == rel:
            return link.get("uri")
    return None


def _normalize_file(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "file_type": item.get("type"),
        "size": item.get("nativeSize"),
        "created": item.get("createdTime"),
        "modified": item.get("modifiedTime"),
        "status": item.get("status"),
        "organization_id": item.get("organizationId"),
        "source": item.get("source"),
        "manufacturer": item.get("manufacturer"),
        "presigned_download_url": _extract_link(item, "presignedDownload"),
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
# STANFORD / PRODUCTION FILES
# ============================================================

_STANFORD_EXTENSIONS = {".hpr", ".mom", ".oin", ".pin", ".prd", ".spi"}


def _is_stanford_file(item: dict) -> bool:
    name = str(item.get("name", "")).lower()
    if any(name.endswith(ext) for ext in _STANFORD_EXTENSIONS):
        return True
    # TIMBERLINK empacota em .zip — inclui todos os zips de máquina
    if name.endswith(".zip") and item.get("type") == "TIMBERLINK":
        return True
    return False


@files_bp.get("/organizations/<string:org_id>/files/stanford")
def get_organization_stanford_files(org_id: str):
    if not org_id.strip():
        return jsonify({"error": "invalid_org_id", "message": "org_id nao pode ser vazio."}), 400

    if not request.args.get("startDate") and not request.args.get("endDate"):
        return jsonify({
            "error": "missing_date_filter",
            "message": "Informe startDate e/ou endDate para evitar timeout. Ex: ?startDate=2025-01-01&endDate=2025-12-31",
        }), 400

    params: dict = {
        "filter": "MACHINE",
        "itemLimit": request.args.get("itemLimit", "100"),
    }
    date_p = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    if date_p:
        params.update(date_p)

    url = _platform_url(f"/organizations/{org_id}/files")
    response, error = _authorized_get(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    data = response.json()
    values = data.get("values", []) if isinstance(data, dict) else []

    stanford_files = [
        _normalize_file(v) for v in values
        if isinstance(v, dict) and _is_stanford_file(v)
    ]

    return jsonify({
        "organization_id": org_id,
        "total_returned": len(values),
        "total_stanford": len(stanford_files),
        "values": stanford_files,
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

    # Tenta presignedDownload primeiro; cai no link download direto se der 403
    download_url = _extract_link(meta, "presignedDownload") or _extract_link(meta, "download")
    if not download_url:
        return jsonify({"error": "no_download_link", "message": "Nenhum link de download disponivel para este arquivo."}), 404

    bin_response, error = _authorized_get(download_url, accept_header="application/octet-stream")
    if error and error[1] == 403:
        fallback_url = _extract_link(meta, "download")
        if fallback_url and fallback_url != download_url:
            bin_response, error = _authorized_get(fallback_url, accept_header="application/octet-stream")
    if error:
        return jsonify(error[0]), error[1]

    content_type = bin_response.headers.get("Content-Type", "application/octet-stream")

    return Response(
        bin_response.content,
        status=200,
        headers={
            "Content-Type": content_type,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
