from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional
import httpx
import sys
sys.path.insert(0, '/app')

from app.models import Nota, SessionLocal, init_db
from app.schemas import NotaCreate, NotaUpdate, Nota as NotaSchema, PromedioEstudiante, ReporteNotas

AUTH_URL = "http://auth-service:8005"
app = FastAPI(title="Notas Service", description="Microservicio para gestión de notas y cálculo de promedios")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    init_db()

# Helpers de autorización
def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Falta token")
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{AUTH_URL}/auth/me", headers={"Authorization": auth})
            if r.status_code != 200:
                raise HTTPException(status_code=401, detail="Token inválido")
            return r.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth no disponible")

def is_admin(user: dict) -> bool:
    return user.get("rol") == "admin"

def docente_tiene_asignatura(db: Session, docente_id: int, asignatura_id: int) -> bool:
    row = db.execute(text("SELECT 1 FROM docente_asignatura WHERE usuario_id=:u AND asignatura_id=:a"), {"u": docente_id, "a": asignatura_id}).fetchone()
    return row is not None

def estudiante_matriculado(db: Session, estudiante_id: int, asignatura_id: int) -> bool:
    row = db.execute(text("SELECT 1 FROM matriculas WHERE estudiante_id=:e AND asignatura_id=:a"), {"e": estudiante_id, "a": asignatura_id}).fetchone()
    return row is not None

def acudiente_de_estudiante(db: Session, acudiente_id: int, estudiante_id: int) -> bool:
    row = db.execute(text("SELECT 1 FROM acudiente_estudiante WHERE usuario_id=:u AND estudiante_id=:e"), {"u": acudiente_id, "e": estudiante_id}).fetchone()
    return row is not None

def asignatura_de_evaluacion(db: Session, evaluacion_id: int) -> Optional[int]:
    row = db.execute(text("SELECT asignatura_id FROM evaluaciones WHERE id=:id"), {"id": evaluacion_id}).fetchone()
    return row[0] if row else None


@app.get("/notas", response_model=List[NotaSchema], tags=["Notas"])
def listar_notas(db: Session = Depends(get_db)):
    """Lista todas las notas"""
    return db.query(Nota).all()

@app.get("/notas/mis-hijos", response_model=List[NotaSchema], tags=["Notas"])
def notas_mis_hijos(request: Request, db: Session = Depends(get_db)):
    """Lista todas las notas de los estudiantes del acudiente autenticado"""
    user = get_current_user(request)
    if user.get("rol") != "acudiente":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener estudiantes del acudiente
    rows = db.execute(text("SELECT estudiante_id FROM acudiente_estudiante WHERE usuario_id = :u"), {"u": user.get("id")}).fetchall()
    estudiante_ids = [row[0] for row in rows]
    
    if not estudiante_ids:
        return []
    
    # Obtener todas las notas de esos estudiantes
    return db.query(Nota).filter(Nota.estudiante_id.in_(estudiante_ids)).all()

