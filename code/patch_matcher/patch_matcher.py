# -*- coding: utf-8 -*-
"""
Created on Fri Feb  4 14:17:03 2022

@author: uic52421
"""
import numpy as np
import time
from abc import ABC, abstractmethod
import math
from scipy import signal, ndimage
import scipy.ndimage.filters as filters
# from patch_matcher.visualisation import show_matched_points
import matplotlib.pyplot as plt
from patch_matcher.visualisation import show_key_points


def debug_image(image):
    image_copy = image.copy().astype('float64')
    image_copy /= image_copy.max()
    image_copy *= 255.0
    plt.imshow(image_copy, cmap='gray', vmin=0, vmax=255)
    plt.show()


def debug_image_grad_image(image, th=0.01):
    image_copy = image.copy().astype('float64')
    image_copy = np.clip(image_copy, a_min=None, a_max=th)
    image_copy /= image_copy.max()
    plt.imshow(image_copy, cmap='gray', vmin=0, vmax=1)
    plt.show()


class PatchMatcher(ABC):

    def __init__(self, verbose=0):
        # params
        # normalizing features
        # use gaussian normalization
        self.use_gauss_norm = False
        self.use_gauss_global_norm = True
        if self.use_gauss_global_norm:
            self.global_feature_mean = 0
            self.global_feature_std = 1

        # use scaling: BAD for distinguishing vectors!
        self.use_scaling_norm = False

        self.verbose = verbose
        self.time_passed_sec = -1
        self.n_points_matched = 0

    def preprocess(self, image):
        image = np.array(image.convert('L'))
        return image

    def first_and_second_smallest(numbers):
        m1 = m2 = float('inf')
        i1 = i2 = -1;
        for i, x in enumerate(numbers):
            if x <= m1:
                m2 = m1
                m1 = x
                i2 = i1
                i1 = i

            elif x < m2:
                m2 = x
                i2 = i
        return m1, i1, m2, i2

    @abstractmethod
    def extract_key_points(self, image):
        pass

    @abstractmethod
    def extract_features(self, key_points):
        pass

    # nomalize features to unit vectors
    def nomalize_features(self, features):
        if self.use_gauss_norm:
            # mean and std
            features -= np.mean(features, axis=1, keepdims=True)
            features /= np.std(features, axis=1, keepdims=True)

        if self.use_gauss_global_norm:
            # mean and std
            features = features - self.global_feature_mean
            features = features / self.global_feature_std

        if self.use_scaling_norm:
            # scaling
            lengths = np.sqrt(np.sum(features ** 2, 1))
            lengths[lengths == 0] = 1
            features = features / lengths[:, None]

        return features

    def match_features(self, patch_features, template_features):
        match = []
        nn_treshold = 0.7
        treshold = 0.2
        # match features
        for i in np.arange(0, patch_features.shape[0]):
            patch_feature = patch_features[i]

            # calculate dist from ith path_feature to each template_feature
            distance = np.sqrt(np.sum((template_features - patch_feature) ** 2, axis=1))
            m1, i1, m2, i2 = PatchMatcher.first_and_second_smallest(distance)
            # if we have just 1 feature we won't use treshold
            if patch_features.shape[0] != 1:
                #if (m1 < treshold) and (m1 / m2 < nn_treshold):
                if m1 / m2 < nn_treshold:
                    match.append((i1, i))
            else:
                match.append((i1, i))

        match = np.array(match)
        return match

    # debug
    def match_features_debug(self, patch_features, template_features, pkp, tkp):

        condition = (tkp[:, 0] <= self.expected_x + 40) & (tkp[:, 0] >= self.expected_x) & (
                tkp[:, 1] >= self.expected_y) & (tkp[:, 1] <= self.expected_y + 40)
        template_features1 = template_features[condition]

        pkp[:, 0] += self.expected_x
        pkp[:, 1] += self.expected_y
        tkp1 = tkp[condition]

        i = 0

    @abstractmethod
    def find_correspodind_location_of_patch(self, patch_key_points, match):
        pass

    # returns left top location on template image of matched patch
    def match_patch(self, patch):
        # calculate time taken to match patch
        start = time.time()

        # preprocess image
        self.curr_image = np.array(patch) / 255
        patch = self.preprocess(patch)

        # extract key points from template
        patch_key_points = self.extract_key_points(patch)
        # check if we have detected some key points
        if (patch_key_points.size == 0):
            self.n_points_matched = 0
            return 0, 0

        # extract key points from template
        patch_key_points, patch_features = self.extract_features(patch_key_points, patch)
        # check if we have detected some features
        if (patch_features.size == 0):
            self.n_points_matched = 0
            return 0, 0

        # nomalize features
        patch_features = self.nomalize_features(patch_features)
        # find feature matchs between patch and template
        # debug
        # self.match_features_debug(patch_features, self.template_features, patch_key_points, self.template_key_points)
        match = self.match_features(patch_features, self.template_features)
        # check if we have matched some features
        if (match.size == 0):
            self.n_points_matched = 0
            return 0, 0

        # find top left location on template of matched patch
        x_left_top, y_left_top, match = self.find_correspodind_location_of_patch(patch_key_points, match)
        # show_matched_points(self.template, patch, self.template_key_points, patch_key_points, match)

        # set num of matched points
        if match.size > 0:
            self.n_points_matched = match.shape[0]
        else:
            self.n_points_matched = 0

        end = time.time()
        self.time_passed_sec = round(1.0 * (end - start), 4)
        if self.verbose > 0:
            print("Time taken to match the patch", round(1.0 * (end - start), 4))

        return x_left_top, y_left_top


