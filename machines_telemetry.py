from flask import Blueprint, jsonify, request

from deere_client import _authorized_get, _date_params, _fetch_all_pages, _platform_url

machines_telemetry_bp = Blueprint("machines_telemetry_bp", __name__)

_SEQ_LABELS: dict[int, str] = {0: "working", 1: "idle", 2: "transport"}
_FUEL_NAME = "Fuel Consumed"
_UTILIZATION_NAME = "Machine Utilization"
_NO_PAGING_HEADER = {"x-deere-no-paging": "true"}


def _def_id_from_item(item: dict) -> str | None:
    embedded = item.get("machineMeasurementDefinition")
    if isinstance(embedded, dict):
        embedded_id = embedded.get("id")
        if embedded_id:
            return str(embedded_id)
    links = item.get("links") if isinstance(item.get("links"), list) else []
    for link in links:
        if isinstance(link, dict) and link.get("rel") == "measurementDefinition":
            uri = link.get("uri", "")
            return uri.split("/")[-1] if uri else None
    return None


def _def_name_from_item(item: dict) -> str | None:
    embedded = item.get("machineMeasurementDefinition")
    if isinstance(embedded, dict):
        return embedded.get("name")
    return None


def _normalize_breadcrumb(item: dict) -> dict:
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    measurement = item.get("measurement") if isinstance(item.get("measurement"), dict) else {}
    return {
        "timestamp": item.get("timestamp"),
        "lat": location.get("lat"),
        "lon": location.get("lon"),
        "altitude": location.get("altitude"),
        "heading": item.get("heading"),
        "speed": measurement.get("asDouble"),
        "speed_unit": measurement.get("unit"),
    }


def _normalize_location_history(item: dict) -> dict:
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    return {
        "timestamp": item.get("timestamp") or item.get("reportTime"),
        "lat": location.get("lat"),
        "lon": location.get("lon"),
        "altitude": location.get("altitude"),
        "source": item.get("source"),
    }


def _normalize_device_state_report(item: dict) -> dict:
    return {
        "report_time": item.get("reportTime"),
        "device_id": item.get("deviceId"),
        "state": item.get("state"),
        "connection_status": item.get("connectionStatus"),
        "resource_type": item.get("@type"),
    }


def _normalize_machine_measurement(item: dict) -> list[dict]:
    measurement_def_id = _def_id_from_item(item)
    measurement_name = _def_name_from_item(item)

    series = item.get("series") if isinstance(item.get("series"), dict) else {}
    level = series.get("level")
    intervals = series.get("intervals") if isinstance(series.get("intervals"), list) else []

    rows = []
    for interval in intervals:
        if not isinstance(interval, dict):
            continue
        interval_start = interval.get("intervalStartDate")
        interval_end = interval.get("intervalEndDate")
        buckets_wrap = interval.get("buckets") if isinstance(interval.get("buckets"), dict) else {}
        buckets = buckets_wrap.get("buckets") if isinstance(buckets_wrap.get("buckets"), list) else []
        for bucket in buckets:
            if not isinstance(bucket, dict):
                continue
            rows.append({
                "measurement_def_id": measurement_def_id,
                "measurement_name": measurement_name,
                "network_type": item.get("networkType"),
                "level": level,
                "interval_start": interval_start,
                "interval_end": interval_end,
                "actual_start": bucket.get("actualStartDate"),
                "actual_end": bucket.get("actualEndDate"),
                "count": bucket.get("count"),
                "sequence_number": bucket.get("sequenceNumber"),
                "value": bucket.get("value"),
            })
    return rows


def _normalize_hours_of_operation(item: dict) -> dict:
    reading = item.get("reading") if isinstance(item.get("reading"), dict) else {}
    return {
        "date": item.get("date"),
        "hours": reading.get("valueAsDouble"),
        "unit": reading.get("unit"),
        "report_time": item.get("reportTime"),
    }


# ============================================================
# MACHINE MEASUREMENTS
# ============================================================

