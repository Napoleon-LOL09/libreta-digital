from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import httpx
import sys
sys.path.insert(0, '/app')

from app.models import Evaluacion, SessionLocal, init_db
from app.schemas import EvaluacionCreate, EvaluacionUpdate, Evaluacion as EvaluacionSchema

AUTH_URL = "http://auth-service:8005"
app = FastAPI(title="Evaluaciones Service", description="Microservicio para gestión de evaluaciones")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    init_db()

# Helpers de autorización
def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Falta token")
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{AUTH_URL}/auth/me", headers={"Authorization": auth})
            if r.status_code != 200:
                raise HTTPException(status_code=401, detail="Token inválido")
            return r.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth no disponible")

def is_admin(user: dict) -> bool:
    return user.get("rol") == "admin"

def docente_tiene_asignatura(db: Session, docente_id: int, asignatura_id: int) -> bool:
    row = db.execute(text("SELECT 1 FROM docente_asignatura WHERE usuario_id=:u AND asignatura_id=:a"), {"u": docente_id, "a": asignatura_id}).fetchone()
    return row is not None


@app.get("/evaluaciones", response_model=List[EvaluacionSchema], tags=["Evaluaciones"])
def listar_evaluaciones(request: Request, db: Session = Depends(get_db)):
    """Lista todas las evaluaciones"""
    _ = get_current_user(request)  # Solo autenticación
    return db.query(Evaluacion).all()

@app.get("/evaluaciones/{evaluacion_id}", response_model=EvaluacionSchema, tags=["Evaluaciones"])
def obtener_evaluacion(evaluacion_id: int, request: Request, db: Session = Depends(get_db)):
    """Obtiene una evaluación por ID"""
    _ = get_current_user(request)
    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    return evaluacion

@app.get("/evaluaciones/asignatura/{asignatura_id}", response_model=List[EvaluacionSchema], tags=["Evaluaciones"])
def listar_evaluaciones_por_asignatura(asignatura_id: int, request: Request, db: Session = Depends(get_db)):
    """Lista evaluaciones por asignatura"""
    user = get_current_user(request)
    if not is_admin(user):
        if user.get("rol") != "docente" or not docente_tiene_asignatura(db, user.get("id"), asignatura_id):
            raise HTTPException(status_code=403, detail="No autorizado")
    return db.query(Evaluacion).filter(Evaluacion.asignatura_id == asignatura_id).all()

@app.post("/evaluaciones", response_model=EvaluacionSchema, tags=["Evaluaciones"])
def crear_evaluacion(evaluacion: EvaluacionCreate, request: Request, db: Session = Depends(get_db)):
    """Crea una nueva evaluación"""
    user = get_current_user(request)
    if not is_admin(user):
        if user.get("rol") != "docente" or not docente_tiene_asignatura(db, user.get("id"), evaluacion.asignatura_id):
            raise HTTPException(status_code=403, detail="No autorizado")
    # Validar que la ponderación esté entre 0 y 100
    if evaluacion.ponderacion < 0 or evaluacion.ponderacion > 100:
        raise HTTPException(status_code=400, detail="La ponderación debe estar entre 0 y 100")
    
    db_evaluacion = Evaluacion(**evaluacion.model_dump())
    db.add(db_evaluacion)
    db.commit()
    db.refresh(db_evaluacion)
    return db_evaluacion

@app.put("/evaluaciones/{evaluacion_id}", response_model=EvaluacionSchema, tags=["Evaluaciones"])
def actualizar_evaluacion(evaluacion_id: int, evaluacion: EvaluacionUpdate, request: Request, db: Session = Depends(get_db)):
    """Actualiza una evaluación existente"""
    user = get_current_user(request)
    db_evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not db_evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    # Autorización
    if not is_admin(user):
        destino_asig_id = evaluacion.asignatura_id if evaluacion.asignatura_id is not None else db_evaluacion.asignatura_id
        if user.get("rol") != "docente" or not docente_tiene_asignatura(db, user.get("id"), destino_asig_id):
            raise HTTPException(status_code=403, detail="No autorizado")

    # Validar ponderación si se proporciona
    if evaluacion.ponderacion is not None:
        if evaluacion.ponderacion < 0 or evaluacion.ponderacion > 100:
            raise HTTPException(status_code=400, detail="La ponderación debe estar entre 0 y 100")
    
    for key, value in evaluacion.model_dump(exclude_unset=True).items():
        setattr(db_evaluacion, key, value)
    
    db.commit()
    db.refresh(db_evaluacion)
    return db_evaluacion

@app.delete("/evaluaciones/{evaluacion_id}", tags=["Evaluaciones"])
def eliminar_evaluacion(evaluacion_id: int, request: Request, db: Session = Depends(get_db)):
    """Elimina una evaluación"""
    user = get_current_user(request)
    db_evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not db_evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    if not is_admin(user):
        if user.get("rol") != "docente" or not docente_tiene_asignatura(db, user.get("id"), db_evaluacion.asignatura_id):
            raise HTTPException(status_code=403, detail="No autorizado")
    
    db.delete(db_evaluacion)
    db.commit()
    return {"mensaje": "Evaluación eliminada correctamente"}

@app.get("/health", tags=["Health"])
def health_check():
    """Verifica el estado del servicio"""
    return {"status": "ok", "service": "evaluaciones"}