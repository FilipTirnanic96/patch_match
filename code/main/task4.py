# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 12:38:04 2020

@author: Filip
"""
import sys
import os
if '../' not in sys.path:
    sys.path.append('../')
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import time
from utils.common.glob_def import DATA_DIR
from patch_matcher.simple_patch_matcher import SimplePatchMatcher
from kpi_calculation.calculate_kpi import CalculateKPI 

def visualize_patch(template, patch, x, y, ph, pw):
    template_copy = template.copy()
    cv2.rectangle(template_copy, (x, y), (x + pw, y + ph), (255,0,0), 3)
    plt.imshow(np.array(template_copy))
    plt.show() 
    plt.imshow(np.array(patch))
    plt.show() 

if __name__ == "__main__":
    # get map template image
    template_image_path = os.path.join(DATA_DIR,"set","map.png")
    template = Image.open(template_image_path)
    
    # show template
    plt.imshow(np.array(template))
    plt.show()
    
    # take first n patches
    n_patches = 10
    # cumulative time taken
    t_cum = 0
 
    # initialise Simple Path Macher
    patch_matcher_ = SimplePatchMatcher(template, 40, 40, 2)
    #kpi_ = CalculateKPI(DATA_DIR)
    #df_kpi = kpi_.calculate_kpis(-1, 10)
    for num in np.arange(0,n_patches):
        
        # get patch image
        path_image_path = os.path.join(DATA_DIR,"set","9",str(num) + ".png")
        patch = Image.open(path_image_path)     
        
        x1, y1 = patch_matcher_.match_patch(patch)

        # get time taken
        time_taken = patch_matcher_.time_passed_sec
        
       
        # visu results
        visualize_patch(np.array(template), np.array(patch), x1, y1, np.array(patch).shape[1], np.array(patch).shape[0])
        
        
        t_cum += time_taken
        
    print('Time taken to match',n_patches, 'patch', t_cum)