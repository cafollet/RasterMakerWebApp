import geopandas as gpd
import pandas as pd
import scipy.interpolate
import xarray as xr
import rioxarray
import argparse
import json
import math
import numpy as np
from shapely.geometry import Point
# from scipy.spatial import KDTree
from sklearn.neighbors import KDTree
from typing import Literal
from io import BytesIO
from config import main_logger


def y2lat(y, R):
    """Convert Mercator y-coordinate to latitude in degrees."""
    return math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2.0)

def lat2y(lat, R):
    """Convert latitude in degrees to Mercator y-coordinate."""
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R

def x2lng(x, R):
    """Convert Mercator x-coordinate to longitude in degrees."""
    return math.degrees(x / R)

def lng2x(lng, R):
    """Convert longitude in degrees to Mercator x-coordinate."""
    return math.radians(lng) * R

def mercator(coord: tuple[float, float] | tuple[float, str], inverse=False) -> tuple[float, float] | float:
    """
    Convert between geographic coordinates and Mercator projection coordinates.

    Args:
        coord: Tuple containing either (longitude, latitude) or (value, 'x'/'y')
        inverse: If True, convert from Mercator to geographic; otherwise, convert from geographic to Mercator

    Returns:
        Tuple of converted coordinates or a single coordinate value
    """
    _radius = 6378137.0  # radius of earth @ equator
    if isinstance(coord[1], (float, int)):
        if not inverse:
            x = lng2x(coord[0], _radius)
            y = lat2y(coord[1], _radius)
            return x, y
        else:
            long = x2lng(coord[0], _radius)
            lat = y2lat(coord[1], _radius)
            return long, lat
    else:
        if not inverse:
            if coord[1] == "x":
                return lng2x(coord[0], _radius)
            elif coord[1] == "y":
                return lat2y(coord[0], _radius)
        else:
            if coord[1] == "x":
                return x2lng(coord[0], _radius)
            elif coord[1] == "y":
                return y2lat(coord[0], _radius)

def interpolate(points, values, grid_x, grid_y, type_: Literal["Linear", "IDW", "Nearest", "Density"] ="IDW", power=2):
    """
    Perform spatial Interpolation.

    Args:
        points: Array of coordinate points
        values: Values at each point
        grid_x: X-coordinates of grid points
        grid_y: Y-coordinates of grid points
        type_: type of interpolation to apply
        power: Power parameter for IDW (default=2)

    Returns:
        Interpolated values on the grid
    """

    try:
        if type_ == "IDW" or type_ == "Density":
            # tree = KDTree(points, compact_nodes=False, balanced_tree=False)
            tree = KDTree(points)
            main_logger.info("\t\tKDTree Created")

            grid_points = np.column_stack((grid_x.ravel(), grid_y.ravel()))
            main_logger.info("\t\tGrid points Created")


            try:
                # distances, indices = tree.query(grid_points, k=max(len(grid_x), len(grid_y)), workers=-1)
                distances, indices = tree.query(grid_points, k=max(len(grid_x), len(grid_y)))
                main_logger.info("\t\tDistances/indices Created")
            except BaseException as e:
                main_logger.info(f"THERE WAS A PROBLEM: {e}")



            if type_ == "IDW":
                weights = 1.0 / (distances ** power)
                interpolated_values = np.sum(weights * values[indices], axis=1) / np.sum(weights, axis=1)
            else:
                weights = 1.0 / distances
                interpolated_values = np.sum(weights * values[indices], axis=1)
        else:
            type_ = type_.lower()
            main_logger.info("\t\tType Created")

            interpolated_values = scipy.interpolate.griddata(points, values, (grid_x, grid_y), type_, fill_value=0)

        return interpolated_values.reshape(grid_x.shape)
    except Exception as e:
        main_logger.info(e)
        return None



def generate_raster_file(in_fp, out_fp, col_weight, geom):
    try:
        main_logger.info("generate_raster_file Started")
        # Load and clean up data
        data = pd.read_csv(in_fp)
        points = []
        df = data.drop(data[data[geom[1]] == 0.0].index)
        df = df.drop(df[df[geom[0]] == 0.0].index)

        if "Count" in col_weight.keys():
            df["Count"] = [1 for _ in range(df[list(df.columns)[0]].size)]

        # Convert geographic coordinates to Mercator points
        for i, row in df.iterrows():
            point = Point(mercator((row[geom[1]], row[geom[0]])))
            points.append(point)

        # Create GeoDataFrame
        df['geometry'] = points
        gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
        main_logger.info("\tcreated and stored GeoDF")
        # Extract coordinates and values
        coords = np.column_stack((gdf.geometry.x, gdf.geometry.y))

        # Compute weighted values
        cols_weights = {}
        for key in col_weight:

            keys = list(col_weight.keys())
            if isinstance(col_weight[key][0], float):
                val = col_weight[key][0]
            else:
                val = float(col_weight[key][0])
            weighted_values = df[key].values * val
            cols_weights[key] = weighted_values


        # Define grid for interpolation
        xmin, ymin, xmax, ymax = gdf.total_bounds
        res = 100  # Resolution in meters Originally 50 - maybe this could be added to script args?
        grid_x, grid_y = np.mgrid[xmin:xmax:res, ymax:ymin:-res]
        main_logger.info("\tcreated meshgrid")

        # Perform IDW interpolation with values
        interpolated_grid = np.zeros_like(grid_x)
        for key in col_weight:
            main_logger.info(f"\tKey \"{key}\" loading")
            interpolated_grid += interpolate(coords, cols_weights[key], grid_x, grid_y, col_weight[key][1])

        # Find max value and normalize
        maximum = np.max(interpolated_grid)
        interpolated_grid = interpolated_grid / maximum

        # Create xarray DataArray
        da = xr.DataArray(
            interpolated_grid,
        dims=["x", "y"],
            coords={"y": np.arange(ymax, ymin, -res), "x": np.arange(xmin, xmax, res)}
        )
        main_logger.info("\t created dataarray")

        # Transpose dimensions to match raster format expectations
        da = da.transpose('y', 'x')


        # Convert to raster dataset
        raster = da.rio.write_crs("EPSG:3857").rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
        raster = raster.rio.reproject("EPSG:4326")

        # Write to file
        if isinstance(out_fp, BytesIO):
            # with out_fp as buffer:
            raster.astype('float32').rio.to_raster(out_fp, driver='GTiff', compress="LDZ")
            out_fp.seek(0)
            main_logger.info(f"\tRaster file saved to {out_fp}")
        else:
            raster.astype('float32').rio.to_raster(f"{out_fp}", driver='GTiff', compress="LDZ")
            main_logger.info(f"\tRaster file saved to {out_fp}.tif")
    except Exception as e:
        main_logger.info(e)

if __name__ == "__main__":
    # Set up command line argument parser
    parser = argparse.ArgumentParser(
        "generates a raster img file from a csv file, and one or multiple columns within the file")
    parser.add_argument("in_fp", help="The file path that the csv file is located", type=str)
    parser.add_argument("out_fp", help="The file path you wish to place the raster file.", type=str)
    parser.add_argument("col_weight",
                        help="The column names and associating weight you want to apply (eg. '{\"col\":weight}')",
                        type=str)
    parser.add_argument("geom",
                        help="The names of the geometry columns, in degrees WGS_84 (eg. \"lat_col\" \"long_col\" ",
                        type=str, nargs=2)
    args = parser.parse_args()

    generate_raster_file(args.in_fp, args.out_fp, json.loads(args.col_weight), args.geom)