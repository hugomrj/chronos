-- =====================================================================
-- Sistema de horarios escolares - Esquema PostgreSQL
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ---------------------------------------------------------------------
-- BASE: colegio (hoy 1 solo registro; deja listo el multi-colegio)
-- ---------------------------------------------------------------------
CREATE TABLE colegio (
  id      serial PRIMARY KEY,
  nombre  text NOT NULL
);

CREATE TABLE anio_lectivo (
  id           serial PRIMARY KEY,
  colegio_id   int  NOT NULL REFERENCES colegio(id),
  nombre       text NOT NULL,              -- '2026'
  fecha_inicio date NOT NULL,
  fecha_fin    date NOT NULL,
  activo       boolean NOT NULL DEFAULT false,
  CHECK (fecha_fin > fecha_inicio),
  UNIQUE (colegio_id, nombre)
);
-- un solo año activo por colegio
CREATE UNIQUE INDEX ux_anio_activo ON anio_lectivo (colegio_id) WHERE activo;

-- ---------------------------------------------------------------------
-- ESTRUCTURA ACADEMICA
-- ---------------------------------------------------------------------
CREATE TABLE nivel (
  id         serial PRIMARY KEY,
  colegio_id int  NOT NULL REFERENCES colegio(id),
  nombre     text NOT NULL,                -- Inicial, Primaria, Secundaria
  UNIQUE (colegio_id, nombre)
);

CREATE TABLE turno (
  id         serial PRIMARY KEY,
  colegio_id int  NOT NULL REFERENCES colegio(id),
  nombre     text NOT NULL,                -- Mañana, Tarde
  UNIQUE (colegio_id, nombre)
);

CREATE TABLE grado (
  id       serial PRIMARY KEY,
  nivel_id int  NOT NULL REFERENCES nivel(id),
  nombre   text NOT NULL,                  -- '7mo grado'
  orden    int  NOT NULL DEFAULT 0,
  UNIQUE (nivel_id, nombre)
);

CREATE TABLE aula (
  id         serial PRIMARY KEY,
  colegio_id int  NOT NULL REFERENCES colegio(id),
  nombre     text NOT NULL,
  tipo       text NOT NULL DEFAULT 'regular'
             CHECK (tipo IN ('regular','laboratorio','informatica','gimnasio','otro')),
  capacidad  int,
  activa     boolean NOT NULL DEFAULT true,
  UNIQUE (colegio_id, nombre)
);

CREATE TABLE materia (
  id                  serial PRIMARY KEY,
  colegio_id          int  NOT NULL REFERENCES colegio(id),
  nombre              text NOT NULL,
  tipo_aula_requerida text CHECK (tipo_aula_requerida IN
                        ('regular','laboratorio','informatica','gimnasio','otro')),
  UNIQUE (colegio_id, nombre)
);

-- ---------------------------------------------------------------------
-- TIEMPO: plantillas de horario y bloques
-- ---------------------------------------------------------------------
CREATE TABLE plantilla_horario (
  id         serial PRIMARY KEY,
  colegio_id int  NOT NULL REFERENCES colegio(id),
  turno_id   int  NOT NULL REFERENCES turno(id),
  nombre     text NOT NULL,
  UNIQUE (colegio_id, nombre)
);

CREATE TABLE bloque (
  id          serial PRIMARY KEY,
  plantilla_id int NOT NULL REFERENCES plantilla_horario(id) ON DELETE CASCADE,
  dia_semana  smallint NOT NULL CHECK (dia_semana BETWEEN 1 AND 7), -- 1=lunes
  numero      smallint NOT NULL,           -- orden dentro del dia
  hora_inicio time NOT NULL,
  hora_fin    time NOT NULL,
  tipo        text NOT NULL DEFAULT 'clase' CHECK (tipo IN ('clase','receso')),
  CHECK (hora_fin > hora_inicio),
  UNIQUE (plantilla_id, dia_semana, numero)
);

-- ---------------------------------------------------------------------
-- SECCIONES Y PLAN DE ESTUDIO
-- ---------------------------------------------------------------------
CREATE TABLE seccion (
  id               serial PRIMARY KEY,
  anio_lectivo_id  int  NOT NULL REFERENCES anio_lectivo(id),
  grado_id         int  NOT NULL REFERENCES grado(id),
  turno_id         int  NOT NULL REFERENCES turno(id),
  nombre           text NOT NULL,          -- 'A', 'B' (puede ser vacio si no hay secciones)
  aula_base_id     int  REFERENCES aula(id),
  plantilla_id     int  NOT NULL REFERENCES plantilla_horario(id),
  UNIQUE (anio_lectivo_id, grado_id, turno_id, nombre)
);

