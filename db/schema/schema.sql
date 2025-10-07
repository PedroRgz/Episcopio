-- Episcopio Database Schema
-- PostgreSQL with PostGIS extension

CREATE EXTENSION IF NOT EXISTS postgis;

-- Catálogo de entidades federativas
CREATE TABLE IF NOT EXISTS geo_entidad (
    cve_ent CHAR(2) PRIMARY KEY,
    nombre TEXT NOT NULL,
    geom GEOMETRY(MULTIPOLYGON, 4326),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Catálogo de municipios
CREATE TABLE IF NOT EXISTS geo_municipio (
    cve_mun CHAR(5) PRIMARY KEY,
    cve_ent CHAR(2) NOT NULL REFERENCES geo_entidad(cve_ent),
    nombre TEXT NOT NULL,
    geom GEOMETRY(MULTIPOLYGON, 4326),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Catálogo de morbilidades
CREATE TABLE IF NOT EXISTS morbilidad (
    id SERIAL PRIMARY KEY,
    codigo TEXT,
    nombre TEXT NOT NULL UNIQUE,
    tipo TEXT CHECK (tipo IN ('transmisible', 'no_transmisible')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Serie temporal oficial (datos epidemiológicos oficiales)
CREATE TABLE IF NOT EXISTS serie_oficial (
    id BIGSERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    semana_iso INT NOT NULL,
    cve_ent CHAR(2) REFERENCES geo_entidad(cve_ent),
    cve_mun CHAR(5) REFERENCES geo_municipio(cve_mun),
    morbilidad_id INT REFERENCES morbilidad(id),
    casos INT DEFAULT 0 CHECK (casos >= 0),
    defunciones INT DEFAULT 0 CHECK (defunciones >= 0),
    fuente TEXT NOT NULL,
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (fecha, cve_ent, cve_mun, morbilidad_id, fuente)
);

-- Índices para serie_oficial
CREATE INDEX IF NOT EXISTS idx_serie_oficial_fecha ON serie_oficial(fecha);
CREATE INDEX IF NOT EXISTS idx_serie_oficial_entidad ON serie_oficial(cve_ent);
CREATE INDEX IF NOT EXISTS idx_serie_oficial_morbilidad ON serie_oficial(morbilidad_id);
CREATE INDEX IF NOT EXISTS idx_serie_oficial_semana ON serie_oficial(semana_iso);

-- Menciones en redes sociales
CREATE TABLE IF NOT EXISTS social_menciones (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    plataforma TEXT NOT NULL,
    texto_hash CHAR(64) NOT NULL,
    cve_ent CHAR(2) REFERENCES geo_entidad(cve_ent),
    cve_mun CHAR(5) REFERENCES geo_municipio(cve_mun),
    relevancia BOOLEAN,
    sentimiento NUMERIC(4,3) CHECK (sentimiento >= -1 AND sentimiento <= 1),
    conteo INT DEFAULT 1,
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (plataforma, texto_hash)
);

-- Índices para social_menciones
CREATE INDEX IF NOT EXISTS idx_social_menciones_ts ON social_menciones(ts);
CREATE INDEX IF NOT EXISTS idx_social_menciones_plataforma ON social_menciones(plataforma);
CREATE INDEX IF NOT EXISTS idx_social_menciones_entidad ON social_menciones(cve_ent);

-- Sondeo clínico (anónimo)
CREATE TABLE IF NOT EXISTS sondeo_clinico (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMP WITH TIME ZONE DEFAULT now(),
    cve_ent CHAR(2) REFERENCES geo_entidad(cve_ent),
    cve_mun CHAR(5) REFERENCES geo_municipio(cve_mun),
    sintomas_observacion TEXT,
    nivel_actividad TEXT CHECK (nivel_actividad IN ('bajo', 'moderado', 'alto')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para sondeo_clinico
CREATE INDEX IF NOT EXISTS idx_sondeo_ts ON sondeo_clinico(ts);
CREATE INDEX IF NOT EXISTS idx_sondeo_entidad ON sondeo_clinico(cve_ent);

-- Alertas
CREATE TABLE IF NOT EXISTS alerta (
    id BIGSERIAL PRIMARY KEY,
    tipo TEXT NOT NULL,
    regla TEXT NOT NULL,
    parametros JSONB NOT NULL,
    evidencia JSONB,
    estado TEXT CHECK (estado IN ('activa', 'resuelta')) DEFAULT 'activa',
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- Índices para alertas
CREATE INDEX IF NOT EXISTS idx_alerta_estado ON alerta(estado);
CREATE INDEX IF NOT EXISTS idx_alerta_created ON alerta(created_at);

-- Boletines
CREATE TABLE IF NOT EXISTS boletin (
    id BIGSERIAL PRIMARY KEY,
    periodo_inicio DATE NOT NULL,
    periodo_fin DATE NOT NULL,
    resumen_html TEXT,
    resumen_md TEXT,
    estado TEXT CHECK (estado IN ('borrador', 'publicado')) DEFAULT 'borrador',
    created_at TIMESTAMPTZ DEFAULT now(),
    published_at TIMESTAMPTZ
);

-- QA de datos
CREATE TABLE IF NOT EXISTS qa_evento (
    id BIGSERIAL PRIMARY KEY,
    check_name TEXT NOT NULL,
    check_type TEXT NOT NULL,
    resultado TEXT NOT NULL,
    severidad TEXT CHECK (severidad IN ('info', 'warning', 'error', 'critical')),
    detalles JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para qa_evento
CREATE INDEX IF NOT EXISTS idx_qa_evento_created ON qa_evento(created_at);
CREATE INDEX IF NOT EXISTS idx_qa_evento_severidad ON qa_evento(severidad);

-- Log de ingesta
CREATE TABLE IF NOT EXISTS ingesta_log (
    id BIGSERIAL PRIMARY KEY,
    fuente TEXT NOT NULL,
    fecha_inicio TIMESTAMPTZ NOT NULL,
    fecha_fin TIMESTAMPTZ,
    filas_procesadas INT DEFAULT 0,
    filas_insertadas INT DEFAULT 0,
    filas_error INT DEFAULT 0,
    duracion_segundos NUMERIC(10,2),
    estado TEXT CHECK (estado IN ('iniciado', 'completado', 'fallido')) DEFAULT 'iniciado',
    error_mensaje TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para ingesta_log
CREATE INDEX IF NOT EXISTS idx_ingesta_log_fuente ON ingesta_log(fuente);
CREATE INDEX IF NOT EXISTS idx_ingesta_log_created ON ingesta_log(created_at);
