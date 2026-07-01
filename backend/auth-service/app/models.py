from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/libreta")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    rol = Column(String(20), default='docente')  # admin, docente, acudiente
    activo = Column(Boolean, default=True)

class DocenteAsignatura(Base):
    __tablename__ = "docente_asignatura"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False)
    asignatura_id = Column(Integer, nullable=False)

class AcudienteEstudiante(Base):
    __tablename__ = "acudiente_estudiante"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False)
    estudiante_id = Column(Integer, nullable=False)

def init_db():
    # Las tablas son creadas por el script init.sql
    # Este método se mantiene por compatibilidad pero no hace nada
    pass