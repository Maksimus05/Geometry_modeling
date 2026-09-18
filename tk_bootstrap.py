"""Исправление путей Tcl/Tk для текущей установки Python."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_tcl_tk() -> None:
    prefix = Path(sys.base_prefix)
    tcl = prefix / "tcl" / "tcl8.6"
    tk = prefix / "tcl" / "tk8.6"
    if (tcl / "init.tcl").is_file():
        os.environ["TCL_LIBRARY"] = str(tcl)
    if tk.is_dir():
        os.environ["TK_LIBRARY"] = str(tk)


ensure_tcl_tk()
