# ⏱️ Chronos

**Sistema inteligente de generación de horarios escolares**

Chronos automatiza la creación de horarios académicos: estructura del colegio,
profesores y disponibilidad, planes de estudio, reglas pedagógicas y un motor
de optimización que evita choques de profesores, aulas y secciones.

---

## 🚀 Tecnologías

- **Backend:** Python 3.12 + Flask (sin blueprints, rutas registradas por módulo)
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
- Profesores con materias habilitadas, carga horaria y disponibilidad semanal.
- Plantillas de horario con bloques de clase y receso.
- Secciones por año/grado/turno con plan de estudios por grado y por sección.
- Reglas obligatorias/deseables con alcance y parámetros JSON.
- Motor MILP con restricciones duras y reglas ponderadas.
- Versiones de horario: borrador, publicación, archivo, duplicado y regeneración
  conservando celdas fijadas.
- Grilla semanal por sección y vista por profesor, edición manual e impresión.
- Multi-colegio: selector de colegio activo en la barra superior.
- Usuarios, perfil, preferencias y configuración.

---

## 📂 Estructura

```text
chronos/
├── app/
│   ├── factory.py             # Application factory + CSRF + contexto global
│   ├── extensions.py          # db, login_manager, bcrypt
│   ├── models/                # Modelos SQLAlchemy
│   ├── routes/                # Rutas (auth, academic, teachers, schedule, horarios, rules, users)
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

5. Cargar datos iniciales y demo (idempotente):

```bash
python scripts/seed_data.py
python scripts/seed_estructura.py
```

6. Ejecutar:

```bash
python run.py
```

Abrir `http://127.0.0.1:5000`.

**Credenciales demo:** `admin@chronos.com` / `admin123`.

---

## 🏫 Multi-colegio

El esquema soporta varios colegios. El colegio activo se guarda en la sesión y
se cambia desde el selector de la barra superior (aparece cuando hay más de un
colegio). Todas las pantallas de configuración y horarios trabajan sobre el
colegio activo.

---

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
python scripts/seed_estructura.py     # estructura + datos demo
python scripts/backup_db.py           # backup .sql
python scripts/restore_db.py          # restaurar backup
```
