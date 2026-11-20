from flask import abort, send_from_directory
from flask_login import login_required


def register_docs_routes(app):
    """Guía de usuario servida desde /guia."""

    @app.route('/guia')
    @login_required
    def guia_usuario():
        destino = app.config.get('DOCS_DIRECTORY') or 'docs'
        return send_from_directory(destino, 'Guia_Chronos.html', mimetype='text/html')

    @app.route('/guia/pdf')
    @login_required
    def guia_pdf():
        destino = app.config.get('DOCS_DIRECTORY') or 'docs'
        try:
            return send_from_directory(destino, 'Guia_Chronos.pdf', mimetype='application/pdf')
        except FileNotFoundError:
            abort(404)
