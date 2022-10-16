import subprocess
import pathlib

import numpy as np
import skimage.io  # Preferred over opencv, since it is smaller and we are just doing io (perf not important)

# cog predict r8.im/longguangwang/arbsr@sha256:9e20d2768e62c16716c585a899105a63cd5d36f6be17a208dbc201027325d881   -i image=@/home/hrichter/Pictures/BingWallpapers/20221015.jpg   -i target_width=2560   -i target_height=1440


def upscale(path_input: str, target_width: int, target_height: int, directory_working: str = '/tmp'):
    assert pathlib.Path(path_input).exists()
    path_output = (pathlib.Path(directory_working) / 'output.ext').with_suffix(pathlib.Path(path_input).suffix)
    path_output.unlink(missing_ok=True)
    call = [
        'cog', 'predict',
        'r8.im/longguangwang/arbsr@sha256:9e20d2768e62c16716c585a899105a63cd5d36f6be17a208dbc201027325d881',
        '-i', f'image=@{path_input}',
        '-i', f'target_width={target_width}',
        '-i', f'target_height={target_height}',
    ]
    subprocess.check_call(call, cwd=str(directory_working))
    assert path_output.exists()
    return path_output


def upscale_paths(path_input: str, target_width: int, target_height: int, parts_x: int = 2, parts_y: int = 2, directory_working: str = '/tmp'):
    # TODO Overlap to negate the iffy side effects
    assert pathlib.Path(path_input).exists()

    path_input = pathlib.Path(path_input)
    image = skimage.io.imread(path_input)
    image_height = image.shape[0]
    image_width = image.shape[1]

    parts_x = list(np.linspace(0, image_width, parts_x, endpoint=False, dtype=int))
    parts_y = list(np.linspace(0, image_height, parts_y, endpoint=False, dtype=int))

    directory_working = pathlib.Path(directory_working)
    parts = []
    for y0, y1 in zip(parts_y, parts_y[1:] + [None, ]):
        parts_ = []
        for x0, x1 in zip(parts_x, parts_x[1:] + [None, ]):
            part = image[y0:y1, x0:x1]
            path_part = (directory_working / 'input').with_suffix(path_input.suffix)
            skimage.io.imsave(path_part, part)

            part_target_width = (target_width/image_width)*part.shape[1]
            part_target_height = (target_height/image_height)*part.shape[0]
            assert part_target_width == int(part_target_width) and part_target_height == int(part_target_height)
            part_target_width, part_target_height = int(part_target_width), int(part_target_height)
            path_upscale = upscale(path_part, part_target_width, part_target_height, directory_working)
            part_upscale = skimage.io.imread(path_upscale)
            parts_.append(part_upscale)
        parts.append(parts_)

    upscaled = np.vstack([np.hstack(parts_) for parts_ in parts])
    return upscaled


if __name__ == '__main__':
    working_directory = '/tmp'
    path_image = '/home/hrichter/Pictures/cog/output_512x512.png'

    upscaled = upscale_paths(path_image, 1024, 1024)
    skimage.io.imsave(pathlib.Path(working_directory) / 'output.png', upscaled)
