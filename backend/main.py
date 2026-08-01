from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime
import os
import shutil

from database import engine, Base, get_db, get_database_info
from models import Concursante, Competicion, Levantamiento, Club
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
    if request is not None:
        if "x-admin-key" in request.headers:
            key = request.headers.get("x-admin-key")
        elif request.query_params.get("admin_key"):
            key = request.query_params.get("admin_key")

    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Operación no autorizada")


def calculate_categoria_peso(peso_corporal: float) -> str:
    categories = [59, 66, 74, 83, 93, 105, 120]
    for category in categories:
        if peso_corporal <= category:
            return str(category)
    return "+120"


def resolve_team_id(db: Session, team_name: str | None):
    if not team_name:
        return None

    normalized = team_name.strip()
    if not normalized:
        return None

    existing = db.query(Club).filter(Club.nombre.ilike(normalized)).first()
    if existing:
        return existing.id

    new_team = Club(nombre=normalized)
    db.add(new_team)
    db.flush()
    return new_team.id

# ==================== RUTAS CONCURSANTES ====================

@app.get("/api/concursantes")
def get_concursantes(db: Session = Depends(get_db)):
    """Obtener todos los concursantes"""
    return db.query(Concursante).all()

@app.post("/api/concursantes", response_model=ConcursanteSchema)
def create_concursante(concursante: ConcursanteCreate, db: Session = Depends(get_db), request: Request = None):
    """Crear un nuevo concursante"""
    payload = concursante.model_dump() if hasattr(concursante, "model_dump") else concursante.dict()

    nombre = (payload.get("nombre") or "").strip()
    peso_corporal = float(payload.get("peso_corporal") or 0)
    sexo = (payload.get("sexo") or "").strip()
    team_name = (payload.get("club") or "").strip()
    birth_year = payload.get("ano_inicio") or payload.get("ano_nacimiento")

    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    if peso_corporal <= 0:
        raise HTTPException(status_code=400, detail="Peso corporal requerido")
    if not sexo:
        raise HTTPException(status_code=400, detail="Sexo requerido")

    db_concursante = db.query(Concursante).filter(
        Concursante.nombre == nombre
    ).first()
    if db_concursante:
        raise HTTPException(status_code=400, detail="Concursante ya existe")

    if ADMIN_KEY:
        check_admin(request)

    team_id = resolve_team_id(db, team_name)
    edad = None
    if birth_year:
        try:
            edad = datetime.utcnow().year - int(birth_year)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Año de nacimiento inválido")

    payload.update({
        "nombre": nombre,
        "peso_corporal": peso_corporal,
        "sexo": sexo,
        "categoria_peso": calculate_categoria_peso(peso_corporal),
        "edad": edad if edad is not None else payload.get("edad") or 0,
        "club": team_name or None,
        "team_id": team_id,
        "ano_inicio": int(birth_year) if birth_year is not None and str(birth_year).strip() != "" else None,
    })

    new_concursante = Concursante(**payload)
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

    payload = concursante.model_dump() if hasattr(concursante, "model_dump") else concursante.dict()
    nombre = (payload.get("nombre") or "").strip()
    peso_corporal = float(payload.get("peso_corporal") or 0)
    sexo = (payload.get("sexo") or "").strip()
    team_name = (payload.get("club") or "").strip()
    birth_year = payload.get("ano_inicio") or payload.get("ano_nacimiento")

    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    if peso_corporal <= 0:
        raise HTTPException(status_code=400, detail="Peso corporal requerido")
    if not sexo:
        raise HTTPException(status_code=400, detail="Sexo requerido")

    team_id = resolve_team_id(db, team_name)
    edad = None
    if birth_year:
        try:
            edad = datetime.utcnow().year - int(birth_year)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Año de nacimiento inválido")

    db_concursante.nombre = nombre
    db_concursante.peso_corporal = peso_corporal
    db_concursante.sexo = sexo
    db_concursante.categoria_peso = calculate_categoria_peso(peso_corporal)
    db_concursante.edad = edad if edad is not None else db_concursante.edad
    db_concursante.club = team_name or None
    db_concursante.team_id = team_id
    db_concursante.ano_inicio = int(birth_year) if birth_year is not None and str(birth_year).strip() != "" else None
    
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

    payload = competicion.model_dump() if hasattr(competicion, "model_dump") else competicion.dict()
    new_competicion = Competicion(**payload)
    db.add(new_competicion)
    db.commit()
    db.refresh(new_competicion)
    return new_competicion


