# cl-census24-zone-design

## Resumen

Este repositorio contiene herramientas y flujos de trabajo para el preprocesamiento de los datos poligonales del Censo 2024 de Chile, con el objetivo de apoyar el diseño de zonas estadísticas.

El objetivo principal es transformar las unidades censales urbanas más pequeñas, conocidas en Chile como manzanas censales, que fueron originalmente creadas como polígonos separados con espacios entre ellos, en una representación espacial contigua.

Las áreas resultantes serán adecuados insumos para el uso de software de diseño de zonas que requieren polígonos contiguos para identificar unidades vecinas potenciales para su fusión. Este proceso se utiliza comúnmente para generar zonas que permitan la publicación de estadísticas de áreas pequeñas y faciliten el análisis espacial con poblaciones más estables.


![Voronoi-based contiguous polygons](images/contiguous_polygons.png)

## Estado del Proyecto 🚧

Trabajo en progreso.

Este proyecto se encuentra en desarrollo activo.  
Los métodos, estructuras de datos y resultados pueden cambiar a medida que se refine el flujo de trabajo.


## Objetivos Específicos

- Integrar los conjuntos de datos de las unidades censales urbanas y rurales más pequeñas (manzanas censales y entidades rurales) en un único conjunto unificado
- Convertir geometrías multipartes en polígonos de una sola parte, incluyendo:
  - Recodificación de identificadores únicos
  - Reasignación de la población en casos de división
- Generar polígonos de Voronoi (Thiessen) basados en las unidades espaciales censales más pequeñas disponibles
- Asegurar la consistencia geométrica y topológica de las áreas resultantes basadas en Voronoi, incluyendo:
  - Contigüidad
  - Ausencia de huecos y superposiciones
  - Geometrías poligonales válidas

## Acceso a los Datos

Los datos poligonales del Censo 2024 de Chile se pueden descargar desde [censo2024.ine.gob.cl](https://censo2024.ine.gob.cl/resultados/) en la sección "Cartografía Censal".  

Para reproducir los flujos de trabajo de este repositorio, es necesario descargar los datos en formato GeoParquet, que permite un procesamiento más rápido.  

Los archivos deben guardarse descomprimidos en la carpeta `data/raw`.

## Configuración del Entorno

Este proyecto incluye un archivo de configuración para un entorno Conda.

Para crear el entorno, ejecute:

```bash
conda env create -f environment.yml
```

Luego, actívelo con:

```bash
conda activate cl-census24
```

## Flujo de Trabajo

<details>
  <summary><strong> Paso 1: Combinar y Estandarizar los Polígonos del Censo </strong></summary>

Ejecute el siguiente script:

```python
python multipart_relabeller.py 
```

Por defecto, este script combina y estandariza los polígonos censales urbanos (manzanas) y rurales (entidades) para una lista predefinida de comunas, ubicada en la zona sureste de la Región Metropolitana.

Para procesar un conjunto diferente de comunas, use la opción `-lc` para proporcionar una lista de códigos de comuna (separados por espacios) que se encuentren en el directorio `data/raw`.

El script generará un archivo espacial llamado `processed_polygons.parquet` en la carpeta `data/processed`.

Para explorar todos los parámetros disponibles:

```python
python multipart_relabeller.py --help
```

</details>

<details>
  <summary><strong> Paso 2: Generar Polígonos de Voronoi Restringidos por Límites </strong></summary>

Este paso genera diagramas de Voronoi utilizando los polígonos preprocesados, con cada diagrama restringido por los límites de las comunas.

Por defecto, el proceso se paraleliza en 12 núcleos de CPU para mejorar el rendimiento, dividiendo cada comuna en áreas intermedias. Este comportamiento se puede ajustar mediante los argumentos del script.

Para ver las opciones disponibles y los parámetros por defecto:

```python
 python voronoi_polys.py --help
```

Para ejecutar el flujo de trabajo por defecto:

```python
 python voronoi_polys.py -i processed_polygons.parquet --overlay-hidden
```

Para generar polígonos de Voronoi para una lista personalizada de comunas, indique sus códigos con la opción-l. Los códigos se encuentran en la columna "Código Comuna 2018" del [archivo Excel proporcionado](data/raw/CUT_2018_v04.xlsx).

Ejemplo con códigos específicos de comunas:

```python
 python voronoi_polys.py -i processed_polygons.parquet -l 5701 5702 5703
```

El proceso generará un archivo llamado `voronoi.gpkg` que contendrá:

- Una capa por comuna con diagramas de Voronoi restringidos.
- Una capa combinada que fusiona todos los polígonos de Voronoi a nivel comunal.

</details>


## Aviso

Este repositorio **no es un producto oficial** del Instituto Nacional de Estadísticas de Chile (INE).  
Está destinado únicamente a la investigación, experimentación y desarrollo metodológico.
