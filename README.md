# cl-census24-zone-design

## Overview

This repository contains tools and workflows to preprocess Chilean Census 2024 polygon data in support of statistical zone design.

The primary objective is to transform the smallest urban census areas, known in Chile as manzanas censales, which were originally created as separate polygon features with gaps between them, into a contiguous spatial representation.

The resulting areas will be suitable for use as inputs in zone design software that requires contiguous polygons to identify potential neighboring units for merging. This process is commonly used to generate zones that support the release of small-area statistics and facilitate spatial analysis with more stable population estimates.

![Voronoi-based contiguous polygons](images/contiguous_polygons.png)

## Project Status 🚧

Work in progress.

This project is under active development.  
Methods, data structures, and outputs may change as the workflow is refined.


## Specific Aims

- Integrate the urban and rural smallest census polygon datasets (manzanas censales and entidades rurales) into a single, unified dataset
- Convert multipart geometries to single-part polygons, including:
  - Relabelling unique identifiers
  - Reassigning population counts where splits occur
- Generate Voronoi (Thiessen) polygons based on the smallest available census spatial units
- Ensure geometric and topological consistency of the resulting Voronoi-based areas, including:
  - Contiguity
  - Absence of gaps and overlaps
  - Valid polygon geometries

## Data Access

Chilean Census 2024 polygon data can be downloaded from [censo2024.ine.gob.cl](https://censo2024.ine.gob.cl/resultados/) in the "Cartografía Censal" section.  

To reproduce the workflows in this repository, it is necessary to download the data in GeoParquet format, which allows faster processing.  

The files should be stored decompressed in the `data/raw` folder.

## Environment Setup

This project includes a Conda environment configuration file.

To create the environment, run:

```bash
conda env create -f environment.yml
```

Then activate it:

```bash
conda activate cl-census24
```

## Workflow

<details>
  <summary><strong> Step 1: Combine and Standardise Chilean Census Polygons </strong></summary>

Run the following script:

```python
python multipart_relabeller.py 
```

By default, this script merges and standardises the raw urban (manzanas) and rural (entidades) census polygons for a predefined list of communes, which are located in the southeastern area of the Metropolitan Region.

To process a different set of communes, use the `-lc` flag to provide a list of commune IDs (separated by spaces) located in the `data/raw` directory. The script will generate a spatial file called `processed_polygons.parquet` in the `data/processed` folder.
To explore the parameters use:

```python
python multipart_relabeller.py --help
```

</details>

<details>
  <summary><strong> Step 2: Generate Voronoi polygons constrained by boundaries </strong></summary>

This step generates Voronoi diagrams using the preprocessed polygons, with each diagram constrained by commune boundaries.

By default, the process is parallelised across 12 CPU cores for performance, dividing each commune into intermediate areas. This can be adjusted via the script arguments.

To view available options and default parameters:

```python
 python voronoi_polys.py --help
```

To execute the default workflow:

```python
 python voronoi_polys.py -i processed_polygons.parquet --overlay-hidden
```

To generate Voronoi polygons for a custom list of communes, provide their codes using the -l flag. You can find the codes in the "Código Comuna 2018" column of the provided [Excel file](data/raw/CUT_2018_v04.xlsx).

Example with specific commune codes:

```python
 python voronoi_polys.py -i processed_polygons.parquet -l 5701 5702 5703
```

The process will generate a file named `voronoi.gpkg` containing:

- One layer per commune with constrained Voronoi diagrams.
- A combined layer that merges all commune-level Voronoi polygons.

</details>


## Disclaimer

This repository is **not an official product** of the Chilean National Statistics Institute (INE).  
It is intended solely for research, experimentation, and methodological development.

## Versión en Español

Para la versión en español de este README, haga clic [aquí](README_es.md).