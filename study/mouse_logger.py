import os
import pickle
from datetime import datetime

import keyboard
import mouse
import pandas as pd
from qtpy.QtCore import QEvent
from qtpy.QtGui import QMoveEvent, QResizeEvent


class MouseLogger:
    def __init__(self):
        self.active_times = pd.DataFrame()

        self.mouse_events = []

        mouse.hook(self.mouse_events.append)
        keyboard.start_recording()  # Starting the recording

        keyboard.add_hotkey("ctrl+ü", self.stop_logging)

        #self.master = Tk()
        #self.text_box = Text(self.master)
        # self.text_box.grid(row=0)
        #self.text_box.pack()

        #e = Entry(self.master)
        #        e.grid(row=0, column=1)

        #btn_ok = Button(self.master, text="OK", command=self.handle_mode)
        #btn_ok.pack()
        #self.master.mainloop()

    def handle_mode(self):
        #self.mode = self.text_box.get("1.0", END)
        #self.save_file_directory = filedialog.askdirectory()
        #self.master.destroy()
        self.start_active = datetime.now().timestamp()

    def move_event(self, event: QMoveEvent, window):
        self._add_change("move", window)

    def resize_event(self, event: QResizeEvent, window):
        self._add_change("resize", window)

    def change_event(self, event: QEvent, window):
        if window.isHidden():
            return
        if window.isActiveWindow() and len(self.active_times) > 0:
            #self.start_active = datetime.now().timestamp()
            self._add_change("active", window)
        else:
            self._add_change("inactive", window)
        print(event)

    def stop_logging(self, window):
        self._add_change("inactive", window)

        mouse.unhook(self.mouse_events.append)
        keyboard_events = keyboard.stop_recording()

        from pathlib import Path

        here = Path(__file__).absolute().parent

        #self.mode = self.mode.replace("\n", "")

        now = datetime.now().strftime("%H-%M-%S")
        from pathlib import Path
        home = Path.home()

        if not os.path.isdir(home / "study_results_palms"):
            os.mkdir(home/"study_results_palms")

        #with open(str(Path(self.save_file_directory) / f"{self.mode}_mouse_events.pkl"), "wb") as f:
        with open(str(home /"study_results_palms" / f"{now}_mouse_events.pkl"), "wb") as f:
            pickle.dump(self.mouse_events, f)

        #with open(str(Path(self.save_file_directory) / f"{self.mode}_window_positions.pkl"), "wb") as f:
        with open(str(home / "study_results_palms" / f"{now}_window_positions.pkl"), "wb") as f:
            pickle.dump(self.active_times, f)

    def _add_change(self, description: str, window, start_time = None):
        if window is None:
            window_name = "MainWindow"
        else:
            window_name = type(window).__name__
        if description in ["move", "resize"]:
            # we will force users to use full screen
            return
            #start = None
        elif start_time:
            start = start_time
        else:
            start = datetime.now().timestamp()
        df = pd.DataFrame(
            data=[
                [
                    window_name,
                    start,
                    window.pos().x(),
                    window.pos().y(),
                    window.size().width(),
                    window.size().height(),
                    description,
                ]
            ],
            columns=["window","start", "pos_x", "pos_y", "width", "height", "event_description"],
        )
        self.active_times = self.active_times.append(df)
        print(self.active_times)

    def register_window(self, window, start_time: None):
        window.moveEvent = lambda ev: self.move_event(ev, window)
        window.changeEvent = lambda ev: self.change_event(ev, window)
        window.resizeEvent = lambda ev: self.resize_event(ev, window)
        if start_time:
            self._add_change("actual_start", window, start_time)
