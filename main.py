from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes.auth import router as auth_router
from routes.salones import router as salones_router

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=['*'],
	allow_credentials=True,
	allow_methods=['*'],
	allow_headers=['*'],
)


@app.on_event('startup')
def on_startup() -> None:
	init_db()


app.include_router(auth_router, prefix='/auth')
app.include_router(salones_router)