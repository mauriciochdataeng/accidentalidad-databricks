# accidentalidad-databricks

Proyecto académico de ingeniería de datos en Databricks sobre accidentalidad vial de
Barranquilla. Implementa arquitectura Medallion, calidad de datos, Delta Lake,
Unity Catalog, Jobs y clasificación de accidentes con víctimas mediante MLflow.

El código está preparado para ejecutarse en Databricks. Los CSV originales, resultados
de Jobs y métricas certificadas no están incluidos en este repositorio. Las comprobaciones
locales no sustituyen la validación con datos reales en el workspace.

## Arquitectura

```text
Cuatro CSV completos e inmutables
           |
Unity Catalog Volume: bronze.raw_files
           |
Lectura + contrato + controles Bronze
           |
Tablas Delta Bronze
           |
Lectura de versiones fijas + transformación + controles Silver
           |
Tablas Delta Silver
           |
Gold: features_accidentalidad + controles
           |
Entrenamiento 2018–2020 -> selección con validación 2021
           |
Prueba final 2022 -> MLflow -> versión candidata en Unity Catalog
           |
Promoción explícita con umbrales -> alias Champion

Auditoría transversal: quality.check_results y quality.orphan_<dataset>
Orquestación: Bronze -> Silver -> Gold/ML opcional
```

Se mantiene el grano de cada fuente. Vehículos y víctimas no se unen directamente para
construir features: esa unión podría multiplicar registros por accidente.

## Preparación desde cero

1. Importe el repositorio **completo** en un Git Folder de Databricks. Los notebooks
   importan el paquete Python `accidentalidad/` desde esa raíz.
2. Use un workspace y compute con Unity Catalog. El objetivo de compatibilidad es
   Databricks Runtime 16.4 LTS o posterior, con Python 3.10 o posterior, o un entorno
   serverless que soporte las mismas operaciones. La compatibilidad efectiva debe
   verificarse mediante [la guía de validación](docs/VALIDACION.md).
3. Para ML y orquestación, instale las dependencias de
   [requirements-databricks.txt](requirements-databricks.txt) en el cluster o entorno
   serverless del Job. No instale un Spark independiente sobre Databricks Runtime.
4. Ejecute `00_Setup/00_Configuracion.ipynb`. Necesita autorización para crear catálogo,
   schemas y un Volume administrado. Crea `bronze`, `silver`, `gold` y `quality`.
5. Cargue los cuatro CSV en `/Volumes/<catalog_name>/bronze/raw_files/` siguiendo
   [data/README.md](data/README.md). La procedencia, versión y licencia de los archivos
   originales todavía deben completarse a partir del material del curso o proveedor.
6. Ejecute Bronze y después Silver. Revise sus controles y las anomalías aceptadas.
7. Ejecute opcionalmente las demostraciones Delta y de gobernanza.
8. Despliegue el Job con el notebook de orquestación. Use `run_job=true` para ejecutarlo
   y verificar su resultado final; `include_ml=true` incorpora Gold y entrenamiento.
9. También puede ejecutar ML manualmente después de Silver. El candidato se registra
   sin cambiar Champion. Una promoción exige `promote_champion=true` y superar sus controles.

Si trabaja en un cluster interactivo, puede instalar las dependencias en una celda de
preparación del entorno, adaptando la ruta al Git Folder:

```python
%pip install -r /Workspace/Users/<usuario>/<repositorio>/requirements-databricks.txt
```

Reinicie Python si el entorno lo solicita antes de ejecutar los notebooks. En Jobs,
prepare las dependencias en el compute o entorno serverless; la sesión interactiva no
transfiere automáticamente sus paquetes al Job.

El rango de dependencias expresa compatibilidad prevista, no un lock de entorno ya
certificado. Cada entrenamiento registra las versiones exactas de sus bibliotecas y
las fija en los requisitos del modelo serializado. Conserve también la versión de
Runtime o del entorno serverless usado en su evidencia de ejecución.

## Fuentes y contrato de carga

| Archivo | Grano | Filas del lote de referencia |
|---|---|---:|
| accidentes.csv | Accidente | 23212 |
| causas.csv | Causa por accidente en este lote | 23212 |
| vehiculos.csv | Vehículo involucrado | 46128 |
| victimas.csv | Víctima | 11328 |

Los conteos son valores de referencia del proyecto original, no resultados calculados
en esta revisión. `croquis` relaciona las fuentes; los encabezados originales `Croquis`
y `Corquis` se normalizan según cada archivo.

**El pipeline usa reemplazo de instantánea completa.** Bronze y Silver escriben con
`overwrite`. Entregar solo las filas nuevas eliminaría el histórico de la versión
actual. La demostración de `MERGE` es independiente y no convierte la ingesta en incremental.
Mantenga los archivos raw inmutables durante toda la ejecución.

