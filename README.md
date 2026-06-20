# Libreta Digital - Sistema de Control de Notas

## Descripción del Proyecto

Sistema web sencillo para la gestión de notas de estudiantes, implementado con arquitectura de microservicios. Permite a los docentes registrar estudiantes, asignaturas, evaluaciones y notas, calculando automáticamente los promedios ponderados.

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Nginx)                         │
│                   http://localhost:8080                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API GATEWAY (FastAPI)                      │
│                    http://localhost:5000                         │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Estudiantes  │    │  Asignaturas  │    │  Evaluaciones │
│   Service     │    │   Service     │    │   Service     │
│  Port: 5001   │    │  Port: 5002   │    │  Port: 5003   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Notas Service        │
                    │   Port: 5004           │
                    │   (Cálculo Promedios)  │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   PostgreSQL DB       │
                    │   Port: 5432          │
                    └───────────────────────┘
```

## Microservicios

### 1. Estudiantes Service (Puerto 5001)
- CRUD completo de estudiantes
- Campos: nombre, apellido, código, email
- Endpoints:
  - `GET /estudiantes` - Lista todos los estudiantes
  - `GET /estudiantes/{id}` - Obtiene un estudiante
  - `POST /estudiantes` - Crea un estudiante
  - `PUT /estudiantes/{id}` - Actualiza un estudiante
  - `DELETE /estudiantes/{id}` - Elimina un estudiante

### 2. Asignaturas Service (Puerto 5002)
- CRUD completo de asignaturas
- Campos: nombre, código, descripción
- Endpoints:
  - `GET /asignaturas` - Lista todas las asignaturas
  - `GET /asignaturas/{id}` - Obtiene una asignatura
  - `POST /asignaturas` - Crea una asignatura
  - `PUT /asignaturas/{id}` - Actualiza una asignatura
  - `DELETE /asignaturas/{id}` - Elimina una asignatura

### 3. Evaluaciones Service (Puerto 5003)
- CRUD completo de evaluaciones
- Campos: nombre, fecha, ponderación, asignatura_id
- Validación: ponderación entre 0 y 100
- Endpoints:
  - `GET /evaluaciones` - Lista todas las evaluaciones
  - `GET /evaluaciones/{id}` - Obtiene una evaluación
  - `GET /evaluaciones/asignatura/{id}` - Lista por asignatura
  - `POST /evaluaciones` - Crea una evaluación
  - `PUT /evaluaciones/{id}` - Actualiza una evaluación
  - `DELETE /evaluaciones/{id}` - Elimina una evaluación

### 4. Notas Service (Puerto 5004)
- CRUD completo de notas
- Cálculo automático de promedios ponderados
- Generación de reportes
- Campos: estudiante_id, evaluacion_id, valor
- Validación: nota entre 0 y 100
- Endpoints:
  - `GET /notas` - Lista todas las notas
  - `GET /notas/{id}` - Obtiene una nota
  - `GET /notas/estudiante/{id}` - Lista por estudiante
  - `POST /notas` - Crea una nota
  - `PUT /notas/{id}` - Actualiza una nota
  - `DELETE /notas/{id}` - Elimina una nota
  - `GET /notas/promedio/estudiante/{id}/asignatura/{id}` - Calcula promedio
  - `GET /notas/reporte/asignatura/{id}` - Genera reporte

### 5. API Gateway (Puerto 5000)
- Punto de entrada único para todos los microservicios
- Redirige todas las peticiones a los servicios correspondientes
- Health check de todos los servicios
- Documentación Swagger: http://localhost:8000/docs
### 6. Auth Service (Puerto 5005)
- Autenticación con JWT
- Gestión de usuarios
- Endpoints:
  - `POST /auth/login` - Iniciar sesión
  - `POST /auth/register` - Registrar nuevo usuario
  - `GET /auth/me` - Obtener información del usuario actual
  - `GET /auth/verify` - Verificar token

## Autenticación

El sistema utiliza autenticación con JWT (JSON Web Tokens). 

### Usuario por defecto
- **Usuario**: admin
- **Contraseña**: admin123

### Flujo de autenticación
1. El usuario inicia sesión con usuario y contraseña
2. El sistema genera un token JWT
3. El token se almacena en localStorage
4. Todas las peticiones a la API incluyen el token en el header `Authorization: Bearer <token>`
5. El token expira en 60 minutos
## Base de Datos

### Tablas

#### estudiantes
- id (PK)
- nombre
- apellido
- codigo (UNIQUE)
- email (UNIQUE)

#### asignaturas
- id (PK)
- nombre
- codigo (UNIQUE)
- descripcion

#### evaluaciones
- id (PK)
- nombre
- fecha
- ponderacion (0-100)
- asignatura_id (FK)

#### notas
- id (PK)
- estudiante_id (FK)
- evaluacion_id (FK)
- valor (0-100)
- UNIQUE(estudiante_id, evaluacion_id)

## Requisitos

- Docker
- Docker Compose
- Navegador web moderno

## Instrucciones de Ejecución

### 1. Clonar o descargar el proyecto

### 2. Construir y ejecutar los contenedores

```bash
# Construir y ejecutar todos los servicios
docker-compose up -d --build

# Verificar que todos los servicios estén corriendo
docker-compose ps

# Ver logs de los servicios
docker-compose logs -f
```

### 3. Acceder al sistema

- **Frontend**: http://localhost:8080
- **API Gateway**: http://localhost:5000
- **Documentación API**: http://localhost:5000/docs

### 4. Iniciar sesión

- **Usuario**: admin
- **Contraseña**: admin123

### 4. Detener los servicios

```bash
docker-compose down

# Para eliminar también los volúmenes
docker-compose down -v
```

## Cálculo de Promedios

El sistema calcula promedios ponderados de la siguiente manera:

```
Promedio = Σ(nota × ponderación/100) / Σ(ponderación) × 100
```

**Ejemplo:**
- Parcial 1: Nota 85, Ponderación 25%
- Parcial 2: Nota 90, Ponderación 25%
- Final: Nota 88, Ponderación 50%

Cálculo:
- Nota ponderada 1: 85 × 0.25 = 21.25
- Nota ponderada 2: 90 × 0.25 = 22.5
- Nota ponderada 3: 88 × 0.50 = 44
- Suma ponderada: 21.25 + 22.5 + 44 = 87.75
- Promedio: 87.75

## Datos de Prueba

El sistema incluye datos de prueba:
- 3 estudiantes
- 3 asignaturas
- 6 evaluaciones
- 9 notas

## Tecnologías Utilizadas

- **Backend**: Python 3.11 + FastAPI
- **Base de Datos**: PostgreSQL 15
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla)
- **Contenedores**: Docker + Docker Compose
- **Web Server**: Nginx (para frontend)
- **Autenticación**: JWT (JSON Web Tokens) + bcrypt
