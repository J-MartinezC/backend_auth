from datetime import date
from uuid import uuid4

import pymysql
from fastapi import APIRouter, Depends, HTTPException

from database import get_db_connection
from models import CalificacionCreate, ReservaCreate, ReservaHistorialOut, ReservaOut, SalonOut
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
                    s.id_salon,
                    s.nombre,
                    s.zona,
                    s.nivel,
                    s.capacidad,
                    s.precio,
                    s.foto,
                    s.descripcion,
                    s.politicas,
                    s.estado,
                    s.id_categoria,
                    c.nombre AS categoria,
                    AVG(cal.cantidad) AS calificacion,
                    GROUP_CONCAT(
                        sb.badge ORDER BY sb.id_salon_badge SEPARATOR '||'
                    ) AS badges_concat,
                    GROUP_CONCAT(
                        sf.foto_url ORDER BY sf.id_salon_foto SEPARATOR '||'
                    ) AS fotos_concat
                FROM salones s
                INNER JOIN categorias c ON c.id_categoria = s.id_categoria
                LEFT JOIN salon_badges sb ON sb.id_salon = s.id_salon
                LEFT JOIN salon_fotos sf ON sf.id_salon = s.id_salon
                LEFT JOIN calificaciones cal ON cal.id_salon = s.id_salon
                WHERE s.estado = 1
                GROUP BY
                    s.id_salon,
                    s.nombre,
                    s.zona,
                    s.nivel,
                    s.capacidad,
                    s.precio,
                    s.foto,
                    s.descripcion,
                    s.politicas,
                    s.estado,
                    s.id_categoria,
                    c.nombre
                ORDER BY s.id_salon ASC
                '''
            )
            rows = cursor.fetchall()

        response: list[SalonOut] = []
        for row in rows:
            raw_badges = row.get('badges_concat')
            badges = []
            if isinstance(raw_badges, str) and raw_badges.strip():
                badges = [badge for badge in raw_badges.split('||') if badge]

            raw_fotos = row.get('fotos_concat')
            fotos = []
            if isinstance(raw_fotos, str) and raw_fotos.strip():
                fotos = [foto for foto in raw_fotos.split('||') if foto]

            calificacion_raw = row.get('calificacion')

            response.append(
                SalonOut(
                    id=int(row['id_salon']),
                    nombre=row['nombre'],
                    zona=row['zona'],
                    nivel=int(row['nivel']) if row['nivel'] is not None else None,
                    capacidad=int(row['capacidad']),
                    precio=float(row['precio']),
                    foto=row.get('foto'),
                    descripcion=row['descripcion'],
                    politicas=row.get('politicas'),
                    estado=bool(row['estado']),
                    categoria_id=int(row['id_categoria']),
                    categoria=row['categoria'],
                    calificacion=float(calificacion_raw) if calificacion_raw is not None else 0.0,
                    badges=[str(badge) for badge in badges],
                    fotos=[str(foto) for foto in fotos],
                )
            )

        return response
    finally:
        connection.close()


@router.get('/salones/{salon_id}', response_model=SalonOut)
def obtener_salon(salon_id: int):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT
                    s.id_salon,
                    s.nombre,
                    s.zona,
                    s.nivel,
                    s.capacidad,
                    s.precio,
                    s.foto,
                    s.descripcion,
                    s.politicas,
                    s.estado,
                    s.id_categoria,
                    c.nombre AS categoria,
                    AVG(cal.cantidad) AS calificacion,
                    GROUP_CONCAT(
                        sb.badge ORDER BY sb.id_salon_badge SEPARATOR '||'
                    ) AS badges_concat,
                    GROUP_CONCAT(
                        sf.foto_url ORDER BY sf.id_salon_foto SEPARATOR '||'
                    ) AS fotos_concat
                FROM salones s
                INNER JOIN categorias c ON c.id_categoria = s.id_categoria
                LEFT JOIN salon_badges sb ON sb.id_salon = s.id_salon
                LEFT JOIN salon_fotos sf ON sf.id_salon = s.id_salon
                LEFT JOIN calificaciones cal ON cal.id_salon = s.id_salon
                WHERE s.id_salon = %s
                GROUP BY
                    s.id_salon,
                    s.nombre,
                    s.zona,
                    s.nivel,
                    s.capacidad,
                    s.precio,
                    s.foto,
                    s.descripcion,
                    s.politicas,
                    s.estado,
                    s.id_categoria,
                    c.nombre
                ''',
                (salon_id,),
            )
            row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail='Salon no encontrado')

        raw_badges = row.get('badges_concat')
        badges = []
        if isinstance(raw_badges, str) and raw_badges.strip():
            badges = [badge for badge in raw_badges.split('||') if badge]

        raw_fotos = row.get('fotos_concat')
        fotos = []
        if isinstance(raw_fotos, str) and raw_fotos.strip():
            fotos = [foto for foto in raw_fotos.split('||') if foto]

        calificacion_raw = row.get('calificacion')

        return SalonOut(
            id=int(row['id_salon']),
            nombre=row['nombre'],
            zona=row['zona'],
            nivel=int(row['nivel']) if row['nivel'] is not None else None,
            capacidad=int(row['capacidad']),
            precio=float(row['precio']),
            foto=row.get('foto'),
            descripcion=row['descripcion'],
            politicas=row.get('politicas'),
            estado=bool(row['estado']),
            categoria_id=int(row['id_categoria']),
            categoria=row['categoria'],
            calificacion=float(calificacion_raw) if calificacion_raw is not None else 0.0,
            badges=[str(badge) for badge in badges],
            fotos=[str(foto) for foto in fotos],
        )
    finally:
        connection.close()


