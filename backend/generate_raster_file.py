import geopandas as gpd
import pandas as pd
import scipy.interpolate
import xarray as xr
import rioxarray
import argparse
import json
import math
import numpy as np
import gc
import logging
import traceback
from shapely.geometry import Point
from sklearn.neighbors import KDTree
from typing import Literal
from io import BytesIO

# Set up logger for this module
logger = logging.getLogger('processing.raster')


def y2lat(y, R):
    """Convert Mercator y-coordinate to latitude in degrees."""
    try:
        result = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2.0)
        logger.debug(f"Converted y={y} to lat={result}")
        return result
    except Exception as e:
        logger.error(f"Error in y2lat conversion: {str(e)}")
        raise

def lat2y(lat, R):
    """Convert latitude in degrees to Mercator y-coordinate."""
    try:
        result = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
        logger.debug(f"Converted lat={lat} to y={result}")
        return result
    except Exception as e:
        logger.error(f"Error in lat2y conversion: {str(e)}")
        raise

def x2lng(x, R):
    """Convert Mercator x-coordinate to longitude in degrees."""
    try:
        result = math.degrees(x / R)
        logger.debug(f"Converted x={x} to lng={result}")
        return result
    except Exception as e:
        logger.error(f"Error in x2lng conversion: {str(e)}")
        raise

def lng2x(lng, R):
    """Convert longitude in degrees to Mercator x-coordinate."""
    try:
        result = math.radians(lng) * R
        logger.debug(f"Converted lng={lng} to x={result}")
        return result
    except Exception as e:
        logger.error(f"Error in lng2x conversion: {str(e)}")
        raise

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
    
    try:
        if isinstance(coord[1], (float, int)):
            if not inverse:
                x = lng2x(coord[0], _radius)
                y = lat2y(coord[1], _radius)
                logger.debug(f"Converted geographic ({coord[0]}, {coord[1]}) to Mercator ({x}, {y})")
                return x, y
            else:
                long = x2lng(coord[0], _radius)
                lat = y2lat(coord[1], _radius)
                logger.debug(f"Converted Mercator ({coord[0]}, {coord[1]}) to geographic ({long}, {lat})")
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
    except Exception as e:
        logger.error(f"Error in mercator conversion: {str(e)}")
        raise

