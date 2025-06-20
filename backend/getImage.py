from PIL import Image
import rasterio
import json
import logging
import traceback
from typing import *
from io import BytesIO, StringIO
import io

# Set up logger for this module
logger = logging.getLogger('processing.image')


def get_pixel_val(img: Image, x: int, y: int) -> float:
    """Get pixel value at specified coordinates"""
    try:
        pix = img.load()
        pixel = pix[x, y]
        logger.debug(f"Got pixel value at ({x}, {y}): {pixel}")
        return pixel
    except Exception as e:
        logger.error(f"Error getting pixel at ({x}, {y}): {str(e)}")
        raise


def set_pixel_val(img: Image, x: int, y: int, val: float | tuple[float, float, float, float]) -> Image:
    """Set pixel value at specified coordinates"""
    try:
        pix = img.load()
        pix[x, y] = val
        logger.debug(f"Set pixel value at ({x}, {y}) to: {val}")
        return img
    except Exception as e:
        logger.error(f"Error setting pixel at ({x}, {y}): {str(e)}")
        raise


def img_to_pixel(img_path: str | BytesIO):
    """Convert image to pixel dictionary with metadata"""
    logger.info("Converting image to pixel dictionary")
    
    try:
        val_dict = {}
        
        # Open dataset
        if isinstance(img_path, BytesIO):
            dataset = rasterio.open(img_path, driver="GTiff")
            logger.debug("Opened BytesIO stream as GeoTIFF")
        else:
            dataset = rasterio.open(img_path)
            logger.debug(f"Opened file: {img_path}")
        
        # Extract bounds
        bounds = dataset.bounds
        logger.info(f"Image bounds: {bounds}")
        
        val_dict["lbound"] = dataset.bounds[0]
        val_dict["bbound"] = dataset.bounds[1]
        val_dict["rbound"] = dataset.bounds[2]
        val_dict["tbound"] = dataset.bounds[3]

        # Get image dimensions
        im = Image.open(img_path)
        w, h = im.size
        val_dict["sizex"] = w
        val_dict["sizey"] = h
        logger.info(f"Image size: {w}x{h}")

        # Extract pixel values
        logger.debug("Extracting pixel values")
        pixel_count = 0
        for x in range(w):
            for y in range(h):
                val_dict[f"{x},{y}"] = {"name": get_pixel_val(im, x, y)}
                pixel_count += 1
                
                # Log progress for large images
                if pixel_count % 10000 == 0:
                    logger.debug(f"Processed {pixel_count}/{w*h} pixels")
        
        logger.info(f"Successfully extracted {pixel_count} pixels")
        return val_dict
        
    except Exception as e:
        logger.error(f"Failed to convert image to pixels: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def write_pix_json(fp: str | BytesIO, out_fp=None):
    """Write pixel data to JSON file or stream"""
    logger.info("Writing pixel data to JSON")
    
    try:
        # Convert image to pixel dictionary
        pixel_data = img_to_pixel(fp)
        
        if not out_fp:
            # Auto-generate output filename
            if isinstance(fp, str):
                for i, x in enumerate(fp):
                    if x == "." and not fp[i+1] == "/":
                        new_fp = fp[:i]
                        break
                output_path = f"{new_fp}_pix.json"
                
                with open(output_path, 'w') as f:
                    json.dump(pixel_data, f)
                logger.info(f"Pixel JSON written to file: {output_path}")
            else:
                logger.error("No output path specified for BytesIO input")
                raise ValueError("Output path required for BytesIO input")
                
        elif isinstance(out_fp, StringIO):
            json.dump(pixel_data, out_fp)
            logger.info("Pixel JSON written to StringIO stream")
            
        else:
            with open(out_fp, 'w') as f:
                json.dump(pixel_data, f)
            logger.info(f"Pixel JSON written to file: {out_fp}")
            
    except Exception as e:
        logger.error(f"Failed to write pixel JSON: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def convert_to_alpha(fp: str | BytesIO, replace: Literal[True] | str = True, out_fp=None):
    """Convert image to alpha channel format"""
    logger.info("Converting image to alpha channel format")
    
    try:
        # Determine output path
        if isinstance(replace, bool):
            new_fp = fp
            suffix = ""
        else:
            if isinstance(fp, str):
                for i, x in enumerate(fp):
                    if x == "." and not fp[i + 1] == "/":
                        new_fp = fp[:i] + replace
                        suffix = fp[i:]
                        break
            else:
                new_fp = fp
                suffix = ""
        
        # Open image
        if isinstance(fp, BytesIO):
            image = Image.open(fp)
            logger.debug("Opened BytesIO stream as image")
        else:
            image = Image.open(fp + suffix if suffix else fp)
            logger.debug(f"Opened image file: {fp + suffix if suffix else fp}")

        format = image.format
        logger.info(f"Image format: {format}")
        
        w, h = image.size
        logger.info(f"Processing {w}x{h} image")
        
        # Scale pixel values
        logger.debug("Scaling pixel values to 0-255 range")
        processed_pixels = 0
        for x in range(w):
            for y in range(h):
                color = get_pixel_val(image, x, y)
                image.putpixel((x, y), int(color * 255))
                processed_pixels += 1
                
                # Log progress for large images
                if processed_pixels % 10000 == 0:
                    logger.debug(f"Scaled {processed_pixels}/{w*h} pixels")
        
        # Convert to LA mode
        logger.info("Converting image to LA (Luminance-Alpha) mode")
        image = image.convert("LA")
        
        # Adjust alpha channel
        logger.debug("Adjusting alpha channel")
        for x in range(w):
            for y in range(h):
                color = get_pixel_val(image, x, y)
                if isinstance(color[0], (int, float)):
                    image.putpixel((x, y), (0, int(color[0])))
        
        # Log sample pixel for verification
        sample_pixel = get_pixel_val(image, 0, 0)
        logger.debug(f"Sample pixel at (0,0): {sample_pixel}")
        
        # Save image
        if not out_fp:
            output_path = new_fp + suffix if suffix else new_fp
            image.save(output_path)
            logger.info(f"Alpha-converted image saved to: {output_path}")
        else:
            image.save(out_fp, format="PNG")
            logger.info("Alpha-converted image saved to BytesIO stream as PNG")
            
    except Exception as e:
        logger.error(f"Failed to convert to alpha: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    # Set up console logging for standalone execution
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info("Running getImage.py as standalone script")
    
    try:
        write_pix_json("test.tif")
        convert_to_alpha("test.tif")
        logger.info("Standalone execution completed successfully")
    except Exception as e:
        logger.error(f"Standalone execution failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
