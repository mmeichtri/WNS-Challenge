# Costo de recetas — WNS Challenge

Aplicación web para elegir un plato de `inputs/Recetas.md` y una fecha de los últimos 30 días y ver:
ingredientes y cantidades, la receta, el costo total en ARS y USD, y otros platos que comparten ingredientes.

La consigna original está en [CONSIGNA.md](CONSIGNA.md).

## Cómo levantarlo

### Con Docker (recomendado)

```bash
docker compose up --build          # app en http://localhost:8000
docker compose run --rm tests      # tests
```

Al arrancar, el contenedor corre la ingesta y después levanta la API. La base SQLite queda en el volumen
`app-data`, así que la cache de cotizaciones sobrevive a los reinicios. Para empezar de cero:
`docker compose down -v`.

### Local (sin Docker)

Requiere Python 3.13.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # opcional: sin .env se usan los valores por defecto

python -m app.ingestion            # carga precios y recetas en data/app.db
uvicorn app.main:app --reload      # http://localhost:8000
pytest                             # tests
```

### Configuración

Todo lo que depende del entorno se configura por variables de entorno (o `.env`), leídas con
`pydantic-settings` en `app/core/config.py`:

| Variable | Default | Para qué |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | Base de datos |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `DEBUG` | `false` | Modo debug de FastAPI |
| `EXCEL_PRICES_PATH` | `inputs/Carnes y Pescados.xlsx` | Precios de carnes y pescados |
| `PDF_PRICES_PATH` | `inputs/verduleria.pdf` | Precios de verduras |
| `RECIPES_PATH` | `inputs/Recetas.md` | Recetas |
| `CURRENCY_API_URL` | jsdelivr, con `{date}` | URL principal de la cotización |
| `CURRENCY_API_FALLBACK_URL` | pages.dev, con `{date}` | URL de fallback |
| `CURRENCY_API_TIMEOUT_SECONDS` | `5` | Timeout de cada consulta a la API |

## Uso

La página está en `/`. Es un HTML estático que consume la misma API con `fetch`.
La documentación interactiva de la API está en `/docs`.

| Endpoint | Respuesta |
|---|---|
| `GET /recipes` | Lista de platos (`id`, `name`) |
| `GET /recipes/{id}?date=YYYY-MM-DD` | Ingredientes, receta, costo en ARS y USD, warnings |
| `GET /recipes/{id}/similar` | Platos con al menos un ingrediente en común, de más a menos compartidos |

Códigos de respuesta:
- `404`: la receta no existe.
- `422`: fecha con formato inválido, futura o anterior a 30 días.
- `200` con `usd: null` y un warning: no se pudo obtener la cotización (ver [Manejo de errores](#manejo-de-errores)).

Los montos se devuelven como string (`"7925.00"`) para no perder precisión al pasar por float.

## Arquitectura

```
app/
├── main.py               # FastAPI: routers, página estática, init de la base
├── models.py             # Modelos SQLAlchemy
├── core/                 # config (variables de entorno) y db (engine, sesión)
├── api/                  # routes, schemas de respuesta, dependencias inyectables
├── services/             # lógica de negocio: costing, dates, exchange_rates, recipes
├── clients/              # currency_api: el único módulo que habla con la API externa
├── ingestion/            # comando aparte: python -m app.ingestion
│   ├── __main__.py       # entrypoint
│   ├── manager.py        # guarda en la base lo que devuelven los parsers
│   ├── normalization.py  # clave de comparación de nombres
│   └── parsers/          # precios (Excel, PDF) y recetas (.md) → dataclasses, sin tocar la base
└── static/index.html
tests/
```

Las dependencias van en un solo sentido: `api → services → clients / models`. Cada capa traduce los errores
de la de abajo a los suyos. Por ejemplo, `CurrencyApiError` (cliente) pasa a ser `ExchangeRateUnavailable`
(servicio), y eso termina en un warning (API). Así los endpoints no saben que la cotización viene de un
servicio HTTP.

### Ingesta

Es un comando separado de la API (`python -m app.ingestion`), como permite la consigna.

- **Parsers.** Cada archivo tiene el suyo y devuelve dataclasses (`schemas.py`) con lo que se pudo leer y lo
  que se rechazó, con el motivo y la ubicación (archivo, hoja, línea/fila). Los parsers no conocen la base.
  - `ExcelPriceParser` y `PdfPriceParser` heredan de la clase abstracta `PriceParser`, que define el contrato
    (`parse() -> PriceParseResult`) y el manejo común de rechazos. Sumar una fuente nueva es sumar una
    subclase.
  - `RecipeParser` queda afuera de esa jerarquía porque devuelve otra cosa.
- **Excel.** La planilla no es una tabla regular: tiene dos bloques lado a lado, subtítulos en celdas
  combinadas y precios en formatos distintos (`6800`, `"6.000"`, `"$2600"`). Cada bloque se ubica por su
  título y se lee hacia abajo hasta la primera fila vacía, en vez de usar rangos fijos.
- **PDF.** Es una página web impresa, sin tablas. Se lee el texto línea por línea y se toman las que tienen
  la forma `Nombre $precio`.
- **Recetas.** `Recetas.md` no sigue un formato fijo: cada receta nombra sus secciones distinto
  ("Ingredientes", "Lista", "Preparación"...), usa listas con `-`, `*`, `1.` o `a.`, y escribe los
  ingredientes de varias formas (`1 kg de Lomo`, `Lomo: 1,25 kg`, `Sal a gusto`). Se recorre línea por
  línea recordando en qué receta y en qué sección estamos.
- **Idempotencia.** Ingredientes y recetas se identifican por `normalized_name` (minúsculas, sin acentos,
  espacios colapsados). Una segunda corrida actualiza lo que cambió y no duplica. Todo corre en una sola
  transacción: si algo falla, no queda nada a medias.
- **Reporte.** Al final se loguea cuántos registros se crearon, actualizaron, quedaron sin cambios o se
  rechazaron. Cada rechazo se loguea con su motivo.

### Modelo de datos

- `ingredients`: nombre, `normalized_name` único, `price_per_kg` en pesos enteros. Es `NULL` si el ingrediente
  no figura en ninguna lista de precios.
- `recipes`: nombre, `normalized_name` único, instrucciones.
- `recipe_ingredients`: tabla intermedia con `quantity_grams`. Es `NULL` para "a gusto".
- `exchange_rates`: cache de cotizaciones por fecha.

Hay `CHECK` de precio y cantidad positivos.

### Costo

- Como todo se vende de a 250 g, se cotiza lo que hay que comprar y no lo que pide la receta: si la receta
  pide 800 g, se compra (y se paga) 1 kg, porque no se pueden comprar 800 g justos y 750 g no alcanzan. Los gramos se manejan siempre como enteros.
- La plata se calcula con `Decimal` y no con `float`, para evitar errores de precisión en operaciones
  monetarias. El total en dólares se calcula sobre el total en pesos y se redondea una sola
  vez; si se redondeara ingrediente por ingrediente, los centavos de diferencia se irían sumando.
- La cotización del dólar se guarda en la base como texto, porque SQLite no tiene un tipo para guardar
  decimales exactos.

### Cotización

- `CurrencyApiClient` prueba la URL principal y, si falla, el fallback. Siempre usa timeout y valida la
  respuesta (JSON válido, `usd.ars` numérico y positivo).
- La cotización se cachea por fecha en `exchange_rates`, evitando consultar nuevamente la API para una fecha
  que ya fue obtenida.

### Platos similares

Es una sola consulta SQL: se cruza `recipe_ingredients` consigo misma por ingrediente, se agrupa por la otra
receta y se cuenta. El orden es por cantidad compartida y después por nombre, para que el
resultado sea determinístico.

## Manejo de errores

- **API externa caída.** Si no hay cotización (no está en cache y fallan las dos URLs), la respuesta es `200`
  con el costo en ARS, `usd: null` y un warning. El costo en ARS no depende de la API, así que se informa
  igual en lugar de fallar el request entero.
- **Validación de inputs del usuario.**
  - FastAPI rechaza con `422` una fecha mal formada.
  - El servicio valida el rango de 30 días.
  - Una receta inexistente da `404`.
- **Validación en la ingesta.** Cada registro inválido se rechaza con su motivo y el resto se sigue
  procesando.
- **Logging.** Se configura una sola vez por entrypoint, con nivel por variable de entorno. Se loguean: los
  rechazos de la ingesta, los fallos de cada URL de la API y las cotizaciones obtenidas.

## Tests

29 tests. No usan internet ni la base real: la base es en memoria y la API de cotización se reemplaza por un
cliente falso mediante `dependency_overrides` de FastAPI. En los tests del cliente HTTP, `requests.get` se
reemplaza con `monkeypatch`.

Qué se prueba:
- **Parsers:** que lean bien los tres archivos reales de `inputs/`, los formatos de precio, y que una línea
  inválida se informe con ubicación y motivo sin frenar el resto.
- **Ingesta:** que cargue todo y que correrla dos veces no duplique datos.
- **Costo:** el redondeo a 250 g y que lo "a gusto" no sume.
- **Fechas:** que acepte los últimos 30 días y rechace fechas futuras o más viejas.
- **Cotización:** que use la URL principal, que pase al fallback si falla y que, una vez obtenida, no la
  vuelva a pedir.
- **Endpoints:** el detalle con ARS y USD, los ingredientes en el orden de la receta, qué pasa si no hay cotización, el 404, el 422 y los platos
  similares.

## Asunciones

- **"Dentro de los 30 días previos"** se interpreta como `[hoy − 30, hoy]`, con los dos extremos incluidos.
  Hoy entra porque la API publica la cotización del día. "Hoy" es la fecha local del servidor.
- **Ingredientes "a gusto"** (sal, pimienta, laurel) se listan pero no se cotizan.
- **Ingredientes sin precio.** Si un ingrediente con cantidad no figura en ninguna lista de precios, el costo
  se calcula sin él y la respuesta lo avisa en `warnings`. Los ingredientes indicados como "a gusto" no
  generan warning porque no requieren cotización.
- **Ingrediente repetido en una misma receta:** se suman las cantidades, como una sola compra.
- **Cruce de nombres** entre recetas y listas de precios: por nombre normalizado, sin acentos ni mayúsculas.
  No hay sinónimos.
- **Precios:** son por kg, en pesos enteros, y no cambian en el tiempo (lo dice la consigna).
- **Platos similares:** cuentan todos los ingredientes compartidos, incluidos los "a gusto".

## Limitaciones

- Si una línea de ingrediente se rechaza, la receta se carga igual sin ese ingrediente, y el rechazo queda en
  el log de la ingesta. La API no avisa que a esa receta le falta un ingrediente.
- La ingesta agrega y actualiza, pero no borra: si se saca una receta de `Recetas.md`, sigue en la base.
- SQLite admite un solo escritor a la vez. Alcanza para uso local, no para muchos usuarios concurrentes.
- La cotización del día puede no estar publicada todavía en la API. En ese caso se responde sin USD.
- La página web no tiene tests automáticos.

## Cómo lo escalaría o desplegaría

- **Base de datos.** Pasaría de SQLite a PostgreSQL: SQLite es un archivo local que no aguanta muchas
  escrituras a la vez ni se puede compartir entre varias instancias de la app. Además usaría Alembic para
  versionar los cambios del esquema.
- **Ingesta.** Sacaría la ingesta del arranque del contenedor y la correría aparte, como una tarea de
  ECS con la misma imagen de Docker, que se dispare cuando se suben archivos nuevos a S3. Así levantar la
  API no depende de leer archivos.
- **Cache de cotizaciones.** Si hubiera varias réplicas, la cache seguiría en la base compartida o pasaría a
  Redis.
- **Llamadas a la API.** Les agregaría reintentos con backoff y un circuit breaker, para no sumar latencia
  cuando la API está caída.

Para producción también agregaría:
- varias instancias de la app en ECS detrás de un Load Balancer, que reparta el tráfico y maneje HTTPS;
- configuración y secretos desde el entorno del orquestador;
- logs estructurados (JSON) y un health check;
- CI que corra los tests y un linter en cada push.

## Qué haría con más tiempo

- **Rechazos en la API.** Decidir con negocio qué hacer con una receta que tiene una línea rechazada:
  cargarla incompleta (como ahora) o no cargarla. En cualquier caso, exponer los rechazos de la ingesta en
  la API, no solo en el log.
- **Repositorios.** Separar las consultas en una capa de repositorios, si el proyecto crece.
- **Más tests.** Tests de la página y un test end-to-end contra el contenedor.
- **Linter y tipos.** Ruff y mypy en CI.

## Alternativas descartadas

- **pypdf para leer el PDF.** Extrae el texto en otro orden: separa el nombre del precio y lo pega a la
  descripción. Por eso uso pdfplumber.
- **`float` para montos.** Errores de redondeo con centavos. Por eso uso `Decimal` de punta a punta, incluso
  al leer el JSON de la API (`parse_float=Decimal`).
- **Pydantic en los parsers.** Lo que necesitaba era rechazar cada fila con su motivo y seguir con el resto.
  Uso dataclasses y validación explícita. Pydantic queda para las respuestas de la API.
- **Rangos fijos en el Excel.** Se rompen si se mueve una fila. Por eso cada bloque se ubica por su título.
- **`503` sin cotización.** Perdía el costo en ARS, que sí está disponible. Por eso devuelvo `200` con
  `usd: null` y un warning.
- **`Protocol` para los parsers de precios.** Una clase abstracta además permite compartir el manejo de
  rechazos.
- **Un framework de frontend.** Para esta interfaz alcanza HTML y `fetch`, sin necesidad de incorporar un
  framework de frontend.

## Uso de IA

Utilicé Claude Code como herramienta de asistencia durante el desarrollo.

- **Scaffolding:** configuración inicial de FastAPI y SQLAlchemy, a partir de la estructura y decisiones de diseño que definí para el proyecto.
- **Tests:** generación de una base inicial de tests, fixtures y algunos casos parametrizados.
- **Documentación:** asistencia en la generación y revisión del README y documentación del proyecto.

El código fue revisado, probado y adaptado durante el desarrollo.
