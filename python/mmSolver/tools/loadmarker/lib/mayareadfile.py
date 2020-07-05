# Copyright (C) 2018, 2019, 2020 David Cattermole.
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
Module for reading marker files.

This should be used by end-users, not the internal modules.
"""

import os

import maya.cmds

import mmSolver.logger

import mmSolver.api as mmapi
import mmSolver.utils.animcurve as anim_utils
import mmSolver.utils.node as node_utils
import mmSolver.tools.loadmarker.lib.fieldofview as fieldofview
import mmSolver.tools.loadmarker.lib.interface as interface
import mmSolver.tools.loadmarker.lib.formatmanager as fmtmgr

# Used to force importing of formats; do not remove this line.
import mmSolver.tools.loadmarker.lib.formats


LOG = mmSolver.logger.get_logger()


def read(file_path, **kwargs):
    """
    Read a file path, find the format parser based on the file extension.
    """
    if isinstance(file_path, (str, unicode)) is False:
        msg = 'file path must be a string, got %r'
        raise TypeError(msg % type(file_path))
    if os.path.isfile(file_path) is False:
        msg = 'file path does not exist; %r'
        raise OSError(msg % file_path)

    file_format_class = None
    mgr = fmtmgr.get_format_manager()
    for fmt in mgr.get_formats():
        attr = getattr(fmt, 'file_exts', None)
        if attr is None:
            continue
        if not isinstance(fmt.file_exts, list):
            continue
        for ext in fmt.file_exts:
            if file_path.endswith(ext):
                file_format_class = fmt
                break
    if file_format_class is None:
        msg = 'No file formats found for file path: %r'
        raise RuntimeError(msg % file_path)

    file_format_obj = file_format_class()
    file_info, mkr_data_list = file_format_obj.parse(file_path, **kwargs)
    return file_info, mkr_data_list


def __create_node(mkr_data, cam, mkr_grp, with_bundles):
    """
    Create a Marker object from a MarkerData object.

    :param mkr_data: The data to create the Marker with.
    :type mkr_data: MarkerData

    :param cam: Camera to create marker node underneath.
    :type cam: Camera

    :param mkr_grp: MarkerGroup to create marker underneath
    :type mkr_grp: MarkerGroup

    :param with_bundles: Create the Marker with Bundle attached?
    :type with_bundles: bool

    :returns: Created Marker and Bundle objects. If with_bundles is
              False, the Bundle object will be None.
    :rtype: (Marker, Bundle or None)
    """
    if isinstance(mkr_data, interface.MarkerData) is False:
        msg = 'mkr_data must be of type: %r'
        raise TypeError(msg % interface.MarkerData.__name__)
    if isinstance(with_bundles, bool) is False:
        msg = 'with_bundles must be of type: %r'
        raise TypeError(msg % bool.__name__)

    name = mkr_data.get_name()
    mkr_name = mmapi.get_new_marker_name(name)
    bnd_name = mmapi.get_new_bundle_name(name)
    bnd = None
    mmapi.load_plugin()
    if with_bundles is True:
        bnd = mmapi.Bundle().create_node(bnd_name)
    if cam and mkr_grp:
        cam = None
    mkr = mmapi.Marker().create_node(
        name=mkr_name,
        cam=cam,
        mkr_grp=mkr_grp,
        bnd=bnd)
    return mkr, bnd


def __set_attr_keyframes(node, attr_name, keyframes,
                         before_value=None,
                         after_value=None,
                         reduce_keys=None):
    """
    Set keyframes on a node.attribute, from a KeyframeData instance.

    :param node: Node to set data on.
    :type node: str

    :param attr_name: Attribute (on 'node') to set keyframes.
    :type attr_name: str

    :param keyframes: The keyframe information.
    :type keyframes: KeyframeData

    :param before_value: Value to set before the first keyframe.
    :type before_value: int, float or bool

    :param after_value: Value to set after the first keyframe.
    :type after_value: int, float or bool

    :param reduce_keys: Allow reducing the keyframes, potentially
                        deleting all keyframes. Values will NEVER be
                        changed, only duplicate keyframe data is
                        removed.
    :type reduce_keys: bool

    :returns: Maya API (version 1) MFnAnimCurve object.
    :rtype: maya.OpenMaya.MFnAnimCurve
    """
    if isinstance(keyframes, interface.KeyframeData) is False:
        msg = 'keyframes must be type %r'
        raise TypeError(msg % interface.KeyframeData.__name__)
    if reduce_keys is None:
        reduce_keys = False
    if isinstance(reduce_keys, bool) is False:
        msg = "reduce_keys must be type 'bool'"
        raise TypeError(msg)
    times, values = keyframes.get_times_and_values()
    assert len(times) == len(values)

    # Set an extra value before/after the first/last keyframe.
    if len(times) > 0:
        if before_value is not None:
            start_time = times[0]
            times = [start_time - 1] + times
            values = [before_value] + values
        if after_value is not None:
            end_time = times[-1]
            times = times + [end_time + 1]
            values = values + [after_value]

    # Reduce keyframes, we don't need per-frame keyframes if the data
    # is the same. Change the times/values just before we set the
    # keyframes
    if reduce_keys is True:
        tmp_times = list(times)
        tmp_values = list(values)
        times = []
        values = []
        prev_t = None
        prev_v = None
        for t, v in zip(tmp_times, tmp_values):
            if prev_v is None:
                times.append(t)
                values.append(v)
            elif interface.float_is_equal(prev_v, v) is False:
                times.append(prev_t)
                values.append(prev_v)
                times.append(t)
                values.append(v)
            prev_t = t
            prev_v = v

    node_attr = node + '.' + attr_name
    anim_fn = anim_utils.create_anim_curve_node_apione(times, values, node_attr)

    if reduce_keys is True:
        locked = maya.cmds.getAttr(node_attr, lock=True)
        maya.cmds.setAttr(node_attr, lock=False)
        maya.cmds.delete(node_attr, staticChannels=True)
        maya.cmds.setAttr(node_attr, lock=locked)
    return anim_fn


def __set_node_data(mkr, bnd, mkr_data,
                    load_bnd_pos,
                    overscan_x, overscan_y):
    """
    Set and override the data on the given marker node.

    .. note:: marker may have existing data or not.

    :param mkr: Marker object to set data on.
    :type mkr: mmapi.Marker

    :param bnd: (optional) Bundle object to set data on.
    :type bnd: None or mmapi.Marker

    :param mkr_data: The data to set on the Marker/Bundle.
    :type mkr_data: MarkerData

    :param load_bnd_pos: Should we set Bundle positions?
    :type load_bnd_pos: bool

    :param overscan_x: Overscan factor to apply to the MarkerData x values.
    :type overscan_x: float

    :param overscan_y: Overscan factor to apply to the MarkerData y values.
    :type overscan_y: float

    :returns: Tuple of Marker and Bundle objects.
    :rtype: (Marker, Bundle or None)
    """
    assert isinstance(mkr, mmapi.Marker)
    assert bnd is None or isinstance(bnd, mmapi.Bundle)
    assert isinstance(mkr_data, interface.MarkerData)
    assert load_bnd_pos is None or isinstance(load_bnd_pos, bool)
    assert isinstance(overscan_x, float)
    assert isinstance(overscan_y, float)
    mkr_node = mkr.get_node()

    mkr_name = mkr_data.get_name()
    assert isinstance(mkr_name, (str, unicode))
    maya.cmds.setAttr(mkr_node + '.markerName', lock=False)
    maya.cmds.setAttr(mkr_node + '.markerName', mkr_name, type='string')
    maya.cmds.setAttr(mkr_node + '.markerName', lock=True)

    # Add marker data ID onto the marker node, to be used
    # for re-mapping point data regardless of point name.
    mkr_id = mkr_data.get_id()
    if mkr_id is None:
        mkr_id = -1
    maya.cmds.setAttr(mkr_node + '.markerId', lock=False)
    maya.cmds.setAttr(mkr_node + '.markerId', mkr_id)
    maya.cmds.setAttr(mkr_node + '.markerId', lock=True)

    # Get keyframe data
    mkr_x_data = mkr_data.get_x().get_raw_data()
    mkr_y_data = mkr_data.get_y().get_raw_data()
    for t, v in mkr_x_data.iteritems():
        mkr_x_data[t] = (v - 0.5) * overscan_x
    for t, v in mkr_y_data.iteritems():
        mkr_y_data[t] = (v - 0.5) * overscan_y
    mkr_x = interface.KeyframeData(data=mkr_x_data)
    mkr_y = interface.KeyframeData(data=mkr_y_data)
    mkr_enable = mkr_data.get_enable()
    mkr_weight = mkr_data.get_weight()

    # Unlock
    maya.cmds.setAttr(mkr_node + '.translateX', lock=False)
    maya.cmds.setAttr(mkr_node + '.translateY', lock=False)
    maya.cmds.setAttr(mkr_node + '.enable', lock=False)
    maya.cmds.setAttr(mkr_node + '.weight', lock=False)

    # Set keyframes.
    __set_attr_keyframes(mkr_node, 'translateX', mkr_x)
    __set_attr_keyframes(mkr_node, 'translateY', mkr_y)
    __set_attr_keyframes(mkr_node, 'enable', mkr_enable,
                         before_value=False,
                         after_value=False,
                         reduce_keys=True)
    __set_attr_keyframes(mkr_node, 'weight', mkr_weight, reduce_keys=True)

    # Lock
    maya.cmds.setAttr(mkr_node + '.translateX', lock=True)
    maya.cmds.setAttr(mkr_node + '.translateY', lock=True)
    maya.cmds.setAttr(mkr_node + '.enable', lock=True)
    maya.cmds.setAttr(mkr_node + '.weight', lock=True)

    # Set Bundle Position
    if bnd and load_bnd_pos:
        bnd_node = bnd.get_node()
        bnd_x = mkr_data.get_bundle_x()
        bnd_y = mkr_data.get_bundle_y()
        bnd_z = mkr_data.get_bundle_z()
        bnd_lock_x = mkr_data.get_bundle_lock_x()
        bnd_lock_y = mkr_data.get_bundle_lock_y()
        bnd_lock_z = mkr_data.get_bundle_lock_z()

        maya.cmds.setAttr(bnd_node + '.translateX', lock=False)
        maya.cmds.setAttr(bnd_node + '.translateY', lock=False)
        maya.cmds.setAttr(bnd_node + '.translateZ', lock=False)

        if isinstance(bnd_x, float):
            maya.cmds.setAttr(bnd_node + '.translateX', bnd_x)
        if isinstance(bnd_y, float):
            maya.cmds.setAttr(bnd_node + '.translateY', bnd_y)
        if isinstance(bnd_z, float):
            maya.cmds.setAttr(bnd_node + '.translateZ', bnd_z)

        if isinstance(bnd_lock_x, bool):
            maya.cmds.setAttr(bnd_node + '.translateX', lock=True)
        if isinstance(bnd_lock_y, bool):
            maya.cmds.setAttr(bnd_node + '.translateY', lock=True)
        if isinstance(bnd_lock_z, bool):
            maya.cmds.setAttr(bnd_node + '.translateZ', lock=True)
    return mkr, bnd


def create_nodes(mkr_data_list,
                 cam=None,
                 mkr_grp=None,
                 with_bundles=None,
                 load_bundle_position=None,
                 camera_field_of_view=None):
    """
    Create Markers for all given MarkerData objects

    :param mkr_data_list: List of MarkerData with data for creating
                          markers.
    :type mkr_data_list: [MarkerData, ..]

    :param cam: Camera to create Markers under.
    :type cam: Camera

    :param mkr_grp: Marker Group, under cam, that the markers will
                    be created under.
    :type mkr_grp: MarkerGroup

    :param with_bundles: Create a bundle for each Marker.
    :type with_bundles: bool

    :param load_bundle_position: Apply the 3D positions to bundle.
    :type load_bundle_position: bool

    :param camera_field_of_view: The camera field of view of the
                                 original camera with this 2D data.
    :type camera_field_of_view: [(int, float, float)]

    :returns: List of Markers.
    :rtype: [Marker, ..]
    """
    if with_bundles is None:
        with_bundles = True
    if load_bundle_position is None:
        load_bundle_position = True
    assert isinstance(cam, mmapi.Camera)
    assert isinstance(mkr_grp, mmapi.MarkerGroup)
    assert isinstance(with_bundles, bool)
    assert isinstance(load_bundle_position, bool)
    assert camera_field_of_view is None \
        or isinstance(camera_field_of_view, (list, tuple))

    selected_nodes = maya.cmds.ls(selection=True, long=True) or []

    overscan_x = 1.0
    overscan_y = 1.0
    if camera_field_of_view is not None:
        overscan_x, overscan_y = fieldofview.calculate_overscan_ratio(
            cam,
            mkr_grp,
            camera_field_of_view
        )

    mkr_nodes = []
    mkr_list = []
    for mkr_data in mkr_data_list:
        # Create the nodes
        mkr, bnd = __create_node(
            mkr_data, cam, mkr_grp,
            with_bundles,
        )
        mkr_nodes.append(mkr.get_node())
        if mkr is not None:
            # Set attributes and add into list
            __set_node_data(
                mkr, bnd, mkr_data,
                load_bundle_position,
                overscan_x, overscan_y
            )
            mkr_list.append(mkr)
    if len(mkr_nodes) > 0:
        maya.cmds.select(mkr_nodes, replace=True)
    else:
        maya.cmds.select(selected_nodes, replace=True)
    return mkr_list


def _get_marker_internal_id(mkr):
    """
    Get the Marker object's internal ID (the 'Persistent ID' given
    from 3DE).

    :rtype: int or None
    """
    assert isinstance(mkr, mmapi.Marker)
    node = mkr.get_node()
    value = None
    attr_name = 'markerId'
    if node_utils.attribute_exists(attr_name, node):
        plug = '{0}.{1}'.format(node, attr_name)
        value = maya.cmds.getAttr(plug)
        if value < 0:
            value = None
    return value


def _get_marker_internal_name(mkr):
    """
    Get the Marker object's internal ID (the 'Persistent ID' given
    from 3DE).

    :rtype: str or None
    """
    assert isinstance(mkr, mmapi.Marker)
    node = mkr.get_node()
    value = None
    attr_name = 'markerName'
    if node_utils.attribute_exists(attr_name, node):
        plug = '{0}.{1}'.format(node, attr_name)
        value = maya.cmds.getAttr(plug)
    return value


def _find_marker_data(mkr, mkr_data_list):
    """
    Find the matching MarkerData object for the given Marker.

    :param mkr: Marker node to find a match for.
    :type mkr:

    :param mkr_data_list: The MarkerData objects to consider as a match for 'mkr'.
    :type mkr_data_list: [MarkerData, ..]

    :returns: A matching MarkerData object.
    :rtype: MarkerData
    """
    assert isinstance(mkr, mmapi.Marker)
    assert len(mkr_data_list) > 0
    found_mkr_data = None
    if len(mkr_data_list) == 1:
        found_mkr_data = mkr_data_list[0]
        return found_mkr_data

    mkr_id = _get_marker_internal_id(mkr)
    mkr_name = _get_marker_internal_name(mkr)
    for mkr_data in mkr_data_list:
        # Do the 'id's match? If not, try using the 'name's.
        mkr_data_id = mkr_data.get_id()
        if (mkr_id is not None
                and mkr_data_id is not None
                and mkr_id == mkr_data_id):
            found_mkr_data = mkr_data
            break
        mkr_data_name = mkr_data.get_name()
        if (mkr_name is not None
                and mkr_data_name is not None
                and mkr_name == mkr_data_name):
            found_mkr_data = mkr_data
            break
    return found_mkr_data


def _update_node(mkr, bnd, mkr_data,
                 load_bundle_position,
                 overscan_x, overscan_y):
    """
    Set the MarkerData on the given Marker and Bundle.
    """
    assert isinstance(mkr, mmapi.Marker)
    assert bnd is None or isinstance(bnd, mmapi.Bundle)
    assert isinstance(mkr_data, interface.MarkerData)
    __set_node_data(
        mkr, bnd, mkr_data,
        load_bundle_position,
        overscan_x, overscan_y
    )
    return


def update_nodes(mkr_list, mkr_data_list,
                 load_bundle_position=None,
                 camera_field_of_view=None):
    """
    Update the given mkr_list with data from mkr_data_list.
    The length of both lists must match.

    :param mkr_list: Markers to update.
    :type mkr_list: [Marker, ..]

    :param mkr_data_list: The MarkerData list to search for a match.
    :type mkr_data_list: [MarkerData, ..]

    :param load_bundle_position: Apply the 3D positions to bundle.
    :type load_bundle_position: bool

    :param camera_field_of_view: The camera field of view of the
                                 original camera with this 2D data.
    :type camera_field_of_view: [(int, float, float)]

    :returns: List of Marker objects that were changed.
    :rtype: [Marker, ..]
    """
    if load_bundle_position is None:
        load_bundle_position = True
    assert isinstance(mkr_list, (list, tuple, set))
    assert isinstance(mkr_data_list, (list, tuple, set))
    assert isinstance(load_bundle_position, bool)
    assert camera_field_of_view is None \
        or isinstance(camera_field_of_view, (list, tuple))
    selected_nodes = maya.cmds.ls(selection=True, long=True) or []

    # Calculate overscan for marker's camera node.
    overscan_per_camera = {}
    if camera_field_of_view is not None:
        for mkr in mkr_list:
            mkr_grp = mkr.get_marker_group()
            cam = mkr.get_camera()
            cam_shp = cam.get_shape_node()
            if cam_shp in overscan_per_camera:
                continue
            overscan_x, overscan_y = fieldofview.calculate_overscan_ratio(
                cam,
                mkr_grp,
                camera_field_of_view
            )
            overscan_per_camera[cam_shp] = (overscan_x, overscan_y)

    mkr_list_changed = []
    if len(mkr_list) == 1 and len(mkr_data_list) == 1:
        mkr = mkr_list[0]
        cam = mkr.get_camera()
        bnd = mkr.get_bundle()
        mkr_data = mkr_data_list[0]
        cam_shp = cam.get_shape_node()
        fallback_overscan = (1.0, 1.0)
        overscan_x, overscan_y = overscan_per_camera.get(
            cam_shp, fallback_overscan
        )
        _update_node(
            mkr, bnd, mkr_data,
            load_bundle_position,
            overscan_x, overscan_y
        )
    else:
        # Make a copy of mkr_list and mkr_data_list, to avoid any
        # posiblity of the given arguments mkr_list and mkr_data_list
        # being modified indirectly (which can happen in Python).
        mkr_list = list(mkr_list)
        mkr_data_list = list(mkr_data_list)
        while len(mkr_list) > 0:
            mkr = mkr_list.pop(0)
            mkr_data = _find_marker_data(mkr, mkr_data_list)
            if mkr_data is None:
                continue
            cam = mkr.get_camera()
            bnd = mkr.get_bundle()
            cam_shp = cam.get_shape_node()
            fallback_overscan = (1.0, 1.0)
            overscan_x, overscan_y = overscan_per_camera.get(
                cam_shp, fallback_overscan,
            )
            _update_node(
                mkr, bnd, mkr_data,
                load_bundle_position,
                overscan_x, overscan_y
            )
            mkr_data_list.remove(mkr_data)
            mkr_list_changed.append(mkr)

    mkr_nodes_changed = [mkr.get_node() for mkr in mkr_list_changed]
    if len(mkr_nodes_changed) > 0:
        maya.cmds.select(mkr_nodes_changed, replace=True)
    else:
        maya.cmds.select(selected_nodes, replace=True)
    return mkr_list_changed
