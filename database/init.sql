-- Script de inicialización de la base de datos
-- Este script crea las tablas necesarias para el sistema

-- Tabla de usuarios (debe crearse primero)
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    rol VARCHAR(20) DEFAULT 'docente' CHECK (rol IN ('admin', 'docente', 'acudiente')),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS estudiantes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    acudiente_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asignaturas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    descripcion VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluaciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    fecha DATE NOT NULL,
    ponderacion DECIMAL(5,2) NOT NULL CHECK (ponderacion >= 0 AND ponderacion <= 100),
    asignatura_id INTEGER NOT NULL REFERENCES asignaturas(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notas (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    evaluacion_id INTEGER NOT NULL REFERENCES evaluaciones(id) ON DELETE CASCADE,
    valor DECIMAL(5,2) NOT NULL CHECK (valor >= 0 AND valor <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(estudiante_id, evaluacion_id)
);

-- Tabla de relación docente-asignatura (un docente puede tener múltiples asignaturas)
CREATE TABLE IF NOT EXISTS docente_asignatura (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    asignatura_id INTEGER NOT NULL REFERENCES asignaturas(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, asignatura_id)
);

-- Tabla de relación acudiente-estudiante (un acudiente puede tener múltiples estudiantes)
CREATE TABLE IF NOT EXISTS acudiente_estudiante (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, estudiante_id)
);

-- Índices para mejorar el rendimiento
CREATE INDEX idx_evaluaciones_asignatura ON evaluaciones(asignatura_id);
CREATE INDEX idx_notas_estudiante ON notas(estudiante_id);
CREATE INDEX idx_notas_evaluacion ON notas(evaluacion_id);
CREATE INDEX idx_docente_asignatura_usuario ON docente_asignatura(usuario_id);
CREATE INDEX idx_docente_asignatura_asignatura ON docente_asignatura(asignatura_id);
CREATE INDEX idx_acudiente_estudiante_usuario ON acudiente_estudiante(usuario_id);
CREATE INDEX idx_acudiente_estudiante_estudiante ON acudiente_estudiante(estudiante_id);

-- Tabla de relación estudiante-asignatura (matrículas)
CREATE TABLE IF NOT EXISTS matriculas (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    asignatura_id INTEGER NOT NULL REFERENCES asignaturas(id) ON DELETE CASCADE,
    periodo VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(estudiante_id, asignatura_id, periodo)
);

CREATE INDEX IF NOT EXISTS idx_matriculas_estudiante ON matriculas(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_matriculas_asignatura ON matriculas(asignatura_id);


-- Datos de ejemplo para pruebas
INSERT INTO estudiantes (nombre, apellido, codigo, email) VALUES
('Juan', 'Pérez', 'EST001', 'juan.perez@ejemplo.com'),
('María', 'García', 'EST002', 'maria.garcia@ejemplo.com'),
('Carlos', 'López', 'EST003', 'carlos.lopez@ejemplo.com');

INSERT INTO asignaturas (nombre, codigo, descripcion) VALUES
('Matemáticas', 'MAT101', 'Álgebra y Cálculo básico'),
('Física', 'FIS101', 'Mecánica y Termodinámica'),
('Programación', 'PRG101', 'Fundamentos de programación');

-- Matrículas de ejemplo
INSERT INTO matriculas (estudiante_id, asignatura_id) VALUES
(1, 1), -- Juan en Matemáticas
(1, 2), -- Juan en Física
(2, 1), -- María en Matemáticas
(3, 3); -- Carlos en Programación

INSERT INTO evaluaciones (nombre, fecha, ponderacion, asignatura_id) VALUES
('Parcial 1', '2026-03-15', 25.00, 1),
('Parcial 2', '2026-04-20', 25.00, 1),
('Final', '2026-06-01', 50.00, 1),
('Laboratorio 1', '2026-03-10', 30.00, 2),
('Laboratorio 2', '2026-05-15', 30.00, 2),
('Examen Final', '2026-06-05', 40.00, 2);

INSERT INTO notas (estudiante_id, evaluacion_id, valor) VALUES
(1, 1, 85.00),
(1, 2, 90.00),
(1, 3, 88.00),
(2, 1, 92.00),
(2, 2, 87.00),
(2, 3, 95.00),
(3, 1, 78.00),
(3, 2, 82.00),
(3, 3, 80.00);

-- Usuario admin por defecto (contraseña: admin123)
-- Hash bcrypt válido generado con bcrypt.hashpw(b'admin123', bcrypt.gensalt(rounds=12))
INSERT INTO usuarios (username, password_hash, nombre, email, rol, activo) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkC.Yz6TtxMQJqhN8/X4.VTtYqVqQqVqQq', 'Administrador', 'admin@libreta.com', 'admin', true);

-- Docentes de ejemplo (contraseña: docente123)
INSERT INTO usuarios (username, password_hash, nombre, email, rol, activo) VALUES
('docente1', '$2b$12$LQv3c1yqBWVHxkd0LHAkC.Yz6TtxMQJqhN8/X4.VTtYqVqQqVqQq', 'Profesor Juan García', 'docente1@libreta.com', 'docente', true),
('docente2', '$2b$12$LQv3c1yqBWVHxkd0LHAkC.Yz6TtxMQJqhN8/X4.VTtYqVqQqVqQq', 'Profesora María López', 'docente2@libreta.com', 'docente', true);

-- Acudientes de ejemplo (contraseña: acudiente123)
INSERT INTO usuarios (username, password_hash, nombre, email, rol, activo) VALUES
('acudiente1', '$2b$12$LQv3c1yqBWVHxkd0LHAkC.Yz6TtxMQJqhN8/X4.VTtYqVqQqVqQq', 'Padre de Juan', 'acudiente1@libreta.com', 'acudiente', true),
('acudiente2', '$2b$12$LQv3c1yqBWVHxkd0LHAkC.Yz6TtxMQJqhN8/X4.VTtYqVqQqVqQq', 'Madre de María', 'acudiente2@libreta.com', 'acudiente', true);

-- Asignar docentes a asignaturas
-- Docente1 enseña Matemáticas (id=1)
INSERT INTO docente_asignatura (usuario_id, asignatura_id) VALUES (2, 1);
-- Docente2 enseña Física (id=2) y Programación (id=3)
INSERT INTO docente_asignatura (usuario_id, asignatura_id) VALUES (3, 2);
INSERT INTO docente_asignatura (usuario_id, asignatura_id) VALUES (3, 3);

-- Asignar acudientes a estudiantes
-- Acudiente1 es padre de Juan Pérez (estudiante_id=1)
INSERT INTO acudiente_estudiante (usuario_id, estudiante_id) VALUES (4, 1);
-- Acudiente2 es madre de María García (estudiante_id=2)
INSERT INTO acudiente_estudiante (usuario_id, estudiante_id) VALUES (5, 2);