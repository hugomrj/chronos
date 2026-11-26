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
- Profesores con materias y especialidades habilitadas, carga horaria y disponibilidad semanal.
- Especialidades BATIN/BATAN, plan de estudios por curso y selección de plan por sección.
- Plantillas de horario con bloques de clase y receso.
- Secciones por año/curso/turno con plan de estudios y especialidad por sección.
- Reglas obligatorias/deseables con alcance y parámetros JSON.
- Motor MILP con restricciones duras y reglas ponderadas.
- Versiones de horario: borrador, publicación, archivo, duplicado y regeneración
  conservando celdas fijadas.
- Grilla semanal por sección y vista por profesor, edición manual e impresión.
- Horario general por día (todas las secciones en columnas) y horario individual
  docente imprimible, con totales y separado por ciclo y turno.
- Reporte de distribución de materias por plan, grado y sección, con áreas,
  tipo de plan y docentes asignados.
- Demo con doble escolaridad: E.E.B. 47 bloques semanales (9 diarios y
  un décimo bloque martes y jueves) y Nivel Medio 60 bloques (12 diarios).
- Etiquetas configurables para filas no clase (Actividades Formativas, Almuerzo, Receso)
  desde `config.py`, sin cambios en la base.
- **Una instancia por colegio** con `COLEGIO_ID`.
- **Roles**: `admin` administra su colegio (menú, usuarios, configuración y roles);
  el resto de los roles ven solo las pantallas que el admin les habilite.
- Menú por rol (`rol_menu`), aplicado en la vista y también en las rutas.
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
python scripts/seed_data.py        # roles master/admin y usuarios
python scripts/cargar_demo.py --force  # opcional: datos de ejemplo
```

6. Ejecutar en desarrollo:

```bash
python run.py
```

o en producción:

```bash
gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app
```

**Credenciales demo:**

- `master@chronos.com` / `admin123` — rol master (roles, menú y ajustes de instancia)
- `admin@chronos.com` / `admin123` — rol admin (administra el colegio)

---

## 🏫 Instancias: una por colegio

Cada colegio corre en su **propia instancia** (subdominio propio), con el mismo
código y la misma base de datos. La instancia sirve **un solo colegio**:

- `COLEGIO_ID` en el `.env` define qué colegio sirve.
- El login rechaza usuarios de otro colegio.
- Todas las consultas filtran por `colegio_id`.
- **No hay pantalla de Colegios**: el alta de colegios es tarea de servidor.

### Ajustes de instancia (solo master)

`/ajustes` define cómo funciona la instalación. Hoy incluye **Uso de aulas**:

- **Con aulas**: cada clase necesita un aula y el motor controla choques de aula.
- **Sin aulas**: el horario se genera solo con profesor y sección; la pantalla
  Aulas desaparece del menú.

Cambiar la opción **no reestructura** los horarios existentes: hay que generarlos
de nuevo.

### Roles

| Rol | Alcance |
|---|---|
| `admin` | Administra todo el colegio: menú completo + usuarios, configuración y roles |
| Otros roles | Solo las pantallas que el admin les habilite |

El admin define el menú de cada rol en **Roles y menú** (`/roles`).
`Usuarios` y `Configuración` quedan siempre habilitados para el admin.
Los demás usuarios solo ven las pantallas marcadas para su rol, y si escriben
una URL no permitida se los redirige al dashboard.

### Alta de un colegio nuevo

1. Crear el colegio en la base (script o SQL) y anotar su `id`.
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

5. Publicar el subdominio en nginx/apache apuntando al puerto de la instancia.
6. Entrar como `admin` y cargar estructura, profesores y horarios.

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
- El menú de cada rol se define en **Roles y menú** y se valida también en las
  rutas, no solo en la vista.
- Solo el rol `admin` accede a usuarios, configuración y roles.

---

## 📌 Limitaciones conocidas

- La generación es por turno; no descuenta la carga docente del otro turno.
- `EVITAR_HUECOS_PROFESOR` se aplica como aproximación lineal.
- No hay migraciones automáticas: los cambios de esquema se aplican con SQL.
- No hay notificaciones por correo ni recuperación de contraseña por email.

---

## 📋 Scripts útiles

```bash
python scripts/cargar_demo.py --force # DEMO doble escolaridad: E.E.B. 47 h, Nivel Medio 60 bloques (conserva usuarios)
python scripts/seed_estructura.py     # estructura básica (sin borrar)
python scripts/nuevo_colegio.py 2 sanjose   # entorno de una instancia nueva
python scripts/generar_manual.py            # guía de usuario en docs/
python scripts/backup_db.py           # backup .sql
python scripts/restore_db.py          # restaurar backup
```
