import os
import pymysql
import ssl  # <- Importante para la seguridad de Aiven

from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()  # Carga variables locales si existen

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')
DB_NAME = os.getenv('DB_NAME', 'bd_sistema_reserva')
DB_PORT = int(os.getenv('DB_PORT', '3306'))


def get_db_connection():
    # Configuración SSL a prueba de fallos para la nube
    ssl_ctx = None
    if "aivencloud.com" in DB_HOST:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE  # Esto evita que Aiven bloquee la app por no tener el archivo ca.pem

    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False,
        ssl=ssl_ctx
    )

def init_db() -> None:
    # Pasamos directo a crear las tablas en la base de datos asignada
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id_usuario INT NOT NULL AUTO_INCREMENT,
                    identidad VARCHAR(100),
                    num_identidad VARCHAR(20),
                    nombre VARCHAR(150) NOT NULL,
                    apellido VARCHAR(150) NOT NULL,
                    usuario VARCHAR(50),
                    correo VARCHAR(150) NOT NULL,
                    telefono VARCHAR(30),
                    direccion TEXT,
                    clave VARCHAR(255) NOT NULL,
                    token VARCHAR(150),
                    verify BOOLEAN NOT NULL DEFAULT 0,
                    rol INT NOT NULL DEFAULT 1,
                    foto_url VARCHAR(255),
                    estado BOOLEAN NOT NULL DEFAULT 1,
                    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT usuarios_pk PRIMARY KEY (id_usuario),
                    CONSTRAINT usuarios__num_identidad__un UNIQUE (num_identidad),
                    CONSTRAINT usuarios__usuario__un UNIQUE (usuario),
                    CONSTRAINT usuarios__correo__un UNIQUE (correo),
                    CONSTRAINT usuarios__rol__ck CHECK (rol IN (1, 2, 3))
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS categorias (
                    id_categoria INT NOT NULL AUTO_INCREMENT,
                    nombre VARCHAR(100) NOT NULL,
                    estado BOOLEAN NOT NULL DEFAULT 1,
                    CONSTRAINT categorias_pk PRIMARY KEY (id_categoria),
                    CONSTRAINT categorias__nombre__un UNIQUE (nombre),
                    CONSTRAINT categorias__estado__ck CHECK (estado IN (0, 1))
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS salones (
                    id_salon INT NOT NULL AUTO_INCREMENT,
                    nombre VARCHAR(150) NOT NULL,
                    zona VARCHAR(100) NOT NULL,
                    nivel INT,
                    capacidad INT NOT NULL,
                    precio DECIMAL(10, 2) NOT NULL,
                    foto VARCHAR(255),
                    descripcion TEXT NOT NULL,
                    politicas TEXT,
                    estado BOOLEAN NOT NULL DEFAULT 1,
                    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    id_categoria INT NOT NULL,
                    CONSTRAINT salones_pk PRIMARY KEY (id_salon),
                    CONSTRAINT salones__nivel__ck CHECK (nivel > 0),
                    CONSTRAINT salones__capacidad__ck CHECK (capacidad > 0),
                    CONSTRAINT salones__precio__ck CHECK (precio >= 0),
                    CONSTRAINT salones__estado__ck CHECK (estado IN (0, 1)),
                    CONSTRAINT salones__id_categoria__fk
                        FOREIGN KEY (id_categoria)
                        REFERENCES categorias(id_categoria)
                        ON DELETE RESTRICT ON UPDATE CASCADE
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS salon_fotos (
                    id_salon_foto INT NOT NULL AUTO_INCREMENT,
                    id_salon INT NOT NULL,
                    foto_url VARCHAR(255) NOT NULL,
                    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT salon_fotos_pk PRIMARY KEY (id_salon_foto),
                    CONSTRAINT salon_fotos__salon__fk
                        FOREIGN KEY (id_salon)
                        REFERENCES salones(id_salon)
                        ON DELETE CASCADE ON UPDATE CASCADE
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS salon_badges (
                    id_salon_badge INT NOT NULL AUTO_INCREMENT,
                    id_salon INT NOT NULL,
                    badge VARCHAR(100) NOT NULL,
                    CONSTRAINT salon_badges_pk PRIMARY KEY (id_salon_badge),
                    CONSTRAINT salon_badges__salon__fk
                        FOREIGN KEY (id_salon)
                        REFERENCES salones(id_salon)
                        ON DELETE CASCADE ON UPDATE CASCADE
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS franjas_horarias (
                    id_franja_horaria INT NOT NULL AUTO_INCREMENT,
                    nombre VARCHAR(50) NOT NULL,
                    hora_inicio TIME NOT NULL,
                    hora_fin TIME NOT NULL,
                    estado BOOLEAN NOT NULL DEFAULT 1,
                    CONSTRAINT franjas_horarias_pk PRIMARY KEY (id_franja_horaria),
                    CONSTRAINT franjas_horarias__nombre__un UNIQUE (nombre),
                    CONSTRAINT franjas_horarias__hora__ck CHECK (hora_fin > hora_inicio),
                    CONSTRAINT franjas_horarias__estado__ck CHECK (estado IN (0, 1))
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS metodos (
                    id_metodo INT NOT NULL AUTO_INCREMENT,
                    nombre VARCHAR(100) NOT NULL,
                    estado BOOLEAN NOT NULL DEFAULT 1,
                    CONSTRAINT metodos_pk PRIMARY KEY (id_metodo),
                    CONSTRAINT metodos__nombre__un UNIQUE (nombre),
                    CONSTRAINT metodos__estado__ck CHECK (estado IN (0, 1))
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS usuarios_metodos (
                    id_usuario_metodo INT NOT NULL AUTO_INCREMENT,
                    id_usuario INT NOT NULL,
                    id_metodo INT NOT NULL,
                    alias VARCHAR(100),
                    numero VARCHAR(80),
                    estado BOOLEAN NOT NULL DEFAULT 1,
                    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT usuarios_metodos_pk PRIMARY KEY (id_usuario_metodo),
                    CONSTRAINT usuarios_metodos__estado__ck CHECK (estado IN (0, 1)),
                    CONSTRAINT usuarios_metodos__un UNIQUE (id_usuario, id_metodo, numero),
                    CONSTRAINT usuarios_metodos__id_usuario__fk
                        FOREIGN KEY (id_usuario)
                        REFERENCES usuarios(id_usuario)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT usuarios_metodos__id_metodo__fk
                        FOREIGN KEY (id_metodo)
                        REFERENCES metodos(id_metodo)
                        ON DELETE RESTRICT ON UPDATE CASCADE
                )
                '''
            )

            cursor.execute('SELECT COUNT(*) AS total FROM metodos')
            total_row = cursor.fetchone()
            if total_row and int(total_row['total']) == 0:
                cursor.executemany(
                    'INSERT INTO metodos (nombre, estado) VALUES (%s, 1)',
                    [
                        ('Tarjeta debito',),
                        ('Tarjeta credito',),
                        ('Nequi',),
                        ('Bancolombia',),
                        ('Daviplata',),
                        ('PSE',),
                    ],
                )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS reservas (
                    id_reserva INT NOT NULL AUTO_INCREMENT,
                    codigo VARCHAR(20) NOT NULL,
                    subtotal DECIMAL(10, 2) NOT NULL,
                    descuento DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    monto DECIMAL(10, 2) NOT NULL,
                    abono DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    num_transaccion VARCHAR(50),
                    asistentes INT NOT NULL,
                    motivo VARCHAR(255),
                    garantia VARCHAR(100),
                    notas TEXT,
                    estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
                    fecha DATE NOT NULL,
                    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    id_salon INT NOT NULL,
                    id_usuario INT NOT NULL,
                    id_franja_horaria INT NOT NULL,
                    id_metodo INT,
                    CONSTRAINT reservas_pk PRIMARY KEY (id_reserva),
                    CONSTRAINT reservas__codigo__un UNIQUE (codigo),
                    CONSTRAINT reservas__salon_fecha_id_franja_horaria__un
                        UNIQUE (id_salon, fecha, id_franja_horaria),
                    CONSTRAINT reservas__subtotal__ck CHECK (subtotal >= 0),
                    CONSTRAINT reservas__descuento__ck CHECK (descuento >= 0),
                    CONSTRAINT reservas__monto__ck CHECK (monto >= 0),
                    CONSTRAINT reservas__abono__ck CHECK (abono >= 0),
                    CONSTRAINT reservas__asistentes__ck CHECK (asistentes > 0),
                    CONSTRAINT reservas__estado__ck
                        CHECK (estado IN ('Pendiente', 'Confirmada', 'Cancelada')),
                    CONSTRAINT reservas__id_salon__fk
                        FOREIGN KEY (id_salon)
                        REFERENCES salones(id_salon)
                        ON DELETE RESTRICT ON UPDATE CASCADE,
                    CONSTRAINT reservas__id_usuario__fk
                        FOREIGN KEY (id_usuario)
                        REFERENCES usuarios(id_usuario)
                        ON DELETE RESTRICT ON UPDATE CASCADE,
                    CONSTRAINT reservas__id_franja_horaria__fk
                        FOREIGN KEY (id_franja_horaria)
                        REFERENCES franjas_horarias(id_franja_horaria)
                        ON DELETE RESTRICT ON UPDATE CASCADE,
                    CONSTRAINT reservas__id_metodo__fk
                        FOREIGN KEY (id_metodo)
                        REFERENCES metodos(id_metodo)
                        ON DELETE SET NULL ON UPDATE CASCADE
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS calificaciones (
                    id_calificacion INT NOT NULL AUTO_INCREMENT,
                    cantidad INT NOT NULL,
                    comentario TEXT,
                    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    id_salon INT NOT NULL,
                    id_usuario INT NOT NULL,
                    CONSTRAINT calificacion_pk PRIMARY KEY (id_calificacion),
                    CONSTRAINT calificaciones__salon_usuario__un
                        UNIQUE (id_salon, id_usuario),
                    CONSTRAINT calificaciones__cantidad__ck
                        CHECK (cantidad >= 1 AND cantidad <= 5),
                    CONSTRAINT calificaciones__id_salon__fk
                        FOREIGN KEY (id_salon)
                        REFERENCES salones(id_salon)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    CONSTRAINT calificaciones__id_usuario__fk
                        FOREIGN KEY (id_usuario)
                        REFERENCES usuarios(id_usuario)
                        ON DELETE CASCADE ON UPDATE CASCADE
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS empresa (
                    NIT VARCHAR(50) NOT NULL,
                    nombre VARCHAR(255) NOT NULL,
                    telefono VARCHAR(30) NOT NULL,
                    direccion VARCHAR(255) NOT NULL,
                    correo VARCHAR(150) NOT NULL,
                    mensaje TEXT NOT NULL,
                    politicas TEXT,
                    facebook VARCHAR(255),
                    twitter VARCHAR(255),
                    instagram VARCHAR(255),
                    whatsapp VARCHAR(50) NOT NULL,
                    CONSTRAINT empresa_pk PRIMARY KEY (NIT)
                )
                '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS periodos_cierre (
                    id_periodo_cierre INT NOT NULL AUTO_INCREMENT,
                    fecha_inicio DATE NOT NULL,
                    fecha_fin DATE NOT NULL,
                    motivo TEXT,
                    estado BOOLEAN NOT NULL DEFAULT 1,
                    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT periodos_cierre_pk PRIMARY KEY (id_periodo_cierre),
                    CONSTRAINT periodos_cierre__fechas__ck
                        CHECK (fecha_fin >= fecha_inicio),
                    CONSTRAINT periodos_cierre__estado__ck CHECK (estado IN (0, 1))
                )
                '''
            )
        connection.commit()
    finally:
        connection.close()
