import geopandas as gpd
from rtree import index

class HiddenPolygonProcessor:
    """Handles identification and processing of hidden polygons."""
    
    @staticmethod
    def find_hidden_polygons(gdf):
        hidden_polygons = []

        for idx, poly in gdf.iterrows():
            for _, other_poly in gdf.iterrows():
            # Compute the difference between the polygons
                if poly['geometry'].intersects(other_poly['geometry']) and poly['geometry'] != other_poly['geometry']:
                    diff = poly['geometry'].difference(other_poly['geometry'])
                    if diff.is_empty:
                        hidden_polygons.append(poly)

        hidden_gdf = gpd.GeoDataFrame(hidden_polygons, columns=['geometry'])

        hidden_gdf.crs = gdf.crs

        hidden_indices = hidden_gdf.index

        return hidden_gdf, hidden_indices
    
    @staticmethod
    def find_partial_overlaps(gdf, min_overlap_area=1.0):
        """
        Find polygons that partially overlap with others.
        
        Args:
            gdf (GeoDataFrame): Input polygons to check
            min_overlap_area (float): Minimum overlap area to consider
            
        Returns:
            tuple: (overlap_gdf, overlap_indices)
        """
    
        idx = index.Index()
        for i, geom in enumerate(gdf.geometry):
            idx.insert(i, geom.bounds)
    
        overlap_indices = set()
        overlapping_pairs = []
        processed_pairs = set()

        # First pass: identify all overlaps
        for i, (_, row) in enumerate(gdf.iterrows()):
            candidates = list(idx.intersection(row.geometry.bounds))
        
            for j in candidates:
                if i >= j:
                    continue
                other_geom = gdf.iloc[j].geometry
                intersection = row.geometry.intersection(other_geom)
            
                if (not intersection.is_empty and 
                    intersection.area >= min_overlap_area and
                    not row.geometry.equals(other_geom)):
                
                    overlap_indices.add(i)
                    overlap_indices.add(j)
                    if (j, i) not in processed_pairs:
                        overlapping_pairs.append((i, j, intersection))
                        processed_pairs.add((i, j))

        modified_gdf = gdf.copy()
    
        # Process each overlapping pair to distribute overlaps
        for i, j, intersection in overlapping_pairs:
            geom_i = modified_gdf.loc[i, 'geometry']
            geom_j = modified_gdf.loc[j, 'geometry']
        
            # Decision rule: keep overlap in the smaller polygon
            if geom_i.area < geom_j.area:

                modified_gdf.loc[j, 'geometry'] = geom_j.difference(intersection)
            else:

                modified_gdf.loc[i, 'geometry'] = geom_i.difference(intersection)
    
        overlap_gdf = modified_gdf.iloc[list(overlap_indices)].copy()
    
        return overlap_gdf, list(overlap_indices)