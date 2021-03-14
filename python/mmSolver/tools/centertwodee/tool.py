# Copyright (C) 2018, 2019, 2021 David Cattermole, Kazuma Tonegawa.
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
The Center 2D tool.
"""

import warnings

import maya.cmds

import mmSolver.api as mmapi
import mmSolver.logger
import mmSolver.tools.centertwodee.lib as lib
import mmSolver.utils.viewport as viewport_utils
import mmSolver.utils.reproject as reproject_utils

LOG = mmSolver.logger.get_logger()


def main():
    """
    Center the selected transform onto the camera view.

    .. todo::

        - Allow 2D Center on selected vertices.

        - Support Stereo-camera setups (center both cameras, and ensure
          both have the same zoom).

        - Allow centering on multiple objects at once. We will center
          on the middle of all transforms.

    """
    model_editor = viewport_utils.get_active_model_editor()
    if model_editor is None:
        msg = 'Please select an active 3D viewport.'
        LOG.warning(msg)
        return

    cam_tfm, cam_shp = viewport_utils.get_viewport_camera(model_editor)
    if cam_shp is None:
        msg = 'Please select an active 3D viewport to get a camera.'
        LOG.warning(msg)
        return

    try:
        mmapi.set_solver_running(True)

        save_sel = maya.cmds.ls(selection=True, long=True) or []

        # Get selection
        nodes = maya.cmds.ls(
            selection=True,
            long=True,
            type='transform',
        ) or []

        # Filter out selected imagePlanes.
        nodes_tmp = list(nodes)
        nodes = []
        for node in nodes_tmp:
            shps = maya.cmds.listRelatives(
                node,
                shapes=True,
                fullPath=True,
                type='imagePlane') or []
            if len(shps) == 0:
                nodes.append(node)

        # Create centering node network.
        if len(nodes) == 0:
            msg = 'No objects selected, removing 2D centering.'
            LOG.warning(msg)
            mmapi.load_plugin()
            reproject_utils.remove_reprojection_from_camera(cam_tfm, cam_shp)
            reproject_utils.reset_pan_zoom(cam_tfm, cam_shp)
        elif len(nodes) == 1:
            msg = 'Applying 2D centering to %r'
            LOG.warning(msg, nodes)
            mmapi.load_plugin()
            reproj_nodes = reproject_utils.find_reprojection_nodes(cam_tfm, cam_shp)
            if len(reproj_nodes) > 0:
                maya.cmds.delete(reproj_nodes)

            reproj_node = reproject_utils.create_reprojection_on_camera(
                cam_tfm, cam_shp)
            reproject_utils.connect_transform_to_reprojection(
                nodes[0], reproj_node)

            # create 2d offset setup
            offset_plus_minus_node = maya.cmds.createNode(
                'plusMinusAverage',
                name='offset_plusMinusAverage1')
            maya.cmds.connectAttr(
                reproj_node + '.outPan',
                offset_plus_minus_node + '.input2D[0]')
            maya.cmds.setAttr(
                offset_plus_minus_node + '.input2D[1]',
                0.0,
                0.0,
                type='float2')
            maya.cmds.connectAttr(
                offset_plus_minus_node + '.output2D',
                cam_shp + '.pan',
                force=True)

            # create a zoom setup
            zoom_mult_node = maya.cmds.createNode(
                'multiplyDivide',
                name='zoom_multiplyDivide1')
            maya.cmds.setAttr(zoom_mult_node + '.input1X', 1.0)
            maya.cmds.setAttr(zoom_mult_node + '.operation', 2)
            maya.cmds.setAttr(zoom_mult_node + '.input2X', 1.0)
            maya.cmds.connectAttr(
                zoom_mult_node + '.outputX',
                cam_shp + '.zoom')

        elif len(nodes) > 1:
            msg = 'Please select only 1 node to center on.'
            LOG.error(msg)

        if len(save_sel) > 0:
            maya.cmds.select(save_sel, replace=True)
    finally:
        mmapi.set_solver_running(False)
    return


def remove():
    """
    Remove the centering nodes in the current active viewport.
    """
    model_editor = viewport_utils.get_active_model_editor()
    if model_editor is None:
        msg = 'Please select an active 3D viewport.'
        LOG.warning(msg)
        return

    cam_tfm, cam_shp = viewport_utils.get_viewport_camera(model_editor)
    if cam_shp is None:
        msg = 'Please select an active 3D viewport to get a camera.'
        LOG.warning(msg)
        return

    try:
        mmapi.set_solver_running(True)
        mmapi.load_plugin()
        reproject_utils.remove_reprojection_from_camera(cam_tfm, cam_shp)
        reproject_utils.reset_pan_zoom(cam_tfm, cam_shp)
    finally:
        mmapi.set_solver_running(False)
    return


def get_offset_nodes():
    """
    Query for Center 2D nodes
    :returns: Two offset nodes (plusMinusAverage and multiplyDivide)
    :rtype: string, string.
    """
    model_editor = viewport_utils.get_active_model_editor()
    cam_tfm, cam_shp = viewport_utils.get_viewport_camera(model_editor)
    reprojection_nodes = reproject_utils.find_reprojection_nodes(cam_tfm, cam_shp)
    offset_node = None
    zoom_node = None
    for node in reprojection_nodes:
        if 'offset_plusMinusAverage' in node:
            offset_node = node
        elif 'zoom_multiplyDivide' in node:
            zoom_node = node
    return offset_node, zoom_node


def get_offset_node_values(offset_node, zoom_node):
    """
    Get attribute values for offset nodes
    :rtype: (float, float, flaot)
    """
    offset_x_value = maya.cmds.getAttr(offset_node + '.input2D[1].input2Dx')
    offset_y_value = maya.cmds.getAttr(offset_node + '.input2D[1].input2Dy')
    zoom_value = maya.cmds.getAttr(zoom_node + '.input2X')
    return (offset_x_value, offset_y_value, zoom_value)


def process_value(**kwargs):
    input_value = kwargs.get('input_value')
    if kwargs.get('zoom') == False:
        new_range = lib.set_offset_range(kwargs.get('source'))
        zoom = False
    elif kwargs.get('zoom') == True:
        new_range = lib.set_zoom_range(**kwargs)
        zoom = True
    input_range_start,\
    input_range_end,\
    output_range_start,\
    output_range_end = new_range

    output = lib.convert_range(
        input_value=input_value,
        input_range_start=input_range_start,
        input_range_end=input_range_end,
        output_range_start=float(output_range_start),
        output_range_end=float(output_range_end),
        zoom=zoom
    )
    return output


def set_horizontal_offset(offset_node, value):
    maya.cmds.setAttr(offset_node + '.input2D[1].input2Dx', value)


def set_vertical_offset(offset_node, value):
    maya.cmds.setAttr(offset_node + '.input2D[1].input2Dy', value)


def set_zoom(zoom_node, value):
    maya.cmds.setAttr(zoom_node + '.input2X', value)


def center_two_dee():
    warnings.warn("Use 'main' function instead.")
    main()


def center_two_dee_ui():
    model_editor = viewport_utils.get_active_model_editor()
    if model_editor is None:
        msg = 'Please select an active 3D viewport.'
        LOG.warning(msg)
        return
    import mmSolver.tools.centertwodee.ui.centertwodee_window as window
    window.main()