class SimplePatchMatcher(PatchMatcher):

    def __init__(self, template_img, pw, ph, verbose=0):
        # init parent constructor
        super().__init__(verbose)
        # preprocess image
        template_img = self.preprocess(template_img)
        # init params
        self.template = template_img
        self.pw = pw
        self.ph = ph
        if (pw != 0 and ph != 0):
            # extract key points from template
            self.template_key_points = self.extract_key_points(self.template)
            # extract template features
            self.template_key_points, self.template_features = self.extract_features(self.template_key_points,
                                                                                     self.template)
            # nomalize features
            self.template_features = self.nomalize_features(self.template_features)
        else:
            self.template_key_points = []
            self.template_features = []

    # override abstract method
    # every point in image is key point
    # returns x,y keypoints location
    def extract_key_points(self, image):
        key_points_list = []
        for y in range(math.floor(self.ph / 2), image.shape[0] - math.floor(self.ph / 2) + 1):
            for x in range(math.floor(self.pw / 2), image.shape[1] - math.floor(self.pw / 2) + 1):
                key_points_list.append((x, y))
        key_points = np.array(key_points_list)
        return key_points

    # override abstract method
    # return fetures for each key point
    def extract_features(self, key_points, image):
        features = []
        for i in np.arange(0, key_points.shape[0]):
            # get key point location
            x, y = key_points[i]
            # get patch around key point
            patch_feature = image[y - math.floor(self.ph / 2): y + math.floor(self.ph / 2),
                            x - math.floor(self.pw / 2): x + math.floor(self.pw / 2)]
            # ravel patch
            feature = patch_feature.ravel()
            # add feature
            features.append(feature)

        features = np.array(features)
        return key_points, features

    # simple matcher just uses one feature for patch so it will be just one match
    # outputs list of meatched features
    def match_features(self, patch_features, template_features):
        match = []
        # match features
        for i in np.arange(0, patch_features.shape[0]):
            patch_feature = patch_features[i]

            # calculate dist from ith path_feature to each template_feature
            distance = np.sqrt(np.sum((template_features - patch_feature) ** 2, axis=1))
            m1, i1, m2, i2 = PatchMatcher.first_and_second_smallest(distance)

            match.append((i1, i))

        return match

    # override abstract method
    # output top let postion of template where the patch match
    def find_correspodind_location_of_patch(self, patch_key_points, match):
        i_kp_template, i_kp_patch = match[0]

        template_center_match = self.template_key_points[i_kp_template]

        x_left_top = template_center_match[0] - math.floor(self.pw / 2)
        y_left_top = template_center_match[1] - math.floor(self.ph / 2)
        return x_left_top, y_left_top, match


