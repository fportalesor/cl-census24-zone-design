import pandas as pd
import geopandas as gpd
import numpy as np
from polygon_processors import PolygonProcessor


class MultipartPolygonRelabeller(PolygonProcessor):
    """
    Processor for handling multipart polygons.

    Identifies multipart polygons and resolves them using one of two strategies:
    - Distribute values across single parts using OpenBuildings area as a proxy.
    - Combine multipart polygons with a single adjacent polygon, summing count
      columns and computing population-weighted averages for other numeric fields.

    Geometries are merged, CRS is preserved, and new polygon IDs are generated
    to reflect the resulting polygons.
    """

    def __init__(
        self,
        input_data=None,
        id_length=16,
        poly_id="block_id",
        num_cols=["n_per", "n_vp_ocupada", "prom_escolaridad18"],
        count_cols=["n_per", "n_vp_ocupada"]
    ):
        self.data = input_data
        self.poly_id = poly_id
        self.id_length = id_length
        self.num_cols = num_cols
        self.count_cols = count_cols
        self.generated_ids = set()

        missing = set(count_cols) - set(num_cols)
        if missing:
            raise ValueError(f"count_cols must be a subset of num_cols: {missing}")


    def _relabel_multipart_blocks(self):
        """
        Identify blocks/entities with multiple polygons and create new IDs.
        
        Returns:
            GeoDataFrame: Duplicated polygons with new IDs
        """
        self.data[self.poly_id] = self.data[self.poly_id].astype(int).astype(str)
        self.data["orig_id"] = self.data[self.poly_id]

        self.data, dup = self.identify_multipart_polygons(
            self.data, self.poly_id, keep_largest=False)

        # Create sequential counts for each duplicated ID
        dup = dup.copy()
        dup['count'] = dup.groupby(self.poly_id).cumcount() + 1
        dup = dup.reset_index(drop=True)

        # Create new unique IDs by appending count
        dup['count'] = dup['count'].astype(str).str.zfill(2)
        dup[self.poly_id] = dup[self.poly_id] + dup["count"]

        dup["was_multipart"] = 1

        # Combine with non-duplicated polygons
        original_ids = dup[self.poly_id].str[:-2]
        self.data = self.data.loc[~self.data[self.poly_id].isin(original_ids)]
        self.data["was_multipart"] = 0

        if not dup.empty:
            self.data = pd.concat([self.data, dup], axis=0, ignore_index=True, sort=False)
        else:
            self.data = self.data.reset_index(drop=True)

        self.data = self.data.reset_index(drop=True)

        # Ensure ID length is 16 characters
        self.data[self.poly_id] = self.data[self.poly_id].str.ljust(self.id_length, fillchar='0')

        expected_cols = ["commune_id", "commune", "orig_id", self.poly_id, "zone_type", "was_multipart", "geometry"] + self.num_cols
        available_cols = [col for col in expected_cols if col in self.data.columns]

        return self.data[available_cols].copy()

    def _generate_new_id(self, orig_id):
        base_id = str(orig_id)[:-2]
        
        # Consider both existing and already generated IDs
        existing_ids = set(self.data[self.poly_id].astype(str))
        used_ids = existing_ids.union(self.generated_ids)
        
        # Find all suffixes used for this base
        suffixes = [int(x[-3:]) for x in used_ids if str(x).startswith(base_id)]
        next_suffix = max(suffixes, default=0) + 1
        
        new_id = f"{base_id}{str(next_suffix).zfill(3)}"
        
        self.generated_ids.add(new_id)
        return new_id

    def _are_parts_contiguous(self, parts_gdf, min_shared_len):
        """
        Returns True if all polygons form a single contiguous set
        and each touching relationship has shared boundary >= min_shared_len.
        """
        geoms = list(parts_gdf.geometry)

        for i, g1 in enumerate(geoms):
            touches_any = False

            for j, g2 in enumerate(geoms):
                if i == j:
                    continue

                if g1.touches(g2):
                    shared = g1.boundary.intersection(g2.boundary).length
                    if shared >= min_shared_len:
                        touches_any = True
                        break

            if not touches_any and len(geoms) > 1:
                return False

        return True

    def _find_best_adjacent_polygon(
        self,
        parts_gdf,
        candidates_gdf,
        min_shared_len,
    ):
        best_idx = None
        best_shared = 0.0

        for idx, cand in candidates_gdf.iterrows():
            total_shared = 0.0
            valid = True

            for geom in parts_gdf.geometry:
                if not cand.geometry.touches(geom):
                    valid = False
                    break

                shared = cand.geometry.boundary.intersection(
                    geom.boundary
                ).length

                if shared < min_shared_len:
                    valid = False
                    break

                total_shared += shared

            if valid and total_shared > best_shared:
                best_shared = total_shared
                best_idx = idx

        return best_idx

    def _resolve_multipart_by_contiguity(
        self,
        dup_gdf,
        non_dup_gdf,
        poly_id,
        pop_col="n_per",
        orig_id_col="orig_id",
        min_shared_len=5.0,
    ):
        resolved_rows = []
        consumed_dup_idx = []
        consumed_nondup_idx = []

        for orig_id, parts in dup_gdf.groupby(orig_id_col):

            # STEP 1 — Direct contiguity
            if self._are_parts_contiguous(parts, min_shared_len):
                row = parts.iloc[0].copy()
                row.geometry = parts.geometry.union_all()
                row[poly_id] = orig_id
                row["was_multipart"] = 1
                row["comb_adj"] = 0

                resolved_rows.append(row)
                consumed_dup_idx.extend(parts.index)
                continue

            # STEP 2 — Strict single adjacent polygon
            candidate_idx = self._find_best_adjacent_polygon(
                parts,
                non_dup_gdf,
                min_shared_len,
            )

            if candidate_idx is not None:
                target = non_dup_gdf.loc[candidate_idx]

                new_row = self._merge_parts_and_targets(
                    parts,
                    [target],
                    poly_id,
                    orig_id,
                    orig_id_col,
                    pop_col,
                )

                resolved_rows.append(new_row)
                consumed_dup_idx.extend(parts.index)
                consumed_nondup_idx.append(candidate_idx)
                continue

            # STEP 3 — multi-adjacent fallback (two-hop)

            result = self._merge_remaining_with_two_targets(
                parts,
                non_dup_gdf,
                poly_id,
                orig_id,
                orig_id_col,
                pop_col,
                min_shared_len,
            )

            if result is not None:
                new_row, used_indices = result
                resolved_rows.append(new_row)
                consumed_dup_idx.extend(parts.index)
                consumed_nondup_idx.extend(used_indices)

        # Create the final GeoDataFrame
        # 1. Remove consumed duplicated polygons
        remaining_dup = dup_gdf.drop(index=consumed_dup_idx)
        
        # 2. Remove consumed non-duplicate polygons
        remaining_nondup = non_dup_gdf.drop(index=consumed_nondup_idx)
        
        # 3. Combine remaining non-duplicates with newly resolved rows
        if resolved_rows:
            # Create DataFrame from resolved rows
            resolved_df = pd.DataFrame(resolved_rows)
            
            # Combine everything first
            combined_df = pd.concat([remaining_nondup, resolved_df], ignore_index=True)
        else:
            combined_df = remaining_nondup.copy()
        
        # 4. Apply column filter
        keep_cols = ["commune", "commune_id", "sregion_id", "geometry", 
                    orig_id_col, poly_id, "was_multipart", "comb_adj"] + self.num_cols
        
        # Get available columns that actually exist in the combined DataFrame
        available_cols = [col for col in keep_cols if col in combined_df.columns]
        
        # Create the final GeoDataFrame with only the columns we want
        resolved_gdf = gpd.GeoDataFrame(
            combined_df[available_cols],
            geometry="geometry",
            crs=dup_gdf.crs
        )

        resolved_gdf[poly_id] = resolved_gdf[poly_id].str[:15]

        resolved_gdf[poly_id] = resolved_gdf[poly_id].str.ljust(15, "0")
        
        return resolved_gdf, remaining_dup


    def _merge_remaining_with_two_targets(
        self,
        parts,
        non_dup_gdf,
        poly_id,
        orig_id,
        orig_id_col,
        pop_col,
        min_shared_len,
    ):
        """
        Find a pair of contiguous non-dup polygons that together touch all duplicated parts.
        Only consider non-dup polygons that touch at least one part.
        """
        # STEP 1: Filter to only non-dup polygons that touch at least one part
        touching_candidates = []
        all_parts_idx = set(parts.index)
        
        for idx, cand in non_dup_gdf.iterrows():
            touches_any = False
            for part_idx, part in parts.iterrows():
                if cand.geometry.touches(part.geometry):
                    touches_any = True
                    break
            
            if touches_any:
                # Also precompute which specific parts this candidate touches
                touching_parts = set()
                for part_idx, part in parts.iterrows():
                    if cand.geometry.touches(part.geometry):
                        touching_parts.add(part_idx)
                
                touching_candidates.append((idx, cand, touching_parts))
        
        if len(touching_candidates) < 2:
            # Not enough touching candidates
            return None
        
        # STEP 2: Find pairs of touching candidates that:
        # 1. Are contiguous with each other (touch with min_shared_len)
        # 2. Together touch ALL duplicated parts
        valid_pairs = []
        
        n_candidates = len(touching_candidates)
        
        for i in range(n_candidates):
            idx1, cand1, touching_parts1 = touching_candidates[i]
            
            for j in range(i + 1, n_candidates):
                idx2, cand2, touching_parts2 = touching_candidates[j]
                
                # Check if they are contiguous with each other
                if not cand1.geometry.touches(cand2.geometry):
                    continue
                
                shared_len = cand1.geometry.boundary.intersection(
                    cand2.geometry.boundary
                ).length
                
                if shared_len < min_shared_len:
                    continue
                
                # Check if together they touch ALL parts
                union_touching = touching_parts1.union(touching_parts2)
                
                if union_touching != all_parts_idx:
                    continue
                
                # Calculate total shared boundary with parts for ranking
                total_shared = 0.0
                
                # Calculate for candidate 1
                for part_idx in touching_parts1:
                    part = parts.loc[part_idx]
                    total_shared += cand1.geometry.boundary.intersection(
                        part.geometry.boundary
                    ).length
                
                # Calculate for candidate 2
                for part_idx in touching_parts2:
                    part = parts.loc[part_idx]
                    total_shared += cand2.geometry.boundary.intersection(
                        part.geometry.boundary
                    ).length
                
                valid_pairs.append((idx1, idx2, total_shared, shared_len))
        
        if not valid_pairs:
            return None
        
        # STEP 3: Select the best pair
        # Sort by: 1) total shared boundary with parts (desc), 2) shared boundary between them
        valid_pairs.sort(key=lambda x: (x[2], x[3]), reverse=True)
        
        best_idx1, best_idx2, _, _ = valid_pairs[0]
        target1 = non_dup_gdf.loc[best_idx1]
        target2 = non_dup_gdf.loc[best_idx2]
        
        # STEP 4: Merge all together
        targets = [target1, target2]
        
        new_row = self._merge_parts_and_targets(
            parts,
            targets,
            poly_id,
            orig_id,
            orig_id_col,
            pop_col,
        )
        
        return new_row, [best_idx1, best_idx2]


    def _merge_parts_and_targets(
        self,
        parts,
        targets,
        poly_id,
        orig_id,
        orig_id_col,
        pop_col,
    ):
        # here we just take one of the duplicated rows
        base_dup = parts.iloc[0]

        new_geom = parts.geometry.union_all()
        for t in targets:
            new_geom = new_geom.union(t.geometry)

        # recalculate count cols
        counts_sum = base_dup[self.count_cols].copy()
        for t in targets:
            counts_sum += t[self.count_cols]

        # recalculate averaged cols
        avg_cols = [c for c in self.num_cols if c not in self.count_cols]

        pop_dup = base_dup[pop_col]
        pop_targets = sum(t[pop_col] for t in targets)
        total_pop = pop_dup + pop_targets

        if total_pop > 0:
            dup_avg = base_dup[avg_cols]

            targets_avg = (
                sum(t[avg_cols] * t[pop_col] for t in targets) / pop_targets
                if pop_targets > 0 else dup_avg
            )

            weighted_avg = (
                dup_avg * (pop_dup / total_pop) +
                targets_avg * (pop_targets / total_pop)
            )
        else:
            weighted_avg = base_dup[avg_cols]

        # Generate new orig_id by combining all IDs
        merged_orig_id = "_".join(
            [str(base_dup[orig_id_col])] + [str(t[orig_id_col]) for t in targets]
        )

        # output
        new_row = targets[0].copy()
        new_row.geometry = new_geom
        new_row[self.count_cols] = counts_sum
        new_row[avg_cols] = weighted_avg
        new_row["was_multipart"] = 1
        new_row["comb_adj"] = len(targets)
        new_row[orig_id_col] = merged_orig_id
        new_row[poly_id] = self._generate_new_id(orig_id)

        return new_row