# Copyright (C) 2019 David Cattermole.
#
# This file is part of mmSolver.
#
# mmSolver is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# mmSolver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with mmSolver.  If not, see <https://www.gnu.org/licenses/>.
#
"""
User facing root frame editing functions.

This function may be called in a UI context.
"""

import maya.cmds

import mmSolver.logger
import mmSolver.tools.solver.ui.solver_window as solver_window
import mmSolver.tools.solver.lib.state as lib_state
import mmSolver.tools.editrootframes.lib as lib

LOG = mmSolver.logger.get_logger()


def main_add_frame():
    """
    Add the current time to the list of root frames.
    """
    col = lib_state.get_active_collection()
    root_frames = lib.get_root_frames_list(col)
    if root_frames is not None:
        assert isinstance(root_frames, list)

        current_frame = maya.cmds.currentTime(query=True)
        root_frames.append(int(current_frame))
        lib.set_root_frames_list(col, root_frames)

        # Update UI
        window_instance = solver_window.SolverWindow.get_instance()
        if window_instance is not None:
            window_instance.triggerCollectionUpdate()
    return


def main_remove_frame():
    """
    Remove the current time from the list of root frames.
    """
    col = lib_state.get_active_collection()
    root_frames = lib.get_root_frames_list(col)
    if root_frames is not None:
        assert isinstance(root_frames, list)
        current_frame = maya.cmds.currentTime(query=True)
        frame = int(current_frame)
        if frame in root_frames:
            root_frames.remove(frame)
            lib.set_root_frames_list(col, root_frames)

            # Update UI
            window_instance = solver_window.SolverWindow.get_instance()
            if window_instance is not None:
                window_instance.triggerCollectionUpdate()
    return

