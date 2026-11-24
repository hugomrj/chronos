# CONTEXT.md — Contexto funcional de Chronos

## Producto

Chronos genera y administra horarios escolares. El objetivo es que un colegio pueda cargar su estructura, planes de estudio, docentes y disponibilidad, y obtener un horario sin choques de profesores, aulas o secciones.

El cliente trabaja con:

- **Ciclos educativos**: E.E.B. (7°, 8°, 9°) y Nivel Medio (1°, 2°, 3°).
- **Planes**: E.E.B. 7°–9°, BATIN (Bachillerato Técnico en Informática) y BATAN (Bachillerato Técnico en Administración de Negocios).
- **Doble escolaridad**: un mismo curso puede tener clases en la mañana y en la tarde. No se modela como dos turnos separados: se usa un turno “Doble escolaridad” y una plantilla full-day por ciclo.
- **Hora cátedra**: nominalmente 40 minutos, configurable por institución. En la práctica hay bloques de 30, 35 y 40 minutos; manda la hora real del bloque.

## Decisiones de modelado

1. **Un colegio por instancia**  
   Cada instancia tiene `COLEGIO_ID` en el `.env`. No hay selector de colegios. La base PostgreSQL puede ser compartida, pero cada instancia ve solo su colegio.

2. **Ciclo = `nivel`**  
   No se agregó una tabla nueva de ciclos: `nivel` cumple ese rol.

3. **Planes**
   - `plan_estudio` pertenece a un ciclo.
   - `grado.plan_id` indica a qué plan pertenece cada grado.
   - Un plan puede abarcar varios grados.
   - BATIN y BATAN se manejan con grados separados (`1° BATIN Informática`, `1° BATAN Contabilidad`), cada uno con su plan.

4. **Áreas**
   - `area_conocimiento` es por colegio.
   - `materia.area_id` es la relación directa: cada materia pertenece a un área.
   - Si se necesita la misma materia en otra área, se crea otro registro de materia.
   - El área se hereda en el plan del grado.

5. **Tipo de plan**
   - `grado_materia.tipo_plan`: `comun`, `especifico` u `optativo`.
   - El reporte de distribución agrupa por tipo → área → materia.

6. **Horas**
   - `grado_materia.horas_semanales` define el plan base.
   - `seccion_materia` copia el plan al crear la sección.
   - `max_bloques_por_dia` limita cuántas veces puede aparecer una materia en un día. Las materias de 6 horas usan 2 para poder entrar en 5 días.

7. **Plantillas**
   - `plantilla_horario` pertenece a un turno.
   - `bloque` tiene día, número, inicio, fin y tipo (`clase`/`receso`).
   - Cada día puede tener una cantidad distinta de bloques.
   - No se guarda una “salida” aparte: la salida es el fin del último bloque.

## Demo actual

La base local fue recreada desde `scripts/schema.sql` y cargada con `scripts/cargar_demo.py`.

```
Colegio:              Colegio Demo
Usuario:              admin@chronos.com / admin123
Hora cátedra:         40 min
Turno:                Doble escolaridad
Planes:               3
Áreas:                10
Materias:             22
Profesores:           20
Aulas:                10
Secciones:            5
Versión publicada:    Demo Doble escolaridad
Bloques:              175
```

### E.E.B.

- Plan de **47 horas semanales**.
- Esqueleto: 9 bloques lunes, miércoles y viernes; 10 bloques martes y jueves.
- Último bloque de martes y jueves: 15:00–15:40.
- Materias: Matemática, Lengua, Ciencias Naturales, Ciencias Sociales, Inglés, Educación Física, Informática, Orientación, Expresión Artística, Formación Ética, Historia y Geografía, Guaraní.

### Nivel Medio

- Plan de **27 horas**.
- Esqueleto de 12 bloques diarios (60 semanales).
- BATIN: 1° A y 1° B.
- BATAN: 1° A.

### Resultado

- 175 bloques generados.
- 0 choques de profesor, aula o sección.
- 0 problemas de disponibilidad.
- Horas del plan exactas.

## Flujo de uso

1. **Estructura**: años, ciclos, grados, turnos, aulas, materias.
2. **Áreas y planes**: crear áreas, crear planes y asignar grados.
3. **Plan del grado**: materias, horas, tipo de plan y áreas.
4. **Profesores**: materias habilitadas, carga máxima y disponibilidad.
5. **Plantillas**: esqueleto de cada ciclo, con días y bloques distintos.
6. **Secciones**: año, grado, turno, plantilla y aula base.
7. **Plan de sección**: profesor por materia, aula requerida y ajustes.
8. **Reglas**: restricciones pedagógicas.
9. **Horarios**: generar, revisar, fijar celdas, publicar.
10. **Reportes**: horario general, docentes y distribución de materias.

## Rutas principales

| Pantalla | Ruta |
|---|---|
| Dashboard | `/dashboard` |
| Áreas | `/areas` |
| Planes | `/planes` |
| Grados | `/grados` |
| Plan del grado | `/grados/<id>/plan` |
| Profesores | `/profesores` |
| Disponibilidad | `/disponibilidad` |
| Plantillas | `/plantillas` |
| Secciones | `/secciones` |
| Horarios | `/horarios` |
| Horarios docentes | `/horarios/docentes` |
| Distribución | `/reportes/distribucion` |
| Configuración | `/configuracion` |
| Guía | `/guia` |
| Presentación | `/presentacion` |

## Seguridad

- CSRF en todos los POST (`_csrf_token`).
- Cookies `HttpOnly`, `SameSite=Lax`, `Secure` en producción.
- Login limitado al colegio de la instancia.
- `/colegios` solo para superadmin.
- Contraseñas con bcrypt.
- Sin recuperación de contraseña por email.

## Pendientes / decisiones abiertas

1. Cargar el **plan real definitivo** del cliente. La demo usa un plan de 47 h construido para probar la capacidad.
2. Confirmar si el plan real de E.E.B. tiene 45 o 47 horas y qué materias incluye.
3. Roles de solo lectura para docentes.
4. UAT con el colegio.
5. Deploy con gunicorn/systemd/HTTPS y backups probados.
6. Carga docente entre turnos/versiones: hoy el motor genera por versión y no controla la suma global de un docente en dos turnos.

## Glosario

- **Ciclo**: nivel educativo; agrupa grados.
- **Plan**: organización curricular de uno o más grados.
- **Grado**: 7°, 1° BATIN, etc.
- **Sección**: curso concreto, por ejemplo 7° A.
- **Área**: agrupación de materias.
- **Tipo de plan**: común, específico u optativo.
- **Plantilla**: esqueleto de bloques de un ciclo.
- **Bloque**: clase o receso con hora de inicio y fin.
- **Hora cátedra**: duración nominal configurable; no reemplaza la hora real del bloque.
