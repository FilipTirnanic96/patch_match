import os.path
import shutil

import pandas as pd

from utils.glob_def import REPORT_DIR, CONFIG_DIR
import matplotlib.pyplot as plt
import matplotlib


class Report:

    def __init__(self, model_name: str = "adv_pm"):
        self.reports_folder_path = REPORT_DIR
        self.model_name = model_name

    def make_report(self, df: pd.DataFrame, input_name: str):
        # make folder for results
        output_dir = os.path.join(self.reports_folder_path, self.model_name)
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        # set matplotlib style
        matplotlib.style.use('ggplot')
        # bar plot percent of true detections
        detection_statistics = df['matched'].value_counts() / df.shape[0]
        plt.figure(figsize=(10, 8))
        plt.title("Percentage of miss detection of " + str(df.shape[0]) + " patches")

        ax = detection_statistics.plot.bar()
        ax.bar_label(ax.containers[0])

        plt.savefig(os.path.join(output_dir, input_name + '_det_stat.png'))
        # get all miss detections
        # bar plot number of miss detections and n_points_matched
        miss_detection_df = df[df['matched'] == False]
        number_of_n_points_matched = miss_detection_df['n_points_matched'].value_counts()
        number_of_n_points_matched = number_of_n_points_matched.sort_index()
        plt.figure(figsize=(10, 8))
        plt.title("Number of matched points in " + str(miss_detection_df.shape[0]) + " miss detections")
        ax = number_of_n_points_matched.plot.bar()
        ax.bar_label(ax.containers[0])

        plt.savefig(os.path.join(output_dir, input_name + '_n_points_matched_miss.png'))

        # save miss detections df with n_points_matched > 1
        miss_detection_df_1_greater = miss_detection_df[miss_detection_df['n_points_matched'] > 1]
        miss_detection_df_1_greater.to_csv(os.path.join(output_dir, input_name + '_n_points_matched_miss_1_greater.csv'))

        miss_detection_df_1_less = miss_detection_df[miss_detection_df['n_points_matched'] <= 1]
        miss_detection_df_1_less.to_csv(os.path.join(output_dir, input_name + '_n_points_matched_miss_1_less.csv'))

        # save algo parameters
        shutil.copyfile(os.path.join(CONFIG_DIR, "patch_match_cfg.yml"),
                        os.path.join(output_dir, "patch_match_cfg.yml"))


if __name__ == "__main__":

    report = Report()
    df = pd.read_csv(r"C:\Users\uic52421\Documents\Python Scripts\PSIML\patch_match\code\df_kpi_6.csv")
    input_name = "6.txt"
    report.make_report(df, input_name)