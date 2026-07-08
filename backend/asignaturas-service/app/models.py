from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/libreta")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Asignatura(Base):
    __tablename__ = "asignaturas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(20), unique=True, nullable=False)
    descripcion = Column(String(255))

def init_db():
    # Las tablas son creadas por el script init.sql
    # Este método se mantiene por compatibilidad pero no hace nada
    pass