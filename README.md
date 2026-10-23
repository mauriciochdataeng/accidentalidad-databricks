# accidentalidad-databricks

Proyecto final del curso de Databricks de la Universidad de los Andes.

## Descripción

Este proyecto construye una solución de datos end-to-end en Databricks a partir de información histórica de accidentalidad vial de Barranquilla.

La implementación cubre:

- arquitectura Medallion con capas Bronze, Silver y Gold;
- ingesta y transformación con PySpark;
- tablas Delta administradas en Unity Catalog;
- controles de calidad e integridad entre fuentes;
- `MERGE INTO`, Time Travel, historial y `OPTIMIZE` con Delta Lake;
- gobernanza y privilegios con Unity Catalog;
- orquestación con Databricks Jobs;
- construcción de un dataset Gold para Machine Learning;
- entrenamiento y comparación de modelos;
- tracking de experimentos con MLflow;
- registro del mejor modelo en Unity Catalog Model Registry.

## Fuentes de datos

El proyecto parte de cuatro archivos CSV:

| Dataset | Grano | Registros |
|---|---|---:|
| `accidentes.csv` | una fila por accidente | 23,212 |
| `causas.csv` | una fila por accidente | 23,212 |
| `vehiculos.csv` | una fila por vehículo involucrado | 46,128 |
| `victimas.csv` | una fila por víctima | 11,328 |

La columna `Croquis` —o `Corquis` en algunos archivos de origen— identifica el accidente y permite relacionar las distintas fuentes.

Los datasets tienen granos diferentes y se mantienen separados para evitar joins que multipliquen filas de forma incorrecta, especialmente entre vehículos y víctimas.

## Arquitectura implementada

```text
CSV originales
     |
     v
Unity Catalog Volume
     |
     v
Bronze
     |
     v
Silver
     |
     v
Gold ML: features_accidentalidad
     |
     v
Machine Learning
     |
     v
MLflow Tracking
     |
     v
Unity Catalog Model Registry
     |
     v
Alias Champion
```

De forma transversal:

```text
Unity Catalog  -> catálogo, schemas, permisos y trazabilidad
Delta Lake     -> MERGE, Time Travel, historial y OPTIMIZE
Databricks Jobs -> orquestación Bronze -> Silver
Git Folder     -> versionamiento con GitHub
```

## 1. Setup y Unity Catalog

El proyecto utiliza el catálogo:

```text
accidentalidad_databricks
├── bronze
├── silver
└── gold
```

También se utiliza un Unity Catalog Volume para almacenar los archivos fuente:

```text
/Volumes/accidentalidad_databricks/bronze/raw_files
```

El notebook de configuración crea el catálogo y los schemas Medallion de forma reproducible.

## 2. Capa Bronze

Las cuatro fuentes se ingieren como tablas Delta:

- `bronze.accidentes`
- `bronze.causas`
- `bronze.vehiculos`
- `bronze.victimas`

Principios aplicados:

- los valores de negocio se conservan sin transformación semántica;
- `inferSchema=False` para preservar inicialmente los datos como texto;
- se normalizan únicamente nombres de columnas incompatibles con Delta;
- `Croquis` / `Corquis` se normaliza técnicamente a `croquis`;
- se conserva `_c0` en Bronze como parte del archivo recibido;
- se agregan `_source_file` y `_ingestion_timestamp` para trazabilidad;
- `_metadata.file_path` se utiliza como alternativa compatible con Unity Catalog.

La ingesta se implementa mediante una función reutilizable para los cuatro datasets.

## 3. Capa Silver

La capa Silver limpia, tipa y estandariza los datos sin alterar el grano de las fuentes.

Transformaciones principales:

- eliminación de `_c0`;
- fechas convertidas a `DATE`;
- año, mes, día, edad, heridos y muertos convertidos a tipos numéricos;
- coordenadas con coma decimal convertidas a `DOUBLE`;
- limpieza de cadenas vacías;
- normalización de categorías;
- corrección del problema de encoding `se¤ales` -> `señales` en causas;
- renombre semántico de campos ambiguos de víctimas;
- conservación de metadatos de trazabilidad;
- agregado de `_silver_transformation_timestamp`.

### Validaciones de calidad

Los conteos se conservaron completamente entre Bronze y Silver:

| Tabla | Bronze | Silver | Resultado |
|---|---:|---:|---|
| accidentes | 23,212 | 23,212 | OK |
| causas | 23,212 | 23,212 | OK |
| vehiculos | 46,128 | 46,128 | OK |
| victimas | 11,328 | 11,328 | OK |

También se validó que:

- no existen `croquis` nulos;
- `accidentes` tiene 23,212 `croquis` distintos;
- `causas` tiene 23,212 `croquis` distintos;
- `vehiculos` tiene 23,215 `croquis` distintos;
- `victimas` contiene 7,758 accidentes distintos;
- las conversiones de fechas, numéricos y coordenadas no introdujeron nuevos valores nulos;
- causas no contiene accidentes huérfanos;
- se identificaron 3 `croquis` en vehículos sin accidente asociado, conservados y documentados como hallazgo de calidad;
- para los 23,212 accidentes, la cantidad de registros de víctimas coincide con `nro_heridos + numero_muertos`.

## 4. Delta Lake

El notebook de Delta Lake utiliza una tabla de demostración independiente derivada de `silver.accidentes`, evitando modificar la tabla Silver original.

Se demuestra:

### MERGE INTO

Se simula una carga incremental con dos escenarios:

- un `croquis` existente se actualiza;
- un `croquis` nuevo se inserta.

Esto representa un patrón de **upsert** (`UPDATE + INSERT`) útil para cargas incrementales reales.

