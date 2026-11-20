import secrets

from flask import current_app, flash, redirect, render_template, request, url_for, session
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import bcrypt
from app.models.auth import Usuario
from app.utils.helpers import colegio_actual, is_safe_url


def register_auth_routes(app):
    """Registra las rutas de autenticación."""

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # Si ya está logueado, redirigir al dashboard
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password')

            # Buscar usuario activo por email
            user = Usuario.query.filter_by(email=email, activo=True).first()

            credenciales_ok = bool(user) and bool(password) and \
                bcrypt.check_password_hash(user.password_hash, password)

            # Cada instancia sirve un único colegio: el usuario debe ser de ese colegio.
            colegio_id = current_app.config.get('COLEGIO_ID') or 0
            pertenece = not colegio_id or (user is not None and user.colegio_id == colegio_id)

            if credenciales_ok and pertenece:
                login_user(user)
                # Rotar token CSRF para evitar fijación de sesión.
                session['_csrf_token'] = secrets.token_urlsafe(32)
                next_page = request.args.get('next')
                if is_safe_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('dashboard'))

            if credenciales_ok and not pertenece:
                flash('Este usuario no pertenece a esta institución.', 'error')
            else:
                flash('Correo electrónico o contraseña incorrectos.', 'error')

        return render_template('auth/login.html', colegio=colegio_actual())

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Has cerrado sesión correctamente.', 'success')
        return redirect(url_for('login'))
