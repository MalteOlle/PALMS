"""
Copyright (c) 2020 Stichting imec Nederland (PALMS@imec.nl)
https://www.imec-int.com/en/imec-the-netherlands
@license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>
See COPYING, README.
"""
import pathlib

from gui.tracking import Wave
from logic.databases.DatabaseHandler import Database
from logic.operation_mode.partitioning import Partitions
from utils.utils_general import resource_path
from utils.utils_gui import Dialog

import pandas as pd
import numpy as np
from pdkit.gait_processor import GaitProcessor

from tkinter import Tk, mainloop, Spinbox, Button, Label

class GaitDetector:
    @staticmethod
    def _reformat_data(df: pd.DataFrame, sampling_rate_hz: float):
        df = df[["acc_x"]]
        df = df.join(pd.DataFrame(data=df.index / sampling_rate_hz, columns=["td"]))
        datetimes = pd.DataFrame(pd.to_datetime(df["td"], unit="s"))
        datetimes.columns = ["timestamp"]
        df = df.join(datetimes)
        df = df.set_index("timestamp")
        return df

    @staticmethod
    def _get_gaitbouts_from_clusters(
        peak_pos_samples, prominences, clusters
    ) -> pd.DataFrame:
        starts_idx = np.nonzero(clusters - np.roll(clusters, -1))[0]
        ends_idx = starts_idx - 1
        ends_idx[-1] = len(peak_pos_samples) - 1
        regions = pd.DataFrame(
            data=[
                peak_pos_samples[starts_idx[:-1]],
                peak_pos_samples[ends_idx[1:]],
                starts_idx[:-1],
                ends_idx[1:],
            ],
            index=["start_sample", "end_sample", "start_peak", "end_peak"],
        ).T

        for row, region in regions.iterrows():
            regions.at[row, "gait"] = True

        gait_bouts = (
            regions.where(regions["gait"] == True)
            .dropna()
            .drop(["start_peak", "end_peak", "gait"], axis=1)
        )
        return gait_bouts

    def apply_pdkit_segmentation(
        self, data: pd.DataFrame, sampling_rate_hz: float
    ) -> pd.DataFrame:
        data = self._reformat_data(data, sampling_rate_hz)

        gp = GaitProcessor(
            sampling_frequency=sampling_rate_hz, filter_order=4, cutoff_frequency=1
        )
        data = gp.resample_signal(data)
        data_filtered = gp.filter_data_frame(data, centre=True, keep_cols=["td"])

        self.master = Tk()
        self.master.eval("tk::PlaceWindow . center")
        self.spinbox = Spinbox(self.master, from_=0, to=100)
        label = Label(self.master, text="Enter desired number of segments:")
        label.pack()
        self.spinbox.pack()
        btn_ok = Button(self.master, text="OK", command=self._set_n_segments)
        btn_ok.pack()
        mainloop()

        peak_pos_samples, prominences, clusters = gp.bellman_segmentation(
            data_filtered["acc_x"], int(self.n_segments)+1
        )

        gait_bouts = self._get_gaitbouts_from_clusters(
            peak_pos_samples, prominences, clusters
        ).astype(int)

        return gait_bouts

    def _set_n_segments(self):
        self.n_segments = self.spinbox.get()
        self.master.destroy()


class PDKIT_ANALYZER(Database):  # NB: !!!!!!!!!!!  class name should be equal to database name (this filename)
    def __init__(self):
        super().__init__()
        self.filetype = 'csv'  # NB: files to be used as source of the data
        self.DATAPATH = pathlib.Path(__file__).parent / 'data_folder'  # NB: top-level folder with the data
        self.file_template = r'**/*' + r'.' + self.filetype or '**/*.' + self.filetype  # NB: source file filter, also in subfolders
        self.output_folder: pathlib.Path = self.DATAPATH  # NB: where to save files; it is overwritten in self.save() once file location is known
        self.existing_annotations_folder: pathlib.Path = self.output_folder  # NB: where to look for existing annotations
        self.main_track_label = 'acc_x'  # NB: signal to which all annotations will apply, should be one of the labels
        # assigned in self.get_data()
        self.tracks_to_plot_initially = [self.main_track_label]  # NB: signals to be visible from the start of the app
        # NB: see !README_AnnotationConfig.xlsx: in this case we want to annotate 2 fiducial: peak and foot
        self.annotation_config_file = resource_path(pathlib.Path('config', 'AnnotationConfig', 'AnnotationConfig_EXAMPLE_PPG.csv'))
        # NB: see !README_EpochConfig.xlsx
        self.epoch_config_file = resource_path(pathlib.Path('config', 'EpochConfig', 'EpochConfig_default_start_with_None.csv'))
        self.RR_interval_as_HR = True  # NB: True: RR intervals in BPM, False: in seconds
        self.outputfile_prefix = ''  # NB: set here your initials, to distinguish multiple annotators' files
        assert 'csv' in self.annotation_config_file.suffix, 'Currently only .csv are supported as annotation configuration'

    def get_data(self, filename):
        super().get_data(filename)

        tracks = {}

        data = pd.read_csv(filename)
        for channel in ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"]:
            tracks[channel] = Wave(np.array(data[channel]), 102, label=channel, filename=self.fullpath.parts[-1][:-1])

        self.tracks = tracks
        self.track_labels = list(tracks.keys())
        self.tracks_to_plot_initially = self.track_labels
        super().test_database_setup()  # NB: test to early catch some of the DB initialization errors
        return tracks

    def set_annotation_data(self):
        data = pd.DataFrame(data=[self.tracks['acc_x'].value], index=["acc_x"]).T
        partitions = GaitDetector().apply_pdkit_segmentation(data, sampling_rate_hz=102)
        Partitions.add_all(["Activity"]*len(partitions), partitions["start_sample"] / 102, partitions["end_sample"] /
                           102)

    def save(self, **kwargs):
        # NB: save annotation data. By default annotations and partitions are saved as .h5 file.
        #  All tracks can be saved too (see Settings in the menu bar).
        #  One can also define custom save protocol here
        # self.output_folder = self.fullpath.parent  # to save in the same location
        # self.output_folder = get_project_root()  # to save in project root/near the executable
        try:
            self.output_folder = self.fullpath.parent
            super().save(filename=self.fullpath.stem, **kwargs)
        except Exception as e:
            Dialog().warningMessage('Save crashed with: \r\n' + str(e))

    def load(self, filename):
        # NB: load previously saved annotations and partitions.
        #  Inherited method loads data from .h5 files, but one can define custom protocol here
        super().load(filename)
