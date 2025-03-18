import numpy as np


def getFileType(path: str):

    return str.split(path, ".")[-1]


def getStandardizedVector(vector: np.ndarray):
    mean_v = np.mean(vector)
    std_v = np.std(vector)
    standardized_vector = (vector - mean_v) / std_v

    return standardized_vector
