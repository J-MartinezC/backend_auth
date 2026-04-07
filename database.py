import os
import json
import pymysql
from pymysql import MySQLError

from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv() # Carga las variables del archivo .env

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')
DB_NAME = os.getenv('DB_NAME', 'bd_sistema_reserva')
DB_PORT = int(os.getenv('DB_PORT', '3306'))


def _connect_without_db():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=True,
    )


def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False,
    )


def init_db() -> None:
    server_connection = _connect_without_db()
    try:
        with server_connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{DB_NAME}`')
    finally:
        server_connection.close()

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    id INT NOT NULL AUTO_INCREMENT,
                    nombre VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    CONSTRAINT users_pk PRIMARY KEY (id),
                    CONSTRAINT users__nombre__un UNIQUE (nombre)
                )
                '''
            )

            # Migrate legacy schemas (username/password) to current schema.
            cursor.execute('SHOW COLUMNS FROM users')
            columns = {row['Field'] for row in cursor.fetchall()}

            if 'nombre' not in columns and 'username' in columns:
                cursor.execute(
                    'ALTER TABLE users CHANGE COLUMN username nombre VARCHAR(255) NOT NULL'
                )
                columns.remove('username')
                columns.add('nombre')

            if 'password_hash' not in columns and 'password' in columns:
                cursor.execute(
                    'ALTER TABLE users CHANGE COLUMN password password_hash VARCHAR(255) NOT NULL'
                )
                columns.remove('password')
                columns.add('password_hash')

            if 'nombre' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN nombre VARCHAR(255) NOT NULL')

            if 'password_hash' not in columns:
                cursor.execute(
                    'ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ""'
                )

            # Keep older environments compatible when constraint names differ.
            cursor.execute('SHOW INDEX FROM users WHERE Key_name = "users__nombre__un"')
            if cursor.fetchone() is None:
                try:
                    cursor.execute(
                        'ALTER TABLE users ADD CONSTRAINT users__nombre__un UNIQUE (nombre)'
                    )
                except MySQLError:
                    pass

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS salones (
                    id INT NOT NULL AUTO_INCREMENT,
                    nombre VARCHAR(255) NOT NULL,
                    zona VARCHAR(100) NOT NULL,
                    capacidad INT NOT NULL,
                    precio DECIMAL(10, 2) NOT NULL,
                    tipo VARCHAR(20) NOT NULL,
                    disponible TINYINT(1) NOT NULL DEFAULT 1,
                    calificacion DECIMAL(2, 1),
                    distancia_km DECIMAL(5, 2),
                    CONSTRAINT salones_pk PRIMARY KEY (id),
                    CONSTRAINT salones__capacidad__ck CHECK (capacidad > 0),
                    CONSTRAINT salones__precio__ck CHECK (precio >= 0),
                    CONSTRAINT salones__tipo__ck CHECK (
                        tipo = 'Fiestas'
                        OR tipo = 'Corporativo'
                        OR tipo = 'Conferencias'
                        OR tipo = 'Reuniones'
                    ),
                    CONSTRAINT salones__disponible__ck CHECK (disponible = 0 OR disponible = 1),
                    CONSTRAINT salones__calificacion__ck CHECK (calificacion >= 0 AND calificacion <= 5)
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS salon_badges (
                    id INT NOT NULL AUTO_INCREMENT,
                    salon_id INT NOT NULL,
                    badge VARCHAR(100) NOT NULL,
                    CONSTRAINT salon_badges_pk PRIMARY KEY (id),
                    CONSTRAINT salon_badges__salon_id__fk
                        FOREIGN KEY (salon_id) REFERENCES salones(id)
                        ON DELETE RESTRICT
                )
                '''
            )

            cursor.execute('SELECT COUNT(*) AS total FROM salones')
            salons_count = cursor.fetchone()['total']
            if salons_count == 0:
                seed_salons = [
                    (
                        'Salon Caribe',
                        'Bocagrande',
                        80,
                        500000,
                        'Fiestas',
                        True,
                        4.9,
                        1.8,
                    ),
                    (
                        'Salon Ejecutivo',
                        'Centro',
                        50,
                        350000,
                        'Corporativo',
                        True,
                        4.7,
                        2.3,
                    ),
                    (
                        'Salon Vista Mar',
                        'Castillogrande',
                        120,
                        800000,
                        'Fiestas',
                        False,
                        4.8,
                        3.5,
                    ),
                    (
                        'Salon Bolivar',
                        'Manga',
                        60,
                        450000,
                        'Conferencias',
                        True,
                        4.6,
                        1.2,
                    ),
                    (
                        'Salon Premier',
                        'Zona Norte',
                        200,
                        1200000,
                        'Fiestas',
                        False,
                        4.5,
                        6.4,
                    ),
                ]
                cursor.executemany(
                    '''
                    INSERT INTO salones (
                        nombre,
                        zona,
                        capacidad,
                        precio,
                        tipo,
                        disponible,
                        calificacion,
                        distancia_km
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    seed_salons,
                )

                seed_badges = [
                    (1, 'Confirmación inmediata'),
                    (1, 'Mas reservado'),
                    (2, 'Mejor precio'),
                    (3, 'Ultimos cupos'),
                    (4, 'Disponible hoy'),
                    (5, 'Premium'),
                ]
                cursor.executemany(
                    'INSERT INTO salon_badges (salon_id, badge) VALUES (%s, %s)',
                    seed_badges,
                )

            # Migrate legacy salones.badges JSON column to salon_badges table if present.
            cursor.execute(
                '''
                SELECT COUNT(*) AS total
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'salones'
                  AND column_name = 'badges'
                ''',
                (DB_NAME,),
            )
            has_legacy_badges_column = int(cursor.fetchone()['total']) > 0

            if has_legacy_badges_column:
                cursor.execute('SELECT COUNT(*) AS total FROM salon_badges')
                badges_count = int(cursor.fetchone()['total'])

                if badges_count == 0:
                    cursor.execute('SELECT id, badges FROM salones')
                    rows = cursor.fetchall()
                    migrated_badges: list[tuple[int, str]] = []

                    for row in rows:
                        salon_id = int(row['id'])
                        raw_badges = row.get('badges')
                        parsed_badges: list[str]

                        if isinstance(raw_badges, str) and raw_badges.strip():
                            try:
                                loaded = json.loads(raw_badges)
                                if isinstance(loaded, list):
                                    parsed_badges = [str(item).strip() for item in loaded]
                                else:
                                    parsed_badges = [str(loaded).strip()]
                            except json.JSONDecodeError:
                                parsed_badges = [raw_badges.strip()]
                        else:
                            parsed_badges = []

                        for badge in parsed_badges:
                            if badge:
                                migrated_badges.append((salon_id, badge))

                    if migrated_badges:
                        cursor.executemany(
                            'INSERT INTO salon_badges (salon_id, badge) VALUES (%s, %s)',
                            migrated_badges,
                        )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS reservas (
                    id INT NOT NULL AUTO_INCREMENT,
                    codigo VARCHAR(20) NOT NULL,
                    usuario_id INT NOT NULL,
                    salon_id INT NOT NULL,
                    fecha DATE NOT NULL,
                    hora VARCHAR(12) NOT NULL,
                    asistentes INT NOT NULL,
                    notas TEXT,
                    estado VARCHAR(20) NOT NULL DEFAULT 'Confirmada',
                    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT reservas_pk PRIMARY KEY (id),
                    CONSTRAINT reservas__codigo__un UNIQUE (codigo),
                    CONSTRAINT reservas__asistentes__ck CHECK (asistentes > 0),
                    CONSTRAINT reservas__hora__ck CHECK (
                        hora = 'Mañana' OR hora = 'Tarde' OR hora = 'Noche'
                    ),
                    CONSTRAINT reservas__estado__ck CHECK (
                        estado = 'Confirmada' OR estado = 'Cancelada' OR estado = 'Pendiente'
                    ),
                    CONSTRAINT reservas__usuario_id__fk
                        FOREIGN KEY (usuario_id) REFERENCES users(id)
                        ON DELETE RESTRICT,
                    CONSTRAINT reservas__salon_id__fk
                        FOREIGN KEY (salon_id) REFERENCES salones(id)
                        ON DELETE RESTRICT
                )
                '''
            )
        connection.commit()
    finally:
        connection.close()
