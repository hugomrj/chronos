# ⏱️ Chronos

**Sistema inteligente de generación de horarios escolares**

Chronos automatiza la creación de horarios académicos: estructura del colegio,
profesores y disponibilidad, planes de estudio, reglas pedagógicas y un motor
de optimización que evita choques de profesores, aulas y secciones.

---

## 🚀 Tecnologías

- **Backend:** Python 3.12 + Flask (sin blueprints, rutas registradas por módulo)
- **Servidor de aplicación:** Gunicorn (`wsgi.py`)
- **Base de datos:** PostgreSQL 16 con `btree_gist` y restricciones `EXCLUDE`
  para impedir choques a nivel de motor de base de datos
- **ORM:** SQLAlchemy / Flask-SQLAlchemy
- **Autenticación:** Flask-Login + Flask-Bcrypt
- **Optimización:** PuLP 4 + solver **HiGHS** (`highspy`)
- **Frontend:** HTML5, Jinja2, CSS3 y JavaScript vanilla
- **Seguridad:** CSRF con token en sesión, contraseñas con bcrypt

---

## ✅ Funcionalidades

- Autenticación, sesión y dashboard.
- ABM de colegios, años lectivos, niveles, grados, turnos, aulas y materias.
- Planes de estudio por ciclo, áreas de conocimiento y tipo de plan
  (común / específico / optativo).
- Duración de la hora cátedra configurable por institución (`minutos_hora_catedra`).
- Límite semanal de horas por área y horas semanales por profesor con historial por año.
- Profesores con materias habilitadas, carga horaria y disponibilidad semanal.
- Plantillas de horario con bloques de clase y receso.
- Secciones por año/grado/turno con plan de estudios por grado y por sección.
- Reglas obligatorias/deseables con alcance y parámetros JSON.
- Motor MILP con restricciones duras y reglas ponderadas.
- Versiones de horario: borrador, publicación, archivo, duplicado y regeneración
  conservando celdas fijadas.
- Grilla semanal por sección y vista por profesor, edición manual e impresión.
- Horario general por día (todas las secciones en columnas) y horario individual
  docente imprimible, con totales y separado por ciclo y turno.
- Reporte de distribución de materias por plan, grado y sección, con áreas,
  tipo de plan y docentes asignados.
- Demo con doble escolaridad: Tercer Ciclo 47 bloques semanales (9 diarios y
  un décimo bloque martes y jueves) y Nivel Medio 60 bloques (12 diarios).
- Etiquetas configurables para filas no clase (Actividades Formativas, Almuerzo, Receso)
  desde `config.py`, sin cambios en la base.
- Una instancia por colegio con `COLEGIO_ID`; el superadmin administra los colegios.
- Usuarios, perfil, preferencias y configuración.

---

## 📂 Estructura

```text
chronos/
├── app/
│   ├── factory.py             # Application factory + CSRF + contexto global
│   ├── extensions.py          # db, login_manager, bcrypt
│   ├── models/                # Modelos SQLAlchemy
│   ├── routes/                # Rutas (auth, academic, plans, teachers, schedule, horarios, rules, users)
│   ├── services/scheduler/    # Motor, catálogo de reglas y restricciones
│   ├── utils/                 # Helpers y decoradores
│   ├── static/                # CSS y JS
│   └── templates/             # Jinja2
├── scripts/                   # DB, seed, backups
├── tests/                     # Smoke tests
├── config.py
├── run.py
└── requirements.txt
```

---

## ⚙️ Instalación

1. Crear y activar el entorno virtual:

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Copiar `.env.example` a `.env` y completar credenciales:

```bash
cp .env.example .env
```

4. Crear la base y aplicar el esquema:

```bash
python scripts/create_db.py
python scripts/init_schema.py
```

Si ya existe una base con un esquema anterior, hay que recrearla:

```bash
python scripts/drop_db.py
python scripts/create_db.py
python scripts/init_schema.py
```

5. Cargar datos iniciales y demo (idempotente):

```bash
python scripts/seed_data.py
python scripts/seed_estructura.py
```

6. Ejecutar en desarrollo:

```bash
python run.py
```

o en producción:

```bash
gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app
```

**Credenciales demo:** `admin@chronos.com` / `admin123`.

---

## 🏫 Una instancia por colegio

Cada colegio corre en su **propia instancia** (subdominio propio) usando el
mismo código y la misma base de datos. Una instancia nunca ve datos de otra:

- `COLEGIO_ID` en el `.env` define el colegio que sirve la instancia.
- El login rechaza usuarios que no pertenecen a ese colegio.
- No hay selector de colegio: el colegio se deriva de la configuración.
- La gestión de colegios (`/colegios`) solo existe en la instancia maestra
  (`SUPERADMIN=True`); en el resto responde 404.

### Crear una instancia para un colegio nuevo

1. Registrar el colegio en la base (instancia maestra con `SUPERADMIN=True`,
   menú **Colegios**) y anotar su `id`.
2. Generar el entorno de la instancia:

```bash
python scripts/nuevo_colegio.py 2 sanjose
# crea .env.sanjose con COLEGIO_ID=2 y SECRET_KEY nueva
```

3. Completar `DB_*`, `HOST`, `PORT` y `USE_PROXY_FIX` en ese archivo y
   enlazarlo como `.env` de la carpeta de la instancia.
4. Arrancar:

```bash
gunicorn -w 2 -b 127.0.0.1:8001 wsgi:app
```

5. Publicar con nginx/apache en el subdominio, apuntando al puerto de la instancia.

Cada colegio consume pocos recursos (Flask + 2 workers); la base es compartida.

---

## 📄 Documentación y presentación

- `AGENT.md`: guía técnica para agentes/desarrolladores.
- `CONTEXT.md`: contexto funcional, decisiones y estado del proyecto.
- `docs/doc.html`: presentación de una sola página para el cliente.
  Se sirve en `/presentacion` (también `/doc`) y sus enlaces abren el sistema
  en una pestaña nueva usando la sesión activa.

## 🧪 Tests

Los smoke tests requieren PostgreSQL y el `.env` configurado:

```bash
python -m unittest discover -s tests
```

---

## 🔐 Seguridad

- Token CSRF en todos los formularios `POST` (configurable con `CSRF_ENABLED`).
- Hash de contraseñas con bcrypt.
- Redirecciones post-login restringidas a rutas internas.
- Cookies de sesión `Secure`, `HttpOnly` y `SameSite=Lax` en producción.
- Login restringido al colegio de la instancia (`COLEGIO_ID`).
- Restricciones de integridad en PostgreSQL para choques de horario.
- Roles: actualmente solo `admin`; la UI de usuarios y configuración está
  protegida por rol.

---

## 📌 Limitaciones conocidas

- La generación es por turno; no descuenta la carga docente del otro turno.
- `EVITAR_HUECOS_PROFESOR` se aplica como aproximación lineal.
- No hay migraciones automáticas: los cambios de esquema se aplican con SQL.
- No hay notificaciones por correo ni recuperación de contraseña por email.

---

## 📋 Scripts útiles

```bash
python scripts/cargar_demo.py --force # DEMO doble escolaridad: Tercer Ciclo 47 h, Nivel Medio 60 bloques (conserva usuarios)
python scripts/seed_estructura.py     # estructura básica (sin borrar)
python scripts/nuevo_colegio.py 2 sanjose   # entorno de una instancia nueva
python scripts/generar_manual.py            # guía de usuario en docs/
python scripts/backup_db.py           # backup .sql
python scripts/restore_db.py          # restaurar backup
```
