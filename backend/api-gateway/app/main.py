from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx

# ==================== SCHEMAS PARA DOCUMENTACIÓN ====================

class EstudianteCreate(BaseModel):
    nombre: str
    apellido: str
    codigo: str
    email: str

class EstudianteResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    codigo: str
    email: str

class AsignaturaCreate(BaseModel):
    nombre: str
    codigo: str
    descripcion: Optional[str] = None

class AsignaturaResponse(BaseModel):
    id: int
    nombre: str
    codigo: str
    descripcion: Optional[str]

class EvaluacionCreate(BaseModel):
    nombre: str
    fecha: str
    ponderacion: float
    asignatura_id: int

class EvaluacionResponse(BaseModel):
    id: int
    nombre: str
    fecha: str
    ponderacion: float
    asignatura_id: int

class NotaCreate(BaseModel):
    estudiante_id: int
    evaluacion_id: int
    valor: float

class NotaResponse(BaseModel):
    id: int
    estudiante_id: int
    evaluacion_id: int
    valor: float
    evaluacion_nombre: Optional[str] = None
    ponderacion: Optional[float] = None
    asignatura_id: Optional[int] = None
    asignatura_nombre: Optional[str] = None

class UsuarioCreate(BaseModel):
    username: str
    password: str
    nombre: str
    email: Optional[str] = None
    rol: Optional[str] = 'docente'  # admin, docente, acudiente

class UsuarioLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class AsignarAsignaturas(BaseModel):
    usuario_id: int
    asignatura_ids: List[int]

class AsignarEstudiantes(BaseModel):
    usuario_id: int
    estudiante_ids: List[int]

class PromedioResponse(BaseModel):
    estudiante_id: int
    promedio_general: Optional[float] = None
    asignaturas: Optional[List[dict]] = None
    mensaje: Optional[str] = None

class ReporteResponse(BaseModel):
    asignatura_id: int
    total_estudiantes: int
    promedio_general: float
    evaluaciones: List[dict]

