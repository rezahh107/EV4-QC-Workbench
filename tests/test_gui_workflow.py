import os
import tkinter as tk

import pytest

from ev4_qc_workbench.app import Application

pytestmark = pytest.mark.windows


def test_gui_has_exactly_one_ce_tab_and_close_guard():
    if os.name != "nt":
        pytest.skip("Windows Tkinter job")
    root = tk.Tk()
    root.withdraw()
    app = Application(root)
    assert list(app.tabs) == ["ce"]
    tab = app.tabs["ce"]
    tab.set_busy(True)
    assert str(tab.run_button.cget("state")) == "disabled"
    tab.set_busy(False)
    assert str(tab.run_button.cget("state")) == "normal"
    root.destroy()
