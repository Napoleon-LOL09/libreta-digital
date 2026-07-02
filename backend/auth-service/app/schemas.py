from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UsuarioBase(BaseModel):
    username: str
    nombre: str
    email: Optional[EmailStr] = None

class UsuarioCreate(UsuarioBase):
    password: str
    rol: Optional[str] = 'docente'  # admin, docente, acudiente

class UsuarioUpdate(BaseModel):
    """Schema para actualización de usuario. Todos los campos son opcionales."""
    username: Optional[str] = None
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    rol: Optional[str] = None

class UsuarioLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    rol: Optional[str] = None

class Usuario(UsuarioBase):
    id: int
    rol: str
    activo: bool
    
    class Config:
        from_attributes = True

# Schemas para relaciones
class DocenteAsignaturaBase(BaseModel):
    usuario_id: int
    asignatura_id: int

class DocenteAsignaturaCreate(DocenteAsignaturaBase):
    pass

class DocenteAsignatura(DocenteAsignaturaBase):
    id: int
    
    class Config:
        from_attributes = True

class AcudienteEstudianteBase(BaseModel):
    usuario_id: int
    estudiante_id: int

class AcudienteEstudianteCreate(AcudienteEstudianteBase):
    pass

class AcudienteEstudiante(AcudienteEstudianteBase):
    id: int
    
    class Config:
        from_attributes = True

# Schemas para asignaciones múltiples
class AsignarAsignaturas(BaseModel):
    usuario_id: int
    asignatura_ids: List[int]

class AsignarEstudiantes(BaseModel):
    usuario_id: int
    estudiante_ids: List[int]

class AsignarRol(BaseModel):
    usuario_id: int
    rol: str

# Matriculas
class MatriculaBase(BaseModel):
    estudiante_id: int
    asignatura_id: int
    periodo: Optional[str] = None

class MatriculaCreate(MatriculaBase):
    pass

class MatriculaDelete(MatriculaBase):
    pass

class Matricula(BaseModel):
    id: int
    estudiante_id: int
    asignatura_id: int
    periodo: Optional[str] = None
    class Config:
        from_attributes = True