-- Plan base por grado
CREATE TABLE grado_materia (
  grado_id             int NOT NULL REFERENCES grado(id),
  materia_id           int NOT NULL REFERENCES materia(id),
  horas_semanales      int NOT NULL CHECK (horas_semanales > 0),
  max_bloques_por_dia  int NOT NULL DEFAULT 1 CHECK (max_bloques_por_dia > 0),
  requiere_bloque_doble boolean NOT NULL DEFAULT false,
  PRIMARY KEY (grado_id, materia_id)
);

-- Plan efectivo por seccion (se copia de grado_materia y se puede ajustar)
CREATE TABLE seccion_materia (
  id                    serial PRIMARY KEY,
  seccion_id            int NOT NULL REFERENCES seccion(id) ON DELETE CASCADE,
  materia_id            int NOT NULL REFERENCES materia(id),
  horas_semanales       int NOT NULL CHECK (horas_semanales > 0),
  max_bloques_por_dia   int NOT NULL DEFAULT 1 CHECK (max_bloques_por_dia > 0),
  requiere_bloque_doble boolean NOT NULL DEFAULT false,
  profesor_id           int,               -- NULL = el sistema decide (FK abajo)
  profesor_fijado       boolean NOT NULL DEFAULT false,
  aula_requerida_id     int REFERENCES aula(id),
  UNIQUE (seccion_id, materia_id),
  CHECK (NOT profesor_fijado OR profesor_id IS NOT NULL)
);

-- ---------------------------------------------------------------------
-- PROFESORES
-- ---------------------------------------------------------------------
CREATE TABLE profesor (
  id                 serial PRIMARY KEY,
  colegio_id         int  NOT NULL REFERENCES colegio(id),
  nombre             text NOT NULL,
  documento          text,
  contacto           text,
  horas_min_semana   int,
  horas_max_semana   int,
  horas_max_dia      int,
  activo             boolean NOT NULL DEFAULT true,
  UNIQUE (colegio_id, documento)
);

ALTER TABLE seccion_materia
  ADD CONSTRAINT fk_sm_profesor FOREIGN KEY (profesor_id) REFERENCES profesor(id);

CREATE TABLE profesor_materia (
  profesor_id int NOT NULL REFERENCES profesor(id) ON DELETE CASCADE,
  materia_id  int NOT NULL REFERENCES materia(id),
  PRIMARY KEY (profesor_id, materia_id)
);

-- Disponibilidad y restricciones fijas (otro colegio, etc.)
-- Interpretacion para el generador:
--   * si el profesor tiene filas 'disponible' -> solo puede en esas franjas
--   * si NO tiene filas 'disponible' -> puede siempre
--   * las filas 'no_disponible' siempre se descuentan
CREATE TABLE profesor_disponibilidad (
  id          serial PRIMARY KEY,
  profesor_id int NOT NULL REFERENCES profesor(id) ON DELETE CASCADE,
  dia_semana  smallint NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
  hora_desde  time NOT NULL,
  hora_hasta  time NOT NULL,
  tipo        text NOT NULL CHECK (tipo IN ('disponible','no_disponible')),
  motivo      text,                        -- 'Trabaja en otro colegio'
  CHECK (hora_hasta > hora_desde)
);

-- ---------------------------------------------------------------------
-- REGLAS (obligatorias y deseables, configurables)
-- ---------------------------------------------------------------------
-- Ejemplo: educacion fisica antes del receso
--   codigo='ANTES_DE_RECESO', materia_id=<ed. fisica>, obligatoria=false, peso=50
-- Otros codigos posibles: EVITAR_HUECOS_PROFESOR, NO_ULTIMA_HORA,
--   DISTRIBUIR_SEMANA, MAX_HORAS_DIA_PROFESOR
CREATE TABLE regla (
  id           serial PRIMARY KEY,
  colegio_id   int  NOT NULL REFERENCES colegio(id),
  codigo       text NOT NULL,
  descripcion  text,
  obligatoria  boolean NOT NULL DEFAULT false,
  peso         int NOT NULL DEFAULT 10,    -- importancia si es deseable
  activa       boolean NOT NULL DEFAULT true,
  materia_id   int REFERENCES materia(id), -- alcance opcional
  nivel_id     int REFERENCES nivel(id),
  profesor_id  int REFERENCES profesor(id),
  parametros   jsonb NOT NULL DEFAULT '{}'
);

