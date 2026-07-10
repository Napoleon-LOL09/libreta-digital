from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import sys
sys.path.insert(0, '/app')

from app.models import Asignatura, SessionLocal, init_db
from app.schemas import AsignaturaCreate, AsignaturaUpdate, Asignatura as AsignaturaSchema

app = FastAPI(title="Asignaturas Service", description="Microservicio para gestión de asignaturas")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/asignaturas", response_model=List[AsignaturaSchema], tags=["Asignaturas"])
def listar_asignaturas(db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    """Lista todas las asignaturas (paginado)"""
    limit = max(1, min(limit, 200))
    return db.query(Asignatura).offset(skip).limit(limit).all()

@app.get("/asignaturas/{asignatura_id}", response_model=AsignaturaSchema, tags=["Asignaturas"])
def obtener_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    """Obtiene una asignatura por ID"""
    asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    return asignatura

@app.post("/asignaturas", response_model=AsignaturaSchema, tags=["Asignaturas"])
def crear_asignatura(asignatura: AsignaturaCreate, db: Session = Depends(get_db)):
    """Crea una nueva asignatura"""
    db_asignatura = Asignatura(**asignatura.model_dump())
    db.add(db_asignatura)
    db.commit()
    db.refresh(db_asignatura)
    return db_asignatura

@app.put("/asignaturas/{asignatura_id}", response_model=AsignaturaSchema, tags=["Asignaturas"])
def actualizar_asignatura(asignatura_id: int, asignatura: AsignaturaUpdate, db: Session = Depends(get_db)):
    """Actualiza una asignatura existente"""
    db_asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not db_asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    
    for key, value in asignatura.model_dump(exclude_unset=True).items():
        setattr(db_asignatura, key, value)
    
    db.commit()
    db.refresh(db_asignatura)
    return db_asignatura

@app.delete("/asignaturas/{asignatura_id}", tags=["Asignaturas"])
def eliminar_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    """Elimina una asignatura"""
    db_asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    if not db_asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    
    db.delete(db_asignatura)
    db.commit()
    return {"mensaje": "Asignatura eliminada correctamente"}

# Endpoint: Asignaturas por docente
@app.get("/asignaturas/docente/{docente_id}", response_model=List[AsignaturaSchema], tags=["Asignaturas"]) 
def asignaturas_por_docente(docente_id: int, db: Session = Depends(get_db), skip: int = 0, limit: int = 50):
    limit = max(1, min(limit, 200))
    ids = db.execute(text("SELECT asignatura_id FROM docente_asignatura WHERE usuario_id = :uid"), {"uid": docente_id}).fetchall()
    asignatura_ids = [row[0] for row in ids]
    if not asignatura_ids:
        return []
    return db.query(Asignatura).filter(Asignatura.id.in_(asignatura_ids)).offset(skip).limit(limit).all()

@app.get("/health", tags=["Health"]) 
def health_check():
    """Verifica el estado del servicio"""
    return {"status": "ok", "service": "asignaturas"}