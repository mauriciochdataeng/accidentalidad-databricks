# Preparación de las fuentes

El repositorio no contiene los datos originales. Se necesitan cuatro instantáneas CSV
completas del histórico de accidentalidad vial de Barranquilla, con estos nombres exactos:

| Archivo | Filas del lote de referencia | Grano |
|---|---:|---|
| accidentes.csv | 23212 | Accidente |
| causas.csv | 23212 | Causa por accidente en este lote |
| vehiculos.csv | 46128 | Vehículo involucrado |
| victimas.csv | 11328 | Víctima |

La URL, versión y licencia de las fuentes originales **no están documentadas en el
repositorio recibido**. Obtenga los archivos del material original del curso o de su
proveedor y registre su procedencia antes de afirmar que la extracción es reproducible.
No se ha añadido una URL inferida ni se han sustituido los datos por datos sintéticos.

1. Ejecute `00_Setup/00_Configuracion.ipynb` en un workspace con Unity Catalog.
2. En Catalog Explorer abra `<catalog_name> > bronze > Volumes > raw_files`.
3. Cargue los cuatro archivos en la raíz del Volume, conservando nombres y encabezados.
4. Ejecute Bronze; usa UTF-8, coma como delimitador, encabezado y lectura como texto.
   Las coordenadas con coma decimal deben estar correctamente entrecomilladas en el CSV.
   Si su fuente usa otro formato, adapte el contrato de lectura explícitamente.
5. No modifique los archivos hasta que termine el pipeline. Cada entrega debe contener
   la instantánea completa; un archivo con solo nuevas filas reemplazaría el histórico.

Bronze valida todos los encabezados definidos en `renombres_*` del notebook y conserva
los campos de negocio. Se admiten los errores originales conocidos `Corquis` y
`Corrdenada X` según cada archivo. Un esquema distinto requiere revisar el mapeo;
no se renombra silenciosamente una columna desconocida.

Para el lote de referencia deje `enforce_reference_counts=true`. Para una nueva
instantánea completa, use `false` y revise fechas, categorías y tolerancia de huérfanos.

Registre al menos proveedor, URL o identificador, fecha de descarga, periodo cubierto,
licencia y hashes SHA-256 de los cuatro CSV en el inventario de su entrega. Puede calcular
los hashes sin leer el contenido en pantalla:

```bash
shasum -a 256 /ruta/al/lote/accidentes.csv /ruta/al/lote/causas.csv /ruta/al/lote/vehiculos.csv /ruta/al/lote/victimas.csv
```

Los CSV locales están excluidos de Git. Evite subir identificadores personales a un
repositorio público; aplique los permisos del proveedor y del workspace.
