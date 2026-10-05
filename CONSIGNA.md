# WNS Challenge - Programador Python Sr./Ssr.

¡Hola! Gracias por aplicar a WNS Asociados. A continuación verás un desafío técnico. Te pedimos que lo completes de acuerdo a los lineamientos aquí detallados:

## Lineamientos del Desafío

Estimamos que el desafío lleva entre 3 y 4 horas. Tenés 1 semana para entregarlo.

### A la hora de entregar te pedimos que

- [ ] Programes el backend en Python.
- [ ] Subas todo el código producido a GitHub y nos envíes un link al repositorio.
- [ ] Empaquetes tu solución con Docker (incluyendo el Dockerfile y/o docker-compose.yml en el repo), de modo que podamos levantarla con un solo comando y correr los tests con otro.
- [ ] Incluyas un archivo README.md o similar detallando las decisiones tomadas y explicando la implementación, sus fortalezas y debilidades.
- [ ] Destaques las asunciones hechas a la hora de desarrollar la solución y expliques las limitaciones y condiciones de operación de la misma.
- [ ] Te asegures de que la explicación incluya pasos detallados para poder reproducir la solución (instalación de librerías, setup, etc.).
- [ ] Incluyas uno o dos párrafos explicando qué cambios harías a tu solución en caso de que se desee escalarla o desplegarla más allá de un entorno local.
- [ ] Incluyas una sección explicando qué harías si tuvieras más tiempo, y qué alternativas consideraste y descartaste (y por qué).
- [ ] Incluyas una sección explicando cómo usaste IA (si la usaste): para qué partes, qué corregiste y qué descartaste.

### Para resolver el desafío podés (aunque no es obligatorio)

- Usar librerías y frameworks apropiados (recordá mencionarlas y proveer los pasos necesarios para instalarlas localmente en caso de que haga falta).
- Usar ChatGPT, Claude, Google o cualquier otro servicio de búsqueda o IA para pensar y diagramar la solución.
- Usar SQLite como Base de Datos.

### Para resolver el desafío NO podés

- Llamar a servicios externos (o usar librerías que lo hagan), más allá de los estipulados en la consigna.
- Utilizar código generado por IA que no seas capaz de comprender y explicar, vamos a preguntarte sobre tu implementación en la entrevista técnica. En la entrevista también te vamos a pedir que hagas un cambio en vivo sobre tu solución.
- Modificar los archivos de Input que te vamos a dar. Tu solución tiene que funcionar con los archivos tal y cómo te los suministramos. Podés crear una etapa/comando/flujo separado para ingestarlos y normalizarlos en una base de datos.

### Cosas que vamos a evaluar

Las expectativas mínimas para un Programador Python Sr./Ssr. y las cosas que vamos a mirar para determinar el seniority del candidato son:

- La arquitectura de la solución.
- La prolijidad, legibilidad y organización coherente del código.
- Uso y modelado correcto de Base de Datos.
- Buenas Prácticas cómo:
  - Correcto manejo de errores (tené en cuenta que la cotización depende de un servicio externo que no controlás).
  - Uso razonable (pero no excesivo) de capas y abstracciones.
  - Validación de inputs (tanto de usuario como en la ingesta de datos).
  - Configuración mediante variables de entorno (nada que dependa del entorno debería estar hardcodeado).
  - Logging razonable y respuestas con códigos HTTP y mensajes de error coherentes.
  - Testing automático básico (no hace falta 100% de test coverage, pero queremos ver tu approach a testear la solución). Los tests no deben depender de la red.

## Consigna

El objetivo de este desafío es construir una pequeña aplicación web que permita al usuario elegir un plato de los provistos en `inputs/Recetas.md` y una fecha dentro de los 30 días previos y permitir al usuario:

- Ver el listado de ingredientes y sus cantidades
- Ver la receta
- Ver el costo total del plato en Pesos argentinos y Dólares estadounidenses.
- Ver una lista de otros platos que tengan al menos un ingrediente en común con el plato elegido, ordenada por cantidad de ingredientes compartidos (de mayor a menor).

A tal efecto, disponés de 2 archivos más:

- `inputs/verduleria.pdf` que contiene el precio de las verduras.
- `inputs/Carnes y Pescados.xlsx` que contiene el precio de Carnes y pescados.

Podés asumir que estos precios NO cambian con el tiempo y son iguales en cualquier momento del mes.

El proceso de ingesta debe poder ejecutarse más de una vez sin duplicar datos, e informar qué registros no pudo procesar y por qué.

Tanto las verduras como las carnes y pescados se venden de a múltiplos de 250 gramos, es decir, si un plato requiere de 800 gramos de Zapallo, es necesario cotizar la compra de 1 kilo del mismo (dado que 750 gramos sería menos de lo necesario y 1 kilo es el valor siguiente aceptable).

A efectos de obtener la cotización del Dólar estadounidense debés utilizar la siguiente API que te permitiría chequear la cotización de cualquier moneda vs el Dólar para una fecha dada:

`https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@[FECHA]/v1/currencies/usd.json`

La fecha se especifica en el formato YYYY-MM-DD dónde YYYY es el año, MM el mes arrancando con 0 en caso de ser menor a 10 y DD el día arrancando con 0 en caso de ser menor a 10. Es decir, para ver la cotización del Dólar en Pesos argentinos el 20 de Julio de 2025 deberás acceder a:

`https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2025-07-20/v1/currencies/usd.json`

y observar el valor del mismo en Pesos Argentinos (el código ISO de la moneda es ARS).

También podés usar el fallback oficial de la misma API, con el mismo formato de fecha:

`https://[FECHA].currency-api.pages.dev/v1/currencies/usd.json`
