from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional
import sys
import os
import bcrypt
sys.path.insert(0, '/app')

from app.models import Usuario as UsuarioModel, DocenteAsignatura, AcudienteEstudiante, SessionLocal, init_db
from app.schemas import (
    UsuarioCreate, UsuarioLogin, Token, Usuario as UsuarioSchema,
    UsuarioUpdate,
    DocenteAsignaturaCreate, AcudienteEstudianteCreate,
    AsignarAsignaturas, AsignarEstudiantes, AsignarRol,
    MatriculaCreate, MatriculaDelete
)

app = FastAPI(title="Auth Service", description="Microservicio de autenticación y gestión de usuarios")

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY", "libreta-digital-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña usando bcrypt"""
    if not plain_password or not hashed_password:
        return False
    try:
        # Soporte de migración: si el hash es del esquema "demo" viejo (terminado en _hashed),
        # comparar directamente para no romper cuentas legacy.
        if hashed_password == f"{plain_password}_hashed":
            return True
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    """Generar hash de contraseña usando bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        rol: str = payload.get("rol")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(UsuarioModel).filter(UsuarioModel.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(current_user: UsuarioModel = Depends(get_current_user)):
    """Verificar que el usuario actual es administrador"""
    if current_user.rol != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos de administrador"
        )
    return current_user

@app.on_event("startup")
def startup():
    init_db()
    print("Servicio de autenticación iniciado")
    # Sembrar/actualizar usuario admin con hash bcrypt real
    from app.models import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(UsuarioModel).filter(UsuarioModel.username == "admin").first()
        admin_hash = get_password_hash("admin123")
        if not admin:
            admin = UsuarioModel(
                username="admin",
                password_hash=admin_hash,
                nombre="Administrador",
                email="admin@libreta.local",
                rol="admin",
                activo=True,
            )
            db.add(admin)
        else:
            admin.password_hash = admin_hash
        db.commit()
        print("Usuario por defecto: admin / admin123")
    except Exception as e:
        db.rollback()
        print(f"Error inicializando admin: {e}")
    finally:
        db.close()

