"""
Copyright (c) 2020 Stichting imec Nederland (PALMS@imec.nl)
https://www.imec-int.com/en/imec-the-netherlands
@license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>
See COPYING, README.
"""
import pathlib
import numpy as np
import pandas as pd
from PyQt5.QtCore import qInfo
from gui.tracking import Wave
from logic.databases.DatabaseHandler import Database
from logic.operation_mode.partitioning import Partitions
from utils.utils_general import get_project_root, butter_highpass_filter, butter_lowpass_filter, resource_path
from utils.utils_gui import Dialog


class PDKIT_LOADER(Database):  # NB: !!!!!!!!!!!  class name should be equal to database name (this filename)
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
        pass

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
