from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import sys
sys.path.insert(0, '/app')

from app.models import Estudiante, SessionLocal, init_db
from app.schemas import (
    EstudianteCreate,
    EstudianteUpdate,
    Estudiante as EstudianteSchema
)

app = FastAPI(title="Estudiantes Service", description="Microservicio para gestión de estudiantes")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/estudiantes", response_model=List[EstudianteSchema], tags=["Estudiantes"]) 
def listar_estudiantes(db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    """Lista todos los estudiantes (paginado)"""
    limit = max(1, min(limit, 200))
    return db.query(Estudiante).offset(skip).limit(limit).all()


@app.get("/estudiantes/{estudiante_id}", response_model=EstudianteSchema, tags=["Estudiantes"])
def obtener_estudiante(estudiante_id: int, db: Session = Depends(get_db)):
    """Obtiene un estudiante por ID"""
    estudiante = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return estudiante

@app.post("/estudiantes", response_model=EstudianteSchema, tags=["Estudiantes"])
def crear_estudiante(estudiante: EstudianteCreate, db: Session = Depends(get_db)):
    """Crea un nuevo estudiante"""
    db_estudiante = Estudiante(**estudiante.model_dump())
    db.add(db_estudiante)
    db.commit()
    db.refresh(db_estudiante)
    
    return db_estudiante

@app.put("/estudiantes/{estudiante_id}", response_model=EstudianteSchema, tags=["Estudiantes"])
def actualizar_estudiante(estudiante_id: int, estudiante: EstudianteUpdate, db: Session = Depends(get_db)):
    """Actualiza un estudiante existente"""
    db_estudiante = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not db_estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    for key, value in estudiante.model_dump(exclude_unset=True).items():
        setattr(db_estudiante, key, value)
    
    db.commit()
    db.refresh(db_estudiante)

    return db_estudiante

@app.delete("/estudiantes/{estudiante_id}", tags=["Estudiantes"])
def eliminar_estudiante(estudiante_id: int, db: Session = Depends(get_db)):
    """Elimina un estudiante"""
    db_estudiante = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not db_estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    db.delete(db_estudiante)
    db.commit()
    return {"mensaje": "Estudiante eliminado correctamente"}

# Endpoints de filtrado
@app.get("/estudiantes/asignatura/{asignatura_id}", response_model=List[EstudianteSchema], tags=["Estudiantes"]) 
def estudiantes_por_asignatura(asignatura_id: int, db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    limit = max(1, min(limit, 200))
    ids = db.execute(text("SELECT estudiante_id FROM matriculas WHERE asignatura_id = :aid"), {"aid": asignatura_id}).fetchall()
    estudiante_ids = [row[0] for row in ids]
    if not estudiante_ids:
        return []
    return db.query(Estudiante).filter(Estudiante.id.in_(estudiante_ids)).offset(skip).limit(limit).all()

@app.get("/estudiantes/acudiente/{acudiente_id}", response_model=List[EstudianteSchema], tags=["Estudiantes"]) 
def estudiantes_por_acudiente(acudiente_id: int, db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    limit = max(1, min(limit, 200))
    ids = db.execute(text("SELECT estudiante_id FROM acudiente_estudiante WHERE usuario_id = :uid"), {"uid": acudiente_id}).fetchall()
    estudiante_ids = [row[0] for row in ids]
    if not estudiante_ids:
        return []
    return db.query(Estudiante).filter(Estudiante.id.in_(estudiante_ids)).offset(skip).limit(limit).all()

@app.get("/health", tags=["Health"]) 
def health_check():
    """Verifica el estado del servicio"""
    return {"status": "ok", "service": "estudiantes"}