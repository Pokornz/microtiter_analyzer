import numpy as np
from skimage.color import rgb2hsv

class MicrotiterMethods:
    def __init__(self):
        self.aggregation_methods = [
            ProtoMethod("arithmetic_mean", "Arithmetic Mean", self.arithmetic_mean),
            ProtoMethod("weighted_mean", "Weighted Mean", self.weighted_mean),
            # Add more methods as needed
        ]
        self.scoring_methods = [
            ProtoMethod("euclidian_rgb", "Euclidian distance in RGB", self.euclidian_rgb),
            ProtoMethod("euclidian_hsv", "Euclidian distance in HSV", self.euclidian_hsv),
            ProtoMethod("distance_saturation", "Simple distance in saturation", self.distance_saturation),
            # Add more methods as needed
        ]

    # Aggregation methods (condensing matrix into one pixel)
    def arithmetic_mean(self, array_2d):
        return np.mean(array_2d)
    
    def weighted_mean(self, array_2d):
        # Weights decrease with distance from the center, but does not use reciprocals like Inverse Distance Weighted mean
        length = len(array_2d)
        center = [np.floor(length/2),np.floor(length/2)]
        distances = []
        for i in range(length):
            row = []
            for j in range(length):
                row.append(np.linalg.norm(np.array([i,j])-np.array(center)))
            distances.append(row)
        weights = np.ceil(length/2) - np.array(distances)
        return np.sum(array_2d*weights)/np.sum(weights)
    
    # Scoring methods
    def euclidian_rgb(self, sample_r, sample_g, sample_b, control_r, control_g, control_b):
        return np.linalg.norm(np.array([sample_r, sample_g, sample_b]) - np.array([control_r, control_g, control_b]))

    def euclidian_hsv(self, sample_r, sample_g, sample_b, control_r, control_g, control_b):
        sample_h, sample_s, sample_v = rgb2hsv(np.array([sample_r, sample_g, sample_b]))
        sample_hsv = np.array([sample_h*255, sample_s*255, sample_v])
        control_h, control_s, control_v = rgb2hsv(np.array([control_r, control_g, control_b]))
        control_hsv = np.array([control_h*255, control_s*255, control_v])
        return np.linalg.norm(sample_hsv - control_hsv)
    
    def distance_saturation(self, sample_r, sample_g, sample_b, control_r, control_g, control_b):
        _, sample_s, _ = rgb2hsv(np.array([sample_r, sample_g, sample_b]))
        _, control_s, _ = rgb2hsv(np.array([control_r, control_g, control_b]))
        return abs(sample_s - control_s)*255

class ProtoMethod:
    def __init__(self, method_code, method_label, method_function):
        self.code = method_code
        self.label = method_label
        self.calculate = method_function