@router.post('/reservas', response_model=ReservaOut)
def crear_reserva(data: ReservaCreate, user: dict = Depends(get_current_user)):
    connection = get_db_connection()
    try:
        if data.fecha < date.today():
            raise HTTPException(status_code=400, detail='La fecha no puede ser en el pasado')
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT id_salon, capacidad, estado, precio
                FROM salones
                WHERE id_salon = %s
                ''',
                (data.salon_id,),
            )
            salon = cursor.fetchone()

            if salon is None:
                raise HTTPException(status_code=404, detail='Salon no encontrado')

            if not bool(salon['estado']):
                raise HTTPException(status_code=400, detail='El salon no esta disponible')

            if data.asistentes > int(salon['capacidad']):
                raise HTTPException(
                    status_code=400,
                    detail='El numero de asistentes supera la capacidad del salon',
                )

            cursor.execute(
                '''
                SELECT id_franja_horaria
                FROM franjas_horarias
                WHERE id_franja_horaria = %s AND estado = 1
                ''',
                (data.franja_horaria_id,),
            )
            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=400,
                    detail='Franja horaria no valida',
                )

            cursor.execute(
                '''
                SELECT id_periodo_cierre
                FROM periodos_cierre
                WHERE estado = 1 AND %s BETWEEN fecha_inicio AND fecha_fin
                ''',
                (data.fecha,),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=400,
                    detail='La fecha solicitada esta bloqueada',
                )

            if data.metodo_id is not None:
                cursor.execute(
                    '''
                    SELECT id_metodo
                    FROM metodos
                    WHERE id_metodo = %s AND estado = 1
                    ''',
                    (data.metodo_id,),
                )
                if cursor.fetchone() is None:
                    raise HTTPException(
                        status_code=400,
                        detail='Metodo de pago no valido',
                    )

            cursor.execute(
                '''
                SELECT id_reserva
                FROM reservas
                WHERE id_salon = %s AND fecha = %s AND id_franja_horaria = %s
                ''',
                (data.salon_id, data.fecha, data.franja_horaria_id),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=400,
                    detail='Ya existe una reserva para esa fecha y franja horaria',
                )

            subtotal = float(salon['precio'])
            descuento = float(data.descuento or 0)
            abono = float(data.abono or 0)
            monto = subtotal - descuento
            if monto < 0:
                raise HTTPException(
                    status_code=400,
                    detail='El descuento no puede ser mayor al subtotal',
                )
            if abono > monto:
                raise HTTPException(
                    status_code=400,
                    detail='El abono no puede ser mayor al monto',
                )

            codigo_temporal = f'TMP-{uuid4().hex[:12].upper()}'
            estado = 'Pendiente'

            cursor.execute(
                '''
                INSERT INTO reservas (
                    codigo,
                    subtotal,
                    descuento,
                    monto,
                    abono,
                    num_transaccion,
                    asistentes,
                    motivo,
                    garantia,
                    notas,
                    estado,
                    fecha,
                    id_salon,
                    id_usuario,
                    id_franja_horaria,
                    id_metodo
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ''',
                (
                    codigo_temporal,
                    subtotal,
                    descuento,
                    monto,
                    abono,
                    data.num_transaccion,
                    data.asistentes,
                    data.motivo,
                    data.garantia,
                    data.notas,
                    estado,
                    data.fecha,
                    data.salon_id,
                    int(user['user_id']),
                    data.franja_horaria_id,
                    data.metodo_id,
                ),
            )
            reserva_id = int(cursor.lastrowid)
            codigo = f'RES-{reserva_id:06d}'

            cursor.execute(
                'UPDATE reservas SET codigo = %s WHERE id_reserva = %s',
                (codigo, reserva_id),
            )

        connection.commit()

        return ReservaOut(
            id=reserva_id,
            codigo=codigo,
            salon_id=data.salon_id,
            fecha=data.fecha,
            franja_horaria_id=data.franja_horaria_id,
            asistentes=data.asistentes,
            estado=estado,
            subtotal=subtotal,
            descuento=descuento,
            monto=monto,
            abono=abono,
            notas=data.notas,
        )
    finally:
        connection.close()


@router.post('/salones/{salon_id}/calificaciones')
def crear_calificacion(
    salon_id: int,
    payload: CalificacionCreate,
    user: dict = Depends(get_current_user),
):
    comentario = payload.comentario.strip() if payload.comentario else None

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO calificaciones (cantidad, comentario, id_salon, id_usuario)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    cantidad = VALUES(cantidad),
                    comentario = VALUES(comentario),
                    fecha = CURRENT_TIMESTAMP
                ''',
                (
                    int(payload.cantidad),
                    comentario,
                    salon_id,
                    int(user['user_id']),
                ),
            )
            # After inserting/updating, return the new/existing rating for convenience
            cursor.execute(
                '''
                SELECT cantidad, comentario
                FROM calificaciones
                WHERE id_salon = %s AND id_usuario = %s
                ''',
                (salon_id, int(user['user_id'])),
            )
            row = cursor.fetchone()
        connection.commit()
        if row:
            return {'cantidad': int(row['cantidad']), 'comentario': row.get('comentario')}
        return {'success': True}
    except pymysql.MySQLError as exc:
        connection.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        connection.close()