@app.get("/notas/promedio-general/estudiante/{estudiante_id}", tags=["Promedios"])
def calcular_promedio_general_estudiante(estudiante_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Calcula el promedio general de un estudiante (promedio de todas sus asignaturas).
    """
    user = get_current_user(request)
    if not is_admin(user):
        if user.get("rol") == "acudiente":
            if not acudiente_de_estudiante(db, user.get("id"), estudiante_id):
                raise HTTPException(status_code=403, detail="No autorizado")
        elif user.get("rol") == "docente":
            # El docente puede ver el promedio general de sus estudiantes
            from sqlalchemy import text
            query = text("""
                SELECT DISTINCT a.id
                FROM asignaturas a
                JOIN matriculas m ON a.id = m.asignatura_id
                JOIN docente_asignatura da ON a.id = da.asignatura_id
                WHERE m.estudiante_id = :estudiante_id AND da.usuario_id = :docente_id
            """)
            result = db.execute(query, {"estudiante_id": estudiante_id, "docente_id": user.get("id")})
            if not result.fetchone():
                raise HTTPException(status_code=403, detail="No autorizado")
        else:
            raise HTTPException(status_code=403, detail="No autorizado")

    from sqlalchemy import text
    
    # Obtener todas las asignaturas del estudiante con sus promedios
    query = text("""
        SELECT DISTINCT a.id as asignatura_id, a.nombre as asignatura_nombre
        FROM asignaturas a
        JOIN matriculas m ON a.id = m.asignatura_id
        WHERE m.estudiante_id = :estudiante_id
    """)
    
    result = db.execute(query, {"estudiante_id": estudiante_id})
    asignaturas = result.fetchall()
    
    if not asignaturas:
        return {
            "estudiante_id": estudiante_id,
            "promedio_general": 0,
            "asignaturas": [],
            "mensaje": "El estudiante no tiene asignaturas matriculadas"
        }
    
    # Calcular promedio por asignatura
    asignaturas_con_promedio = []
    suma_promedios = 0
    count_asignaturas = 0
    
    for asig in asignaturas:
        # Obtener notas de esta asignatura
        query_notas = text("""
            SELECT n.valor as nota, e.ponderacion
            FROM notas n
            JOIN evaluaciones e ON n.evaluacion_id = e.id
            WHERE n.estudiante_id = :estudiante_id AND e.asignatura_id = :asignatura_id
        """)
        
        result_notas = db.execute(query_notas, {"estudiante_id": estudiante_id, "asignatura_id": asig.asignatura_id})
        notas = result_notas.fetchall()
        
        if notas:
            # Calcular promedio ponderado de la asignatura
            suma_ponderada = 0
            suma_ponderaciones = 0
            for nota in notas:
                suma_ponderada += (nota.nota * nota.ponderacion) / 100
                suma_ponderaciones += nota.ponderacion
            
            promedio_asignatura = (suma_ponderada / suma_ponderaciones * 100) if suma_ponderaciones > 0 else 0
            promedio_asignatura = round(promedio_asignatura, 2)
        else:
            promedio_asignatura = 0
        
        asignaturas_con_promedio.append({
            "asignatura_id": asig.asignatura_id,
            "asignatura_nombre": asig.asignatura_nombre,
            "promedio": promedio_asignatura
        })
        
        if promedio_asignatura > 0:
            suma_promedios += promedio_asignatura
            count_asignaturas += 1
    
    # Promedio general (promedio de promedios)
    promedio_general = round(suma_promedios / count_asignaturas, 2) if count_asignaturas > 0 else 0
    
    return {
        "estudiante_id": estudiante_id,
        "promedio_general": promedio_general,
        "asignaturas": asignaturas_con_promedio
    }

@app.get("/notas/{nota_id}", response_model=NotaSchema, tags=["Notas"])
def obtener_nota(nota_id: int, db: Session = Depends(get_db)):
    """Obtiene una nota por ID"""
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return nota

@app.get("/notas/estudiante/{estudiante_id}", response_model=List[NotaSchema], tags=["Notas"])
def listar_notas_por_estudiante(estudiante_id: int, request: Request, db: Session = Depends(get_db)):
    """Lista notas por estudiante"""
    user = get_current_user(request)
    if not is_admin(user):
        # Permitir a acudiente de ese estudiante o docente de alguna asignatura del estudiante
        if user.get("rol") == "acudiente":
            if not acudiente_de_estudiante(db, user.get("id"), estudiante_id):
                raise HTTPException(status_code=403, detail="No autorizado")
        elif user.get("rol") == "docente":
            row = db.execute(text("""
                SELECT 1
                FROM docente_asignatura da
                JOIN matriculas m ON m.asignatura_id = da.asignatura_id
                WHERE da.usuario_id = :u AND m.estudiante_id = :e
                LIMIT 1
            """), {"u": user.get("id"), "e": estudiante_id}).fetchone()
            if not row:
                raise HTTPException(status_code=403, detail="No autorizado")
        else:
            raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener notas con información de evaluación y asignatura
    query = text("""
        SELECT n.id, n.estudiante_id, n.evaluacion_id, n.valor,
               e.nombre as evaluacion_nombre, e.ponderacion, e.asignatura_id,
               a.nombre as asignatura_nombre
        FROM notas n
        JOIN evaluaciones e ON n.evaluacion_id = e.id
        JOIN asignaturas a ON e.asignatura_id = a.id
        WHERE n.estudiante_id = :estudiante_id
    """)
    
    result = db.execute(query, {"estudiante_id": estudiante_id})
    rows = result.fetchall()
    
    notas = []
    for row in rows:
        notas.append({
            "id": row.id,
            "estudiante_id": row.estudiante_id,
            "evaluacion_id": row.evaluacion_id,
            "valor": row.valor,
            "evaluacion_nombre": row.evaluacion_nombre,
            "ponderacion": row.ponderacion,
            "asignatura_id": row.asignatura_id,
            "asignatura_nombre": row.asignatura_nombre
        })
    
    return notas

@app.get("/notas/asignatura/{asignatura_id}", response_model=List[NotaSchema], tags=["Notas"]) 
def listar_notas_por_asignatura(asignatura_id: int, request: Request, db: Session = Depends(get_db)):
    """Lista notas por asignatura (via evaluaciones)"""
    user = get_current_user(request)
    if not is_admin(user) and user.get("rol") == "docente":
        if not docente_tiene_asignatura(db, user.get("id"), asignatura_id):
            raise HTTPException(status_code=403, detail="No autorizado")
    elif not is_admin(user):
        raise HTTPException(status_code=403, detail="No autorizado")
    rows = db.execute(text("""
        SELECT n.id
        FROM notas n
        JOIN evaluaciones e ON e.id = n.evaluacion_id
        WHERE e.asignatura_id = :aid
    """), {"aid": asignatura_id}).fetchall()
    nota_ids = [r[0] for r in rows]
    if not nota_ids:
        return []
    return db.query(Nota).filter(Nota.id.in_(nota_ids)).all()


@app.post("/notas", response_model=NotaSchema, tags=["Notas"])
def crear_nota(nota: NotaCreate, request: Request, db: Session = Depends(get_db)):
    """Crea una nueva nota"""
    user = get_current_user(request)
    if not is_admin(user):
        if user.get("rol") != "docente":
            raise HTTPException(status_code=403, detail="No autorizado")
        asig_id = asignatura_de_evaluacion(db, nota.evaluacion_id)
        if asig_id is None or not docente_tiene_asignatura(db, user.get("id"), asig_id):
            raise HTTPException(status_code=403, detail="No autorizado")
        if not estudiante_matriculado(db, nota.estudiante_id, asig_id):
            raise HTTPException(status_code=400, detail="Estudiante no matriculado en la asignatura")
    # Validar que la nota esté entre 0 y 100
    if nota.valor < 0 or nota.valor > 100:
        raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 100")
    
    # Verificar si ya existe una nota para este estudiante y evaluación
    existing = db.query(Nota).filter(
        Nota.estudiante_id == nota.estudiante_id,
        Nota.evaluacion_id == nota.evaluacion_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una nota para este estudiante en esta evaluación")
    
    db_nota = Nota(**nota.model_dump())
    db.add(db_nota)
    db.commit()
    db.refresh(db_nota)
    return db_nota

@app.put("/notas/{nota_id}", response_model=NotaSchema, tags=["Notas"])
def actualizar_nota(nota_id: int, nota: NotaUpdate, request: Request, db: Session = Depends(get_db)):
    """Actualiza una nota existente"""
    user = get_current_user(request)
    db_nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not db_nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    # Autorización
    if not is_admin(user):
        if user.get("rol") != "docente":
            raise HTTPException(status_code=403, detail="No autorizado")
        # Obtener asignatura a partir de la evaluación actual o propuesta
        eval_id = nota.evaluacion_id if nota.evaluacion_id is not None else db_nota.evaluacion_id
        asig_id = asignatura_de_evaluacion(db, eval_id)
        if asig_id is None or not docente_tiene_asignatura(db, user.get("id"), asig_id):
            raise HTTPException(status_code=403, detail="No autorizado")
        est_id = nota.estudiante_id if nota.estudiante_id is not None else db_nota.estudiante_id
        if not estudiante_matriculado(db, est_id, asig_id):
            raise HTTPException(status_code=400, detail="Estudiante no matriculado en la asignatura")

    # Validar valor si se proporciona
    if nota.valor is not None:
        if nota.valor < 0 or nota.valor > 100:
            raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 100")
    
    for key, value in nota.model_dump(exclude_unset=True).items():
        setattr(db_nota, key, value)
    
    db.commit()
    db.refresh(db_nota)
    return db_nota

@app.delete("/notas/{nota_id}", tags=["Notas"])
def eliminar_nota(nota_id: int, request: Request, db: Session = Depends(get_db)):
    """Elimina una nota"""
    user = get_current_user(request)
    db_nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not db_nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    if not is_admin(user):
        if user.get("rol") != "docente":
            raise HTTPException(status_code=403, detail="No autorizado")
        asig_id = asignatura_de_evaluacion(db, db_nota.evaluacion_id)
        if asig_id is None or not docente_tiene_asignatura(db, user.get("id"), asig_id):
            raise HTTPException(status_code=403, detail="No autorizado")
    
    db.delete(db_nota)
    db.commit()
    return {"mensaje": "Nota eliminada correctamente"}

@app.get("/notas/promedio/estudiante/{estudiante_id}/asignatura/{asignatura_id}", tags=["Promedios"])
def calcular_promedio_estudiante(estudiante_id: int, asignatura_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Calcula el promedio ponderado de un estudiante en una asignatura.
    El promedio se calcula sumando (nota * ponderacion) / 100 para cada evaluación.
    """
    user = get_current_user(request)
    if not is_admin(user):
        if user.get("rol") == "acudiente":
            if not acudiente_de_estudiante(db, user.get("id"), estudiante_id):
                raise HTTPException(status_code=403, detail="No autorizado")
        elif user.get("rol") == "docente":
            if not docente_tiene_asignatura(db, user.get("id"), asignatura_id):
                raise HTTPException(status_code=403, detail="No autorizado")
        else:
            raise HTTPException(status_code=403, detail="No autorizado")

    from sqlalchemy import text
    
    # Query para obtener notas con ponderaciones
    query = text("""
        SELECT n.estudiante_id, n.evaluacion_id, n.valor as nota, 
               e.ponderacion, e.nombre as evaluacion_nombre, e.asignatura_id
        FROM notas n
        JOIN evaluaciones e ON n.evaluacion_id = e.id
        WHERE n.estudiante_id = :estudiante_id AND e.asignatura_id = :asignatura_id
    """)
    
    result = db.execute(query, {"estudiante_id": estudiante_id, "asignatura_id": asignatura_id})
    rows = result.fetchall()
    
    if not rows:
        return {
            "estudiante_id": estudiante_id,
            "asignatura_id": asignatura_id,
            "promedio": 0,
            "notas": [],
            "mensaje": "No hay notas registradas"
        }
    
    # Calcular promedio ponderado
    suma_ponderada = 0
    suma_ponderaciones = 0
    notas_detalle = []
    
    for row in rows:
        nota_ponderada = (row.nota * row.ponderacion) / 100
        suma_ponderada += nota_ponderada
        suma_ponderaciones += row.ponderacion
        notas_detalle.append({
            "evaluacion_id": row.evaluacion_id,
            "evaluacion_nombre": row.evaluacion_nombre,
            "nota": row.nota,
            "ponderacion": row.ponderacion,
            "nota_ponderada": round(nota_ponderada, 2)
        })
    
    # Si las ponderaciones no suman 100, ajustar proporcionalmente
    promedio = (suma_ponderada / suma_ponderaciones * 100) if suma_ponderaciones > 0 else 0
    
    return {
        "estudiante_id": estudiante_id,
        "asignatura_id": asignatura_id,
        "promedio": round(promedio, 2),
        "suma_ponderaciones": suma_ponderaciones,
        "notas": notas_detalle
    }

@app.get("/notas/reporte/asignatura/{asignatura_id}", tags=["Reportes"])
def generar_reporte_asignatura(asignatura_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Genera un reporte completo de notas para una asignatura.
    Incluye todos los estudiantes con sus notas y promedios.
    """
    user = get_current_user(request)
    if not is_admin(user) and (user.get("rol") != "docente" or not docente_tiene_asignatura(db, user.get("id"), asignatura_id)):
        raise HTTPException(status_code=403, detail="No autorizado")

    from sqlalchemy import text
    
    query = text("""
        SELECT e.id as estudiante_id, e.nombre || ' ' || e.apellido as estudiante_nombre,
               ev.nombre as evaluacion_nombre, ev.ponderacion,
               n.valor as nota, (n.valor * ev.ponderacion / 100) as nota_ponderada
        FROM estudiantes e
        CROSS JOIN evaluaciones ev
        LEFT JOIN notas n ON n.estudiante_id = e.id AND n.evaluacion_id = ev.id
        WHERE ev.asignatura_id = :asignatura_id
        ORDER BY e.apellido, e.nombre, ev.fecha
    """)
    
    result = db.execute(query, {"asignatura_id": asignatura_id})
    rows = result.fetchall()
    
    # Organizar datos por estudiante
    estudiantes_dict = {}
    for row in rows:
        if row.estudiante_id not in estudiantes_dict:
            estudiantes_dict[row.estudiante_id] = {
                "estudiante_id": row.estudiante_id,
                "estudiante_nombre": row.estudiante_nombre,
                "notas": [],
                "promedio": 0
            }
        
        if row.nota is not None:
            estudiantes_dict[row.estudiante_id]["notas"].append({
                "evaluacion_nombre": row.evaluacion_nombre,
                "nota": row.nota,
                "ponderacion": row.ponderacion,
                "nota_ponderada": round(row.nota_ponderada, 2)
            })
    
    # Calcular promedios
    reporte = []
    for estudiante_id, data in estudiantes_dict.items():
        if data["notas"]:
            suma_ponderada = sum(n["nota_ponderada"] for n in data["notas"])
            suma_ponderaciones = sum(n["ponderacion"] for n in data["notas"])
            promedio = (suma_ponderada / suma_ponderaciones * 100) if suma_ponderaciones > 0 else 0
            data["promedio"] = round(promedio, 2)
        reporte.append(data)
    
    return {
        "asignatura_id": asignatura_id,
        "total_estudiantes": len(reporte),
        "reporte": reporte
    }

@app.get("/notas/reporte/estudiante/{estudiante_id}", tags=["Reportes"]) 
def generar_reporte_estudiante(estudiante_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Reporte para un estudiante: por cada asignatura matriculada, lista evaluaciones con sus notas y promedio por asignatura.
    Acceso: admin o acudiente del estudiante.
    """
    user = get_current_user(request)
    if not is_admin(user):
        if user.get("rol") != "acudiente" or not acudiente_de_estudiante(db, user.get("id"), estudiante_id):
            raise HTTPException(status_code=403, detail="No autorizado")

    query = text("""
        SELECT a.id as asignatura_id, a.nombre as asignatura_nombre,
               ev.id as evaluacion_id, ev.nombre as evaluacion_nombre, ev.ponderacion,
               n.valor as nota, (n.valor * ev.ponderacion / 100) as nota_ponderada
        FROM matriculas m
        JOIN asignaturas a ON a.id = m.asignatura_id
        JOIN evaluaciones ev ON ev.asignatura_id = a.id
        LEFT JOIN notas n ON n.estudiante_id = m.estudiante_id AND n.evaluacion_id = ev.id
        WHERE m.estudiante_id = :estudiante_id
        ORDER BY a.nombre, ev.fecha
    """)
    rows = db.execute(query, {"estudiante_id": estudiante_id}).fetchall()

    asignaturas = {}
    for row in rows:
        if row.asignatura_id not in asignaturas:
            asignaturas[row.asignatura_id] = {
                "asignatura_id": row.asignatura_id,
                "asignatura_nombre": row.asignatura_nombre,
                "notas": [],
                "promedio": 0
            }
        if row.nota is not None:
            asignaturas[row.asignatura_id]["notas"].append({
                "evaluacion_id": row.evaluacion_id,
                "evaluacion_nombre": row.evaluacion_nombre,
                "nota": row.nota,
                "ponderacion": row.ponderacion,
                "nota_ponderada": round(row.nota_ponderada, 2)
            })

    reporte = []
    for aid, data in asignaturas.items():
        if data["notas"]:
            suma_ponderada = sum(n["nota_ponderada"] for n in data["notas"])
            suma_ponderaciones = sum(n["ponderacion"] for n in data["notas"])
            promedio = (suma_ponderada / suma_ponderaciones * 100) if suma_ponderaciones > 0 else 0
            data["promedio"] = round(promedio, 2)
        reporte.append(data)

    return {
        "estudiante_id": estudiante_id,
        "asignaturas": reporte
    }

@app.get("/health", tags=["Health"]) 
def health_check():
    """Verifica el estado del servicio"""
    return {"status": "ok", "service": "notas"}