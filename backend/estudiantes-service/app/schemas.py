from pydantic import BaseModel
from typing import Optional

class EstudianteBase(BaseModel):
    nombre: str
    apellido: str
    codigo: str
    email: Optional[str] = None

class EstudianteCreate(EstudianteBase):
    acudiente_id: Optional[int] = None

class EstudianteUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    codigo: Optional[str] = None
    email: Optional[str] = None
    acudiente_id: Optional[int] = None

class Estudiante(EstudianteBase):
    id: int
    
    class Config:
        from_attributes = True