Para un lote completo diferente, desactive `enforce_reference_counts` y revise las reglas
que dependan del contrato. Use un catálogo distinto por entorno: `entorno` es descriptivo
y no modifica automáticamente el nombre del catálogo.

## Calidad y publicación

Bronze verifica archivos, encabezados, claves presentes, datasets no vacíos y, por defecto,
conteos de referencia. Lee los datos como texto con `FAILFAST`, normaliza encabezados y
agrega archivo de origen, timestamp e identificador de ingesta.

Silver lee versiones fijas de las cuatro tablas Bronze y:

- elimina `_c0`, limpia texto y normaliza categorías;
- convierte fechas con `try_to_timestamp` y coordenadas con coma decimal;
- valida conservación de filas, claves presentes y unicidad en accidentes/causas;
- detecta pérdidas al convertir, fracciones en conteos/edad y valores fuera de dominio;
- comprueba coherencia del calendario y coordenadas numéricas dentro de límites globales;
- valida integridad referencial y concilia víctimas con heridos y muertos.

Los controles se evalúan sobre los DataFrames candidatos **antes de publicar Silver**.
`quality.check_results` guarda ejecución, capa, dataset, regla, resultado, severidad,
detalle y fecha. Un fallo `ERROR` lanza una excepción después de persistir el reporte;
un `WARN` conserva la anomalía sin bloquear. Si falla la escritura de auditoría, tampoco
se publica la capa.

Causas y víctimas no admiten accidentes huérfanos. Vehículos permite hasta 3 claves
huérfanas por defecto, reproduciendo la tolerancia documentada del lote académico.
Se conservan sus filas en Silver y se copian a `quality.orphan_vehiculos`. La tolerancia
es cuantitativa: **no confirma que sean las mismas tres claves históricas**. Use
`max_vehicle_orphans=0` para exigir integridad estricta.

La validación previa evita publicar datos conocidos como inválidos. Las escrituras de
las cuatro tablas son transacciones Delta individuales, **no una transacción conjunta**.
Un fallo de infraestructura durante la publicación puede dejar una capa parcialmente
actualizada. El Job fallará y debe repetirse con la misma instantánea raw después de
resolverlo; no consuma una ejecución fallida como una entrega completa. Mantenga un
único escritor por catálogo, incluidas las ejecuciones manuales.

## Delta Lake

`02_Delta_Lake.ipynb` recrea exclusivamente `silver.accidentes_delta_demo` a partir de
accidentes. Demuestra actualización e inserción con `MERGE`, historial, Time Travel y
`OPTIMIZE`. Falla si los resultados finales o el estado histórico no coinciden con lo
esperado. Esta tabla de demostración no alimenta Gold y su historial se reinicia al
recrear la demo.

## Gobernanza

El notebook inspecciona permisos por defecto. Para conceder lectura de Silver, un
administrador especifica un grupo de cuenta existente en `reader_group` y ejecuta con
`apply_grants=true`. Concede `USE CATALOG`, `USE SCHEMA` y `SELECT`; no se concede
lectura automáticamente al usuario propietario como prueba de aislamiento.

Después, un miembro lector ejecuta con `apply_grants=false` y `verify_reader=true`.
La prueba exige lectura y denegación de una inserción sin filas. Otros errores se
propagan. Si la escritura está permitida por propiedad u otros privilegios heredados,
la comprobación falla. No se crean grupos ni se revocan permisos existentes.

Silver conserva nombres, placas e identificadores originales. Seleccione los miembros
del grupo según la autorización sobre esas fuentes; para consumidores más amplios,
prepare vistas con los campos permitidos antes de conceder acceso.

## Orquestación

El Job se llama `accidentalidad_barranquilla_pipeline_<catalog_name>` y contiene
`bronze_ingestion -> silver_transformation`, con `gold_and_training` opcional.

- Crear o volver a desplegar sincroniza la definición completa mediante `jobs.reset`.
- Los Jobs duplicados y una ejecución activa bloquean el despliegue.
- El Job antiguo sin sufijo de catálogo no se elimina ni migra automáticamente.
- Se permite una ejecución concurrente; las tareas tienen timeout y reintentos acotados.
- ML no tiene reintento automático porque registrar una versión es una operación con efecto persistente.
- `run_job=false` solo despliega; `true` inicia, espera y exige resultado `SUCCESS`.
- El Job siempre envía `promote_champion=false` a ML.

La definición del repositorio es la fuente de configuración del Job: el despliegue
reemplaza también ajustes manuales que no estén representados en ella. Añada allí las
notificaciones y demás opciones operativas que necesite conservar. `source=WORKSPACE`
ejecuta los notebooks del Git Folder; fije su revisión y evite editarlo durante una ejecución.