def interpolate(points, values, grid_x, grid_y, type_: Literal["Linear", "IDW", "Nearest", "Density"] ="IDW", power=2,
                max_neighbours=50, chunk_size=10000):
    """
    Perform spatial Interpolation.

    Args:
        points: Array of coordinate points
        values: Values at each point
        grid_x: X-coordinates of grid points
        grid_y: Y-coordinates of grid points
        type_: type of interpolation to apply
        power: Power parameter for IDW (default=2)
        max_neighbours: Maximum number of neighbours to consider
        chunk_size: Size of chunks for processing large grids

    Returns:
        Interpolated values on the grid
    """
    logger.info(f"Starting {type_} interpolation with {len(points)} points")
    logger.debug(f"Grid size: {grid_x.shape}, Power: {power}, Max neighbors: {max_neighbours}")

    try:
        if type_ == "IDW" or type_ == "Density":
            logger.debug("Creating KDTree for spatial indexing")
            tree = KDTree(points)
            logger.info("KDTree created successfully")

            grid_points = np.column_stack((grid_x.ravel(), grid_y.ravel()))
            logger.debug(f"Created grid with {len(grid_points)} points")

            k = min(max_neighbours, len(points))
            logger.debug(f"Using {k} nearest neighbors for interpolation")

            interpolated_values = np.zeros(len(grid_points))
            total_chunks = (len(grid_points) - 1) // chunk_size + 1
            
            for i in range(0, len(grid_points), chunk_size):
                end_idx = min(i + chunk_size, len(grid_points))
                chunk_points = grid_points[i:end_idx]
                chunk_num = i // chunk_size + 1
                
                logger.debug(f"Processing chunk {chunk_num}/{total_chunks}")
                distances, indices = tree.query(chunk_points, k=k)

                if type_ == "IDW":
                    distances = np.maximum(distances, 1e-10)  # Avoid division by zero
                    weights = 1.0 / (distances ** power)
                    interpolated_chunk = np.sum(weights * values[indices], axis=1) / np.sum(weights, axis=1)
                else:  # Density
                    distances = np.maximum(distances, 1e-10)
                    weights = 1.0 / distances
                    interpolated_chunk = np.sum(weights * values[indices], axis=1)

                interpolated_values[i:end_idx] = interpolated_chunk

                # Clean up memory
                del distances, indices, chunk_points
                if i % (5 * chunk_size) == 0:
                    gc.collect()
                    logger.debug("Performed garbage collection")

            logger.info(f"{type_} interpolation completed successfully")

        else:
            type_ = type_.lower()
            logger.info(f"Using scipy griddata for {type_} interpolation")
            interpolated_values = scipy.interpolate.griddata(points, values, (grid_x, grid_y), type_, fill_value=0)
            interpolated_values = interpolated_values.ravel()
            logger.info("Scipy interpolation completed successfully")

        return interpolated_values.reshape(grid_x.shape)
        
    except Exception as e:
        logger.error(f"Interpolation failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def generate_raster_file(in_fp, out_fp, col_weight, geom):
    """
    Generate a raster file from CSV data with weighted columns.
    
    Args:
        in_fp: Input file path or BytesIO object containing CSV data
        out_fp: Output file path or BytesIO object for raster
        col_weight: Dictionary of column weights and interpolation methods
        geom: List of geometry column names [lat_col, lon_col]
    """
    logger.info("="*60)
    logger.info("GENERATE RASTER FILE - START")
    logger.info("="*60)
    
    try:
        # Load and validate data
        logger.info("Loading CSV data")
        data = pd.read_csv(in_fp)
        logger.info(f"Loaded {len(data)} rows, {len(data.columns)} columns")
        
        # Clean data
        logger.debug("Removing rows with zero coordinates")
        initial_rows = len(data)
        df = data.drop(data[data[geom[1]] == 0.0].index)
        df = df.drop(df[df[geom[0]] == 0.0].index)
        logger.info(f"Removed {initial_rows - len(df)} rows with zero coordinates")

        # Add count column if needed
        if "Count" in col_weight.keys():
            logger.debug("Adding Count column")
            df["Count"] = [1 for _ in range(df[list(df.columns)[0]].size)]

        # Convert geographic coordinates to Mercator
        logger.info("Converting coordinates to Mercator projection")
        points = []
        for idx, (i, row) in enumerate(df.iterrows()):
            if idx % 1000 == 0:
                logger.debug(f"Processing coordinate {idx}/{len(df)}")
            point = Point(mercator((row[geom[1]], row[geom[0]])))
            points.append(point)

        # Create GeoDataFrame
        logger.info("Creating GeoDataFrame")
        df['geometry'] = points
        gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
        logger.info("GeoDataFrame created successfully")
        
        # Extract coordinates
        coords = np.column_stack((gdf.geometry.x, gdf.geometry.y))
        logger.debug(f"Extracted {len(coords)} coordinate pairs")

        # Process weighted columns
        logger.info("Computing weighted values for columns")
        cols_weights = {}
        for key in col_weight:
            logger.debug(f"Processing column: {key}")
            if isinstance(col_weight[key][0], float):
                val = col_weight[key][0]
            else:
                val = float(col_weight[key][0])
            
            weighted_values = df[key].values * val
            cols_weights[key] = weighted_values
            logger.debug(f"Column {key}: weight={val}, interpolation={col_weight[key][1]}")

        # Define grid bounds and resolution
        xmin, ymin, xmax, ymax = gdf.total_bounds
        logger.info(f"Bounds: xmin={xmin:.2f}, ymin={ymin:.2f}, xmax={xmax:.2f}, ymax={ymax:.2f}")

        # Calculate area and adjust resolution
        area = (xmax - xmin) * (ymax - ymin)
        if area > 1e10:  # Very large area
            res = 500
            logger.info(f"Very large area detected ({area:.2e}), using resolution: {res}")
        elif area > 1e9:
            res = 250
            logger.info(f"Large area detected ({area:.2e}), using resolution: {res}")
        else:
            res = 100
            logger.info(f"Standard area ({area:.2e}), using resolution: {res}")

        # Process in chunks to reduce memory usage
        chunk_size = 1000
        x_chunks = np.array_split(np.arange(xmin, xmax, res), (xmax - xmin) // (res * chunk_size) + 1)
        logger.info(f"Processing grid in {len(x_chunks)} chunks")

        interpolated_grid_full = []

        for chunk_idx, x_chunk in enumerate(x_chunks):
            logger.debug(f"Processing chunk {chunk_idx + 1}/{len(x_chunks)}")
            x_start, x_end = x_chunk[0], x_chunk[-1] + res
            grid_x_chunk, grid_y_chunk = np.mgrid[x_start:x_end:res, ymax:ymin:-res]

            # Perform interpolation on this chunk
            interpolated_chunk = np.zeros_like(grid_x_chunk)
            for key in col_weight:
                logger.debug(f"Interpolating {key} for chunk {chunk_idx + 1}")
                interpolated_chunk += interpolate(coords, cols_weights[key], grid_x_chunk, grid_y_chunk,
                                                  col_weight[key][1])

            interpolated_grid_full.append(interpolated_chunk)
            gc.collect()

        # Combine chunks
        logger.info("Combining interpolated chunks")
        interpolated_grid = np.hstack(interpolated_grid_full)

        # Normalize data
        maximum = np.max(interpolated_grid)
        logger.info(f"Maximum value before normalization: {maximum}")
        
        if maximum > 0:
            interpolated_grid = interpolated_grid / maximum
            logger.info("Grid normalized to [0, 1] range")
        else:
            logger.warning("Maximum value is 0, skipping normalization")

        # Create xarray DataArray
        logger.info("Creating xarray DataArray")
        da = xr.DataArray(
            interpolated_grid,
            dims=["x", "y"],
            coords={"y": np.arange(ymax, ymin, -res), "x": np.arange(xmin, xmax, res)}
        )
        logger.debug("DataArray created successfully")

        # Transpose dimensions
        da = da.transpose('y', 'x')
        logger.debug("Dimensions transposed")

        # Convert to raster and reproject
        logger.info("Converting to raster and reprojecting to EPSG:4326")
        raster = da.rio.write_crs("EPSG:3857").rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)
        raster = raster.rio.reproject("EPSG:4326")
        logger.info("Reprojection completed")

        # Write to output
        logger.info("Writing raster to output")
        if isinstance(out_fp, BytesIO):
            raster.astype('float32').rio.to_raster(out_fp, driver='GTiff', compress="LDZ")
            out_fp.seek(0)
            logger.info("Raster saved to BytesIO buffer")
        else:
            output_path = f"{out_fp}.tif" if not out_fp.endswith('.tif') else out_fp
            raster.astype('float32').rio.to_raster(output_path, driver='GTiff', compress="LDZ")
            logger.info(f"Raster saved to file: {output_path}")

        logger.info("="*60)
        logger.info("GENERATE RASTER FILE - COMPLETED")
        logger.info("="*60)
        
    except Exception as e:
        logger.error("="*60)
        logger.error("GENERATE RASTER FILE - FAILED")
        logger.error("="*60)
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    # Set up console logging for standalone execution
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(
        description="Generates a raster img file from a csv file, and one or multiple columns within the file")
    parser.add_argument("in_fp", help="The file path that the csv file is located", type=str)
    parser.add_argument("out_fp", help="The file path you wish to place the raster file.", type=str)
    parser.add_argument("col_weight",
                        help="The column names and associating weight you want to apply (eg. '{\"col\":weight}')",
                        type=str)
    parser.add_argument("geom",
                        help="The names of the geometry columns, in degrees WGS_84 (eg. \"lat_col\" \"long_col\" ",
                        type=str, nargs=2)
    args = parser.parse_args()

    logger.info(f"Running from command line with args: {args}")
    
    try:
        generate_raster_file(args.in_fp, args.out_fp, json.loads(args.col_weight), args.geom)
    except Exception as e:
        logger.error(f"Command line execution failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
