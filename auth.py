import os
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

auth_bp = Blueprint("auth_bp", __name__)


def _client_id() -> str:
    return os.environ.get("DEERE_CLIENT_ID", "").strip()


def _client_secret() -> str:
    return os.environ.get("DEERE_CLIENT_SECRET", "").strip()


def _redirect_uri() -> str:
    return os.environ.get("DEERE_REDIRECT_URI", "http://localhost:5000/auth/callback").strip()


def _oauth_issuer() -> str:
    return os.environ.get(
        "DEERE_OAUTH_ISSUER",
        "https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7",
    ).strip()


def _well_known_url() -> str:
    return f"{_oauth_issuer()}/.well-known/oauth-authorization-server"


def _scopes() -> str:
    return os.environ.get("DEERE_SCOPES", "ag1 org1 offline_access").strip()


def _http_timeout_seconds() -> int:
    return int(os.environ.get("HTTP_TIMEOUT_SECONDS", "20"))


def _oauth_config() -> dict[str, Any]:
    cached = session.get("oauth_server")
    if isinstance(cached, dict) and cached.get("authorization_endpoint") and cached.get("token_endpoint"):
        return cached

    response = requests.get(_well_known_url(), timeout=_http_timeout_seconds())
    response.raise_for_status()
    data = response.json()

    config = {
        "authorization_endpoint": data.get("authorization_endpoint"),
        "token_endpoint": data.get("token_endpoint"),
    }
    session["oauth_server"] = config
    return config


def _store_tokens(token_data: dict[str, Any]) -> None:
    expires_in = int(token_data.get("expires_in", 0))
    session["access_token"] = token_data.get("access_token")
    session["refresh_token"] = token_data.get("refresh_token") or session.get("refresh_token")
    session["token_type"] = token_data.get("token_type", "Bearer")
    session["expires_at"] = int(time.time()) + expires_in if expires_in > 0 else None


def _token_expired() -> bool:
    expires_at = session.get("expires_at")
    if not expires_at:
        return False
    return int(time.time()) >= int(expires_at) - 60


def _clear_auth_session() -> None:
    for key in [
        "access_token",
        "refresh_token",
        "token_type",
        "expires_at",
        "oauth_state",
        "oauth_server",
    ]:
        session.pop(key, None)


def _exchange_code_for_token(code: str) -> dict[str, Any]:
    config = _oauth_config()
    token_endpoint = config.get("token_endpoint")

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _redirect_uri(),
        "client_id": _client_id(),
        "client_secret": _client_secret(),
    }

    response = requests.post(token_endpoint, data=payload, timeout=_http_timeout_seconds())
    response.raise_for_status()
    return response.json()


def _refresh_access_token_internal() -> bool:
    refresh_token = session.get("refresh_token")
    if not refresh_token:
        return False

    try:
        config = _oauth_config()
        token_endpoint = config.get("token_endpoint")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "scope": _scopes(),
        }
        response = requests.post(token_endpoint, data=payload, timeout=_http_timeout_seconds())
        response.raise_for_status()
        _store_tokens(response.json())
        return True
    except requests.RequestException:
        current_app.logger.exception("Falha ao renovar token de acesso.")
        _clear_auth_session()
        return False


def get_valid_access_token() -> str | None:
    access_token = session.get("access_token")
    if not access_token:
        return None

    if _token_expired():
        refreshed = _refresh_access_token_internal()
        if not refreshed:
            return None
        return session.get("access_token")

    return access_token


@auth_bp.get("/login")
def login():
    if not _client_id() or not _client_secret():
        return (
            jsonify(
                {
                    "error": "missing_configuration",
                    "message": "Defina DEERE_CLIENT_ID e DEERE_CLIENT_SECRET.",
                }
            ),
            500,
        )

    try:
        config = _oauth_config()
        authorization_endpoint = config.get("authorization_endpoint")
    except requests.RequestException as exc:
        current_app.logger.exception("Falha ao carregar configuração OAuth.")
        return jsonify({"error": "oauth_discovery_failed", "message": str(exc)}), 502

    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state

    params = {
        "client_id": _client_id(),
        "response_type": "code",
        "redirect_uri": _redirect_uri(),
        "scope": _scopes(),
        "state": state,
    }
    return redirect(f"{authorization_endpoint}?{urlencode(params)}")


@auth_bp.get("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return jsonify({"error": error, "description": request.args.get("error_description")}), 400

    code = request.args.get("code")
    returned_state = request.args.get("state")

    if not code:
        return jsonify({"error": "missing_code", "message": "Codigo de autorizacao ausente."}), 400

    expected_state = session.get("oauth_state")
    session.pop("oauth_state", None)

    if not expected_state or expected_state != returned_state:
        return jsonify({"error": "invalid_state", "message": "State OAuth invalido."}), 400

    try:
        token_data = _exchange_code_for_token(code)
    except requests.RequestException as exc:
        current_app.logger.exception("Falha na troca do codigo por token.")
        return jsonify({"error": "token_exchange_failed", "message": str(exc)}), 502

    _store_tokens(token_data)
    return redirect(url_for("operations_center_bp.get_organizations"))


@auth_bp.get("/refresh-token")
def refresh_token_route():
    if not _client_id() or not _client_secret():
        return jsonify({"error": "missing_configuration"}), 500

    if _refresh_access_token_internal():
        return jsonify({"message": "token_refreshed"}), 200

    return jsonify({"error": "refresh_failed", "message": "Faca login novamente."}), 401


@auth_bp.get("/logout")
def logout():
    _clear_auth_session()
    return jsonify({"message": "logout_success"}), 200


@auth_bp.get("/status")
def auth_status():
    return jsonify(
        {
            "authenticated": bool(session.get("access_token")),
            "expires_at": session.get("expires_at"),
            "has_refresh_token": bool(session.get("refresh_token")),
        }
    )
