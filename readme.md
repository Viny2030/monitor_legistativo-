# MEL-TP — Monitor de Eficiencia Legislativa y Transparencia Presupuestaria

> Ranking público de diputados argentinos por Score de Función Ejecutiva (SFE),
> con centro de costos estimado y datos abiertos del H. Cámara de Diputados.

---

## Estructura del proyecto

```
monitor_legistativo/
│
├── api/                          # Backend FastAPI
│   ├── main.py                   # App principal + CORS
│   └── routes/
│       ├── diputados.py          # GET /api/diputados/
│       ├── ranking.py            # GET /api/ranking/        ← SFE
│       ├── bloques.py            # GET /api/bloques/
│       ├── costos.py             # GET /api/costos/
│       └── modulo.py             # GET /api/modulo/monitorear
│
├── frontend/
│   └── index.html                # Dashboard completo (single-file)
│
├── scripts/
│   ├── actualizar_tel.py         # TEL real desde datos.hcdn.gob.ar
│   └── monitorear_modulo.py      # Detecta cambios en el módulo
│
├── .github/workflows/
│   └── pipeline_semanal.yml      # GitHub Actions — lunes 6am
│
├── obtener_datos.py              # Scraper nómina de diputados
├── scraper_asistencia.py         # Scraper asistencia a sesiones
├── scraper_diputados.py          # Scraper auxiliar
├── pipeline.py                   # Orquestador principal
├── personal.py                   # Módulo legislativo y costos base
│
├── nomina_diputados.csv          # Generado por obtener_datos.py
├── asistencia_diputados.csv      # Generado por scraper_asistencia.py
├── tel_diputados.csv             # Generado por scripts/actualizar_tel.py
├── ranking_sfe.csv               # Generado por pipeline.py
│
├── Dockerfile                    # Deploy Railway / Docker
├── railway.toml                  # Configuración Railway
└── requirements.txt
```

---

## Score de Función Ejecutiva (SFE)

```
SFE = 0.40 × Asistencia  +  0.35 × Bipartisan  +  0.25 × TEL
```

| Componente | Peso | Fuente actual | Fuente objetivo |
|---|---|---|---|
| Asistencia | 40% | `scraper_asistencia.py` → HCDN | sesiones.hcdn.gob.ar |
| Bipartisanship | 35% | proxy determinista | votaciones.hcdn.gob.ar |
| TEL | 25% | proxy determinista | datos.hcdn.gob.ar |

> **TEL** = Tasa de Éxito Legislativo = proyectos aprobados / proyectos presentados por autor.
> Reemplaza el proxy ejecutando `python scripts/actualizar_tel.py`.

---

## Setup local

```bash
# 1. Clonar
git clone https://github.com/Viny2030/monitor_legistativo
cd monitor_legistativo

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Obtener datos frescos
python obtener_datos.py          # → nomina_diputados.csv
python scraper_asistencia.py     # → asistencia_diputados.csv (opcional)
python scripts/actualizar_tel.py # → tel_diputados.csv (opcional)

# 4. Generar ranking
python pipeline.py               # → ranking_sfe.csv

# 5. Levantar API
uvicorn api.main:app --reload --port 8000

# 6. Abrir dashboard
# Editar frontend/index.html → API_BASE = 'http://localhost:8000'
# Abrir en browser
```

---

## API Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/` | Health check |
| GET | `/health` | Estado del servidor |
| GET | `/api/diputados/` | Lista con filtros `?bloque=&provincia=` |
| GET | `/api/ranking/` | Ranking SFE completo `?bloque=&top=20` |
| GET | `/api/ranking/top/{n}` | Top N diputados |
| GET | `/api/bloques/` | SFE agregado por bloque |
| GET | `/api/bloques/lista` | Lista de bloques |
| GET | `/api/costos/` | Centro de costos `?bloque=&top=20` |
| GET | `/api/costos/diputado/{nombre}` | Costos de un diputado |
| GET | `/api/costos/modulo` | Valor actual del módulo |
| GET | `/api/modulo/monitorear` | Detecta cambio en módulo (scraping live) |
| POST | `/api/modulo/actualizar` | Actualiza valor manualmente |

Docs interactivos: `http://localhost:8000/docs`

---

## Deploy en Railway

```bash
# 1. Conectar repo en railway.app
# 2. Variables de entorno (opcional):
VALOR_MODULO=215000    # override del módulo

# railway.toml ya está configurado con:
# - healthcheck en /health
# - restart policy ON_FAILURE
```

---

## Pipeline automático (GitHub Actions)

El workflow `.github/workflows/pipeline_semanal.yml` corre cada **lunes a las 6am (AR)**:

1. `obtener_datos.py` — actualiza nómina
2. `scraper_asistencia.py` — actualiza asistencia *(activar cuando sea estable)*
3. `scripts/actualizar_tel.py` — actualiza TEL *(activar cuando dataset disponible)*
4. Commit automático de CSVs

Para correr manualmente: **Actions → pipeline_semanal → Run workflow**

---

## Pendientes por prioridad

### 🔴 Hecho (este PR)
- [x] `api/main.py` + todos los routes
- [x] `Dockerfile` + `railway.toml`
- [x] `requirements.txt` actualizado
- [x] `frontend/index.html` — dashboard completo
- [x] `personal.py` — módulo legislativo
- [x] `pipeline.py` — orquestador principal
- [x] `.github/workflows/pipeline_semanal.yml`

### 🟡 Próximos pasos
- [ ] **TEL real** — adaptar `calcular_tel()` en `scripts/actualizar_tel.py`
  según columnas reales del dataset en `datos.hcdn.gob.ar`
- [ ] **Bipartisan real** — extraer desde `votaciones.hcdn.gob.ar`
- [ ] **Integrar `monitorear_modulo()`** al pipeline (descomentar en `.yml`)
- [ ] **Viajes nacionales** — inspeccionar red en HCDN para links dinámicos

### 🟢 Post-deploy
- [ ] Subsidios 2025/2026 — monitorear publicación
- [ ] Notificaciones Slack/email cuando cambia el módulo
- [ ] Caché Redis para endpoints de ranking

---

## Fuentes de datos

| Dataset | URL | Estado |
|---|---|---|
| Nómina de diputados | diputados.gov.ar/diputados | ✅ activo |
| Sesiones y asistencia | hcdn.gob.ar/sesiones | ✅ activo |
| Proyectos parlamentarios | datos.hcdn.gob.ar | ✅ disponible |
| Votaciones | votaciones.hcdn.gob.ar | ✅ disponible |
| Módulo legislativo | hcdn.gob.ar/institucional/modulo | ✅ disponible |
| Subsidios | hcdn.gob.ar | ⏳ 2025/2026 no publicado |
| Viajes nacionales | hcdn.gob.ar | ⚠ links dinámicos |