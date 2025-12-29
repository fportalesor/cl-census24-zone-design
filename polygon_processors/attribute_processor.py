import pandas as pd
import numpy as np
from unidecode import unidecode

class AttributeCalculator():
    """
    A class to calculate and downscale socioeconomic attributes for polygons.

    This class handles loading socioeconomic data, adjusting proportions
    using proxies like education, and computing population counts
    for low, middle, and high socioeconomic categories.
    """

    def __init__(self, input_data=None, poly_id="block_id", 
                 ):
        """
        Initialise the AttributeCalculator.

        Args:
            input_data (GeoDataFrame, optional): Polygon input data with population
                and other attributes. Defaults to None.
            poly_id (str, optional): Column name identifying polygons. Defaults to "block_id".
        """
        self.data = input_data
        self.poly_id = poly_id

    def _load_commune_socioeconomic_data(self, se_data_path, aux_data_path):
        """
        Load and process commune-level stratified socioeconomic data from AIM Chile.

        Data source: https://aimchile.cl/gse-chile/

        Args:
            se_data_path (str or Path): Path to the main socioeconomic Excel file.
            aux_data_path (str or Path): Path to the auxiliary Excel file containing
                commune names and codes.

        Returns:
            pandas.DataFrame: DataFrame with columns:
                - commune_id
                - p_high
                - p_middle
                - p_low
        """
        data = pd.read_excel(se_data_path, skiprows=3)
        data = data.drop(data.columns[-1], axis=1)
        data = data.rename(columns={data.columns[0]: "commune"})
        data["commune"] = data["commune"].str.upper().apply(unidecode)
        
        aux = pd.read_excel(aux_data_path)
        aux = aux.rename(columns={"Nombre Comuna": "commune",
                                  "Código Comuna 2018": "commune_id"})
        
        aux["commune"] = aux["commune"].str.upper().apply(unidecode)
        aux = aux[["commune", "commune_id"]]
        data = aux.merge(data, on="commune", how="left")
        data = data.loc[data["commune_id"].notna()]
        data["commune_id"] = data["commune_id"].astype(int)

        data["p_high"] = (data["AB"] + data["C1a"] + data["C1b"]) / 100
        data["p_middle"] = (data["C2"] + data["C3"]) / 100
        data["p_low"] = (data["D"] + data["E"]) / 100
        
        data = data[["commune_id", "p_high", "p_middle", "p_low"]]

        return data

    def socioeconomic_downscaling(
        self,
        pop_col="n_per",
        edu_col="prom_escolaridad18",
        alpha=0.2,
        se_data=None
    ):
        """
        Downscale socioeconomic proportions using education as a proxy

        Args:
            pop_col (str, optional): Column name for total population per polygon.
                Defaults to "n_per".
            edu_col (str, optional): Column name for education proxy.
                Defaults to "prom_escolaridad18".
            alpha (float, optional): Adjustment intensity factor.
            se_data (pandas.DataFrame): Socioeconomic proportions per commune with
                columns 'commune_id', 'p_low', 'p_middle', 'p_high'.

        Returns:
            geopandas.GeoDataFrame: Input GeoDataFrame with added columns:
                - pop_low
                - pop_middle
                - pop_high
                - adj_p_low
                - adj_p_middle
                - adj_p_high
        """
        data = self.data.copy()
        data = data.merge(se_data, on="commune_id", how="left")

        # Percentile of education
        data["edu_pctl"] = data[edu_col].rank(pct=True)	

        # Deviation from mean
        delta = data["edu_pctl"] - 0.5
        delta_smooth = np.tanh(3 * delta)

        # Smooth adjustment of proportions
        data["adj_p_high"] = data["p_high"] + alpha * delta_smooth
        data["adj_p_low"] = data["p_low"] - alpha * delta_smooth
        data["adj_p_middle"] = 1 - data["adj_p_high"] - data["adj_p_low"]

        props = ["adj_p_low", "adj_p_middle", "adj_p_high"]
        data[props] = data[props].clip(lower=0)
        data[props] = data[props].div(data[props].sum(axis=1), axis=0)

        # Convert proportions to counts
        data["pop_low"] = (data[pop_col] * data["adj_p_low"]).round().astype(int)
        data["pop_middle"] = (data[pop_col] * data["adj_p_middle"]).round().astype(int)
        data["pop_high"] = data[pop_col] - data["pop_low"] - data["pop_middle"]

        return data
