from PIL import Image
import rasterio
import json
from typing import *
from io import BytesIO, StringIO
import io


def get_pixel_val(img: Image, x: int, y: int) -> float:
    pix = img.load()
    pixel = pix[x,y]
    return pixel

def set_pixel_val(img: Image, x: int, y: int, val = float | tuple[float, float, float, float]) -> Image:
    pix = img.load()
    pix[x,y] = val
    return img


def img_to_pixel(img_path: str | BytesIO):
    val_dict = {}
    if isinstance(img_path, BytesIO):
        dataset = rasterio.open(img_path, driver="GTiff")
    else:
        dataset = rasterio.open(img_path)
    print(dataset.bounds)

    val_dict["lbound"] = dataset.bounds[0]
    val_dict["bbound"] = dataset.bounds[1]
    val_dict["rbound"] = dataset.bounds[2]
    val_dict["tbound"] = dataset.bounds[3]

    im = Image.open(img_path)
    w, h = im.size
    val_dict["sizex"] = w
    val_dict["sizey"] = h

    for x in range(w):
        for y in range(h):
            val_dict[f"{x},{y}"] = {"name": get_pixel_val(im, x, y)}
    return val_dict

def write_pix_json(fp: str, out_fp = None):
    if not out_fp:
        for i, x in enumerate(fp):
            if x == "." and not fp[i+1] == "/":
                new_fp = fp[:i]
        with open(f"{new_fp}_pix.json", 'w') as f:
            json.dump(img_to_pixel(fp), f)
    elif isinstance(out_fp, StringIO):
        json.dump(img_to_pixel(fp), out_fp)
    else:
        with open(out_fp, 'w') as f:
            json.dump(img_to_pixel(fp), f)

def convert_to_alpha(fp: str | BytesIO, replace: Literal[True] | str=True, out_fp = None):
    if isinstance(replace, bool):
        new_fp = fp
        suffix = ""
    else:
        for i, x in enumerate(fp):
            if x == "." and not fp[i + 1] == "/":
                new_fp = fp[:i] + replace
                suffix = fp[i:]
    if isinstance(fp, BytesIO):
        image = Image.open(fp)
    else:
        image = Image.open(fp+suffix)

    format = image.format
    print("FORMAT:", format)
    w, h = image.size
    for x in range(w):
        for y in range(h):
            color = get_pixel_val(image, x, y)
            image.putpixel((x, y), color*255)
    image = image.convert("LA")
    for x in range(w):
        for y in range(h):
            color = get_pixel_val(image, x, y)
            if isinstance(color[0], int) or isinstance(color[0], float):
                image.putpixel((x, y), (0, color[0]))
    print(get_pixel_val(image, 0, 0))
    if not out_fp:
        image.save(new_fp+suffix)
    else:
        image.save(out_fp, format="PNG")
        image.save("../images/test.TIFF", format=format) # check if it works




if __name__ == "__main__":
    write_pix_json("test.tif")
    convert_to_alpha("test.tif")

