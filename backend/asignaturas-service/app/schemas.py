from pydantic import BaseModel
from typing import Optional

class AsignaturaBase(BaseModel):
    nombre: str
    codigo: str
    descripcion: Optional[str] = None

class AsignaturaCreate(AsignaturaBase):
    pass

class AsignaturaUpdate(BaseModel):
    nombre: Optional[str] = None
    codigo: Optional[str] = None
    descripcion: Optional[str] = None

class Asignatura(AsignaturaBase):
    id: int
    
    class Config:
        from_attributes = True