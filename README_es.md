# cl-census24-zone-design

## Resumen

Este repositorio contiene herramientas y flujos de trabajo para el preprocesamiento de los datos poligonales del Censo 2024 de Chile, con el objetivo de apoyar el diseño de zonas estadísticas.

El objetivo principal es transformar las unidades censales urbanas más pequeñas, conocidas en Chile como manzanas censales, que fueron originalmente creadas como polígonos separados con espacios entre ellos, en una representación espacial contigua.

Las áreas resultantes serán adecuados insumos para software de diseño de zonas que requiere polígonos contiguos para identificar unidades vecinas potenciales para su fusión. Este proceso se utiliza comúnmente para generar zonas que permitan la publicación de estadísticas de áreas pequeñas y faciliten el análisis espacial con poblaciones más estables.

---

![Voronoi-based contiguous polygons](images/contiguous_polygons.png)

## Estado del Proyecto 🚧

Trabajo en progreso.

Este proyecto se encuentra en desarrollo activo.  
Los métodos, estructuras de datos y resultados pueden cambiar a medida que se refine el flujo de trabajo.

---

## Objetivos Específicos

- Integrar los conjuntos de datos de las unidades censales urbanas y rurales más pequeñas (manzanas censales y entidades rurales) en un único conjunto unificado
- Convertir geometrías multipartes en polígonos de una sola parte, incluyendo:
  - Relabellado de identificadores únicos
  - Reasignación de la población en casos de división
- Generar polígonos de Voronoi (Thiessen) basados en las unidades espaciales censales más pequeñas disponibles
- Asegurar la consistencia geométrica y topológica de las áreas resultantes basadas en Voronoi, incluyendo:
  - Contigüidad
  - Ausencia de huecos y superposiciones
  - Geometrías poligonales válidas

---

## Resultados Esperados

- Unidades espaciales listas para análisis y construcción de zonas estadísticas
- Flujos de trabajo reproducibles implementados en Python

---

## Aviso

Este repositorio **no es un producto oficial** del Instituto Nacional de Estadísticas de Chile (INE).  
Está destinado únicamente a la investigación, experimentación y desarrollo metodológico.
