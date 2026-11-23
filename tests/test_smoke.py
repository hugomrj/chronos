"""Smoke tests de Chronos. Requieren PostgreSQL y el .env configurado."""
import re
import unittest

from app.extensions import db
from app.factory import create_app
from app.models import AreaConocimiento, Colegio, Grado, PlanEstudio


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
            '/turnos', '/aulas', '/materias', '/areas', '/planes',
            '/profesores', '/disponibilidad', '/plantillas', '/secciones',
            '/reglas', '/horarios', '/horarios/docentes',
            '/reportes/distribucion', '/presentacion', '/guia', '/usuarios',
            '/perfil', '/preferencias', '/configuracion',
        ]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_areas_y_planes(self):
        self.client.post('/login', data={
            'email': 'admin@chronos.com',
            'password': 'admin123',
        })
        with self.app.app_context():
            nivel_id = Grado.query.first().nivel_id
            AreaConocimiento.query.filter_by(nombre='Área Smoke').delete()
            PlanEstudio.query.filter_by(nombre='Plan Smoke').delete()
            db.session.commit()

        r = self.client.post('/areas/guardar', data={
            'nombre': 'Área Smoke', 'orden': '99', 'activa': 'on',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        with self.app.app_context():
            area = AreaConocimiento.query.filter_by(nombre='Área Smoke').first()
            self.assertIsNotNone(area)
            area_id = area.id

        r = self.client.post('/planes/guardar', data={
            'nombre': 'Plan Smoke', 'nivel_id': str(nivel_id),
            'orden': '99', 'activo': 'on',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        with self.app.app_context():
            plan = PlanEstudio.query.filter_by(nombre='Plan Smoke').first()
            self.assertIsNotNone(plan)
            plan_id = plan.id

        self.client.post(f'/planes/{plan_id}/eliminar')
        self.client.post(f'/areas/{area_id}/eliminar')

    def test_configuracion_hora_catedra(self):
        self.client.post('/login', data={
            'email': 'admin@chronos.com',
            'password': 'admin123',
        })
        r = self.client.post('/configuracion/guardar', data={
            'nombre': 'Colegio Demo', 'minutos_hora_catedra': '45',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        with self.app.app_context():
            self.assertEqual(Colegio.query.first().minutos_hora_catedra, 45)
        self.client.post('/configuracion/guardar', data={
            'nombre': 'Colegio Demo', 'minutos_hora_catedra': '40',
        })

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