app = FastAPI(
    title="Libreta Digital - API Gateway",
    description="""
## Sistema de Control de Notas

API Gateway centralizado para la gestión de notas de estudiantes.

### Autenticación

La mayoría de los endpoints requieren autenticación JWT. Para obtener un token:

1. Regístrate en `/auth/register` o usa las credenciales por defecto:
   - **Usuario**: `admin`
   - **Contraseña**: `admin123`

2. Inicia sesión en `/auth/login` para obtener el token JWT

3. Incluye el token en el header: `Authorization: Bearer <token>`

### Endpoints disponibles

- **Autenticación**: Login, registro, verificación
- **Estudiantes**: CRUD completo de estudiantes
- **Asignaturas**: CRUD completo de asignaturas
- **Evaluaciones**: CRUD completo de evaluaciones
- **Notas**: CRUD completo de notas
- **Promedios**: Cálculo de promedios ponderados
- **Reportes**: Generación de reportes por asignatura

### URLs

- **Frontend**: http://localhost:8080
- **API Gateway**: http://localhost:5000
- **Documentación**: http://localhost:5000/docs
- **Documentación alternativa**: http://localhost:5000/redoc
    """,
    version="1.0.0",
    contact={
        "name": "Libreta Digital",
        "email": "contacto@libretadigital.com",
    },
    license_info={
        "name": "MIT",
    },
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URLs de los microservicios
SERVICES = {
    "auth": "http://auth-service:8005",
    "estudiantes": "http://estudiantes-service:8001",
    "asignaturas": "http://asignaturas-service:8002",
    "evaluaciones": "http://evaluaciones-service:8003",
    "notas": "http://notas-service:8004"
}

# Cliente HTTP asíncrono
client = httpx.AsyncClient(timeout=30.0)
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verificar token JWT con el servicio de autenticación"""
    try:
        response = await client.get(
            f"{SERVICES['auth']}/auth/verify",
            headers={"Authorization": f"Bearer {credentials.credentials}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        return credentials.credentials
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Error conectando con el servicio de autenticación")

async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtener información del usuario actual desde el token"""
    try:
        response = await client.get(
            f"{SERVICES['auth']}/auth/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        return response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Error conectando con el servicio de autenticación")

async def require_admin(user=Depends(get_current_user_info)):
    """Verificar que el usuario es administrador"""
    if user.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Permisos insuficientes")
    return user

async def proxy_request(service: str, path: str, request: Request) -> JSONResponse:
    """Proxy genérico para redirigir peticiones a los microservicios"""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Servicio '{service}' no encontrado")
    
    url = f"{SERVICES[service]}{path}"
    
    # Obtener el cuerpo de la petición si existe
    body = await request.body()
    
    # Copiar headers relevantes
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ["host", "content-length"]:
            headers[key] = value
    
    try:
        response = await client.request(
            method=request.method,
            url=url,
            content=body if body else None,
            headers=headers,
            params=request.query_params
        )
        
        return JSONResponse(
            content=response.json() if response.content else {},
            status_code=response.status_code
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Error conectando con el servicio: {str(e)}")

# ==================== AUTENTICACIÓN (SIN PROTECCIÓN) ====================

@app.post(
    "/auth/login", 
    tags=["Autenticación"],
    response_model=Token,
    summary="Iniciar sesión",
    description="""
    Inicia sesión y obtiene un token JWT válido por 60 minutos.
    
    **Credenciales por defecto:**
    - Usuario: `admin`
    - Contraseña: `admin123`
    """,
    responses={
        200: {"description": "Token JWT generado exitosamente"},
        401: {"description": "Credenciales inválidas"}
    }
)
async def login(request: Request):
    """Iniciar sesión"""
    return await proxy_request("auth", "/auth/login", request)

@app.post(
    "/auth/register", 
    tags=["Autenticación"],
    response_model=EstudianteResponse,
    summary="Registrar nuevo usuario",
    description="Registra un nuevo usuario en el sistema.",
    responses={
        201: {"description": "Usuario registrado exitosamente"},
        400: {"description": "El usuario ya existe"}
    }
)
async def register(request: Request):
    """Registrar nuevo usuario"""
    return await proxy_request("auth", "/auth/register", request)

@app.get(
    "/auth/me", 
    tags=["Autenticación"],
    response_model=EstudianteResponse,
    summary="Obtener usuario actual",
    description="Obtiene la información del usuario autenticado actualmente.",
    responses={
        200: {"description": "Información del usuario"},
        401: {"description": "Token inválido o expirado"}
    }
)
async def get_current_user(request: Request):
    """Obtener información del usuario actual"""
    return await proxy_request("auth", "/auth/me", request)

# ==================== ESTUDIANTES (CON AUTENTICACIÓN) ====================

@app.get(
    "/estudiantes", 
    tags=["Estudiantes"],
    response_model=List[EstudianteResponse],
    summary="Listar todos los estudiantes",
    description="Obtiene una lista con todos los estudiantes registrados en el sistema.",
    responses={
        200: {"description": "Lista de estudiantes"},
        401: {"description": "No autenticado"}
    }
)
async def listar_estudiantes(request: Request, user=Depends(get_current_user_info)):
    """Lista todos los estudiantes (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("estudiantes", "/estudiantes", request)

@app.get(
    "/estudiantes/mis-estudiantes", 
    tags=["Estudiantes"],
    response_model=List[EstudianteResponse],
    summary="Listar estudiantes del docente",
    description="Obtiene la lista de estudiantes matriculados en las asignaturas del docente autenticado.",
    responses={
        200: {"description": "Lista de estudiantes del docente"},
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado"}
    }
)
async def estudiantes_docente(request: Request, user=Depends(get_current_user_info)):
    """Obtiene los estudiantes matriculados en las asignaturas del docente"""
    if user.get("rol") != "docente":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener las asignaturas del docente
    usuario_id = user.get("id")
    auth_header = request.headers.get("authorization")
    
    # Obtener asignaturas del docente
    asignaturas_response = await client.get(
        f"{SERVICES['auth']}/admin/docente-asignaturas/{usuario_id}",
        headers={"Authorization": auth_header} if auth_header else None
    )
    
    print(f"Respuesta asignaturas: {asignaturas_response.status_code} - {asignaturas_response.text}")
    
    if asignaturas_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error al obtener asignaturas del docente")
    
    asignaturas = asignaturas_response.json() or []
    
    # Obtener estudiantes de cada asignatura
    estudiantes_ids = set()
    estudiantes = []
    
    for asig in asignaturas:
        asignatura_id = asig.get("asignatura_id")
        if asignatura_id:
            # Obtener estudiantes matriculados en esta asignatura
            matriculas_response = await client.get(
                f"{SERVICES['auth']}/admin/matriculas?asignatura_id={asignatura_id}",
                headers={"Authorization": auth_header} if auth_header else None
            )
            
            if matriculas_response.status_code == 200:
                matriculas = matriculas_response.json() or []
                for mat in matriculas:
                    estudiante_id = mat.get("estudiante_id")
                    if estudiante_id and estudiante_id not in estudiantes_ids:
                        estudiantes_ids.add(estudiante_id)
                        # Obtener información del estudiante
                        estudiante_response = await client.get(
                            f"{SERVICES['estudiantes']}/estudiantes/{estudiante_id}",
                            headers={"Authorization": auth_header} if auth_header else None
                        )
                        if estudiante_response.status_code == 200:
                            estudiantes.append(estudiante_response.json())
    
    return estudiantes

@app.get(
    "/estudiantes/mis-hijos", 
    tags=["Estudiantes"],
    response_model=List[EstudianteResponse],
    summary="Listar estudiantes del acudiente",
    description="Obtiene la lista de estudiantes asignados al acudiente autenticado.",
    responses={
        200: {"description": "Lista de estudiantes del acudiente"},
        401: {"description": "No autenticado"}
    }
)
async def estudiantes_acudiente(request: Request, user=Depends(get_current_user_info)):
    """Obtiene los estudiantes asignados al acudiente"""
    usuario_id = user.get("id")
    return await proxy_request("estudiantes", f"/estudiantes/acudiente/{usuario_id}", request)

@app.get(
    "/estudiantes/{estudiante_id}", 
    tags=["Estudiantes"],
    response_model=EstudianteResponse,
    summary="Obtener estudiante por ID",
    description="Obtiene la información detallada de un estudiante específico.",
    responses={
        200: {"description": "Información del estudiante"},
        401: {"description": "No autenticado"},
        404: {"description": "Estudiante no encontrado"}
    }
)
async def obtener_estudiante(estudiante_id: int, request: Request, token: str = Depends(verify_token)):
    """Obtiene un estudiante por ID"""
    return await proxy_request("estudiantes", f"/estudiantes/{estudiante_id}", request)

@app.post(
    "/estudiantes", 
    tags=["Estudiantes"],
    response_model=EstudianteResponse,
    status_code=201,
    summary="Crear nuevo estudiante",
    description="""
    Registra un nuevo estudiante en el sistema.
    
    **Campos requeridos:**
    - `nombre`: Nombre del estudiante
    - `apellido`: Apellido del estudiante
    - `codigo`: Código único del estudiante
    - `email`: Correo electrónico único del estudiante
    
    **Nota:** Si el usuario es un docente, el estudiante será automáticamente matriculado en todas las asignaturas del docente.
    """,
    responses={
        201: {"description": "Estudiante creado exitosamente"},
        400: {"description": "Datos inválidos o código/email duplicado"},
        401: {"description": "No autenticado"}
    }
)
async def crear_estudiante(request: Request, user=Depends(get_current_user_info)):
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")

    # 1. LEER EL BODY UNA SOLA VEZ
    body = await request.json()
    acudiente_id = body.get("acudiente_id")

    # 2. PREPARAR BODY PARA estudiantes-service
    estudiante_data = body.copy()
    estudiante_data.pop("acudiente_id", None)

    auth_header = request.headers.get("authorization")

    # 3. CREAR ESTUDIANTE EN estudiantes-service
    estudiante_response = await client.post(
        f"{SERVICES['estudiantes']}/estudiantes",
        json=estudiante_data,
        headers={"Authorization": auth_header} if auth_header else None
    )

    estudiante = estudiante_response.json()
    estudiante_id = estudiante.get("id")

    # 4. ASIGNAR ACUDIENTE EN auth-service
    if acudiente_id:
        await client.post(
            f"{SERVICES['auth']}/admin/asignar-estudiantes",
            headers={"Authorization": auth_header} if auth_header else None,
            json={"usuario_id": acudiente_id, "estudiante_ids": [estudiante_id]}
        )

    # 5. SI ES DOCENTE, MATRICULAR AUTOMÁTICAMENTE
    if user.get("rol") == "docente":
        try:
            resp = await client.get(
                f"{SERVICES['auth']}/admin/docente-asignaturas/{user.get('id')}",
                headers={"Authorization": auth_header} if auth_header else None
            )

            if resp.status_code == 200:
                asignaciones = resp.json() or []

                for asig in asignaciones:
                    asignatura_id = asig.get("asignatura_id")
                    if asignatura_id:
                        await client.post(
                            f"{SERVICES['auth']}/admin/matriculas",
                            headers={"Authorization": auth_header} if auth_header else None,
                            json={"estudiante_id": estudiante_id, "asignatura_id": asignatura_id}
                        )
        except Exception as e:
            print(f"Error en matriculación automática: {e}")

    return estudiante

@app.put(
    "/estudiantes/{estudiante_id}", 
    tags=["Estudiantes"],
    response_model=EstudianteResponse,
    summary="Actualizar estudiante",
    description="Actualiza la información de un estudiante existente.",
    responses={
        200: {"description": "Estudiante actualizado exitosamente"},
        400: {"description": "Datos inválidos"},
        401: {"description": "No autenticado"},
        404: {"description": "Estudiante no encontrado"}
    }
)
async def actualizar_estudiante(estudiante_id: int, request: Request, user=Depends(get_current_user_info)):
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")

    # 1. LEER EL BODY UNA SOLA VEZ
    body = await request.json()
    acudiente_id = body.get("acudiente_id")

    # 2. PREPARAR BODY PARA estudiantes-service
    estudiante_data = body.copy()
    estudiante_data.pop("acudiente_id", None)

    auth_header = request.headers.get("authorization")

    # 3. ACTUALIZAR ESTUDIANTE EN estudiantes-service
    estudiante_response = await client.put(
        f"{SERVICES['estudiantes']}/estudiantes/{estudiante_id}",
        json=estudiante_data,
        headers={"Authorization": auth_header} if auth_header else None
    )

    estudiante = estudiante_response.json()

    # 4. ASIGNAR ACUDIENTE EN auth-service
    if acudiente_id:
        await client.post(
            f"{SERVICES['auth']}/admin/asignar-estudiantes",
            headers={"Authorization": auth_header} if auth_header else None,
            json={"usuario_id": acudiente_id, "estudiante_ids": [estudiante_id]}
        )

    return estudiante

@app.delete(
    "/estudiantes/{estudiante_id}", 
    tags=["Estudiantes"],
    summary="Eliminar estudiante",
    description="Elimina un estudiante del sistema.",
    responses={
        200: {"description": "Estudiante eliminado exitosamente"},
        401: {"description": "No autenticado"},
        404: {"description": "Estudiante no encontrado"}
    }
)
async def eliminar_estudiante(estudiante_id: int, request: Request, user=Depends(get_current_user_info)):
    """Elimina un estudiante (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("estudiantes", f"/estudiantes/{estudiante_id}", request)

# ==================== ASIGNATURAS (CON AUTENTICACIÓN) ====================

@app.get(
    "/asignaturas", 
    tags=["Asignaturas"],
    response_model=List[AsignaturaResponse],
    summary="Listar todas las asignaturas",
    description="Obtiene una lista con todas las asignaturas registradas en el sistema.",
    responses={
        200: {"description": "Lista de asignaturas"},
        401: {"description": "No autenticado"}
    }
)
async def listar_asignaturas(request: Request, user=Depends(get_current_user_info)):
    """Lista todas las asignaturas (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("asignaturas", "/asignaturas", request)

@app.get(
    "/asignaturas/mias", 
    tags=["Asignaturas"],
    response_model=List[AsignaturaResponse],
    summary="Listar asignaturas del docente",
    description="Obtiene las asignaturas asignadas al docente autenticado.",
    responses={
        200: {"description": "Lista de asignaturas del docente"},
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado"}
    }
)
async def gw_asignaturas_mias(request: Request, user=Depends(get_current_user_info)):
    """Obtiene las asignaturas del docente autenticado"""
    if user.get("rol") != "docente":
        raise HTTPException(status_code=403, detail="No autorizado")
    docente_id = user.get("id")
    return await proxy_request("asignaturas", f"/asignaturas/docente/{docente_id}", request)

@app.get(
    "/asignaturas/{asignatura_id}", 
    tags=["Asignaturas"],
    response_model=AsignaturaResponse,
    summary="Obtener asignatura por ID",
    description="Obtiene la información detallada de una asignatura específica.",
    responses={
        200: {"description": "Información de la asignatura"},
        401: {"description": "No autenticado"},
        404: {"description": "Asignatura no encontrada"}
    }
)
async def obtener_asignatura(asignatura_id: int, request: Request, token: str = Depends(verify_token)):
    """Obtiene una asignatura por ID"""
    return await proxy_request("asignaturas", f"/asignaturas/{asignatura_id}", request)

@app.post(
    "/asignaturas", 
    tags=["Asignaturas"],
    response_model=AsignaturaResponse,
    status_code=201,
    summary="Crear nueva asignatura",
    description="""
    Registra una nueva asignatura en el sistema.
    
    **Campos requeridos:**
    - `nombre`: Nombre de la asignatura
    - `codigo`: Código único de la asignatura
    - `descripcion`: Descripción de la asignatura (opcional)
    """,
    responses={
        201: {"description": "Asignatura creada exitosamente"},
        400: {"description": "Datos inválidos o código duplicado"},
        401: {"description": "No autenticado"}
    }
)
async def crear_asignatura(request: Request, user=Depends(get_current_user_info)):
    """Crea una nueva asignatura (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Crear la asignatura
    asignatura_response = await proxy_request("asignaturas", "/asignaturas", request)
    
    # Obtener el JSON del body de la respuesta
    asignatura_data = asignatura_response.body if hasattr(asignatura_response, 'body') else asignatura_response
    if isinstance(asignatura_data, bytes):
        import json
        asignatura = json.loads(asignatura_data)
    else:
        asignatura = asignatura_data
    
    # Si es docente, asignar automáticamente la asignatura a él
    if user.get("rol") == "docente":
        try:
            auth_header = request.headers.get("authorization")
            asignatura_id = asignatura.get("id")
            
            # Asignar la asignatura al docente
            await client.post(
                f"{SERVICES['auth']}/admin/asignar-asignaturas",
                headers={"Authorization": auth_header} if auth_header else None,
                json={"usuario_id": user.get("id"), "asignatura_ids": [asignatura_id]}
            )
        except Exception as e:
            print(f"Error asignando asignatura al docente: {e}")
    
    return asignatura_response

@app.put(
    "/asignaturas/{asignatura_id}", 
    tags=["Asignaturas"],
    response_model=AsignaturaResponse,
    summary="Actualizar asignatura",
    description="Actualiza la información de una asignatura existente.",
    responses={
        200: {"description": "Asignatura actualizada exitosamente"},
        400: {"description": "Datos inválidos"},
        401: {"description": "No autenticado"},
        404: {"description": "Asignatura no encontrada"}
    }
)
async def actualizar_asignatura(asignatura_id: int, request: Request, user=Depends(get_current_user_info)):
    """Actualiza una asignatura existente (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("asignaturas", f"/asignaturas/{asignatura_id}", request)

@app.delete(
    "/asignaturas/{asignatura_id}", 
    tags=["Asignaturas"],
    summary="Eliminar asignatura",
    description="Elimina una asignatura del sistema.",
    responses={
        200: {"description": "Asignatura eliminada exitosamente"},
        401: {"description": "No autenticado"},
        404: {"description": "Asignatura no encontrada"}
    }
)
async def eliminar_asignatura(asignatura_id: int, request: Request, user=Depends(get_current_user_info)):
    """Elimina una asignatura (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("asignaturas", f"/asignaturas/{asignatura_id}", request)

# ==================== EVALUACIONES (CON AUTENTICACIÓN) ====================

@app.get(
    "/evaluaciones", 
    tags=["Evaluaciones"],
    response_model=List[EvaluacionResponse],
    summary="Listar todas las evaluaciones",
    description="Obtiene una lista con todas las evaluaciones registradas en el sistema.",
    responses={
        200: {"description": "Lista de evaluaciones"},
        401: {"description": "No autenticado"}
    }
)
async def listar_evaluaciones(request: Request, user=Depends(get_current_user_info)):
    """Lista todas las evaluaciones (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("evaluaciones", "/evaluaciones", request)

@app.get(
    "/evaluaciones/mias", 
    tags=["Evaluaciones"],
    response_model=List[EvaluacionResponse],
    summary="Listar evaluaciones del docente",
    description="Obtiene todas las evaluaciones de las asignaturas del docente autenticado.",
    responses={
        200: {"description": "Lista de evaluaciones del docente"},
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado"}
    }
)
async def gw_evaluaciones_mias(request: Request, user=Depends(get_current_user_info)):
    """Obtiene todas las evaluaciones de las asignaturas del docente autenticado"""
    if user.get("rol") != "docente":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener asignaturas del docente
    try:
        auth_header = request.headers.get("authorization")
        resp = await client.get(
            f"{SERVICES['auth']}/admin/docente-asignaturas/{user.get('id')}",
            headers={"Authorization": auth_header} if auth_header else None
        )
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Error conectando con auth-service")
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="No se pudo validar asignación de docente")
    
    asignaciones = resp.json() or []
    asign_ids = [a.get("asignatura_id") for a in asignaciones]
    
    if not asign_ids:
        return []
    
    # Obtener evaluaciones de todas las asignaturas del docente
    all_evaluaciones = []
    for asig_id in asign_ids:
        try:
            eval_resp = await client.get(
                f"{SERVICES['evaluaciones']}/evaluaciones/asignatura/{asig_id}",
                headers={"Authorization": auth_header} if auth_header else None
            )
            if eval_resp.status_code == 200:
                all_evaluaciones.extend(eval_resp.json())
        except httpx.RequestError:
            pass
    
    return all_evaluaciones

@app.get(
    "/evaluaciones/{evaluacion_id}", 
    tags=["Evaluaciones"],
    response_model=EvaluacionResponse,
    summary="Obtener evaluación por ID",
    description="Obtiene la información detallada de una evaluación específica.",
    responses={
        200: {"description": "Información de la evaluación"},
        401: {"description": "No autenticado"},
        404: {"description": "Evaluación no encontrada"}
    }
)
async def obtener_evaluacion(evaluacion_id: int, request: Request, token: str = Depends(verify_token)):
    """Obtiene una evaluación por ID"""
    return await proxy_request("evaluaciones", f"/evaluaciones/{evaluacion_id}", request)

@app.get(
    "/evaluaciones/asignatura/{asignatura_id}", 
    tags=["Evaluaciones"],
    response_model=List[EvaluacionResponse],
    summary="Listar evaluaciones por asignatura",
    description="Obtiene todas las evaluaciones de una asignatura específica.",
    responses={
        200: {"description": "Lista de evaluaciones de la asignatura"},
        401: {"description": "No autenticado"}
    }
)
async def listar_evaluaciones_por_asignatura(asignatura_id: int, request: Request, user=Depends(get_current_user_info)):
    """Lista evaluaciones por asignatura"""
    if user.get("rol") == "admin":
        return await proxy_request("evaluaciones", f"/evaluaciones/asignatura/{asignatura_id}", request)
    if user.get("rol") == "docente":
        try:
            auth_header = request.headers.get("authorization")
            resp = await client.get(
                f"{SERVICES['auth']}/admin/docente-asignaturas/{user.get('id')}",
                headers={"Authorization": auth_header} if auth_header else None
            )
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Error conectando con auth-service")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="No se pudo validar asignación de docente")
        asignaciones = resp.json() or []
        asign_ids = {a.get("asignatura_id") for a in asignaciones}
        if asignatura_id not in asign_ids:
            raise HTTPException(status_code=403, detail="No autorizado")
        return await proxy_request("evaluaciones", f"/evaluaciones/asignatura/{asignatura_id}", request)
    raise HTTPException(status_code=403, detail="No autorizado")

@app.post(
    "/evaluaciones", 
    tags=["Evaluaciones"],
    response_model=EvaluacionResponse,
    status_code=201,
    summary="Crear nueva evaluación",
    description="""
    Registra una nueva evaluación en el sistema.
    
    **Campos requeridos:**
    - `nombre`: Nombre de la evaluación
    - `fecha`: Fecha de la evaluación (formato: YYYY-MM-DD)
    - `ponderacion`: Peso de la evaluación (0-100)
    - `asignatura_id`: ID de la asignatura
    """,
    responses={
        201: {"description": "Evaluación creada exitosamente"},
        400: {"description": "Datos inválidos o ponderación fuera de rango"},
        401: {"description": "No autenticado"}
    }
)
async def crear_evaluacion(request: Request, user=Depends(get_current_user_info)):
    """Crea una nueva evaluación (admin o docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("evaluaciones", "/evaluaciones", request)

@app.put(
    "/evaluaciones/{evaluacion_id}", 
    tags=["Evaluaciones"],
    response_model=EvaluacionResponse,
    summary="Actualizar evaluación",
    description="Actualiza la información de una evaluación existente.",
    responses={
        200: {"description": "Evaluación actualizada exitosamente"},
        400: {"description": "Datos inválidos"},
        401: {"description": "No autenticado"},
        404: {"description": "Evaluación no encontrada"}
    }
)
async def actualizar_evaluacion(evaluacion_id: int, request: Request, user=Depends(get_current_user_info)):
    """Actualiza una evaluación existente (admin o docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("evaluaciones", f"/evaluaciones/{evaluacion_id}", request)

@app.delete(
    "/evaluaciones/{evaluacion_id}", 
    tags=["Evaluaciones"],
    summary="Eliminar evaluación",
    description="Elimina una evaluación del sistema.",
    responses={
        200: {"description": "Evaluación eliminada exitosamente"},
        401: {"description": "No autenticado"},
        404: {"description": "Evaluación no encontrada"}
    }
)
async def eliminar_evaluacion(evaluacion_id: int, request: Request, user=Depends(get_current_user_info)):
    """Elimina una evaluación (admin o docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("evaluaciones", f"/evaluaciones/{evaluacion_id}", request)

# ==================== NOTAS (CON AUTENTICACIÓN) ====================

@app.get(
    "/notas/promedio-general/estudiante/{estudiante_id}", 
    tags=["Promedios"],
    summary="Calcular promedio general del estudiante",
    description="""
    Calcula el promedio general de un estudiante (promedio de todas sus asignaturas).
    
    **Fórmula:**
    
    `Promedio General = Σ(promedio_asignatura) / número_asignaturas`
    
    **Permisos:**
    - Admin: puede ver cualquier estudiante
    - Docente: puede ver estudiantes de sus asignaturas
    - Acudiente: puede ver sus estudiantes asignados
    """,
    responses={
        200: {"description": "Promedio general calculado exitosamente"},
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado"},
        404: {"description": "Estudiante no encontrado"}
    }
)
async def calcular_promedio_general_estudiante(estudiante_id: int, request: Request, token: str = Depends(verify_token)):
    """Calcula el promedio general de un estudiante (promedio de todas sus asignaturas)"""
    return await proxy_request("notas", f"/notas/promedio-general/estudiante/{estudiante_id}", request)

@app.get(
    "/notas", 
    tags=["Notas"],
    response_model=List[NotaResponse],
    summary="Listar todas las notas",
    description="Obtiene una lista con todas las notas registradas en el sistema.",
    responses={
        200: {"description": "Lista de notas"},
        401: {"description": "No autenticado"}
    }
)
async def listar_notas(request: Request, user=Depends(get_current_user_info)):
    """Lista todas las notas (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("notas", "/notas", request)

@app.get(
    "/notas/mis-hijos", 
    tags=["Notas"],
    response_model=List[NotaResponse],
    summary="Listar notas de los estudiantes del acudiente",
    description="Obtiene todas las notas de los estudiantes asignados al acudiente autenticado.",
    responses={
        200: {"description": "Lista de notas de los estudiantes del acudiente"},
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado"}
    }
)
async def gw_notas_mis_hijos(request: Request, user=Depends(get_current_user_info)):
    """Obtiene todas las notas de los estudiantes del acudiente autenticado"""
    if user.get("rol") != "acudiente":
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("notas", "/notas/mis-hijos", request)

@app.get(
    "/notas/mis-estudiantes",
    tags=["Notas"],
    response_model=List[NotaResponse],
    summary="Listar notas de los estudiantes del docente",
    description="Obtiene las notas de los estudiantes matriculados en las asignaturas del docente autenticado.",
    responses={
        200: {"description": "Lista de notas de los estudiantes del docente"},
        401: {"description": "No autenticado"},
        403: {"description": "No autorizado"}
    }
)
async def notas_mis_estudiantes(request: Request, user=Depends(get_current_user_info)):
    """Obtiene las notas de los estudiantes matriculados en las asignaturas del docente"""
    if user.get("rol") != "docente":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    usuario_id = user.get("id")
    auth_header = request.headers.get("authorization")
    
    # Obtener asignaturas del docente
    asignaturas_response = await client.get(
        f"{SERVICES['auth']}/admin/docente-asignaturas/{usuario_id}",
        headers={"Authorization": auth_header} if auth_header else None
    )
    
    if asignaturas_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error al obtener asignaturas del docente")
    
    asignaturas = asignaturas_response.json() or []
    asignatura_ids = [asig.get("asignatura_id") for asig in asignaturas if asig.get("asignatura_id")]
    
    # Obtener estudiantes matriculados en las asignaturas del docente
    estudiantes_ids = set()
    for asignatura_id in asignatura_ids:
        matriculas_response = await client.get(
            f"{SERVICES['auth']}/admin/matriculas?asignatura_id={asignatura_id}",
            headers={"Authorization": auth_header} if auth_header else None
        )
        if matriculas_response.status_code == 200:
            matriculas = matriculas_response.json() or []
            for mat in matriculas:
                estudiante_id = mat.get("estudiante_id")
                if estudiante_id:
                    estudiantes_ids.add(estudiante_id)
    
    # Obtener todas las notas
    notas_response = await client.get(
        f"{SERVICES['notas']}/notas",
        headers={"Authorization": auth_header} if auth_header else None
    )
    
    if notas_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error al obtener notas")
    
    todas_notas = notas_response.json() or []
    
    # Filtrar notas de los estudiantes del docente
    notas_docente = [nota for nota in todas_notas if nota.get("estudiante_id") in estudiantes_ids]
    
    return notas_docente

@app.get(
    "/notas/promedio/estudiante/{estudiante_id}/asignatura/{asignatura_id}",
    tags=["Promedios"],
    response_model=PromedioResponse,
    summary="Calcular promedio ponderado",
    description="""
    Calcula el promedio ponderado de un estudiante en una asignatura específica.
    
    **Fórmula:**
    
    `Promedio = Σ(nota × ponderación/100) / Σ(ponderación) × 100`
    
    **Ejemplo:**
    - Parcial 1: Nota 85, Ponderación 25%
    - Parcial 2: Nota 90, Ponderación 25%
    - Final: Nota 88, Ponderación 50%
    
    Resultado: 87.75
    """,
    responses={
        200: {"description": "Promedio calculado exitosamente"},
        401: {"description": "No autenticado"},
        404: {"description": "Estudiante o asignatura no encontrados"}
    }
)
async def calcular_promedio_estudiante(estudiante_id: int, asignatura_id: int, request: Request, token: str = Depends(verify_token)):
    """Calcula el promedio ponderado de un estudiante en una asignatura"""
    return await proxy_request("notas", f"/notas/promedio/estudiante/{estudiante_id}/asignatura/{asignatura_id}", request)

@app.get(
    "/notas/reporte/asignatura/{asignatura_id}",
    tags=["Reportes"],
    response_model=ReporteResponse,
    summary="Generar reporte de asignatura",
    description="""
    Genera un reporte completo de notas para una asignatura.
    
    **Incluye:**
    - Lista de estudiantes con sus notas
    - Promedio general de la asignatura
    - Distribución de notas por evaluación
    - Estadísticas generales
    """,
    responses={
        200: {"description": "Reporte generado exitosamente"},
        401: {"description": "No autenticado"},
        404: {"description": "Asignatura no encontrada"}
    }
)
async def generar_reporte_asignatura(asignatura_id: int, request: Request, token: str = Depends(verify_token)):
    """Genera un reporte completo de notas para una asignatura"""
    return await proxy_request("notas", f"/notas/reporte/asignatura/{asignatura_id}", request)

@app.get(
    "/notas/{nota_id}", 
    tags=["Notas"],
    response_model=NotaResponse,
    summary="Obtener nota por ID",
    description="Obtiene la información detallada de una nota específica.",
    responses={
        200: {"description": "Información de la nota"},
        401: {"description": "No autenticado"},
        404: {"description": "Nota no encontrada"}
    }
)
async def obtener_nota(nota_id: int, request: Request, token: str = Depends(verify_token)):
    """Obtiene una nota por ID"""
    return await proxy_request("notas", f"/notas/{nota_id}", request)

@app.get(
    "/notas/estudiante/{estudiante_id}", 
    tags=["Notas"],
    response_model=List[NotaResponse],
    summary="Listar notas por estudiante",
    description="Obtiene todas las notas de un estudiante específico.",
    responses={
        200: {"description": "Lista de notas del estudiante"},
        401: {"description": "No autenticado"}
    }
)
async def listar_notas_por_estudiante(estudiante_id: int, request: Request, token: str = Depends(verify_token)):
    """Lista notas por estudiante"""
    return await proxy_request("notas", f"/notas/estudiante/{estudiante_id}", request)

@app.get(
    "/notas/asignatura/{asignatura_id}",
    tags=["Notas"],
    response_model=List[NotaResponse],
    summary="Listar notas por asignatura",
    responses={
        200: {"description": "Lista de notas por asignatura"},
        401: {"description": "No autenticado"}
    }
)
async def listar_notas_por_asignatura(asignatura_id: int, request: Request, token: str = Depends(verify_token)):
    return await proxy_request("notas", f"/notas/asignatura/{asignatura_id}", request)

@app.post(
    "/notas", 
    tags=["Notas"],
    response_model=NotaResponse,
    status_code=201,
    summary="Crear nueva nota",
    description="""
    Registra una nueva nota en el sistema.
    
    **Campos requeridos:**
    - `estudiante_id`: ID del estudiante
    - `evaluacion_id`: ID de la evaluación
    - `valor`: Nota obtenida (0-100)
    
    **Validaciones:**
    - La nota debe estar entre 0 y 100
    - No puede existir una nota duplicada para el mismo estudiante y evaluación
    """,
    responses={
        201: {"description": "Nota creada exitosamente"},
        400: {"description": "Datos inválidos o nota duplicada"},
        401: {"description": "No autenticado"}
    }
)
async def crear_nota(request: Request, user=Depends(get_current_user_info)):
    """Crea una nueva nota (admin o docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("notas", "/notas", request)

@app.put(
    "/notas/{nota_id}", 
    tags=["Notas"],
    response_model=NotaResponse,
    summary="Actualizar nota",
    description="Actualiza la información de una nota existente.",
    responses={
        200: {"description": "Nota actualizada exitosamente"},
        400: {"description": "Datos inválidos"},
        401: {"description": "No autenticado"},
        404: {"description": "Nota no encontrada"}
    }
)
async def actualizar_nota(nota_id: int, request: Request, user=Depends(get_current_user_info)):
    """Actualiza una nota existente (admin o docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("notas", f"/notas/{nota_id}", request)

@app.delete(
    "/notas/{nota_id}", 
    tags=["Notas"],
    summary="Eliminar nota",
    description="Elimina una nota del sistema.",
    responses={
        200: {"description": "Nota eliminada exitosamente"},
        401: {"description": "No autenticado"},
        404: {"description": "Nota no encontrada"}
    }
)
async def eliminar_nota(nota_id: int, request: Request, user=Depends(get_current_user_info)):
    """Elimina una nota (admin o docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("notas", f"/notas/{nota_id}", request)

# ==================== HEALTH CHECK ====================

@app.get(
    "/health", 
    tags=["Health"],
    summary="Verificar estado del sistema",
    description="""
    Verifica el estado de todos los microservicios del sistema.
    
    **Estados posibles:**
    - `ok`: Servicio funcionando correctamente
    - `error`: Servicio con errores
    - `unreachable`: Servicio no accesible
    
    **Respuesta:**
    - `status`: Estado general del sistema (`ok` o `degraded`)
    - `gateway`: Estado del API Gateway
    - `services`: Estado de cada microservicio
    """,
    responses={
        200: {"description": "Estado del sistema"}
    }
)
async def health_check():
    """Verifica el estado de todos los servicios"""
    services_status = {}
    
    for service_name, service_url in SERVICES.items():
        try:
            response = await client.get(f"{service_url}/health")
            services_status[service_name] = "ok" if response.status_code == 200 else "error"
        except:
            services_status[service_name] = "unreachable"
    
    all_ok = all(status == "ok" for status in services_status.values())
    
    return {
        "status": "ok" if all_ok else "degraded",
        "gateway": "ok",
        "services": services_status
    }

# ==================== ADMINISTRACIÓN Y AUTORIZACIÓN ====================

# Usuarios (solo admin)
@app.get("/usuarios", tags=["Usuarios"])
async def gw_listar_usuarios(request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", "/usuarios", request)

@app.get("/usuarios/acudientes", tags=["Usuarios"])
async def gw_listar_acudientes(request: Request, user=Depends(get_current_user_info)):
    """Lista todos los usuarios con rol acudiente"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("auth", "/usuarios?rol=acudiente", request)

@app.get("/usuarios/{usuario_id}", tags=["Usuarios"])
async def gw_obtener_usuario(usuario_id: int, request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", f"/usuarios/{usuario_id}", request)

@app.put("/usuarios/{usuario_id}", tags=["Usuarios"])
async def gw_actualizar_usuario(usuario_id: int, request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", f"/usuarios/{usuario_id}", request)

@app.delete("/usuarios/{usuario_id}", tags=["Usuarios"])
async def gw_eliminar_usuario(usuario_id: int, request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", f"/usuarios/{usuario_id}", request)

# Asignaciones (solo admin)
@app.post("/admin/asignar-asignaturas", tags=["Administración"])
async def gw_asignar_asignaturas(request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", "/admin/asignar-asignaturas", request)

@app.post("/admin/asignar-estudiantes", tags=["Administración"])
async def gw_asignar_estudiantes(request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", "/admin/asignar-estudiantes", request)

@app.post("/admin/asignar-rol", tags=["Administración"]) 
async def gw_asignar_rol(request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", "/admin/asignar-rol", request)

# Matrículas (solo admin)
@app.post("/admin/matriculas", tags=["Administración"]) 
async def gw_crear_matricula(request: Request, user=Depends(get_current_user_info)):
    """Crear matrícula estudiante-asignatura (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("auth", "/admin/matriculas", request)

@app.delete("/admin/matriculas", tags=["Administración"]) 
async def gw_eliminar_matricula(request: Request, user=Depends(require_admin)):
    return await proxy_request("auth", "/admin/matriculas", request)

@app.get("/admin/matriculas", tags=["Administración"]) 
async def gw_listar_matriculas(request: Request, user=Depends(get_current_user_info)):
    """Listar matrículas (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("auth", "/admin/matriculas", request)

@app.get("/admin/docente-asignaturas/{usuario_id}", tags=["Administración"])
async def gw_obtener_asignaturas_docente(usuario_id: int, request: Request, user=Depends(get_current_user_info)):
    """Obtener las asignaturas de un docente (admin y docente)"""
    if user.get("rol") not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("auth", f"/admin/docente-asignaturas/{usuario_id}", request)

# ==================== REPORTES ====================

# Endpoints rol-específicos y filtros
@app.get("/estudiantes/acudiente/{acudiente_id}", tags=["Estudiantes"])
async def gw_estudiantes_por_acudiente(acudiente_id: int, request: Request, user=Depends(get_current_user_info)):
    if user.get("rol") not in ("admin", "docente") and user.get("id") != acudiente_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("estudiantes", f"/estudiantes/acudiente/{acudiente_id}", request)

@app.get("/estudiantes/asignatura/{asignatura_id}", tags=["Estudiantes"])
async def gw_estudiantes_por_asignatura(asignatura_id: int, request: Request, user=Depends(get_current_user_info)):
    if user.get("rol") == "admin":
        return await proxy_request("estudiantes", f"/estudiantes/asignatura/{asignatura_id}", request)
    if user.get("rol") == "docente":
        # Verificar que el docente esté asignado a la asignatura
        try:
            auth_header = request.headers.get("authorization")
            resp = await client.get(
                f"{SERVICES['auth']}/admin/docente-asignaturas/{user.get('id')}",
                headers={"Authorization": auth_header} if auth_header else None
            )
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Error conectando con auth-service")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="No se pudo validar asignación de docente")
        asignaciones = resp.json() or []
        asign_ids = {a.get("asignatura_id") for a in asignaciones}
        if asignatura_id not in asign_ids:
            raise HTTPException(status_code=403, detail="No autorizado")
        return await proxy_request("estudiantes", f"/estudiantes/asignatura/{asignatura_id}", request)
    raise HTTPException(status_code=403, detail="No autorizado")

@app.get("/asignaturas/docente/{docente_id}", tags=["Asignaturas"])
async def gw_asignaturas_por_docente(docente_id: int, request: Request, user=Depends(get_current_user_info)):
    if user.get("rol") != "admin" and user.get("id") != docente_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    return await proxy_request("asignaturas", f"/asignaturas/docente/{docente_id}", request)

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()