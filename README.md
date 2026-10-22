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

## Objetivo de Data Engineering

Construir un pipeline reproducible que permita:

1. Ingerir los archivos originales en la capa Bronze.
2. Limpiar, tipar y estandarizar los datos en Silver.
3. Integrar y preparar información analítica en Gold.
4. Aplicar controles de calidad y consistencia entre las diferentes fuentes.
5. Orquestar las distintas etapas del pipeline.

## Objetivo de Machine Learning

Como punto de partida, se evaluará la construcción de un modelo de clasificación que estime si un accidente presenta víctimas.

Variable objetivo propuesta:

- `tiene_victimas = 0`: accidente con solo daños.
- `tiene_victimas = 1`: accidente con heridos o muertos.

La definición final de las variables predictoras deberá evitar data leakage y utilizar únicamente información válida para el momento conceptual de la predicción.

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
 v
Gold
 |
 v
Machine Learning
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