# ==================== RUTAS EQUIPOS ====================

@app.get("/api/equipos", response_model=list[dict])
def get_equipos(db: Session = Depends(get_db)):
    """Obtener todos los equipos"""
    equipos = db.query(Club).all()
    result = []
    for e in equipos:
        result.append({
            "id": e.id,
            "nombre": e.nombre,
            "descripcion": e.descripcion,
            "miembros_count": len(e.concursantes)
        })
    return result


@app.get("/api/equipos/{equipo_id}")
def get_equipo(equipo_id: int, db: Session = Depends(get_db)):
    db_equipo = db.query(Club).filter(Club.id == equipo_id).first()
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
            } for m in db_equipo.concursantes
        ]
    }


@app.get("/api/equipos/{equipo_id}/atletas")
def get_equipo_atletas(equipo_id: int, db: Session = Depends(get_db)):
    db_equipo = db.query(Club).filter(Club.id == equipo_id).first()
    if not db_equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return db_equipo.concursantes


@app.get("/api/equipos/{equipo_id}/competiciones")
def get_competiciones_equipo(equipo_id: int, db: Session = Depends(get_db)):
    """Obtener competiciones en las que participó algún miembro del equipo"""
    db_equipo = db.query(Club).filter(Club.id == equipo_id).first()
    if not db_equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    miembro_ids = [m.id for m in db_equipo.concursantes]
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
    existing = db.query(Club).filter(Club.nombre == nombre).first()
    if existing:
        raise HTTPException(status_code=400, detail="Equipo ya existe")
    new_equipo = Club(nombre=nombre, descripcion=descripcion)
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
                "peso_corporal": l.concursante.peso_corporal,
                "sexo": l.concursante.sexo,
                "categoria_peso": l.concursante.categoria_peso,
                "photo_url": l.concursante.photo_url,
                "team": l.concursante.team.nombre if l.concursante.team else None,
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
                "peso_corporal": l.concursante.peso_corporal,
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
        "levantamientos": levantamientos,
        "atletas": atletas_ordenados,
        "top_levantamientos": sorted(levantamientos, key=lambda item: item["ipf_score"], reverse=True),
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
    if ADMIN_KEY:
        check_admin(request)

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

    sentadilla_best = float(getattr(levantamiento, "sentadilla", None) or 0.0)
    press_banca_best = float(getattr(levantamiento, "press_banca", None) or 0.0)
    peso_muerto_best = float(getattr(levantamiento, "peso_muerto", None) or 0.0)

    total = sentadilla_best + press_banca_best + peso_muerto_best
    ipf_score = calculate_ipf_points(
        total,
        db_concursante.categoria_peso,
        db_concursante.sexo
    )

    payload = levantamiento.model_dump() if hasattr(levantamiento, "model_dump") else levantamiento.dict()
    payload.update({
        "sentadilla": sentadilla_best,
        "press_banca": press_banca_best,
        "peso_muerto": peso_muerto_best,
        "ipf_score": ipf_score
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

    sentadilla_best = float(getattr(levantamiento, "sentadilla", None) or 0.0)
    press_banca_best = float(getattr(levantamiento, "press_banca", None) or 0.0)
    peso_muerto_best = float(getattr(levantamiento, "peso_muerto", None) or 0.0)

    total = sentadilla_best + press_banca_best + peso_muerto_best
    ipf_score = calculate_ipf_points(total, db_concursante.categoria_peso, db_concursante.sexo)

    db_levantamiento.concursante_id = levantamiento.concursante_id
    db_levantamiento.competicion_id = levantamiento.competicion_id
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


@app.get("/api/health/db")
def health_db():
    """Diagnostico no sensible de conexion a BD para validar persistencia en despliegue."""
    return get_database_info()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
