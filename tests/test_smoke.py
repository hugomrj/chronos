"""Smoke tests de Chronos. Requieren PostgreSQL y el .env configurado."""
import re
import unittest

from app.factory import create_app


class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True, CSRF_ENABLED=False)
        cls.client = cls.app.test_client()

    def test_login_y_paginas_principales(self):
        r = self.client.post('/login', data={
            'email': 'admin@chronos.com',
            'password': 'admin123',
        })
        self.assertEqual(r.status_code, 302)

        rutas = [
            '/dashboard', '/anios', '/niveles', '/grados',
            '/turnos', '/aulas', '/materias', '/profesores', '/disponibilidad',
            '/plantillas', '/secciones', '/reglas', '/horarios',
            '/horarios/docentes', '/guia', '/usuarios',
            '/perfil', '/preferencias', '/configuracion',
        ]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_colegios_solo_para_superadmin(self):
        self.client.post('/login', data={
            'email': 'admin@chronos.com',
            'password': 'admin123',
        })
        # La instancia normal no administra colegios.
        self.assertEqual(self.client.get('/colegios').status_code, 404)

    def test_instancia_ajena_rechaza_login(self):
        app = create_app()
        app.config.update(TESTING=True, CSRF_ENABLED=False, COLEGIO_ID=9999)
        client = app.test_client()
        r = client.post('/login', data={
            'email': 'admin@chronos.com',
            'password': 'admin123',
        })
        self.assertEqual(r.status_code, 200)
        self.assertIn('no pertenece a esta instituci', r.get_data(as_text=True))

    def test_post_sin_csrf_es_rechazado(self):
        app = create_app()
        app.config.update(TESTING=True, CSRF_ENABLED=True)
        client = app.test_client()

        html = client.get('/login').get_data(as_text=True)
        token = re.search(r'name="_csrf_token" value="([^"]+)"', html).group(1)

        self.assertEqual(client.post('/login', data={
            'email': 'admin@chronos.com',
            'password': 'admin123',
        }).status_code, 400)

        self.assertEqual(client.post('/login', data={
            'email': 'admin@chronos.com',
            'password': 'admin123',
            '_csrf_token': token,
        }).status_code, 302)


if __name__ == '__main__':
    unittest.main()
