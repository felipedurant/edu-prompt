"""Flask application factory."""

import logging

from flask import Flask, render_template_string

from app.config import FLASK_SECRET_KEY, LOG_LEVEL, LOG_FORMAT, DATA_DIR

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Erro {{ code }}</title>
<style>body{font-family:sans-serif;background:#0f1117;color:#c0caf5;display:flex;
justify-content:center;align-items:center;height:100vh;margin:0}
.box{text-align:center}h1{font-size:3rem;color:#f7768e}
a{color:#7aa2f7}</style></head>
<body><div class="box"><h1>{{ code }}</h1><p>{{ message }}</p>
<a href="/">Voltar ao inicio</a></div></body></html>
"""


def create_app() -> Flask:
    """Cria e configura a aplicacao Flask."""
    app = Flask(__name__)
    app.secret_key = FLASK_SECRET_KEY

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    from app.web.routes import bp
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template_string(
            ERROR_TEMPLATE, code=404, message="Pagina nao encontrada."
        ), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error("Erro interno: %s", e)
        return render_template_string(
            ERROR_TEMPLATE, code=500, message="Erro interno do servidor."
        ), 500

    return app
