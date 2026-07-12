from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/libreta")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Evaluacion(Base):
    __tablename__ = "evaluaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    fecha = Column(Date, nullable=False)
    ponderacion = Column(Float, nullable=False)  # Porcentaje (0-100)
    asignatura_id = Column(Integer, nullable=False)

def init_db():
    # Las tablas son creadas por el script init.sql
    # Este método se mantiene por compatibilidad pero no hace nada
    pass