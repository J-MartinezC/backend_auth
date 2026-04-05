from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class UsuarioAuth(BaseModel):
    usuario: str = Field(min_length=1)
    password: str = Field(min_length=6)


class Usuario(BaseModel):
    id: int | None = None
    nombre: str
    password_hash: str
    creado_en: datetime | None = None


class SalonOut(BaseModel):
    id: int
    nombre: str
    zona: str
    capacidad: int
    precio: int
    tipo: Literal['Fiestas', 'Corporativo', 'Conferencias', 'Reuniones']
    disponible: bool
    calificacion: float
    distancia_km: float
    badges: list[str]


class ReservaCreate(BaseModel):
    salon_id: int = Field(gt=0)
    fecha: date
    hora: Literal['Mañana', 'Tarde', 'Noche']
    asistentes: int = Field(gt=0)
    notas: str | None = None


class ReservaOut(BaseModel):
    id: int
    codigo: str
    salon_id: int
    fecha: date
    hora: str
    asistentes: int
    notas: str | None = None


class ReservaHistorialOut(BaseModel):
    id: int
    codigo: str
    salon_id: int
    salon: str
    fecha: date
    hora: str
    asistentes: int
    estado: str
    precio: int
    notas: str | None = None
    creado_en: datetime