@machines_telemetry_bp.get("/machines/<string:machine_id>/machineMeasurements")
def get_machine_measurements(machine_id: str):
    if not machine_id.strip():
        return jsonify({"error": "invalid_machine_id", "message": "machine_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    url = _platform_url(f"/machines/{machine_id}/machineMeasurements")

    params: dict = {}
    date_p = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    if date_p:
        params.update(date_p)
    interval = request.args.get("interval")
    if interval:
        params["interval"] = interval

    if raw:
        response, error = _authorized_get(url, params=params or None)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    params["embed"] = "measurementDefinition"

    values, error = _fetch_all_pages(url, params=params, extra_headers=_NO_PAGING_HEADER)
    if error:
        return jsonify(error[0]), error[1]

    rows = [row for item in values for row in _normalize_machine_measurement(item)]

    return jsonify({
        "machine_id": machine_id,
        "measurement_definitions": len(values),
        "total": len(rows),
        "values": rows,
    }), 200


# ============================================================
# FUEL AND UTILIZATION
# ============================================================

@machines_telemetry_bp.get("/machines/<string:machine_id>/fuelAndUtilization")
def get_fuel_and_utilization(machine_id: str):
    if not machine_id.strip():
        return jsonify({"error": "invalid_machine_id", "message": "machine_id nao pode ser vazio."}), 400

    params: dict = {"embed": "measurementDefinition"}
    date_p = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    if date_p:
        params.update(date_p)
    interval = request.args.get("interval")
    if interval:
        params["interval"] = interval

    url = _platform_url(f"/machines/{machine_id}/machineMeasurements")
    values, error = _fetch_all_pages(url, params=params, extra_headers=_NO_PAGING_HEADER)
    if error:
        return jsonify(error[0]), error[1]

    target_names = {_FUEL_NAME, _UTILIZATION_NAME}
    rows = []

    for item in values:
        name = _def_name_from_item(item)
        if name not in target_names:
            continue

        def_id = _def_id_from_item(item)
        series = item.get("series") if isinstance(item.get("series"), dict) else {}
        level = series.get("level")
        intervals = series.get("intervals") if isinstance(series.get("intervals"), list) else []

        for interval_item in intervals:
            if not isinstance(interval_item, dict):
                continue
            interval_start = interval_item.get("intervalStartDate")
            interval_end = interval_item.get("intervalEndDate")
            buckets_wrap = interval_item.get("buckets") if isinstance(interval_item.get("buckets"), dict) else {}
            buckets = buckets_wrap.get("buckets") if isinstance(buckets_wrap.get("buckets"), list) else []
            for bucket in buckets:
                if not isinstance(bucket, dict):
                    continue
                seq = bucket.get("sequenceNumber")
                value = bucket.get("value")
                row: dict = {
                    "measurement_def_id": def_id,
                    "measurement_name": name,
                    "network_type": item.get("networkType"),
                    "level": level,
                    "interval_start": interval_start,
                    "interval_end": interval_end,
                    "actual_start": bucket.get("actualStartDate"),
                    "actual_end": bucket.get("actualEndDate"),
                    "count": bucket.get("count"),
                    "sequence_number": seq,
                    "category": _SEQ_LABELS.get(seq),
                    "value": value,
                }
                if name == _UTILIZATION_NAME and value is not None:
                    row["value_hours"] = round(value / 3600, 4)
                rows.append(row)

    return jsonify({
        "machine_id": machine_id,
        "total": len(rows),
        "values": rows,
    }), 200


# ============================================================
# BREADCRUMBS
# ============================================================

@machines_telemetry_bp.get("/machines/<string:machine_id>/breadcrumbs")
def get_machine_breadcrumbs(machine_id: str):
    if not machine_id.strip():
        return jsonify({"error": "invalid_machine_id", "message": "machine_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url(f"/machines/{machine_id}/breadcrumbs")

    if raw:
        response, error = _authorized_get(url, params=params)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "machine_id": machine_id,
        "total": len(values),
        "values": [_normalize_breadcrumb(v) for v in values],
    }), 200


# ============================================================
# LOCATION HISTORY
# ============================================================

@machines_telemetry_bp.get("/machines/<string:machine_id>/locationHistory")
def get_machine_location_history(machine_id: str):
    if not machine_id.strip():
        return jsonify({"error": "invalid_machine_id", "message": "machine_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url(f"/machines/{machine_id}/locationHistory")

    if raw:
        response, error = _authorized_get(url, params=params)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "machine_id": machine_id,
        "total": len(values),
        "values": [_normalize_location_history(v) for v in values],
    }), 200


# ============================================================
# DEVICE STATE REPORTS
# ============================================================

@machines_telemetry_bp.get("/machines/<string:machine_id>/deviceStateReports")
def get_machine_device_state_reports(machine_id: str):
    if not machine_id.strip():
        return jsonify({"error": "invalid_machine_id", "message": "machine_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url(f"/machines/{machine_id}/deviceStateReports")

    if raw:
        response, error = _authorized_get(url, params=params)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "machine_id": machine_id,
        "total": len(values),
        "values": [_normalize_device_state_report(v) for v in values],
    }), 200


# ============================================================
# HOURS OF OPERATION
# ============================================================

@machines_telemetry_bp.get("/machines/<string:machine_id>/hoursOfOperation")
def get_machine_hours_of_operation(machine_id: str):
    if not machine_id.strip():
        return jsonify({"error": "invalid_machine_id", "message": "machine_id nao pode ser vazio."}), 400

    raw = request.args.get("raw", "false").lower() == "true"
    params = _date_params(request.args.get("startDate"), request.args.get("endDate"))
    url = _platform_url(f"/machines/{machine_id}/hoursOfOperation")

    if raw:
        response, error = _authorized_get(url, params=params)
        if error:
            return jsonify(error[0]), error[1]
        return jsonify(response.json()), 200

    values, error = _fetch_all_pages(url, params=params)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({
        "machine_id": machine_id,
        "total": len(values),
        "values": [_normalize_hours_of_operation(v) for v in values],
    }), 200