-- ---------------------------------------------------------------------
-- RESULTADO: versiones del horario y sus celdas
-- ---------------------------------------------------------------------
CREATE TABLE horario_version (
  id               serial PRIMARY KEY,
  anio_lectivo_id  int  NOT NULL REFERENCES anio_lectivo(id),
  turno_id         int  NOT NULL REFERENCES turno(id),
  nombre           text,
  estado           text NOT NULL DEFAULT 'borrador'
                   CHECK (estado IN ('borrador','publicado','archivado')),
  notas            text,
  creado_en        timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_version_publicada
  ON horario_version (anio_lectivo_id, turno_id) WHERE estado = 'publicado';

CREATE TABLE horario_celda (
  id                 serial PRIMARY KEY,
  version_id         int NOT NULL REFERENCES horario_version(id) ON DELETE CASCADE,
  seccion_materia_id int NOT NULL REFERENCES seccion_materia(id),
  bloque_id          int NOT NULL REFERENCES bloque(id),
  aula_id            int REFERENCES aula(id),
  profesor_id        int REFERENCES profesor(id),
  fijado             boolean NOT NULL DEFAULT false,   -- el generador no lo toca
  origen             text NOT NULL DEFAULT 'auto' CHECK (origen IN ('manual','auto')),

  -- Copiados desde bloque/seccion_materia por trigger, para validar choques
  -- entre turnos y plantillas distintas por dia + rango horario real
  seccion_id   int      NOT NULL,
  dia_semana   smallint NOT NULL,
  inicio_min   int      NOT NULL,
  fin_min      int      NOT NULL,
  franja       int4range GENERATED ALWAYS AS (int4range(inicio_min, fin_min)) STORED,

  -- Nadie puede estar en dos lugares a la vez (NULL no genera conflicto)
  CONSTRAINT no_choque_profesor EXCLUDE USING gist
    (version_id WITH =, profesor_id WITH =, dia_semana WITH =, franja WITH &&),
  CONSTRAINT no_choque_aula EXCLUDE USING gist
    (version_id WITH =, aula_id WITH =, dia_semana WITH =, franja WITH &&),
  CONSTRAINT no_choque_seccion EXCLUDE USING gist
    (version_id WITH =, seccion_id WITH =, dia_semana WITH =, franja WITH &&)
);

CREATE INDEX ix_celda_version   ON horario_celda (version_id);
CREATE INDEX ix_celda_profesor  ON horario_celda (version_id, profesor_id);
CREATE INDEX ix_celda_seccion_m ON horario_celda (seccion_materia_id);

CREATE OR REPLACE FUNCTION fn_celda_completar() RETURNS trigger AS $$
DECLARE b bloque%ROWTYPE;
BEGIN
  SELECT * INTO b FROM bloque WHERE id = NEW.bloque_id;
  SELECT sm.seccion_id INTO NEW.seccion_id
    FROM seccion_materia sm WHERE sm.id = NEW.seccion_materia_id;
  NEW.dia_semana := b.dia_semana;
  NEW.inicio_min := EXTRACT(HOUR FROM b.hora_inicio)::int * 60
                  + EXTRACT(MINUTE FROM b.hora_inicio)::int;
  NEW.fin_min    := EXTRACT(HOUR FROM b.hora_fin)::int * 60
                  + EXTRACT(MINUTE FROM b.hora_fin)::int;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_celda_completar
  BEFORE INSERT OR UPDATE OF bloque_id, seccion_materia_id ON horario_celda
  FOR EACH ROW EXECUTE FUNCTION fn_celda_completar();

-- ---------------------------------------------------------------------
-- ACCESO (hoy solo admin)
-- ---------------------------------------------------------------------
CREATE TABLE rol (
  id     serial PRIMARY KEY,
  nombre text NOT NULL UNIQUE
);
INSERT INTO rol (nombre) VALUES ('admin');

CREATE TABLE usuario (
  id            serial PRIMARY KEY,
  colegio_id    int  NOT NULL REFERENCES colegio(id),
  email         text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  rol_id        int  NOT NULL REFERENCES rol(id),
  profesor_id   int  REFERENCES profesor(id),  -- futuro: profesor ve su horario
  activo        boolean NOT NULL DEFAULT true
);