@router.get('/salones/{salon_id}/calificaciones/mias')
def obtener_mi_calificacion(salon_id: int, user: dict = Depends(get_current_user)):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT cantidad, comentario
                FROM calificaciones
                WHERE id_salon = %s AND id_usuario = %s
                ''',
                (salon_id, int(user['user_id'])),
            )
            row = cursor.fetchone()

        if row:
            return {'cantidad': int(row['cantidad']), 'comentario': row.get('comentario')}
        return {}
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
                    r.id_reserva,
                    r.codigo,
                    r.id_salon,
                    s.nombre AS salon,
                    r.fecha,
                    fh.nombre AS franja_horaria,
                    r.asistentes,
                    r.estado,
                    r.monto,
                    r.abono,
                    r.notas,
                    r.creado_en
                FROM reservas r
                INNER JOIN salones s ON s.id_salon = r.id_salon
                INNER JOIN franjas_horarias fh
                    ON fh.id_franja_horaria = r.id_franja_horaria
                WHERE r.id_usuario = %s
                ORDER BY r.fecha DESC, r.id_reserva DESC
                ''',
                (int(user['user_id']),),
            )
            rows = cursor.fetchall()

            # No change to reservation listing

        return [
            ReservaHistorialOut(
                id=int(row['id_reserva']),
                codigo=str(row['codigo']),
                salon_id=int(row['id_salon']),
                salon=str(row['salon']),
                fecha=row['fecha'],
                franja_horaria=str(row['franja_horaria']),
                asistentes=int(row['asistentes']),
                estado=str(row['estado']),
                monto=float(row['monto']),
                abono=float(row['abono']),
                notas=row['notas'],
                creado_en=row['creado_en'],
            )
            for row in rows
        ]
    finally:
        connection.close()


@router.post('/reservas/{reserva_id}/cancelar')
def cancelar_reserva(reserva_id: int, user: dict = Depends(get_current_user)):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT id_reserva, estado, id_usuario
                FROM reservas
                WHERE id_reserva = %s
                ''',
                (reserva_id,),
            )
            reserva = cursor.fetchone()

            if reserva is None:
                raise HTTPException(status_code=404, detail='Reserva no encontrada')

            if int(reserva['id_usuario']) != int(user['user_id']):
                raise HTTPException(status_code=403, detail='No tienes permisos')

            estado = str(reserva['estado'])
            if estado not in ('Pendiente', 'Confirmada'):
                raise HTTPException(
                    status_code=400,
                    detail='La reserva no se puede cancelar',
                )

            cursor.execute(
                'UPDATE reservas SET estado = %s WHERE id_reserva = %s',
                ('Cancelada', reserva_id),
            )

        connection.commit()
        return {'success': True}
    finally:
        connection.close()
