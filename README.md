# accidentalidad-databricks

Proyecto final del curso de Databricks de la Universidad de los Andes.

## Descripción

Este proyecto utiliza datos históricos de accidentalidad de tránsito en Barranquilla para construir una solución de datos de extremo a extremo en Databricks.

El objetivo es aplicar los conceptos trabajados durante el curso, incluyendo:

- Arquitectura Medallion: Bronze, Silver y Gold.
- Ingesta y transformación de datos con PySpark y SQL.
- Delta Lake.
- Unity Catalog y gobernanza.
- Orquestación con Databricks Jobs.
- Modelado dimensional para consumo analítico.
- Machine Learning.
- MLflow Tracking.
- Model Registry en Unity Catalog.
- Model Serving.

## Fuentes de datos

El proyecto parte de cuatro archivos CSV:

- `accidentes.csv`
- `vehiculos.csv`
- `victimas.csv`
- `causas.csv`

Estos datasets contienen información relacionada con accidentes de tránsito ocurridos en Barranquilla.

La columna `Croquis` —o `Corquis` en algunos archivos de origen— permite relacionar los registros correspondientes a un mismo accidente.

Los datasets tienen granos diferentes:

- `accidentes.csv`: una fila por accidente.
- `causas.csv`: una fila por accidente.
- `vehiculos.csv`: una fila por vehículo involucrado.
- `victimas.csv`: una fila por víctima.

Esta diferencia de grano se conservará en el modelado para evitar duplicaciones y joins que multipliquen filas incorrectamente.

## Objetivo de Data Engineering

Construir un pipeline reproducible que permita:

1. Ingerir los archivos originales en la capa Bronze.
2. Limpiar, tipar y estandarizar los datos en Silver.
3. Aplicar controles de calidad y consistencia entre las diferentes fuentes.
4. Construir un modelo dimensional en Gold para consumo analítico.
5. Construir un dataset Gold específico para Machine Learning.
6. Orquestar las distintas etapas del pipeline.

## Arquitectura Medallion

### Bronze

Contendrá una representación fiel de los archivos originales, conservando los datos tal como llegan desde la fuente.

Tablas previstas:

- `bronze.accidentes`
- `bronze.vehiculos`
- `bronze.victimas`
- `bronze.causas`

### Silver

Contendrá los datos limpios y estandarizados. Entre otras transformaciones se espera:

- Normalización de nombres de columnas.
- Estandarización de `Croquis` / `Corquis` a `croquis`.
- Conversión de fechas y tipos de datos.
- Conversión de coordenadas a tipos numéricos.
- Tratamiento justificado de valores nulos.
- Eliminación de columnas técnicas innecesarias provenientes de los CSV.
- Validaciones de integridad y consistencia entre accidentes, vehículos, víctimas y causas.

### Gold

La capa Gold tendrá dos propósitos separados: consumo analítico y Machine Learning.

#### Gold analítico: modelo dimensional

Se construirá un modelo dimensional manteniendo el grano natural de cada entidad.

Dimensiones propuestas:

- `gold.dim_fecha`
- `gold.dim_geografia`
- `gold.dim_clase_accidente`
- `gold.dim_gravedad`
- `gold.dim_causa`
- `gold.dim_tipo_vehiculo`
- `gold.dim_tipo_victima`
- `gold.dim_sexo`

Tablas de hechos propuestas:

- `gold.fct_accidentes`: una fila por accidente (`croquis`).
- `gold.fct_vehiculos`: una fila por vehículo involucrado.
- `gold.fct_victimas`: una fila por víctima.

`gold.fct_accidentes` podrá incluir medidas como:

- número de heridos;
- número de muertos;
- cantidad de vehículos involucrados;
- cantidad de víctimas.

La separación entre hechos evita construir una única tabla resultante de unir vehículos y víctimas, lo cual podría multiplicar registros debido a sus relaciones 1:N con el accidente.

#### Gold para Machine Learning

Se construirá además una tabla específica para entrenamiento y serving, por ejemplo:

- `gold.features_accidentalidad`

Esta tabla tendrá una fila por accidente y contendrá únicamente las variables válidas para el problema predictivo definido, evitando incluir información que produzca data leakage.

## Objetivo de Machine Learning

Como punto de partida, se evaluará la construcción de un modelo de clasificación que estime si un accidente presenta víctimas.

Variable objetivo propuesta:

- `tiene_victimas = 0`: accidente con solo daños.
- `tiene_victimas = 1`: accidente con heridos o muertos.

La definición final de las variables predictoras deberá evitar data leakage y utilizar únicamente información válida para el momento conceptual de la predicción.

Variables que revelen directamente el resultado, como el número de heridos, número de muertos o información posterior de las víctimas, no deberán utilizarse como predictores de `tiene_victimas`.

## Arquitectura propuesta

```text
CSV
 |
 v
Bronze
 |
 v
Silver
 |
 +-------------------------+
 |                         |
 v                         v
Gold analítico          Gold ML
Modelo dimensional      features_accidentalidad
 |                         |
 v                         v
BI / análisis           Machine Learning
                           |
                           v
                        MLflow
                           |
                           v
                    Model Registry
                           |
                           v
                     Model Serving
```

## Estructura del proyecto

```text
accidentalidad-databricks/
├── 00_Setup/
├── 01_Exploracion_y_Transformacion/
├── 02_Delta_Lake/
├── 03_Gobernanza/
├── 04_Orquestacion/
├── 05_Machine_Learning/
├── data/
└── README.md
```

## Estado

Proyecto en construcción.
