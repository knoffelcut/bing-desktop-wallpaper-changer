import subprocess
import pathlib

import numpy as np
import skimage.io  # Preferred over opencv, since it is smaller and we are just doing io (perf not important)


def upscale(path_input: str, target_width: int, target_height: int, directory_working: str = '/tmp'):
    assert pathlib.Path(path_input).exists()
    path_output = pathlib.Path(directory_working) / 'output.png'
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


def upscale_parts(
    path_input: str, target_width: int, target_height: int,
    parts_x: int = 2, parts_y: int = 2, overlap: int = 128,
    directory_working: str = '/tmp'
):
    assert pathlib.Path(path_input).exists()

    path_input = pathlib.Path(path_input)
    image = skimage.io.imread(path_input)
    image_height = image.shape[0]
    image_width = image.shape[1]
    fx = (target_width/image_width)
    fy = (target_height/image_height)

    parts_x = list(np.linspace(0, image_width, parts_x, endpoint=False, dtype=int))
    parts_y = list(np.linspace(0, image_height, parts_y, endpoint=False, dtype=int))

    directory_working = pathlib.Path(directory_working)
    parts = []
    for y0, y1 in zip(parts_y, parts_y[1:] + [None, ]):
        parts_ = []
        for x0, x1 in zip(parts_x, parts_x[1:] + [None, ]):
            overlap_x = overlap/fx
            overlap_y = overlap/fy
            assert overlap_x == int(overlap_x) and overlap_y == int(overlap_y)
            overlap_x, overlap_y = int(overlap_x), int(overlap_y)

            py0, py1 = overlap_x*bool(y0), overlap_x*bool(y1)
            px0, px1 = overlap_y*bool(x0), overlap_y*bool(x1)

            part = image[y0 - py0:(y1 + py1) if y1 is not None else y1, x0 - px0:(x1 + px1) if x1 is not None else x1]
            path_part = (directory_working / 'input').with_suffix(path_input.suffix)
            skimage.io.imsave(path_part, part)

            part_target_width = fx*part.shape[1]
            part_target_height = fy*part.shape[0]
            assert part_target_width == int(part_target_width) and part_target_height == int(part_target_height)
            part_target_width, part_target_height = int(part_target_width), int(part_target_height)
            path_upscale = upscale(path_part, part_target_width, part_target_height, directory_working)
            part_upscale = skimage.io.imread(path_upscale)

            # Remove the upscaled overlap sections
            py0, py1 = int(fy*py0), int(fy*py1)
            px0, px1 = int(fx*px0), int(fx*px1)
            part_upscale = part_upscale[py0:-py1 if py1 > 0 else None, px0:-px1 if px1 > 0 else None]

            parts_.append(part_upscale)
        parts.append(parts_)

    upscaled = np.vstack([np.hstack(parts_) for parts_ in parts])
    return upscaled
