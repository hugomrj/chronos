# AGENT.md — Guía para agentes que trabajan en Chronos

## Qué es este proyecto

Chronos es un sistema Flask para armar horarios escolares. Corre **una instancia por colegio**, contra una base PostgreSQL compartida. El colegio activo se define con `COLEGIO_ID` en el `.env`; no hay selector de colegios en la interfaz.

- Backend: Python 3.12, Flask 3.1, SQLAlchemy 2.x, Flask-SQLAlchemy, Flask-Login.
- Base: PostgreSQL 16 con `btree_gist`.
- Motor: PuLP 4 + HiGHS.
- Frontend: Jinja, CSS propio, JavaScript vanilla. Chart.js autoalojado.
- Sin blueprints: cada módulo de rutas expone `register_*_routes(app)` y se registra en `app/routes/registry.py`.

## Arranque rápido

```bash
cd /home/hugo/dev/flask/chronos
source venv/bin/activate
python run.py
```

La URL por defecto está en `.env` (`HOST`, `PORT`). Para producción se usa `wsgi.py` con gunicorn.

Usuario demo:

```
admin@chronos.com / admin123
```

## Comandos importantes

```bash
# Tests
./venv/bin/python -m unittest discover -s tests -v

# Compilar
./venv/bin/python -m compileall -q app scripts

# Recrear base desde cero
python scripts/drop_db.py
python scripts/create_db.py
python scripts/init_schema.py
printf 's\n' | python scripts/seed_data.py
python scripts/cargar_demo.py --force

# Regenerar guía HTML
python scripts/generar_manual.py
```

Advertencias:

- `cargar_demo.py` **borra todos los datos académicos** y conserva usuarios/roles/colegios.
- `drop_db.py` borra toda la base, incluidos usuarios.
- No hay migraciones automáticas. `scripts/schema.sql` es la fuente del esquema.
- No ejecutar `cargar_demo.py` en producción.

## Estructura

```
app/
  factory.py              create_app, CSRF, ProxyFix, contexto
  extensions.py           db, login_manager
  models/                 SQLAlchemy
  routes/
    auth.py               login/logout
    dashboard.py          KPIs y gráficos
    academic.py           años, niveles, grados, turnos, aulas, materias
    plans.py              áreas de conocimiento y planes de estudio
    teachers.py           profesores y disponibilidad
    schedule.py           plantillas, bloques, secciones y planes
    rules.py              reglas del motor
    horarios.py           generación, versiones, publicación, celdas
    reports.py            horario general, docentes, distribución
    users.py              usuarios, perfil, preferencias, configuración
    docs.py               guía y presentación
  services/scheduler/     motor MILP y constraints
  templates/              Jinja
  static/css/             estilos
scripts/
  schema.sql              esquema maestro
  init_schema.py          aplica schema.sql
  cargar_demo.py          demo completa
  seed_data.py            rol admin, colegio y usuario
  drop_db.py / create_db.py
  generar_manual.py
docs/
  Guia_Chronos.html
  doc.html                presentación para cliente
tests/test_smoke.py
```

## Modelo de datos clave

- `colegio`: `minutos_hora_catedra`.
- `nivel` = ciclo educativo.
- `plan_estudio`: un ciclo puede tener varios planes.
- `grado.plan_id`: cada grado pertenece a un plan.
- `materia`: asignatura.
- `grado_materia`: plan por grado; incluye horas, máximo por día, bloque doble y `tipo_plan` (`comun`, `especifico`, `optativo`).
- `area_conocimiento`: áreas del colegio.
- `materia.area_id`: cada materia pertenece a un área. Si se necesita el mismo nombre en otra área, se crea otra materia.
- `seccion`: curso concreto (`7° A`), año, grado, turno y plantilla.
- `seccion_materia`: copia del plan del grado; el motor la usa.
- `horario_version` y `horario_celda`: resultados, publicación y edición manual.
- `profesor_disponibilidad`: ventanas permitidas.

Los cambios de esquema deben reflejarse en **tres lugares**:

1. `scripts/schema.sql`
2. modelos en `app/models/`
3. `scripts/cargar_demo.py` si la demo usa el dato

## Motor

- `app/services/scheduler/engine.py`: MILP con variables `x` (materia/bloque), `y` (aula) y `q` (pares).
- `app/services/scheduler/constraints.py`: disponibilidad, bloques, solapamientos, aulas.
- El motor no distingue mañana/tarde: usa bloques con hora real.
- La hora cátedra configurada es **informativa**; manda la duración del bloque.
- Si un plan no entra en el esqueleto, la generación falla o la UI avisa.

## Convenciones

- Responder y escribir código/comentarios en español.
- Mantener el estilo visual existente (Outfit, glass, variables CSS).
- Los POST requieren `_csrf_token`; usar `csrf_token()` en formularios y el meta `csrf-token` para JS.
- Usar `colegio_actual()` para el colegio de la instancia.
- No exponer datos de otro colegio.
- No commitear sin pedido explícito del usuario.
- No modificar la base si el usuario pide solo análisis.
- Evitar dependencias nuevas; Chart.js está autoalojado.
- Los reportes usan el esquema existente; no agregar tablas para etiquetas.

## Estado actual

- Base local recreada y demo cargada.
- Demo: **Doble escolaridad**.
- E.E.B.: **47 bloques semanales** (9, 10, 9, 10, 9).
- Nivel Medio: 12 bloques diarios, 60 semanales.
- 5 secciones, 20 profesores, 22 materias, 10 áreas, 3 planes.
- Versión publicada: **Demo Doble escolaridad**, 175 bloques, sin choques.
- Tests: 6 OK.

## Limitaciones conocidas

- No hay roles de solo lectura para docentes.
- No hay migraciones; se recrea la base.
- El motor no admite bloques triples.
- La carga docente entre turnos/versiones no se controla globalmente.
- La UI de áreas/planes está implementada; el reporte de distribución es por plan/grado, no una matriz de todos los grados a la vez.

## Producción

- Revisar `.env`: `COLEGIO_ID`, `SUPERADMIN`, `SESSION_COOKIE_SECURE`, `USE_PROXY_FIX`, `FLASK_CONFIG`.
- Servir con gunicorn (`wsgi:app`) detrás de nginx.
- Backup y restore probados.
- Cargar datos reales y hacer UAT antes de publicar.
