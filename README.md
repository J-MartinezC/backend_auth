# backend_auth

Backend REST para autenticación, catálogo de salones y gestión de reservas.

## Stack

- FastAPI
- MySQL (PyMySQL)
- JWT para autenticación
- bcrypt para hash de contraseñas

## Requisitos

- Python 3.10+
- MySQL 8+ (o compatible)
- pip

## Instalación

```bash
cd backend_auth
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

```
## Ejecutar en desarrollo

```bash
cd backend_auth
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Variables de entorno

El proyecto lee un archivo `.env` en esta misma carpeta.

Ejemplo recomendado: (No es el del proyecto)

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=1234
DB_NAME=bd_sistema_reserva
DB_PORT=3306

JWT_SECRET=secreto-este-secreto-este-secreto
JWT_EXPIRE_MINUTES=1440
```

Notas:
- Si no existe `.env`, se usan valores por defecto definidos en el código.
- Al iniciar, `init_db()` crea base/tablas si no existen y siembra datos base de salones.

Documentación automática:
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## Endpoints principales

### Auth

- `POST /auth/registro`
	- Body: `{ "usuario": "...", "password": "..." }`
	- Registra usuario nuevo.
	- Valida contraseña mínima de 6 y sin espacios.

- `POST /auth/login`
	- Body: `{ "usuario": "...", "password": "..." }`
	- Devuelve token JWT.

- `POST /auth/forgot-password`
	- Body: `{ "usuario": "...", "new_password": "..." }`
	- Actualiza contraseña del usuario.

### Salones y reservas

- `GET /salones`
	- Lista salones con badges y métricas.

- `POST /reservas`
	- Requiere inicio de sesión. Se debe enviar el token JWT en el header Authorization.
	- Crea reserva validando disponibilidad y capacidad.

- `GET /reservas/mis`
	- Requiere inicio de sesión. Se debe enviar el token JWT en el header Authorization.
	- Historial de reservas del usuario autenticado.

## Estructura

```text
backend_auth/
	main.py                # App FastAPI y registro de routers
	database.py            # Conexión, bootstrap y migraciones simples
	models.py              # Modelos Pydantic de request/response
	routes/
		auth.py              # Registro, login, cambio de contraseña
		salones.py           # Salones, crear reserva, historial
	utils/
		security.py          # JWT + hash/verify de contraseña
	requirements.txt
```

## Troubleshooting rápido

- Error de conexión a MySQL:
	- Verifica host/puerto/usuario/password en `.env`.
	- Confirma que el servicio MySQL esté activo.

- Error 401 en rutas protegidas:
	- Iniciar sesión otra vez si el token expiró.

- CORS:
	- En desarrollo

## Seguridad

- Contraseñas almacenadas con bcrypt.
- JWT firmado con `JWT_SECRET`.