### Historial y Time Travel

Se utiliza `DESCRIBE HISTORY` para inspeccionar las versiones de la tabla y Time Travel para consultar el estado previo al `MERGE`.

### OPTIMIZE

Se ejecuta `OPTIMIZE` para demostrar compactación física de archivos Delta. En este dataset su beneficio de rendimiento es limitado por el volumen, pero representa una práctica relevante en tablas incrementales de mayor escala.

## 5. Gobernanza con Unity Catalog

El proyecto utiliza un catálogo propio y los schemas Medallion para separar responsabilidades y niveles de procesamiento.

El notebook de gobernanza:

- identifica el principal actual con `current_user()`;
- aplica `USE CATALOG`;
- aplica `USE SCHEMA`;
- aplica `SELECT` sobre Silver;
- verifica los privilegios mediante `SHOW GRANTS`;
- documenta el principio de mínimo privilegio.

En un entorno empresarial, estos privilegios deberían asignarse preferiblemente a grupos en lugar de usuarios individuales.

## 6. Orquestación

Se crea programáticamente un Databricks Job llamado:

```text
accidentalidad_barranquilla_pipeline
```

DAG implementado:

```text
bronze_ingestion
       |
       v
silver_transformation
```

La tarea Silver depende explícitamente de que la ingesta Bronze termine correctamente.

El Job fue ejecutado exitosamente de extremo a extremo.

## 7. Gold para Machine Learning

Se crea la tabla:

```text
gold.features_accidentalidad
```

Su grano es una fila por accidente.

### Variable objetivo

```text
tiene_victimas = 0 -> accidente con solo daños
tiene_victimas = 1 -> accidente con heridos o muertos
```

El problema se plantea como clasificación al momento conceptual del registro del accidente, no como predicción de que un accidente vaya a ocurrir.

### Prevención de data leakage

No se utilizan como features variables que revelan directamente el resultado, entre ellas:

- `gravedad`;
- `nro_heridos`;
- `numero_muertos`;
- información de la tabla de víctimas.

Las features utilizadas incluyen contexto temporal, geográfico y de clase de accidente.

### Separación temporal

La evaluación utiliza:

- entrenamiento: 2018-2021;
- prueba: 2022.

Se utiliza un periodo posterior como test para aproximar mejor un escenario real de generalización temporal.

## 8. Machine Learning y MLflow

Se entrenan y comparan dos candidatos:

- Logistic Regression;
- Random Forest.

Para cada modelo se registran en MLflow:

- parámetros;
- accuracy;
- precision;
- recall;
- F1;
- ROC-AUC;
- reporte de clasificación;
- modelo serializado con firma e input example.

El mejor modelo se selecciona por **F1** y se registra en Unity Catalog Model Registry como:

```text
accidentalidad_databricks.gold.modelo_riesgo_victimas
```

La versión seleccionada recibe el alias:

```text
Champion
```

Finalmente, el notebook vuelve a cargar el modelo mediante el alias y ejecuta una inferencia de validación.

> Las métricas exactas de la ejecución se consultan en el experimento de MLflow. No se fijan en este README para evitar documentar valores que cambien cuando el entrenamiento se vuelva a ejecutar.

## Estructura del repositorio

```text
accidentalidad-databricks/
├── 00_Setup/
│   └── 00_Configuracion.ipynb
├── 01_Exploracion_y_Transformacion/
│   ├── 01_Ingesta_Bronze.ipynb
│   └── 02_Transformacion_Silver.ipynb
├── 02_Delta_Lake/
│   └── 02_Delta_Lake.ipynb
├── 03_Gobernanza/
│   └── 03_Gobernanza.ipynb
├── 04_Orquestacion/
│   └── 04_Orquestacion.ipynb
├── 05_Machine_Learning/
│   └── 05_Machine_Learning.ipynb
├── data/
└── README.md
```

## Orden recomendado de ejecución

```text
1. 00_Setup/00_Configuracion.ipynb
2. 01_Exploracion_y_Transformacion/01_Ingesta_Bronze.ipynb
3. 01_Exploracion_y_Transformacion/02_Transformacion_Silver.ipynb
4. 02_Delta_Lake/02_Delta_Lake.ipynb
5. 03_Gobernanza/03_Gobernanza.ipynb
6. 04_Orquestacion/04_Orquestacion.ipynb
7. 05_Machine_Learning/05_Machine_Learning.ipynb
```

## Cobertura de la rúbrica

| Módulo | Evidencia implementada | Estado |
|---|---|---|
| Ingesta y transformación | Bronze + limpieza Silver | ✅ |
| Delta Lake | MERGE, Time Travel, historial y OPTIMIZE | ✅ |
| Gobernanza | catálogo propio, schemas Medallion y GRANT documentado | ✅ |
| Orquestación | Databricks Job con dependencias y ejecución exitosa | ✅ |
| Machine Learning | modelo entrenado, MLflow Tracking y registro en Unity Catalog | ✅ |

## Trabajo futuro

El proyecto deja definidos como posibles extensiones:

- construir el modelo dimensional Gold analítico (`dim_*` y `fct_*`);
- incorporar nuevos lotes incrementales reales en lugar de la simulación de `MERGE`;
- ampliar los controles de calidad y convertirlos en tests automatizados;
- agregar tuning de hiperparámetros;
- evaluar drift temporal del modelo;
- crear un endpoint de Model Serving;
- extender el Databricks Job para incluir Delta, gobernanza y Machine Learning según las necesidades operativas.

## Estado

**Proyecto final implementado y ejecutado correctamente para los componentes requeridos del curso.**
