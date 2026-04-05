import os
import json
import pymysql

from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv() # Carga las variables del archivo .env

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')
DB_NAME = os.getenv('DB_NAME', 'auth_db')
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
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            cursor.execute('SHOW INDEX FROM users WHERE Key_name = "uq_users_nombre"')
            if cursor.fetchone() is None:
                cursor.execute('ALTER TABLE users ADD UNIQUE KEY uq_users_nombre (nombre)')

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS salones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(120) NOT NULL,
                    zona VARCHAR(120) NOT NULL,
                    capacidad INT NOT NULL,
                    precio INT NOT NULL,
                    tipo VARCHAR(30) NOT NULL,
                    disponible BOOLEAN NOT NULL DEFAULT TRUE,
                    calificacion DECIMAL(3, 2) NOT NULL,
                    distancia_km DECIMAL(6, 2) NOT NULL,
                    badges TEXT NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                        json.dumps(['Confirmación inmediata', 'Mas reservado']),
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
                        json.dumps(['Mejor precio']),
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
                        json.dumps(['Ultimos cupos']),
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
                        json.dumps(['Disponible hoy']),
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
                        json.dumps(['Premium']),
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
                        distancia_km,
                        badges
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    seed_salons,
                )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS reservas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    codigo VARCHAR(20) UNIQUE,
                    usuario_id INT NOT NULL,
                    salon_id INT NOT NULL,
                    fecha DATE NOT NULL,
                    hora VARCHAR(12) NOT NULL,
                    asistentes INT NOT NULL,
                    notas TEXT,
                    estado VARCHAR(20) NOT NULL DEFAULT 'Confirmada',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_reservas_usuario_id (usuario_id),
                    INDEX idx_reservas_salon_id (salon_id),
                    CONSTRAINT fk_reservas_usuario
                        FOREIGN KEY (usuario_id) REFERENCES users(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_reservas_salon
                        FOREIGN KEY (salon_id) REFERENCES salones(id)
                        ON DELETE CASCADE
                )
                '''
            )
        connection.commit()
    finally:
        connection.close()