@app.post("/auth/login", response_model=Token, tags=["Autenticación"])
def login(usuario: UsuarioLogin, db: Session = Depends(get_db)):
    """Iniciar sesión y obtener token JWT"""
    user = db.query(UsuarioModel).filter(UsuarioModel.username == usuario.username).first()

    if not user or not verify_password(usuario.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    access_token = create_access_token(data={"sub": user.username, "rol": user.rol, "id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/register", response_model=UsuarioSchema, tags=["Autenticación"])
def register(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Registrar nuevo usuario"""
    # Verificar si el usuario ya existe
    db_user = db.query(UsuarioModel).filter(UsuarioModel.username == usuario.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    
    # Verificar si el email ya existe
    if usuario.email:
        db_email = db.query(UsuarioModel).filter(UsuarioModel.email == usuario.email).first()
        if db_email:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(usuario.password)
    # Usar el rol proporcionado (por defecto 'docente' si no se especifica)
    new_user = UsuarioModel(
        username=usuario.username,
        password_hash=hashed_password,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=usuario.rol if usuario.rol else 'docente',
        activo=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/auth/me", response_model=UsuarioSchema, tags=["Autenticación"])
async def read_users_me(current_user: UsuarioModel = Depends(get_current_user)):
    """Obtener información del usuario actual"""
    return current_user

@app.get("/auth/verify", tags=["Autenticación"])
async def verify_token(current_user: UsuarioModel = Depends(get_current_user)):
    """Verificar si el token es válido"""
    return {"valid": True, "username": current_user.username}

@app.get("/usuarios", response_model=List[UsuarioSchema], tags=["Usuarios"])
async def listar_usuarios(rol: Optional[str] = None, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Listar todos los usuarios (requiere autenticación). Opcionalmente filtrar por rol."""
    query = db.query(UsuarioModel)
    if rol:
        query = query.filter(UsuarioModel.rol == rol)
    return query.all()

@app.get("/usuarios/{usuario_id}", response_model=UsuarioSchema, tags=["Usuarios"])
async def obtener_usuario(usuario_id: int, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtener un usuario por ID"""
    user = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@app.put("/usuarios/{usuario_id}", response_model=UsuarioSchema, tags=["Usuarios"])
async def actualizar_usuario(usuario_id: int, usuario: UsuarioUpdate, current_user: UsuarioModel = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Actualizar un usuario (solo admin)"""
    db_user = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Actualizar campos opcionales
    if usuario.nombre is not None:
        db_user.nombre = usuario.nombre
    if usuario.email is not None:
        db_user.email = usuario.email
    if usuario.rol is not None:
        db_user.rol = usuario.rol
    if usuario.username is not None:
        db_user.username = usuario.username

    # Si se envió una contraseña no vacía, re-hashearla con bcrypt
    if usuario.password is not None and usuario.password.strip() != "":
        db_user.password_hash = get_password_hash(usuario.password)

    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/usuarios/{usuario_id}", tags=["Usuarios"])
async def eliminar_usuario(usuario_id: int, current_user: UsuarioModel = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Eliminar un usuario (solo admin)"""
    db_user = db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    db.delete(db_user)
    db.commit()
    return {"message": "Usuario eliminado exitosamente"}

# ==================== ASIGNACIONES (SOLO ADMIN) ====================

@app.post("/admin/asignar-asignaturas", tags=["Administración"])
async def asignar_asignaturas(asignacion: AsignarAsignaturas, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Asignar múltiples asignaturas a un docente (admin y docente)"""
    # Solo admin y docente pueden asignar asignaturas
    if current_user.rol not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Verificar que el usuario existe y es docente
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == asignacion.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.rol != 'docente':
        raise HTTPException(status_code=400, detail="El usuario debe ser docente")
    
    # Si es docente, solo puede asignarse asignaturas a sí mismo
    if current_user.rol == 'docente' and asignacion.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para asignar asignaturas a otros docentes")
    
    # Asignar las asignaturas
    for asignatura_id in asignacion.asignatura_ids:
        # Verificar si ya existe la asignación
        existing = db.query(DocenteAsignatura).filter(
            DocenteAsignatura.usuario_id == asignacion.usuario_id,
            DocenteAsignatura.asignatura_id == asignatura_id
        ).first()
        
        if not existing:
            nueva_asignacion = DocenteAsignatura(
                usuario_id=asignacion.usuario_id,
                asignatura_id=asignatura_id
            )
            db.add(nueva_asignacion)
    
    db.commit()
    return {"message": f"Asignaturas asignadas exitosamente al docente {usuario.nombre}"}

@app.post("/admin/asignar-estudiantes", tags=["Administración"])
async def asignar_estudiantes(asignacion: AsignarEstudiantes, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Asignar múltiples estudiantes a un acudiente (solo admin)"""
    # Verificar que el usuario existe y es acudiente
    usuario = db.query(UsuarioModel).filter(UsuarioModel.id == asignacion.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if current_user.rol not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Asignar los estudiantes
    for estudiante_id in asignacion.estudiante_ids:
        # Verificar si ya existe la asignación
        existing = db.query(AcudienteEstudiante).filter(
            AcudienteEstudiante.usuario_id == asignacion.usuario_id,
            AcudienteEstudiante.estudiante_id == estudiante_id
        ).first()
        
        if not existing:
            nueva_asignacion = AcudienteEstudiante(
                usuario_id=asignacion.usuario_id,
                estudiante_id=estudiante_id
            )
            db.add(nueva_asignacion)
    
    db.commit()
    return {"message": f"Estudiantes asignados exitosamente al acudiente {usuario.nombre}"}

@app.get("/admin/docente-asignaturas/{usuario_id}", tags=["Administración"])
async def obtener_asignaturas_docente(usuario_id: int, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtener las asignaturas de un docente"""
    asignaturas = db.query(DocenteAsignatura).filter(DocenteAsignatura.usuario_id == usuario_id).all()
    return [{"asignatura_id": a.asignatura_id} for a in asignaturas]

@app.get("/admin/acudiente-estudiantes/{usuario_id}", tags=["Administración"])
async def obtener_estudiantes_acudiente(usuario_id: int, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obtener los estudiantes de un acudiente"""
    estudiantes = db.query(AcudienteEstudiante).filter(AcudienteEstudiante.usuario_id == usuario_id).all()
    return [{"estudiante_id": e.estudiante_id} for e in estudiantes]

# ==================== MATRÍCULAS (ADMIN Y DOCENTE) ====================
@app.post("/admin/matriculas", tags=["Administración"])
async def crear_matricula(payload: MatriculaCreate, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Crear matrícula estudiante-asignatura (opcional periodo) - Admin y Docente"""
    if current_user.rol not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    params = {"e": payload.estudiante_id, "a": payload.asignatura_id, "p": payload.periodo}
    exists = db.execute(text("""
        SELECT id FROM matriculas 
        WHERE estudiante_id=:e AND asignatura_id=:a AND COALESCE(periodo,'')=COALESCE(:p,'')
    """), params).fetchone()
    if exists:
        raise HTTPException(status_code=400, detail="La matrícula ya existe")
    row = db.execute(text("""
        INSERT INTO matriculas (estudiante_id, asignatura_id, periodo)
        VALUES (:e, :a, :p)
        RETURNING id, estudiante_id, asignatura_id, periodo
    """), params).fetchone()
    db.commit()
    return {"id": row[0], "estudiante_id": row[1], "asignatura_id": row[2], "periodo": row[3]}

@app.delete("/admin/matriculas", tags=["Administración"])
async def eliminar_matricula(payload: MatriculaDelete, current_user: UsuarioModel = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Eliminar matrícula por claves (estudiante, asignatura, periodo opcional)"""
    params = {"e": payload.estudiante_id, "a": payload.asignatura_id, "p": payload.periodo}
    row = db.execute(text("""
        DELETE FROM matriculas 
        WHERE estudiante_id=:e AND asignatura_id=:a AND COALESCE(periodo,'')=COALESCE(:p,'')
        RETURNING id
    """), params).fetchone()
    if not row:
        db.rollback()
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
    db.commit()
    return {"message": "Matrícula eliminada"}

@app.get("/admin/matriculas", tags=["Administración"])
async def listar_matriculas(estudiante_id: int | None = None, asignatura_id: int | None = None, current_user: UsuarioModel = Depends(get_current_user), db: Session = Depends(get_db)):
    """Listar matrículas, filtrando opcionalmente por estudiante o asignatura (Admin y Docente)"""
    # Solo admin y docente pueden ver matrículas
    if current_user.rol not in ("admin", "docente"):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    base = "SELECT id, estudiante_id, asignatura_id, periodo FROM matriculas"
    where = []
    params = {}
    if estudiante_id is not None:
        where.append("estudiante_id = :e")
        params["e"] = estudiante_id
    if asignatura_id is not None:
        where.append("asignatura_id = :a")
        params["a"] = asignatura_id
    if where:
        base += " WHERE " + " AND ".join(where)
    base += " ORDER BY id DESC"
    rows = db.execute(text(base), params).fetchall()
    return [{"id": r[0], "estudiante_id": r[1], "asignatura_id": r[2], "periodo": r[3]} for r in rows]

@app.post("/admin/asignar-rol", tags=["Administración"]) 
async def asignar_rol(payload: AsignarRol, current_user: UsuarioModel = Depends(get_current_admin_user), db: Session = Depends(get_db)):

    """Asignar rol a un usuario (solo admin)"""
    if payload.rol not in ("admin", "docente", "acudiente"):
        raise HTTPException(status_code=400, detail="Rol inválido")
    db_user = db.query(UsuarioModel).filter(UsuarioModel.id == payload.usuario_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db_user.rol = payload.rol
    db.commit()
    db.refresh(db_user)
    return {"message": f"Rol actualizado a {payload.rol}", "usuario_id": db_user.id}


@app.get("/health", tags=["Health"])
def health_check():
    """Verificar el estado del servicio"""
    return {"status": "ok", "service": "auth"}