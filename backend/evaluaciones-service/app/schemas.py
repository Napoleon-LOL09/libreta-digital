from pydantic import BaseModel
from typing import Optional
from datetime import date

class EvaluacionBase(BaseModel):
    nombre: str
    fecha: date
    ponderacion: float
    asignatura_id: int

class EvaluacionCreate(EvaluacionBase):
    pass

class EvaluacionUpdate(BaseModel):
    nombre: Optional[str] = None
    fecha: Optional[date] = None
    ponderacion: Optional[float] = None
    asignatura_id: Optional[int] = None

class Evaluacion(EvaluacionBase):
    id: int
    
    class Config:
        from_attributes = True