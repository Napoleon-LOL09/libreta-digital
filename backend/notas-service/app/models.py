from sqlalchemy import Column, Integer, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/libreta")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Nota(Base):
    __tablename__ = "notas"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, nullable=False)
    evaluacion_id = Column(Integer, nullable=False)
    valor = Column(Float, nullable=False)  # Nota de 0 a 100

def init_db():
    # Las tablas son creadas por el script init.sql
    # Este método se mantiene por compatibilidad pero no hace nada
    pass