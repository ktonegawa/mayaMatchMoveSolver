# Copyright (C) 2020 John Smith.
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
Remove Solver Nodes - user facing.
"""
from functools import wraps

import mmSolver.logger
import mmSolver.api as mmapi
import maya.cmds as cmds
import mmSolver._api.utils as api_utils

LOG = mmSolver.logger.get_logger()

def undoStack(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        try:
            return func(*args, **kwargs)
        except Exception:
            raise
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrap

def filter_nodes(what_to_delete_dict):
    nodes = cmds.ls(long=True) or []
    cmds.select([])
    node_categories = mmapi.filter_nodes_into_categories(nodes)
    unknown_node_found = False
    print 'filter_nodes run'
    all_list_to_delete = list()
    for key in what_to_delete_dict.keys():
        if key == 'markers' and what_to_delete_dict[key]:
            all_list_to_delete += \
                collect_nodes(node_categories, mode='marker')
        elif key == 'other_nodes' and what_to_delete_dict[key]:
            all_list_to_delete += collect_misc_nodes()
        elif key == 'bundles' and what_to_delete_dict[key]:
            delete_list, unknown_node_found = collect_bundles(node_categories)
            all_list_to_delete += delete_list
        elif key == 'marker_groups' and what_to_delete_dict[key]:
            all_list_to_delete += \
                collect_nodes(node_categories, mode='markergroup')
        elif key == 'collections' and what_to_delete_dict[key]:
            all_list_to_delete += \
                collect_nodes(node_categories, mode='collection')
    return all_list_to_delete, unknown_node_found

def collect_nodes(node_categories, mode='marker'):
    list_to_delete = list()
    for key in sorted(node_categories.keys()):
        if key in ['attribute', 'bundle', 'camera', 'other']:
            continue
        for node in node_categories[mode]:
            list_to_delete.append(node)
    return list_to_delete

def collect_misc_nodes():
    misc_nodes = cmds.ls(long=True,
                       type=['mmMarkerScale',
                             'mmReprojection',
                             'mmMarkerGroupTransform'])
    other_nodes = cmds.ls('mmSolver*', long=True)
    combined_set = set(misc_nodes+other_nodes)
    return list(combined_set)

def collect_bundles(node_categories):
    unknown_node_found = False
    list_to_delete = list()
    for node in node_categories['bundle']:
        if cmds.objectType(node) != 'transform':
            continue
        list_to_delete.append(node)
        children = cmds.listRelatives(node, children=True, type='transform',
                                      fullPath=True)
        if children:
            for child in children:
                if api_utils.get_object_type(child) != 'bundle':
                    unknown_node_found = True
    return list_to_delete, unknown_node_found

@undoStack
def delete_nodes(nodes_to_delete):
    for node in nodes_to_delete:
        if cmds.objExists(node):
            cmds.delete(node)

def main():
    """
    Open the Channel Sensitivity window.
    """
    import mmSolver.tools.removesolvernodes.ui.removesolvernodes_window as window
    window.main()
