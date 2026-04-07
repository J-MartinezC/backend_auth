from fastapi import APIRouter, Depends, HTTPException

from database import get_db_connection
from models import ReservaCreate, ReservaHistorialOut, ReservaOut, SalonOut
from utils.security import get_current_user

router = APIRouter()


@router.get('/salones', response_model=list[SalonOut])
def listar_salones():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT
                    s.id,
                    s.nombre,
                    s.zona,
                    s.capacidad,
                    s.precio,
                    s.tipo,
                    s.disponible,
                    s.calificacion,
                    s.distancia_km,
                    GROUP_CONCAT(sb.badge ORDER BY sb.id SEPARATOR '||') AS badges_concat
                FROM salones s
                LEFT JOIN salon_badges sb ON sb.salon_id = s.id
                GROUP BY
                    s.id,
                    s.nombre,
                    s.zona,
                    s.capacidad,
                    s.precio,
                    s.tipo,
                    s.disponible,
                    s.calificacion,
                    s.distancia_km
                ORDER BY s.calificacion DESC, s.id ASC
                '''
            )
            rows = cursor.fetchall()

        response: list[SalonOut] = []
        for row in rows:
            raw_badges = row.get('badges_concat')
            badges = []
            if isinstance(raw_badges, str) and raw_badges.strip():
                badges = [badge for badge in raw_badges.split('||') if badge]

            calificacion_raw = row.get('calificacion')
            distancia_raw = row.get('distancia_km')

            response.append(
                SalonOut(
                    id=int(row['id']),
                    nombre=row['nombre'],
                    zona=row['zona'],
                    capacidad=int(row['capacidad']),
                    precio=int(float(row['precio'])),
                    tipo=row['tipo'],
                    disponible=bool(row['disponible']),
                    calificacion=float(calificacion_raw) if calificacion_raw is not None else 0.0,
                    distancia_km=float(distancia_raw) if distancia_raw is not None else 0.0,
                    badges=[str(badge) for badge in badges],
                )
            )

        return response
    finally:
        connection.close()


@router.post('/reservas', response_model=ReservaOut)
def crear_reserva(data: ReservaCreate, user: dict = Depends(get_current_user)):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id, capacidad, disponible FROM salones WHERE id = %s',
                (data.salon_id,),
            )
            salon = cursor.fetchone()

            if salon is None:
                raise HTTPException(status_code=404, detail='Salon no encontrado')

            if not bool(salon['disponible']):
                raise HTTPException(status_code=400, detail='El salon no esta disponible')

            if data.asistentes > int(salon['capacidad']):
                raise HTTPException(
                    status_code=400,
                    detail='El numero de asistentes supera la capacidad del salon',
                )

            cursor.execute(
                '''
                INSERT INTO reservas (usuario_id, salon_id, fecha, hora, asistentes, notas)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    int(user['user_id']),
                    data.salon_id,
                    data.fecha,
                    data.hora,
                    data.asistentes,
                    data.notas,
                ),
            )
            reserva_id = int(cursor.lastrowid)
            codigo = f'RES-{reserva_id:03d}'

            cursor.execute(
                'UPDATE reservas SET codigo = %s WHERE id = %s',
                (codigo, reserva_id),
            )

        connection.commit()

        return ReservaOut(
            id=reserva_id,
            codigo=codigo,
            salon_id=data.salon_id,
            fecha=data.fecha,
            hora=data.hora,
            asistentes=data.asistentes,
            notas=data.notas,
        )
    finally:
        connection.close()


@router.get('/reservas/mis', response_model=list[ReservaHistorialOut])
def listar_mis_reservas(user: dict = Depends(get_current_user)):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT
                    r.id,
                    COALESCE(r.codigo, CONCAT('RES-', LPAD(r.id, 3, '0'))) AS codigo,
                    r.salon_id,
                    s.nombre AS salon,
                    r.fecha,
                    r.hora,
                    r.asistentes,
                    r.estado,
                    s.precio,
                    r.notas,
                    r.creado_en
                FROM reservas r
                INNER JOIN salones s ON s.id = r.salon_id
                WHERE r.usuario_id = %s
                ORDER BY r.fecha DESC, r.id DESC
                ''',
                (int(user['user_id']),),
            )
            rows = cursor.fetchall()

        return [
            ReservaHistorialOut(
                id=int(row['id']),
                codigo=str(row['codigo']),
                salon_id=int(row['salon_id']),
                salon=str(row['salon']),
                fecha=row['fecha'],
                hora=str(row['hora']),
                asistentes=int(row['asistentes']),
                estado=str(row['estado']),
                precio=int(row['precio']),
                notas=row['notas'],
                creado_en=row['creado_en'],
            )
            for row in rows
        ]
    finally:
        connection.close()
