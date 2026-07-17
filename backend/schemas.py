from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class LevantamientoBase(BaseModel):
    concursante_id: int
    competicion_id: Optional[int] = None
    # Intentos (pueden ser None si se falló el intento)
    sentadilla_1: Optional[float] = None
    sentadilla_2: Optional[float] = None
    sentadilla_3: Optional[float] = None

    press_banca_1: Optional[float] = None
    press_banca_2: Optional[float] = None
    press_banca_3: Optional[float] = None

    peso_muerto_1: Optional[float] = None
    peso_muerto_2: Optional[float] = None
    peso_muerto_3: Optional[float] = None
    # Compatibilidad: también permitimos enviar directamente el mejor levantamiento
    sentadilla: Optional[float] = None
    press_banca: Optional[float] = None
    peso_muerto: Optional[float] = None

class LevantamientoCreate(LevantamientoBase):
    pass

class Levantamiento(LevantamientoBase):
    id: int
    # Campos calculados
    sentadilla: float
    press_banca: float
    peso_muerto: float
    ipf_score: float
    fecha_levantamiento: datetime
    
    class Config:
        from_attributes = True

class ConcursanteBase(BaseModel):
    nombre: str
    edad: int
    peso_corporal: float
    sexo: str
    categoria_peso: str
    club: str
    ciudad: str
    team_id: Optional[int] = None
    ano_inicio: int

class ConcursanteCreate(ConcursanteBase):
    pass

class Concursante(ConcursanteBase):
    id: int
    fecha_registro: datetime
    levantamientos: List[Levantamiento] = []
    photo_url: Optional[str] = None
    team: Optional[dict] = None
    
    class Config:
        from_attributes = True

class CompeticionBase(BaseModel):
    nombre: str
    fecha: datetime
    ubicacion: str
    descripcion: Optional[str] = None

class CompeticionCreate(CompeticionBase):
    pass

class Competicion(CompeticionBase):
    id: int
    levantamientos: List[Levantamiento] = []
    
    class Config:
        from_attributes = True


class EquipoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class EquipoCreate(EquipoBase):
    pass


class Equipo(EquipoBase):
    id: int
    miembros: List[Concursante] = []

    class Config:
        from_attributes = True
