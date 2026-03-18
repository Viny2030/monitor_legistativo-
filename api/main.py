"""
MEL-TP — Monitor de Eficiencia Legislativa y Transparencia Presupuestaria
Backend FastAPI — api/main.py
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import diputados, ranking, bloques, costos, modulo

app = FastAPI(
    title="MEL-TP API",
    description="Monitor de Eficiencia Legislativa y Transparencia Presupuestaria",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diputados.router, prefix="/api/diputados", tags=["Diputados"])
app.include_router(ranking.router,   prefix="/api/ranking",   tags=["Ranking SFE"])
app.include_router(bloques.router,   prefix="/api/bloques",   tags=["Bloques"])
app.include_router(costos.router,    prefix="/api/costos",    tags=["Costos"])
app.include_router(modulo.router,    prefix="/api/modulo",    tags=["Módulo"])


@app.get("/")
def root():
    return {"status": "ok", "proyecto": "MEL-TP", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}