class AdvancePatchMatcher(PatchMatcher):

    def __init__(self, template_img, verbose=0):
        super().__init__(verbose)
        # init params
        self.grad_mag = []
        self.grad_theta = []

        # debug
        self.expected_x = -1
        self.expected_y = -1

        # ------- params ---------
        # <FEATURE PARAMS>
        # use all 3 channels for features
        self.use_3_channels = True
        self.use_sum_feature = True

        # init in respect to params
        if self.use_3_channels:
            self.channels_grad_mag = []
            self.channels_grad_theta = []

        # <MATCHING PARAMS>
        # filtering outlier matches
        self.use_match_median_filter = True
        self.use_match_gauss_filter = True

        # gradient histogrm
        self.num_angle_bins = 8

        # preprocess image
        self.curr_image = np.array(template_img) / 255
        template_img = self.preprocess(template_img)
        self.template = template_img

        # extract key points from template
        self.template_key_points = self.extract_key_points(self.template)
        # extract template features
        self.template_key_points, self.template_features = self.extract_features(self.template_key_points,
                                                                                 self.template)

        if self.use_gauss_global_norm:
            self.global_feature_mean = np.mean(self.template_features, axis=0, keepdims=True)
            self.global_feature_std = np.std(self.template_features, axis=0, keepdims=True)

        # nomalize features
        self.template_features = self.nomalize_features(self.template_features)




    # override abstract method
    # use Harris detector to extrack corner points
    # returns x,y keypoints location
    def extract_key_points(self, image):
        key_points_list = []

        if self.use_3_channels:
            self.channels_grad_mag.clear()
            self.channels_grad_theta.clear()

            # calculate gradients magnitude and orientation for each channel
            for channel in [0, 1, 2]:
                channel_img = self.curr_image[:, :, channel]
                # find image gradiants
                # % gradient image, for gradients in x direction.
                channel_img_dx = 1.0 * signal.convolve2d(channel_img, np.reshape(np.array([-1, 0, 1]), (1, -1)),
                                                         mode='same',
                                                         boundary='symm') / 255
                # % gradients in y direction.
                channel_img_dy = 1.0 * signal.convolve2d(channel_img, np.reshape(np.array([-1, 0, 1]), (-1, 1)),
                                                         mode='same',
                                                         boundary='symm') / 255

                # calculate gradient angle
                channel_grad_theta = np.arctan2(channel_img_dy, channel_img_dx)
                # map gradient from 0 - 2* pi
                channel_grad_theta = channel_grad_theta % (2 * np.pi)

                channel_grad_mag = 1.0 * channel_img_dx ** 2 + 1.0 * channel_img_dy ** 2

                # debug_image_grad_image(channel_grad_mag)
                self.channels_grad_mag.append(channel_grad_mag)
                self.channels_grad_theta.append(channel_grad_theta)

        # find image gradiants
        # % gradient image, for gradients in x direction.
        img_dx = 1.0 * signal.convolve2d(image, np.reshape(np.array([-1, 0, 1]), (1, -1)), mode='same',
                                         boundary='symm') / 255
        # % gradients in y direction.
        img_dy = 1.0 * signal.convolve2d(image, np.reshape(np.array([-1, 0, 1]), (-1, 1)), mode='same',
                                         boundary='symm') / 255

        # anulate invalid features
        if image.size > 20000:
            img_dx[:, 0:3] = 0
            img_dy[img_dy.shape[0] - 3:img_dy.shape[0], :] = 0

        # calculate gradient angle
        self.grad_theta = np.arctan2(img_dy, img_dx)
        # map gradient from 0 - 2* pi
        self.grad_theta = self.grad_theta % (2 * np.pi)

        # take abs of gradients
        img_dx = np.absolute(img_dx)
        img_dy = np.absolute(img_dy)

        # calculate values for M matrix
        img_dx2 = 1.0 * img_dx ** 2
        img_dy2 = 1.0 * img_dy ** 2
        img_dxy = 1.0 * img_dx * img_dy

        self.grad_mag = img_dx2 + img_dy2
        # debug_image_grad_image(self.grad_mag)

        # blur gradiants
        img_dx2 = ndimage.gaussian_filter(img_dx2, sigma=2, truncate=1)
        img_dy2 = ndimage.gaussian_filter(img_dy2, sigma=2, truncate=1)
        img_dxy = ndimage.gaussian_filter(img_dxy, sigma=2, truncate=1)

        # calculate det and trace for finding R
        detA = (img_dx2 * img_dy2) - (img_dxy ** 2)
        traceA = (img_dx2 + img_dy2)

        # calculate response for Harris Corner equation
        k = 0.05
        R = detA - k * (traceA ** 2)

        threshold2 = 1e-10
        threshold1 = 1e-10
        R[(R < threshold1) & (R > threshold2)] = 0

        R = abs(R)
        # non maxima supresion
        R_max = filters.maximum_filter(R, size=3)

        R[R != R_max] = 0

        # debug_image(R)
        if image.size < 20000:
            th = 1e-5
            R[R < th] = 0

        # debug_image(R)
        # debug_image_grad_image(R)
        # extract key points
        key_points_indeces = np.where(R > 0)
        key_points_list = [(key_points_indeces[1][i], key_points_indeces[0][i]) for i in
                           np.arange(0, key_points_indeces[0].shape[0])]

        key_points = np.array(key_points_list)
        #show_key_points(image, key_points)

        return key_points

    def compute_gradient_histogram(self, num_bins, gradient_magnitudes, gradient_angles):
        angle_step = 2 * np.pi / num_bins
        angles = np.arange(0, 2 * np.pi + angle_step, angle_step)

        indices = np.digitize(gradient_angles.ravel(), bins=angles)
        indices -= 1
        gradient_magnitudes_ravel = gradient_magnitudes.ravel();
        histogram = np.zeros((num_bins));
        for i in range(0, indices.shape[0]):
            histogram[indices[i]] += gradient_magnitudes_ravel[i]

        return histogram

    def compute_gradient_feature(self, num_bins, gradient_magnitudes, gradient_angles):
        feature = np.zeros((gradient_magnitudes.size * 2))
        grad_x = gradient_magnitudes.ravel() * np.cos(gradient_angles.ravel())
        gray_y = gradient_magnitudes.ravel() * np.sin(gradient_angles.ravel())

        feature[0:gradient_magnitudes.size] = grad_x
        feature[gradient_magnitudes.size:gradient_magnitudes.size * 2] = gray_y
        return feature

    def compute_gray_value_feature(self, patch):
        feature = patch.ravel()

        return feature

    def compute_color_histogram_feature(self, patch):
        feature = patch.ravel()
        return feature

    #
    def extract_features(self, key_points, image):
        features = []
        patch_size = 3
        patch_step = math.floor(patch_size / 2)
        num_angles = self.num_angle_bins
        key_points_flag = np.ones((key_points.shape[0]), dtype=bool)
        for i in np.arange(0, key_points.shape[0]):
            # get key point location
            x, y = key_points[i]
            # get patch around key point
            min_y = y - patch_step
            max_y = y + patch_step + 1
            min_x = x - patch_step
            max_x = x + patch_step + 1

            # if patch out of bounds skip key point
            if ((min_y < 0) or (max_y > image.shape[0]) or (min_x < 0) or (max_x > image.shape[1])):
                key_points_flag[i] = 0
                continue

            if self.use_3_channels:
                feature = []
                for channel in [0, 1, 2]:
                    channel_grad_mag = self.channels_grad_mag[channel]
                    channel_grad_theta = self.channels_grad_theta[channel]

                    channel_patch_grad = channel_grad_mag[min_y: max_y, min_x: max_x]
                    channel_patch_theta = channel_grad_theta[min_y: max_y, min_x: max_x]
                    channel_feature = self.compute_gradient_histogram(num_angles, channel_patch_grad,
                                                                      channel_patch_theta)

                    if self.use_sum_feature:
                        if len(feature) == 0:
                            feature = channel_feature
                        else:
                            feature += channel_feature
                    else:
                        if len(feature) == 0:
                            feature = channel_feature
                        else:
                            np.concatenate(feature, channel_feature, axis=0)
            else:
                patch_grad = self.grad_mag[min_y: max_y, min_x: max_x]
                patch_theta = self.grad_theta[min_y: max_y, min_x: max_x]

                patch = self.curr_image[min_y: max_y, min_x: max_x]
                feature = self.compute_gradient_histogram(num_angles, patch_grad, patch_theta)
                # feature = self.compute_gradient_feature(num_angles, patch_grad, patch_theta)
                # feature = self.compute_color_histogram_feature(patch)

            features.append(feature)

        key_points = key_points[key_points_flag, :]
        features = np.array(features)
        return key_points, features

    def filter_outlayers(H, pt1, pt2, match, errorTreshold=70):
        # transform top left corner of patch (coordinate 0,0)
        pt1_transform = np.matmul(pt1, H)
        dist = np.sqrt(np.sum((pt2 - pt1_transform) ** 2, 1))
        dist_std = np.std(dist)
        errorTreshold = 3 * dist_std
        match = match[dist <= errorTreshold]
        return match

    def find_correspodind_location_of_patch(self, patch_key_points, match):
        # extract matched key points from patch
        pt1 = np.ones((len(match), 3))
        pt1[:, 0:2] = patch_key_points[match[:, 1], :]
        # extract matched key points from template
        pt2 = np.ones((len(match), 3))
        pt2 = self.template_key_points[match[:, 0], :]

        if self.use_match_median_filter:
            # compute affine matrix
            H = AdvancePatchMatcher.compute_affine_matrix(pt1, pt2)
            # filter outlayers
            match = AdvancePatchMatcher.filter_outlayers(H, pt1, pt2, match)
            # check if we filter out all matches
            if match.size == 0:
                return 0, 0, match

        if self.use_match_gauss_filter:
            # extract matched key points from patch
            pt1 = np.ones((len(match), 3))
            pt1[:, 0:2] = patch_key_points[match[:, 1], :]
            # extract matched key points from template
            pt2 = np.ones((len(match), 3))
            pt2 = self.template_key_points[match[:, 0], :]
            # use median filter
            match = AdvancePatchMatcher.median_filter(pt1, pt2, match, 60)

            # check if we filter out all matches
            if match.size == 0:
                return 0, 0, match

        # check if we filter out all matches
        if match.size == 0:
            return 0, 0, match
        # recompute afine matrix
        # extract matched key points from patch
        pt1 = np.ones((len(match), 3))
        pt1[:, 0:2] = patch_key_points[match[:, 1], :]
        # extract matched key points from template
        pt2 = self.template_key_points[match[:, 0], :]

        # compute affine matrix
        H = AdvancePatchMatcher.compute_affine_matrix(pt1, pt2)

        # transform top left corner of patch (coordinate 0,0)
        result = np.matmul(np.array([0, 0, 1], ndmin=2), H)
        x_top_left = int(np.round(result[0, 0]))
        y_top_left = int(np.round(result[0, 1]))

        return x_top_left, y_top_left, match

    @staticmethod
    # filter array with median
    def median_filter(pt1, pt2, match, th):
        # if we have more then 4 mathced points use median filter
        # calculate residuals
        pts = pt2 - pt1[:, 0:2]
        inds = np.ones(pts.shape[0], dtype=bool)
        if pts.shape[0] > 4:
            for i in [0, 1]:
                pt = pts[:, i]
                median = np.median(pt)
                res = abs(pt - median)
                ind = np.where(res > th)
                inds[ind] = 0

            match = match[inds, :]
        return match

    @staticmethod
    # we need to compute matrix H such as patchKP * H = templateKP
    def compute_affine_matrix(pt1, pt2):
        # compute translation matrix
        H = np.zeros((3, 2))
        residuals = pt2 - pt1[:, 0:2]

        mean_residuals = np.mean(residuals, axis=0)
        H[0, 0] = 1
        H[2, 0] = mean_residuals[0]
        H[1, 1] = 1
        H[2, 1] = mean_residuals[1]

        return H
