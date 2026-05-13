import json
import os

from flask import Flask, jsonify, url_for


def load_env_from_json() -> None:
    candidates = ["variaveis_ambiente.json", "variaveis_ambiente_exemplo.json"]
    for filename in candidates:
        if not os.path.exists(filename):
            continue
        try:
            with open(filename, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                for key, value in data.items():
                    if value is None:
                        continue
                    os.environ.setdefault(str(key), str(value))
            return
        except (OSError, json.JSONDecodeError):
            return


def create_app() -> Flask:
    load_env_from_json()
    from auth import auth_bp
    from operations_center import operations_center_bp
    from bi import bi_bp
    from equipment import equipment_bp
    from machines_telemetry import machines_telemetry_bp
    from assets import assets_bp
    from maps import maps_bp
    from files_api import files_bp
    from agronomy import agronomy_bp
    from farm_ops import farm_ops_bp

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(operations_center_bp, url_prefix="/api/oc")
    app.register_blueprint(bi_bp, url_prefix="/api/bi")

    # Operations Center — domínios separados, mesmo prefixo /api/oc
    app.register_blueprint(equipment_bp, url_prefix="/api/oc")
    app.register_blueprint(machines_telemetry_bp, url_prefix="/api/oc")
    app.register_blueprint(assets_bp, url_prefix="/api/oc")
    app.register_blueprint(maps_bp, url_prefix="/api/oc")
    app.register_blueprint(files_bp, url_prefix="/api/oc")
    app.register_blueprint(farm_ops_bp, url_prefix="/api/oc")

    # Agronomia — prefixo dedicado /api/agro
    app.register_blueprint(agronomy_bp, url_prefix="/api/agro")

    @app.get("/")
    def root():
        login_url = url_for("auth_bp.login", _external=True)
        status_url = url_for("auth_bp.auth_status", _external=True)
        organizations_url = url_for("operations_center_bp.get_organizations", _external=True)
        return f"""
        <html>
            <head><title>John Deere API</title></head>
            <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>John Deere Operations Center API</h1>
                <p>API em execucao com sucesso.</p>
                <ul>
                    <li><a href="{login_url}">Fazer login (OAuth)</a></li>
                    <li><a href="{status_url}">Ver status da autenticacao</a></li>
                    <li><a href="{organizations_url}">Listar organizacoes</a></li>
                </ul>
                <h2>Prefixos disponíveis</h2>
                <ul>
                    <li><code>/api/oc</code> — Organizations, Equipment, Machines, Assets, Maps, Files, Farms, Operators</li>
                    <li><code>/api/agro</code> — Chemicals, Fertilizers, Varieties, TankMixes, DryBlends, ProductCompanies, ActiveIngredients</li>
                    <li><code>/api/bi</code> — Dados formatados para BI</li>
                </ul>
            </body>
        </html>
        """

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
