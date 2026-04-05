from fastapi import APIRouter, HTTPException

from database import get_db_connection
from models import UsuarioAuth
from utils.security import create_access_token, get_password_hash, verify_password

router = APIRouter()


@router.post('/registro')
def registro(data: UsuarioAuth):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM users WHERE nombre = %s',
                (data.usuario,),
            )
            existing = cursor.fetchone()
            if existing:
                raise HTTPException(status_code=400, detail='El usuario ya existe')

            password_hash = get_password_hash(data.password)
            cursor.execute(
                'INSERT INTO users (nombre, password_hash) VALUES (%s, %s)',
                (data.usuario, password_hash),
            )
        connection.commit()

        return {'success': True, 'message': 'Usuario creado exitosamente'}
    finally:
        connection.close()


@router.post('/login')
def login(data: UsuarioAuth):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id, nombre, password_hash FROM users WHERE nombre = %s',
                (data.usuario,),
            )
            user = cursor.fetchone()

        if user is None or not verify_password(data.password, user['password_hash']):
            raise HTTPException(status_code=401, detail='Credenciales incorrectas')

        token = create_access_token(user_id=user['id'], username=user['nombre'])

        return {
            'success': True,
            'message': 'Autenticación exitosa',
            'usuario': user['nombre'],
            'token': token,
        }
    finally:
        connection.close()
