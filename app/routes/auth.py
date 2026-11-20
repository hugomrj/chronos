import secrets

from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, bcrypt
from app.models.auth import Usuario
from app.utils.helpers import is_safe_url

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
            
            # Verificar contraseña con bcrypt
            if user and bcrypt.check_password_hash(user.password_hash, password):
                login_user(user)
                # El colegio del usuario queda como colegio activo inicial.
                session['colegio_id'] = user.colegio_id
                # Rotar token CSRF para evitar fijación de sesión.
                session['_csrf_token'] = secrets.token_urlsafe(32)
                next_page = request.args.get('next')
                if is_safe_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                flash('Correo electrónico o contraseña incorrectos.', 'error')
                
        return render_template('auth/login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Has cerrado sesión correctamente.', 'success')
        return redirect(url_for('login'))
