"""
Утилиты кодирования масок сегментации.
RLE (Run-Length Encoding) — компактный формат для передачи бинарных масок через API.
"""

import numpy as np


def mask_to_rle(mask: np.ndarray) -> list[int]:
    """
    Кодирует бинарную маску в формат RLE.
    Формат: [start1, length1, start2, length2, ...]
    Индексы идут по строкам (row-major / C-order).

    :param mask: бинарная маска (H x W), dtype uint8
    :return: список целых чисел [start, length, start, length, ...]
    """
    flat = mask.flatten()
    # Находим границы серий единиц
    padded = np.concatenate([[0], flat, [0]])
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    rle: list[int] = []
    for s, e in zip(starts, ends):
        rle.extend([int(s), int(e - s)])
    return rle


def rle_to_mask(rle: list[int], shape: tuple[int, int]) -> np.ndarray:
    """
    Декодирует RLE обратно в бинарную маску.

    :param rle: список [start, length, ...]
    :param shape: (height, width)
    :return: бинарная маска (H x W)
    """
    mask = np.zeros(shape[0] * shape[1], dtype=np.uint8)
    for i in range(0, len(rle), 2):
        start, length = rle[i], rle[i + 1]
        mask[start : start + length] = 1
    return mask.reshape(shape)
