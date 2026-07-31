from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime
import os
import shutil

from database import engine, Base, get_db
from models import Concursante, Competicion, Levantamiento, Equipo
from schemas import (
    Concursante as ConcursanteSchema,
    ConcursanteCreate,
    Competicion as CompeticionSchema,
    CompeticionCreate,
    Levantamiento as LevantamientoSchema,
    LevantamientoCreate
)
from ipf_calculator import calculate_ipf_points
from fastapi import Request

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Powerlifting API - Cuba", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar carpeta estática para fotos
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
PHOTOS_DIR = os.path.join(STATIC_DIR, "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Leer clave admin desde variable de entorno
ADMIN_KEY = os.environ.get("ADMIN_KEY")


def check_admin(request: Request):
    """Verifica si la petición incluye la clave administrativa por header o query param."""
    key = None
    if "x-admin-key" in request.headers:
        key = request.headers.get("x-admin-key")
    elif request.query_params.get("admin_key"):
        key = request.query_params.get("admin_key")

    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Operación no autorizada")

# ==================== RUTAS CONCURSANTES ====================

@app.get("/api/concursantes")
def get_concursantes(db: Session = Depends(get_db)):
    """Obtener todos los concursantes"""
    return db.query(Concursante).all()

@app.post("/api/concursantes", response_model=ConcursanteSchema)
def create_concursante(concursante: ConcursanteCreate, db: Session = Depends(get_db), request: Request = None):
    """Crear un nuevo concursante"""
    # Verificar que no exista
    db_concursante = db.query(Concursante).filter(
        Concursante.nombre == concursante.nombre
    ).first()
    if db_concursante:
        raise HTTPException(status_code=400, detail="Concursante ya existe")
    # Protección: solo admin puede crear concursantes si ADMIN_KEY está configurada
    if ADMIN_KEY:
        check_admin(request)

    new_concursante = Concursante(**concursante.dict())
    db.add(new_concursante)
    db.commit()
    db.refresh(new_concursante)
    return new_concursante


@app.post("/api/concursantes/{concursante_id}/photo")
def upload_concursante_photo(concursante_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), request: Request = None):
    """Subir foto tipo carnet para un concursante"""
    if ADMIN_KEY:
        check_admin(request)
    db_concursante = db.query(Concursante).filter(Concursante.id == concursante_id).first()
    if not db_concursante:
        raise HTTPException(status_code=404, detail="Concursante no encontrado")

    filename = f"conc_{concursante_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    safe_path = os.path.join(PHOTOS_DIR, filename)
    try:
        with open(safe_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    db_concursante.photo_filename = filename
    db.add(db_concursante)
    db.commit()
    db.refresh(db_concursante)
    return {"message": "Foto subida", "photo_url": db_concursante.photo_url}

@app.get("/api/concursantes/{concursante_id}")
def get_concursante(concursante_id: int, db: Session = Depends(get_db)):
    """Obtener detalles de un concursante"""
    db_concursante = db.query(Concursante).filter(
        Concursante.id == concursante_id
    ).first()
    if not db_concursante:
        raise HTTPException(status_code=404, detail="Concursante no encontrado")
    return db_concursante

@app.put("/api/concursantes/{concursante_id}", response_model=ConcursanteSchema)
def update_concursante(
    concursante_id: int, 
    concursante: ConcursanteCreate, 
    db: Session = Depends(get_db),
    request: Request = None
):
    """Actualizar concursante"""
    if ADMIN_KEY:
        check_admin(request)
    db_concursante = db.query(Concursante).filter(
        Concursante.id == concursante_id
    ).first()
    if not db_concursante:
        raise HTTPException(status_code=404, detail="Concursante no encontrado")
    
    for key, value in concursante.dict().items():
        setattr(db_concursante, key, value)
    
    db.commit()
    db.refresh(db_concursante)
    return db_concursante

@app.delete("/api/concursantes/{concursante_id}")
def delete_concursante(concursante_id: int, db: Session = Depends(get_db), request: Request = None):
    """Eliminar concursante"""
    if ADMIN_KEY:
        check_admin(request)
    db_concursante = db.query(Concursante).filter(
        Concursante.id == concursante_id
    ).first()
    if not db_concursante:
        raise HTTPException(status_code=404, detail="Concursante no encontrado")
    
    db.delete(db_concursante)
    db.commit()
    return {"message": "Concursante eliminado"}

# ==================== RUTAS COMPETICIONES ====================

@app.get("/api/competiciones")
def get_competiciones(
    desde: int = Query(2024, ge=1900, description="Año mínimo para incluir competiciones"),
    db: Session = Depends(get_db)
):
    """Obtener el historial de competiciones desde un año dado"""
    competiciones = db.query(Competicion).all()

    historial = [
        competicion
        for competicion in competiciones
        if competicion.fecha and competicion.fecha.year >= desde
    ]

    historial.sort(key=lambda competicion: competicion.fecha or datetime.min, reverse=True)
    return historial

@app.post("/api/competiciones", response_model=CompeticionSchema)
def create_competicion(competicion: CompeticionCreate, db: Session = Depends(get_db), request: Request = None):
    """Crear una nueva competición (admin only)."""
    if ADMIN_KEY:
        check_admin(request)

    new_competicion = Competicion(**competicion.dict())
    db.add(new_competicion)
    db.commit()
    db.refresh(new_competicion)
    return new_competicion


# ==================== RUTAS EQUIPOS ====================

@app.get("/api/equipos", response_model=list[dict])
def get_equipos(db: Session = Depends(get_db)):
    """Obtener todos los equipos"""
    equipos = db.query(Equipo).all()
    result = []
    for e in equipos:
        result.append({
            "id": e.id,
            "nombre": e.nombre,
            "descripcion": e.descripcion,
            "miembros_count": len(e.miembros)
        })
    return result


@app.get("/api/equipos/{equipo_id}")
def get_equipo(equipo_id: int, db: Session = Depends(get_db)):
    db_equipo = db.query(Equipo).filter(Equipo.id == equipo_id).first()
    if not db_equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return {
        "id": db_equipo.id,
        "nombre": db_equipo.nombre,
        "descripcion": db_equipo.descripcion,
        "miembros": [
            {
                "id": m.id,
                "nombre": m.nombre,
                "categoria_peso": m.categoria_peso,
                "sexo": m.sexo,
                "photo_url": m.photo_url
            } for m in db_equipo.miembros
        ]
    }


@app.get("/api/equipos/{equipo_id}/atletas")
def get_equipo_atletas(equipo_id: int, db: Session = Depends(get_db)):
    db_equipo = db.query(Equipo).filter(Equipo.id == equipo_id).first()
    if not db_equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return db_equipo.miembros


@app.get("/api/equipos/{equipo_id}/competiciones")
def get_competiciones_equipo(equipo_id: int, db: Session = Depends(get_db)):
    """Obtener competiciones en las que participó algún miembro del equipo"""
    db_equipo = db.query(Equipo).filter(Equipo.id == equipo_id).first()
    if not db_equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    miembro_ids = [m.id for m in db_equipo.miembros]
    # Buscar levantamientos de esos miembros y agrupar competiciones
    compet_ids = db.query(Levantamiento.competicion_id).filter(
        Levantamiento.concursante_id.in_(miembro_ids),
        Levantamiento.competicion_id.isnot(None)
    ).distinct().all()

    comp_ids = [c[0] for c in compet_ids if c[0] is not None]
    competiciones = db.query(Competicion).filter(Competicion.id.in_(comp_ids)).all() if comp_ids else []

    result = [
        {
            'id': c.id,
            'nombre': c.nombre,
            'fecha': c.fecha.isoformat() if c.fecha else None,
            'ubicacion': c.ubicacion,
            'descripcion': c.descripcion
        } for c in competiciones
    ]
    return result


@app.post("/api/equipos")
def create_equipo(equipo: dict, db: Session = Depends(get_db), request: Request = None):
    """Crear un equipo (admin only)."""
    if ADMIN_KEY:
        check_admin(request)

    nombre = equipo.get("nombre")
    descripcion = equipo.get("descripcion")
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    existing = db.query(Equipo).filter(Equipo.nombre == nombre).first()
    if existing:
        raise HTTPException(status_code=400, detail="Equipo ya existe")
    new_equipo = Equipo(nombre=nombre, descripcion=descripcion)
    db.add(new_equipo)
    db.commit()
    db.refresh(new_equipo)
    return {"id": new_equipo.id, "nombre": new_equipo.nombre, "descripcion": new_equipo.descripcion}

@app.get("/api/competiciones/{competicion_id}")
def get_competicion(competicion_id: int, db: Session = Depends(get_db)):
    """Obtener detalles de una competición"""
    db_competicion = db.query(Competicion).filter(
        Competicion.id == competicion_id
    ).first()
    if not db_competicion:
        raise HTTPException(status_code=404, detail="Competición no encontrada")

    # Construir respuesta con levantamientos y datos del concursante embebidos
    levantamientos = []
    atletas = {}
    for l in db_competicion.levantamientos:
        total = l.sentadilla + l.press_banca + l.peso_muerto
        atleta_id = l.concursante_id
        if atleta_id not in atletas:
            atletas[atleta_id] = {
                "id": l.concursante.id,
                "nombre": l.concursante.nombre,
                "sexo": l.concursante.sexo,
                "categoria_peso": l.concursante.categoria_peso,
                "photo_url": l.concursante.photo_url,
                "levantamientos": [],
                "mejor_ipf": 0,
            }

        atletas[atleta_id]["levantamientos"].append({
            "id": l.id,
            "sentadilla": l.sentadilla,
            "press_banca": l.press_banca,
            "peso_muerto": l.peso_muerto,
            "total": total,
            "ipf_score": l.ipf_score,
            "fecha_levantamiento": l.fecha_levantamiento.isoformat()
        })
        atletas[atleta_id]["mejor_ipf"] = max(atletas[atleta_id]["mejor_ipf"], l.ipf_score)

        levantamientos.append({
            "id": l.id,
            "concursante_id": l.concursante_id,
            "concursante": {
                "id": l.concursante.id,
                "nombre": l.concursante.nombre,
                "sexo": l.concursante.sexo,
                "categoria_peso": l.concursante.categoria_peso,
                "photo_url": l.concursante.photo_url,
                "team": l.concursante.team.nombre if l.concursante.team else None
            },
            
            "sentadilla": l.sentadilla,
            "press_banca": l.press_banca,
            "peso_muerto": l.peso_muerto,
            "total": total,
            "ipf_score": l.ipf_score,
            "fecha_levantamiento": l.fecha_levantamiento.isoformat()
        })

    atletas_ordenados = sorted(
        atletas.values(),
        key=lambda atleta: atleta["mejor_ipf"],
        reverse=True
    )

    mejor_ipf = max((levantamiento["ipf_score"] for levantamiento in levantamientos), default=0)

    return {
        "id": db_competicion.id,
        "nombre": db_competicion.nombre,
        "fecha": db_competicion.fecha.isoformat() if db_competicion.fecha else None,
        "ubicacion": db_competicion.ubicacion,
        "descripcion": db_competicion.descripcion,
        "levantamientos": levantamientos,
        "atletas": atletas_ordenados,
        "mejor_ipf": mejor_ipf,
        "total_atletas": len(atletas_ordenados)
    }

# ==================== RUTAS LEVANTAMIENTOS ====================

@app.get("/api/levantamientos", response_model=list[LevantamientoSchema])
def get_levantamientos(db: Session = Depends(get_db)):
    """Obtener todos los levantamientos"""
    return db.query(Levantamiento).all()

@app.post("/api/levantamientos", response_model=LevantamientoSchema)
def create_levantamiento(levantamiento: LevantamientoCreate, db: Session = Depends(get_db), request: Request = None):
    """Crear un nuevo levantamiento y calcular IPF"""
    # Solo admin puede crear levantamientos si ADMIN_KEY está configurada
    if ADMIN_KEY:
        check_admin(request)
    # Verificar que exista el concursante
    db_concursante = db.query(Concursante).filter(
        Concursante.id == levantamiento.concursante_id
    ).first()
    if not db_concursante:
        raise HTTPException(status_code=404, detail="Concursante no encontrado")

    if levantamiento.competicion_id is not None:
        db_competicion = db.query(Competicion).filter(
            Competicion.id == levantamiento.competicion_id
        ).first()
        if not db_competicion:
            raise HTTPException(status_code=404, detail="Competición no encontrada")


    # Compatibilidad: si el cliente envió directamente `sentadilla`, usarlo
    if getattr(levantamiento, 'sentadilla', None) is not None:
        sentadilla_best = levantamiento.sentadilla
        s1, s2, s3 = levantamiento.sentadilla, None, None
    else:
        sentadilla_best = best_valid(levantamiento.sentadilla_1, levantamiento.sentadilla_2, levantamiento.sentadilla_3)
        s1, s2, s3 = levantamiento.sentadilla_1, levantamiento.sentadilla_2, levantamiento.sentadilla_3

    if getattr(levantamiento, 'press_banca', None) is not None:
        press_banca_best = levantamiento.press_banca
        pb1, pb2, pb3 = levantamiento.press_banca, None, None
    else:
        press_banca_best = best_valid(levantamiento.press_banca_1, levantamiento.press_banca_2, levantamiento.press_banca_3)
        pb1, pb2, pb3 = levantamiento.press_banca_1, levantamiento.press_banca_2, levantamiento.press_banca_3

    if getattr(levantamiento, 'peso_muerto', None) is not None:
        peso_muerto_best = levantamiento.peso_muerto
        pm1, pm2, pm3 = levantamiento.peso_muerto, None, None
    else:
        peso_muerto_best = best_valid(levantamiento.peso_muerto_1, levantamiento.peso_muerto_2, levantamiento.peso_muerto_3)
        pm1, pm2, pm3 = levantamiento.peso_muerto_1, levantamiento.peso_muerto_2, levantamiento.peso_muerto_3

    total = sentadilla_best + press_banca_best + peso_muerto_best
    ipf_score = calculate_ipf_points(
        total,
        db_concursante.categoria_peso,
        db_concursante.sexo
    )

    payload = levantamiento.dict()
    # Sobrescribir/asegurar intentos y mejores
    payload.update({
        'sentadilla_1': s1,
        'sentadilla_2': s2,
        'sentadilla_3': s3,
        'press_banca_1': pb1,
        'press_banca_2': pb2,
        'press_banca_3': pb3,
        'peso_muerto_1': pm1,
        'peso_muerto_2': pm2,
        'peso_muerto_3': pm3,
        'sentadilla': sentadilla_best,
        'press_banca': press_banca_best,
        'peso_muerto': peso_muerto_best,
        'ipf_score': ipf_score
    })

    new_levantamiento = Levantamiento(**payload)
    db.add(new_levantamiento)
    db.commit()
    db.refresh(new_levantamiento)
    return new_levantamiento

@app.put("/api/levantamientos/{levantamiento_id}", response_model=LevantamientoSchema)
def update_levantamiento(levantamiento_id: int, levantamiento: LevantamientoCreate, db: Session = Depends(get_db), request: Request = None):
    """Actualizar un levantamiento"""
    if ADMIN_KEY:
        check_admin(request)
    
    db_levantamiento = db.query(Levantamiento).filter(
        Levantamiento.id == levantamiento_id
    ).first()
    if not db_levantamiento:
        raise HTTPException(status_code=404, detail="Levantamiento no encontrado")
    
    # Verificar que exista el concursante (actualización)
    db_concursante = db.query(Concursante).filter(
        Concursante.id == levantamiento.concursante_id
    ).first()
    if not db_concursante:
        raise HTTPException(status_code=404, detail="Concursante no encontrado")

    # Recalcular mejor intento y IPF
    def best_valid(*attempts):
        vals = [a for a in attempts if a is not None]
        return max(vals) if vals else 0.0

    sentadilla_best = best_valid(levantamiento.sentadilla_1, levantamiento.sentadilla_2, levantamiento.sentadilla_3, levantamiento.sentadilla)
    press_banca_best = best_valid(levantamiento.press_banca_1, levantamiento.press_banca_2, levantamiento.press_banca_3, levantamiento.press_banca)
    peso_muerto_best = best_valid(levantamiento.peso_muerto_1, levantamiento.peso_muerto_2, levantamiento.peso_muerto_3, levantamiento.peso_muerto)

    total = sentadilla_best + press_banca_best + peso_muerto_best
    ipf_score = calculate_ipf_points(total, db_concursante.categoria_peso, db_concursante.sexo)

    # Actualizar campos
    db_levantamiento.concursante_id = levantamiento.concursante_id
    db_levantamiento.sentadilla_1 = levantamiento.sentadilla_1
    db_levantamiento.sentadilla_2 = levantamiento.sentadilla_2
    db_levantamiento.sentadilla_3 = levantamiento.sentadilla_3
    db_levantamiento.press_banca_1 = levantamiento.press_banca_1
    db_levantamiento.press_banca_2 = levantamiento.press_banca_2
    db_levantamiento.press_banca_3 = levantamiento.press_banca_3
    db_levantamiento.peso_muerto_1 = levantamiento.peso_muerto_1
    db_levantamiento.peso_muerto_2 = levantamiento.peso_muerto_2
    db_levantamiento.peso_muerto_3 = levantamiento.peso_muerto_3
    db_levantamiento.sentadilla = sentadilla_best
    db_levantamiento.press_banca = press_banca_best
    db_levantamiento.peso_muerto = peso_muerto_best
    db_levantamiento.ipf_score = ipf_score

    db.add(db_levantamiento)
    db.commit()
    db.refresh(db_levantamiento)
    return db_levantamiento

@app.delete("/api/levantamientos/{levantamiento_id}")
def delete_levantamiento(levantamiento_id: int, db: Session = Depends(get_db), request: Request = None):
    """Eliminar un levantamiento"""
    if ADMIN_KEY:
        check_admin(request)
    
    db_levantamiento = db.query(Levantamiento).filter(
        Levantamiento.id == levantamiento_id
    ).first()
    if not db_levantamiento:
        raise HTTPException(status_code=404, detail="Levantamiento no encontrado")
    
    db.delete(db_levantamiento)
    db.commit()
    return {"message": "Levantamiento eliminado"}

@app.get("/api/levantamientos/concursante/{concursante_id}", response_model=list[LevantamientoSchema])
def get_levantamientos_concursante(concursante_id: int, db: Session = Depends(get_db)):
    """Obtener todos los levantamientos de un concursante"""
    return db.query(Levantamiento).filter(
        Levantamiento.concursante_id == concursante_id
    ).all()

# ==================== RUTAS RANKING ====================

@app.get("/api/ranking")
def get_ranking(db: Session = Depends(get_db)):
    """Obtener ranking de concursantes por IPF"""
    levantamientos = db.query(Levantamiento).all()
    ranking = sorted(
        [
            {
                "concursante_id": l.concursante_id,
                "nombre": l.concursante.nombre,
                "sexo": l.concursante.sexo,
                "categoria_peso": l.concursante.categoria_peso,
                "total": l.sentadilla + l.press_banca + l.peso_muerto,
                "ipf_score": l.ipf_score,
                "sentadilla": l.sentadilla,
                "press_banca": l.press_banca,
                "peso_muerto": l.peso_muerto
            }
            for l in levantamientos
        ],
        key=lambda x: x['ipf_score'],
        reverse=True
    )
    return ranking

@app.get("/api/ranking/{categoria}")
def get_ranking_categoria(categoria: str, db: Session = Depends(get_db)):
    """Obtener ranking por categoría de peso"""
    levantamientos = db.query(Levantamiento).all()
    ranking = sorted(
        [
            {
                "concursante_id": l.concursante_id,
                "nombre": l.concursante.nombre,
                "sexo": l.concursante.sexo,
                "total": l.sentadilla + l.press_banca + l.peso_muerto,
                "ipf_score": l.ipf_score,
                "sentadilla": l.sentadilla,
                "press_banca": l.press_banca,
                "peso_muerto": l.peso_muerto
            }
            for l in levantamientos
            if l.concursante.categoria_peso == categoria
        ],
        key=lambda x: x['ipf_score'],
        reverse=True
    )
    return ranking


@app.get("/api/records")
def get_records(db: Session = Depends(get_db)):
    """Obtener el record absoluto (mejor total) entre todos los levantamientos"""
    levantamientos = db.query(Levantamiento).all()
    best = None
    for l in levantamientos:
        total = (l.sentadilla or 0) + (l.press_banca or 0) + (l.peso_muerto or 0)
        if best is None or total > best['total']:
            best = {
                'concursante': l.concursante.nombre,
                'categoria_peso': l.concursante.categoria_peso,
                'sentadilla': l.sentadilla,
                'press_banca': l.press_banca,
                'peso_muerto': l.peso_muerto,
                'total': total,
                'ipf_score': l.ipf_score,
                'competicion_id': l.competicion_id
            }
    return best or {}

# ==================== RUTAS ESTADÍSTICAS ====================

@app.get("/api/estadisticas")
def get_estadisticas(db: Session = Depends(get_db)):
    """Obtener estadísticas generales"""
    total_concursantes = db.query(Concursante).count()
    total_competiciones = db.query(Competicion).count()
    total_levantamientos = db.query(Levantamiento).count()
    
    levantamientos = db.query(Levantamiento).all()
    mejor_ipf = max([l.ipf_score for l in levantamientos], default=0) if levantamientos else 0
    
    return {
        "total_concursantes": total_concursantes,
        "total_competiciones": total_competiciones,
        "total_levantamientos": total_levantamientos,
        "mejor_ipf": mejor_ipf
    }

# ==================== RUTA SALUD ====================

@app.get("/")
def read_root():
    """Health check"""
    return {"message": "Powerlifting API - Hermandad Cubana", "status": "online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
