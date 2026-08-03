from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class LevantamientoBase(BaseModel):
    concursante_id: int
    competicion_id: Optional[int] = None
    sentadilla: Optional[float] = None
    press_banca: Optional[float] = None
    peso_muerto: Optional[float] = None

class LevantamientoCreate(LevantamientoBase):
    pass

class Levantamiento(LevantamientoBase):
    id: int
    sentadilla: float = 0
    press_banca: float = 0
    peso_muerto: float = 0
    ipf_score: float
    fecha_levantamiento: datetime

    class Config:
        from_attributes = True

class ConcursanteBase(BaseModel):
    nombre: str
    peso_corporal: float
    sexo: str
    club: Optional[str] = None
    ano_inicio: Optional[int] = None
    edad: Optional[int] = None
    categoria_peso: Optional[str] = None
    team_id: Optional[int] = None

class ConcursanteCreate(ConcursanteBase):
    pass

class Concursante(ConcursanteBase):
    id: int
    fecha_registro: datetime
    levantamientos: List[Levantamiento] = []
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
