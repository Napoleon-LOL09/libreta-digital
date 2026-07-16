from pydantic import BaseModel
from typing import Optional, List

class NotaBase(BaseModel):
    estudiante_id: int
    evaluacion_id: int
    valor: float

class NotaCreate(NotaBase):
    pass

class NotaUpdate(BaseModel):
    estudiante_id: Optional[int] = None
    evaluacion_id: Optional[int] = None
    valor: Optional[float] = None

class Nota(NotaBase):
    id: int
    evaluacion_nombre: Optional[str] = None
    ponderacion: Optional[float] = None
    asignatura_id: Optional[int] = None
    asignatura_nombre: Optional[str] = None

    class Config:
        from_attributes = True

class PromedioEstudiante(BaseModel):
    estudiante_id: int
    estudiante_nombre: str
    asignatura_id: int
    asignatura_nombre: str
    promedio: float
    notas: List[dict]

class ReporteNotas(BaseModel):
    estudiante_id: int
    estudiante_nombre: str
    asignatura_nombre: str
    evaluacion_nombre: str
    nota: float
    ponderacion: float
    nota_ponderada: float