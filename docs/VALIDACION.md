# Validación de integración en Databricks

Esta guía se ejecuta con los archivos reales y una cuenta autorizada. No implica que las
comprobaciones ya se hayan realizado. Use un catálogo de prueba independiente y el Git
Folder completo. No use datos reales en un repositorio público.

## Preparación

- Registre el commit y los cambios locales, la versión de Runtime o del entorno
  serverless, las dependencias instaladas y la identidad ejecutora.
- En serverless, habilite Shared Serverless y conecte los notebooks del Git Folder al
  mismo compute compartido. El setup sincroniza `pyproject.toml` con `%uv sync`.
  Después de ejecutarlo, compruebe desde ML, sin celdas de instalación, que se pueden
  importar `mlflow`, `sklearn` y `databricks.sdk`. Registre el `uv.lock` generado.
  Esta comprobación requiere entorno versión 5 o superior y la función habilitada por
  un administrador. En un cluster clásico, instale requirements como biblioteca del
  cluster y omita las celdas de sincronización/reinicio del setup.
- Ejecute setup con un `catalog_name` de prueba. Compruebe schemas y el Volume.
- Prepare los cuatro CSV completos según `data/README.md` y registre sus hashes.
- Verifique que el compute y su identidad puedan leer el Volume, escribir tablas en
  las capas y en `quality`, crear/actualizar Jobs y registrar modelos cuando corresponda.

## Ejecución correcta

1. Ejecute Bronze con `enforce_reference_counts=true` para el lote de referencia.
2. Ejecute Silver; revise las filas huérfanas y su tolerancia. Confirme que la conciliación
   de víctimas pasa y que cada tabla conserva el número de filas del lote.
3. Consulte el reporte usando el identificador impreso por cada notebook:

   ```sql
   SELECT layer, dataset, rule, observed, expected, severity, passed, details
   FROM <catalog_name>.quality.check_results
   WHERE run_id = '<run_id>'
   ORDER BY layer, dataset, rule;
   ```

4. Ejecute la demo Delta. Exija controles finales verdaderos, un nuevo registro,
   actualización del existente y Time Travel mostrando el estado previo.
5. Despliegue el Job, cambie una opción como `include_ml` y vuelva a desplegar.
   Compruebe que conserva su ID y refleja la nueva definición. Ejecute con `run_job=true`:
   el notebook debe esperar y exigir `SUCCESS`.
6. Ejecute ML con `promote_champion=false`. Verifique periodos disjuntos, ambas clases,
   baseline, métricas `validation_*`, test solo para el ganador, versiones Delta y
   requisitos exactos del modelo. Confirme que registrar el candidato no cambia Champion.
7. Compruebe la igualdad entre predicciones del candidato seleccionado y el registrado.
8. Con una ejecución candidata revisada, pruebe la promoción explícita en el catálogo de
   prueba. Debe exigir los umbrales de validación y, si existe, comparación con Champion.

La prueba de 2022 deja de ser una evaluación independiente si se utiliza repetidamente
para modificar el modelo. No ajuste modelos con los resultados de esta guía sin reservar
un nuevo periodo de prueba.

## Fallos controlados

Use copias de las fuentes y un catálogo de prueba. Conserve el lote original para restaurar.
Antes de cada caso registre las versiones actuales de las tablas mediante
`DESCRIBE HISTORY <catalog_name>.<capa>.<tabla>`.

| Caso | Resultado esperado |
|---|---|
| Quitar un CSV del Volume de prueba | Bronze falla antes de publicar tablas |
| Cambiar un encabezado requerido | Bronze falla indicando las columnas ausentes |
| Reducir un CSV con conteos de referencia activados | Auditoría ERROR y ninguna publicación Bronze |
| Duplicar `croquis` de accidentes conservando filas o desactivando conteos de referencia | Silver falla por unicidad y no publica ninguna tabla Silver |
| Introducir fecha inválida o conteo `1.5` | Silver falla por conversión/coherencia o fracción, respectivamente |
| Añadir vehículos huérfanos por encima de la tolerancia | Filas de diagnóstico persistidas, ERROR y publicación Silver bloqueada |
| Usar tolerancia cero con el lote que tiene tres huérfanos | Silver bloqueado por integridad referencial |
| Cambiar una gravedad a una categoría desconocida | Gold audita la exclusión y falla con tolerancia cero |
| Introducir hora `25:80` | Gold falla por hora inválida |
| Reducir `max_driver_rows` por debajo del tamaño Gold | ML falla antes de recopilar datos en el driver |
| Vaciar una partición o dejarla con una sola clase | ML falla antes de entrenar |
| Solicitar promoción con mínimo inalcanzable | Se conserva la versión candidata; Champion no cambia |
| Intentar desplegar durante una ejecución activa | Se bloquea la actualización del Job |

Después de un control bloqueante, compruebe que las versiones de las tablas de la capa
publicada no cambiaron; el reporte y las tablas de diagnóstico sí pueden haber cambiado.
Un fallo de infraestructura durante las escrituras finales es un caso diferente: puede
haber publicación parcial y requiere repetir la ejecución con la misma instantánea.

## Gobernanza con dos identidades

1. Un administrador indica un grupo existente y aplica los grants con `apply_grants=true`.
2. Un miembro de ese grupo, sin propiedad ni grants adicionales de escritura, abre el
   notebook con `apply_grants=false` y `verify_reader=true`.
3. Exija consulta de Silver exitosa y rechazo explícito de la inserción sin filas.
4. Si la escritura se permite, la prueba falla: revise privilegios directos, grupos
   heredados y propiedad. El notebook no revoca permisos automáticamente.

La verificación ejecutada como propietario no sustituye esta comprobación.

## Evidencia de la entrega

Guarde enlaces al Job y a su ejecución terminada, reportes de calidad por run_id,
versiones Delta, experimento y runs de MLflow, versión candidata, decisión de promoción
y resultado de la prueba con identidad lectora. Registre las anomalías aceptadas y
cualquier ajuste al contrato de fuentes. Añada resultados al README solo con esta
evidencia; no convierta valores esperados en resultados observados.
