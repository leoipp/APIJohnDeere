from flask import Blueprint, jsonify, request

from deere_client import _authorized_get

bi_bp = Blueprint("bi_bp", __name__)


def _machine_to_row(machine: dict) -> dict:
    return {
        "organization_id": machine.get("organization", {}).get("id"),
        "machine_id": machine.get("id"),
        "principal_id": machine.get("principalId"),
        "erid": machine.get("ERID"),
        "name": machine.get("name"),
        "serial_number": machine.get("serialNumber"),
        "engine_serial_number": machine.get("engineSerialNumber"),
        "model": machine.get("model", {}).get("name"),
        "model_id": machine.get("model", {}).get("id"),
        "model_year": machine.get("modelYear"),
        "make": machine.get("make", {}).get("name"),
        "type": machine.get("type", {}).get("name"),
        "type_id": machine.get("type", {}).get("id"),
        "isg_type": machine.get("isgType", {}).get("name"),
        "isg_type_id": machine.get("isgType", {}).get("id"),
        "archived": machine.get("archived"),
        "telematics_capable": machine.get("telematicsCapable"),
        "in_possession": machine.get("organizationRole", {}).get("inPossession"),
        "organization_role_type": machine.get("organizationRole", {}).get("type"),
        "organization_role_event": machine.get("organizationRole", {}).get("event"),
        "organization_role_effective_ts": machine.get("organizationRole", {}).get("effectiveTS"),
    }


@bi_bp.get("/fleet")
def get_fleet_for_bi():
    organization_id = request.args.get("organization_id", "413958")

    url = "https://api.deere.com/isg/equipment"

    response, error = _authorized_get(
        url,
        params={"organizationIds": organization_id},
    )

    if error:
        return jsonify(error[0]), error[1]

    payload = response.json()
    values = payload.get("values", [])

    rows = [
        _machine_to_row(item)
        for item in values
        if isinstance(item, dict)
    ]

    return jsonify(rows), 200