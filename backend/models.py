from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from database import Base

class Concursante(Base):
    __tablename__ = "concursantes"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    edad = Column(Integer)
    peso_corporal = Column(Float)  # en kg
    sexo = Column(String)  # M/F
    categoria_peso = Column(String)  # ej: 59kg, 66kg, 74kg, etc
    club = Column(String)
    ciudad = Column(String)
    team_id = Column(Integer, ForeignKey("equipos.id"), nullable=True)
    ano_inicio = Column(Integer)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    photo_filename = Column(String, nullable=True)
    
    # Relación con levantamientos
    levantamientos = relationship("Levantamiento", back_populates="concursante", cascade="all, delete-orphan")
    team = relationship("Equipo", back_populates="miembros")
    
    @hybrid_property
    def photo_url(self):
        if self.photo_filename:
            return f"/static/photos/{self.photo_filename}"
        return None

    @hybrid_property
    def photo_url(self):
        if self.photo_filename:
            return f"/static/photos/{self.photo_filename}"
        return None

class Competicion(Base):
    __tablename__ = "competiciones"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    fecha = Column(DateTime)
    ubicacion = Column(String)
    descripcion = Column(String)
    
    # Relación con levantamientos
    levantamientos = relationship("Levantamiento", back_populates="competicion", cascade="all, delete-orphan")


class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    descripcion = Column(String, nullable=True)

    miembros = relationship("Concursante", back_populates="team")

class Levantamiento(Base):
    __tablename__ = "levantamientos"
    
    id = Column(Integer, primary_key=True, index=True)
    concursante_id = Column(Integer, ForeignKey("concursantes.id"))
    competicion_id = Column(Integer, ForeignKey("competiciones.id"))
    
    # Intentos (hasta 3) por movimiento
    sentadilla_1 = Column(Float, nullable=True)
    sentadilla_2 = Column(Float, nullable=True)
    sentadilla_3 = Column(Float, nullable=True)

    press_banca_1 = Column(Float, nullable=True)
    press_banca_2 = Column(Float, nullable=True)
    press_banca_3 = Column(Float, nullable=True)

    peso_muerto_1 = Column(Float, nullable=True)
    peso_muerto_2 = Column(Float, nullable=True)
    peso_muerto_3 = Column(Float, nullable=True)

    # Mejores levantamientos por movimiento (calculados)
    sentadilla = Column(Float, default=0.0)  # en kg
    press_banca = Column(Float, default=0.0)  # en kg
    peso_muerto = Column(Float, default=0.0)  # en kg
    
    # Score IPF (se calcula)
    ipf_score = Column(Float, default=0)
    
    fecha_levantamiento = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    concursante = relationship("Concursante", back_populates="levantamientos")
    competicion = relationship("Competicion", back_populates="levantamientos")
