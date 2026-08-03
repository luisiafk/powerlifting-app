from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from database import Base


class Concursante(Base):
    __tablename__ = "concursantes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    edad = Column(Integer, nullable=False)
    peso_corporal = Column(Float, nullable=False)
    sexo = Column(String, nullable=False)
    categoria_peso = Column(String, nullable=False)
    club = Column(String, nullable=True)
    ciudad = Column(String, nullable=True)
    ano_inicio = Column(Integer, nullable=True)
    team_id = Column(Integer, ForeignKey("clubs.id"), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    levantamientos = relationship(
        "Levantamiento",
        back_populates="concursante",
        cascade="all, delete-orphan",
    )
    team = relationship("Club", back_populates="concursantes")


class Competicion(Base):
    __tablename__ = "competiciones"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True, nullable=False)
    fecha = Column(DateTime, nullable=False)
    ubicacion = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)

    levantamientos = relationship(
        "Levantamiento",
        back_populates="competicion",
        cascade="all, delete-orphan",
    )


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)
    descripcion = Column(String, nullable=True)

    concursantes = relationship("Concursante", back_populates="team")


class Levantamiento(Base):
    __tablename__ = "levantamientos"

    id = Column(Integer, primary_key=True, index=True)
    concursante_id = Column(Integer, ForeignKey("concursantes.id"), nullable=False)
    competicion_id = Column(Integer, ForeignKey("competiciones.id"), nullable=True)

    sentadilla = Column(Float, default=0.0)
    press_banca = Column(Float, default=0.0)
    peso_muerto = Column(Float, default=0.0)
    ipf_score = Column(Float, default=0.0)
    fecha_levantamiento = Column(DateTime, default=datetime.utcnow)

    concursante = relationship("Concursante", back_populates="levantamientos")
    competicion = relationship("Competicion", back_populates="levantamientos")