La reconciliación de un Job existente sigue la API oficial de
[Databricks Jobs](https://databricks-sdk-py.readthedocs.io/en/stable/workspace/jobs/jobs.html).

## Machine Learning

Gold mantiene una fila por accidente. El objetivo `tiene_victimas` deriva de `gravedad`:
`SOLO DAÑOS=0`, `CON HERIDOS/CON MUERTOS=1`. La gravedad, los conteos de heridos/muertos
y la tabla de víctimas no se usan como features.

Se utilizan mes, día de semana, hora, localidad, clase de accidente y coordenadas.
Es una clasificación contextual del accidente: debe comprobarse que cada campo esté
disponible en el instante previsto de uso; no predice que vaya a ocurrir un accidente.

Gold verifica unicidad, claves, año, horas válidas y etiquetas. Las etiquetas desconocidas
se auditan y se copian a `quality.unknown_labels`; por defecto bloquean la publicación.
`max_unknown_labels` permite una tolerancia explícita, siempre contabilizando las exclusiones.
Antes de `toPandas`, se exige el límite `max_driver_rows` (100000 por defecto).

| Partición | Periodo | Uso |
|---|---|---|
| Entrenamiento | 2018–2020 | Ajuste del preprocesador y modelos |
| Validación | 2021 | Selección por F1 y decisión de promoción |
| Prueba | 2022 | Evaluación final únicamente del candidato seleccionado |

Cada partición debe tener filas y ambas clases. Los años fuera del periodo se contabilizan
y excluyen del entrenamiento/evaluación. Se compara Regresión Logística y Random Forest,
con imputación, escalado numérico y one-hot de categorías. Cada candidato tiene un
preprocesador independiente y se compara con un baseline de clase mayoritaria.

MLflow registra hiperparámetros, accuracy, precision, recall, F1, ROC-AUC, average precision
(`pr_auc`), reportes, firma, ejemplo de entrada, versiones exactas de bibliotecas, hashes de
código, commit cuando está disponible, exclusiones y versiones Delta de entrada. Los requisitos
del modelo se registran con versiones exactas mediante
[MLflow sklearn](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.sklearn.html).

El candidato elegido conserva su entrenamiento 2018–2020 y se registra como una nueva versión
de `gold.modelo_riesgo_victimas`. `promote_champion=false` permite registrar e inspeccionar
sin cambiar el modelo vigente. Con `true`, el candidato debe:

1. Alcanzar `minimum_validation_f1` (0.5 por defecto).
2. Superar estrictamente el baseline en validación.
3. Superar a Champion, si existe, en esa misma validación, por más de `minimum_improvement`.

Un Champion sin evidencia de entrenamiento anterior a 2021 bloquea la comparación. La
prueba final no decide la promoción. No ajuste repetidamente decisiones observando sus
resultados: las siguientes iteraciones requieren otro periodo de prueba. Solo debe haber
una promoción en curso por modelo; esta implementación no ofrece bloqueo de alias concurrente.

La inferencia desde la versión registrada se compara con el modelo seleccionado; si hubo
promoción, también se comprueba el alias Champion. Una repetición del entrenamiento puede
crear una nueva versión, incluso si los datos y parámetros son iguales.

## Parámetros principales

| Parámetro | Notebook | Predeterminado |
|---|---|---|
| catalog_name | Todos | accidentalidad_databricks |
| enforce_reference_counts | Bronze / Job | true |
| max_vehicle_orphans | Silver / Job | 3 |
| include_ml | Job | false |
| run_job | Job | false |
| existing_cluster_id | Job | Vacío: serverless |
| reader_group | Gobernanza | Vacío |
| apply_grants / verify_reader | Gobernanza | false / false |
| promote_champion | ML | false |
| minimum_validation_f1 / minimum_improvement | ML | 0.5 / 0.0 |
| max_unknown_labels | ML | 0 |
| max_driver_rows | ML | 100000 |

## Comprobaciones y evidencia

Desde la raíz del repositorio, con Python 3.10 o posterior y sin dependencias externas:

```bash
python3 -m unittest discover -s tests -v
```

La suite cubre límites temporales, selección independiente del test, promoción,
configuración inválida, creación/actualización de Jobs y comportamiento bloqueante de
calidad. Simula SDK y persistencia Spark; también analiza sintácticamente los notebooks.
GitHub Actions ejecuta estas comprobaciones en cada push y pull request.

La [guía de validación en Databricks](docs/VALIDACION.md) describe las comprobaciones con
fuentes reales. Solo después de completarla corresponde afirmar que la ejecución integral,
los permisos y el registro del modelo están verificados. El repositorio no certifica los
conteos originales, la disponibilidad del compute ni los permisos de un workspace concreto.
