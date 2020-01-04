/*
 * Copyright (C) 2019 David Cattermole.
 *
 * This file is part of mmSolver.
 *
 * mmSolver is free software: you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * mmSolver is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with mmSolver.  If not, see <https://www.gnu.org/licenses/>.
 * ====================================================================
 *
 * Command for running mmReprojection.
 */


// Internal
#include <MMReprojectionCmd.h>
#include <mayaUtils.h>
#include <Camera.h>
#include <core/bundleAdjust_base.h>
#include <core/reprojection.h>

// STL
#include <vector>
#include <cmath>
#include <cassert>

// Utils
#include <utilities/debugUtils.h>
#include <utilities/stringUtils.h>

// Maya
#include <maya/MSyntax.h>
#include <maya/MArgList.h>
#include <maya/MArgDatabase.h>
#include <maya/MString.h>
#include <maya/MStringArray.h>
#include <maya/MObject.h>
#include <maya/MPlug.h>
#include <maya/MTime.h>
#include <maya/MTimeArray.h>
#include <maya/MMatrix.h>
#include <maya/MMatrixArray.h>
#include <maya/MDagPath.h>
#include <maya/MFnDependencyNode.h>



MMReprojectionCmd::~MMReprojectionCmd() {}

void *MMReprojectionCmd::creator() {
    return new MMReprojectionCmd();
}

MString MMReprojectionCmd::cmdName() {
    return MString("mmReprojection");
}

/*
 * Tell Maya we have a syntax function.
 */
bool MMReprojectionCmd::hasSyntax() const {
    return true;
}

bool MMReprojectionCmd::isUndoable() const {
    return false;
}

/*
 * Add flags to the command syntax
 */
MSyntax MMReprojectionCmd::newSyntax() {
    MSyntax syntax;
    syntax.enableQuery(false);
    syntax.enableEdit(false);

    unsigned int minNumObjects = 0;
    syntax.setObjectType(MSyntax::kSelectionList, minNumObjects);

    // Flags
    syntax.addFlag(WORLD_POINT_FLAG, WORLD_POINT_FLAG_LONG,
            MSyntax::kDouble, MSyntax::kDouble, MSyntax::kDouble);
    syntax.addFlag(CAMERA_FLAG, CAMERA_FLAG_LONG,
            MSyntax::kString, MSyntax::kString);
    syntax.addFlag(TIME_FLAG, TIME_FLAG_LONG,
            MSyntax::kDouble);
    syntax.addFlag(IMAGE_RES_FLAG, IMAGE_RES_FLAG_LONG,
            MSyntax::kDouble, MSyntax::kDouble);
    syntax.addFlag(AS_CAM_POINT_FLAG, AS_CAM_POINT_FLAG_LONG,
            MSyntax::kBoolean);
    syntax.addFlag(AS_WORLD_POINT_FLAG, AS_WORLD_POINT_FLAG_LONG,
            MSyntax::kBoolean);
    syntax.addFlag(AS_COORD_FLAG, AS_COORD_FLAG_LONG,
            MSyntax::kBoolean);
    syntax.addFlag(AS_NORM_COORD_FLAG, AS_NORM_COORD_FLAG_LONG,
            MSyntax::kBoolean);
    syntax.addFlag(AS_MARKER_COORD_FLAG, AS_MARKER_COORD_FLAG_LONG,
            MSyntax::kBoolean);
    syntax.addFlag(AS_PIXEL_COORD_FLAG, AS_PIXEL_COORD_FLAG_LONG,
            MSyntax::kBoolean);

    syntax.makeFlagMultiUse(TIME_FLAG);

    return syntax;
}

/*
 * Parse command line arguments
 */
MStatus MMReprojectionCmd::parseArgs(const MArgList &args) {
    MStatus status = MStatus::kSuccess;

    MArgDatabase argData(syntax(), args, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);

    // Get Camera Point flag
    m_asCameraPoint = false;
    bool cameraPointFlagIsSet = argData.isFlagSet(AS_CAM_POINT_FLAG, &status);
    if (cameraPointFlagIsSet == true) {
        status = argData.getFlagArgument(AS_CAM_POINT_FLAG, 0, m_asCameraPoint);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }

    // Get World Point flag
    m_asWorldPoint = false;
    bool worldPointFlagIsSet = argData.isFlagSet(AS_WORLD_POINT_FLAG, &status);
    if (worldPointFlagIsSet == true) {
        status = argData.getFlagArgument(AS_WORLD_POINT_FLAG, 0, m_asWorldPoint);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }

    // Get Coordinate flag
    m_asCoordinate = false;
    bool coordFlagIsSet = argData.isFlagSet(AS_COORD_FLAG, &status);
    if (coordFlagIsSet == true) {
        status = argData.getFlagArgument(AS_COORD_FLAG, 0, m_asCoordinate);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }

    // Get Normalized Coordinate flag
    m_asNormalizedCoordinate = false;
    bool normCoordFlagIsSet = argData.isFlagSet(AS_NORM_COORD_FLAG, &status);
    if (normCoordFlagIsSet == true) {
        status = argData.getFlagArgument(AS_NORM_COORD_FLAG, 0, m_asNormalizedCoordinate);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }

    // Get Marker Coordinate flag
    m_asMarkerCoordinate = false;
    bool markerCoordFlagIsSet = argData.isFlagSet(AS_MARKER_COORD_FLAG, &status);
    if (markerCoordFlagIsSet == true) {
        status = argData.getFlagArgument(AS_MARKER_COORD_FLAG, 0, m_asMarkerCoordinate);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }

    // Get Pixel Coordinate flag
    m_asPixelCoordinate = false;
    bool pixelCoordFlagIsSet = argData.isFlagSet(AS_PIXEL_COORD_FLAG, &status);
    if (pixelCoordFlagIsSet == true) {
         status = argData.getFlagArgument(AS_PIXEL_COORD_FLAG, 0, m_asPixelCoordinate);
         CHECK_MSTATUS_AND_RETURN_IT(status);
    }

    // Get Image Resolution flag
    m_imageResX = 2048.0;
    m_imageResY = 1556.0;
    bool imageResFlagIsSet = argData.isFlagSet(IMAGE_RES_FLAG, &status);
    if (imageResFlagIsSet == true) {
        status = argData.getFlagArgument(IMAGE_RES_FLAG, 0, m_imageResX);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        status = argData.getFlagArgument(IMAGE_RES_FLAG, 1, m_imageResY);
        CHECK_MSTATUS_AND_RETURN_IT(status);
    }

    // Get World Flag flag or Get Transforms
    m_nodeList.clear();
    m_worldPoint = MPoint();
    m_givenWorldPoint = argData.isFlagSet(WORLD_POINT_FLAG, &status);
    if (m_givenWorldPoint == true) {
        double worldPointX = 0.0;
        double worldPointY = 0.0;
        double worldPointZ = 0.0;
        status = argData.getFlagArgument(WORLD_POINT_FLAG, 0, worldPointX);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        status = argData.getFlagArgument(WORLD_POINT_FLAG, 1, worldPointY);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        status = argData.getFlagArgument(WORLD_POINT_FLAG, 2, worldPointZ);
        CHECK_MSTATUS_AND_RETURN_IT(status);

        m_worldPoint.x = worldPointX;
        m_worldPoint.y = worldPointY;
        m_worldPoint.z = worldPointZ;
    } else {
        status = argData.getObjects(m_nodeList);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        if (m_nodeList.length() == 0) {
            status = MStatus::kFailure;
            status.perror("No objects given!");
            return status;
        }
    }

    // Get Time
    unsigned int timeNum = argData.numberOfFlagUses(TIME_FLAG);
    if (timeNum == 0) {
        status = MStatus::kFailure;
        status.perror("No times flags given. Time values are required.");
        return status;
    }
    m_timeList.clear();
    MTime::Unit unit = MTime::uiUnit();
    MArgList argList;
    for (unsigned int i = 0; i < timeNum; ++i) {
        status = argData.getFlagArgumentList(TIME_FLAG, i, argList);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        double tmp = argList.asDouble(i, &status);
        MTime time(tmp, unit);
        CHECK_MSTATUS_AND_RETURN_IT(status);
        m_timeList.append(time);
    }
    if (m_timeList.length() == 0) {
        status = MStatus::kFailure;
        status.perror("No time values to query.");
        return status;
    }

    // Get Camera
    bool cameraFlagIsSet = argData.isFlagSet(CAMERA_FLAG, &status);
    if (cameraFlagIsSet == false) {
        status = MStatus::kFailure;
        status.perror("\'camera\' flag was not given, but is required!");
        return status;
    }
    MString cameraTransform = "";
    MString cameraShape = "";
    MArgList cameraArgs;
    status = argData.getFlagArgumentList(CAMERA_FLAG, 0, cameraArgs);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    if (cameraArgs.length() != 2) {
        status = MStatus::kFailure;
        status.perror("\'camera\' flag must have 2 arguments; "
                      "\"cameraTransform\", \"cameraShape\".");
        return status;
    }

    cameraTransform = cameraArgs.asString(0, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    nodeExistsAndIsType(cameraTransform, MFn::Type::kTransform);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    m_camera.setTransformNodeName(cameraTransform);

    cameraShape = cameraArgs.asString(1, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    nodeExistsAndIsType(cameraShape, MFn::Type::kCamera);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    m_camera.setShapeNodeName(cameraShape);

    return status;
}


MStatus MMReprojectionCmd::doIt(const MArgList &args) {
//
//  Description:
//    implements the MEL mmReprojection command.
//
//  Arguments:
//    argList - the argument list that was passes to the command from MEL
//
//  Return Value:
//    MStatus::kSuccess - command succeeded
//    MStatus::kFailure - command failed (returning this value will cause the
//                     MEL script that is being run to terminate unless the
//                     error is caught using a "catch" statement.
//
    MStatus status = MStatus::kSuccess;

    // Command Outputs
    MDoubleArray outResult;

    // Read all the flag arguments.
    status = parseArgs(args);
    if (status == MStatus::kFailure) {
        return status;
    }

    // Flush the query cache for the camera.
    m_camera.clearAuxilaryAttrsCache();
    m_camera.clearProjMatrixCache();
    m_camera.clearWorldProjMatrixCache();
    m_camera.clearAttrValueCache();

    // Camera
    double focalLength = 35;
    double horizontalFilmAperture = 1;
    double verticalFilmAperture = 1;
    double horizontalFilmOffset = 0;
    double verticalFilmOffset = 0;
    short filmFit = 1;
    double nearClipPlane = 0.1;
    double farClipPlane = 1000;
    double cameraScale = 1;

    // Image
    double imageWidth = m_imageResX;
    double imageHeight = m_imageResY;

    // Manipulation
    MMatrix applyMatrix;
    bool overrideScreenX = false;
    bool overrideScreenY = false;
    bool overrideScreenZ = false;
    double screenX = 0;
    double screenY = 0;
    double screenZ = 0;
    double depthScale = 1.0;

    // Reprojection Outputs
    double outCoordX;
    double outCoordY;
    double outNormCoordX;
    double outNormCoordY;
    double outMarkerCoordX;
    double outMarkerCoordY;
    double outMarkerCoordZ;
    double outPixelX;
    double outPixelY;
    bool outInsideFrustum;
    double outPointX;
    double outPointY;
    double outPointZ;
    double outWorldPointX;
    double outWorldPointY;
    double outWorldPointZ;
    MMatrix outMatrix;
    MMatrix outWorldMatrix;
    MMatrix outCameraProjectionMatrix;
    MMatrix outInverseCameraProjectionMatrix;
    MMatrix outWorldCameraProjectionMatrix;
    MMatrix outWorldInverseCameraProjectionMatrix;
    double outHorizontalPan;
    double outVerticalPan;

    Attr cameraMatrixAttr = m_camera.getMatrixAttr();

    // Assumed to *not* be animated.
    farClipPlane = m_camera.getFarClipPlaneValue();
    cameraScale = m_camera.getCameraScaleValue();
    filmFit = m_camera.getFilmFitValue();

    // Lists of values to collect, then loop over and batch compute.
    MMatrixArray tfmMatrixList;
    MMatrixArray camMatrixList;
    MTimeArray timeList;
    std::vector<double> focalLengthList;
    std::vector<double> horizontalFilmApertureList;
    std::vector<double> verticalFilmApertureList;
    std::vector<double> horizontalFilmOffsetList;
    std::vector<double> verticalFilmOffsetList;

    //
    if (m_nodeList.length() == 0 && m_givenWorldPoint == true) {
        // We use the given world space point, rather than the list
        // of transform nodes.
        MMatrix tfmMatrix;
        tfmMatrix[3][0] = m_worldPoint.x;
        tfmMatrix[3][1] = m_worldPoint.y;
        tfmMatrix[3][2] = m_worldPoint.z;
        for (unsigned int j = 0; j < m_timeList.length(); ++j) {
            MTime time = m_timeList[j];
            timeList.append(time);

            MMatrix camMatrix;
            status = cameraMatrixAttr.getValue(camMatrix, time);
            camMatrixList.append(camMatrix);
            tfmMatrixList.append(tfmMatrix);

            // Possibly Animated
            focalLength = m_camera.getFocalLengthValue(time);
            horizontalFilmAperture = m_camera.getFilmbackWidthValue(time);
            verticalFilmAperture = m_camera.getFilmbackHeightValue(time);
            horizontalFilmOffset = m_camera.getFilmbackOffsetXValue(time);
            verticalFilmOffset = m_camera.getFilmbackOffsetYValue(time);

            focalLengthList.push_back(focalLength);
            horizontalFilmApertureList.push_back(horizontalFilmAperture);
            verticalFilmApertureList.push_back(verticalFilmAperture);
            horizontalFilmOffsetList.push_back(horizontalFilmOffset);
            verticalFilmOffsetList.push_back(verticalFilmOffset);
        }
    } else {
        // Reproject the list of transform nodes given to the command.
        for (unsigned int i = 0; i < m_nodeList.length(); ++i) {
            MDagPath dagPath;
            status = m_nodeList.getDagPath(i, dagPath);
            CHECK_MSTATUS_AND_RETURN_IT(status);
            MString nodeNamePath = dagPath.fullPathName(&status);
            CHECK_MSTATUS_AND_RETURN_IT(status);

            Attr tfmMatrixAttr;
            tfmMatrixAttr.setNodeName(nodeNamePath);
            tfmMatrixAttr.setAttrName("worldMatrix");
            for (unsigned int j = 0; j < m_timeList.length(); ++j) {
                MTime time = m_timeList[j];
                timeList.append(time);

                MMatrix camMatrix;
                MMatrix tfmMatrix;
                status = cameraMatrixAttr.getValue(camMatrix, time);
                status = tfmMatrixAttr.getValue(tfmMatrix, time);
                camMatrixList.append(camMatrix);
                tfmMatrixList.append(tfmMatrix);

                // Possibly Animated
                focalLength = m_camera.getFocalLengthValue(time);
                horizontalFilmAperture = m_camera.getFilmbackWidthValue(time);
                verticalFilmAperture = m_camera.getFilmbackHeightValue(time);
                horizontalFilmOffset = m_camera.getFilmbackOffsetXValue(time);
                verticalFilmOffset = m_camera.getFilmbackOffsetYValue(time);

                focalLengthList.push_back(focalLength);
                horizontalFilmApertureList.push_back(horizontalFilmAperture);
                verticalFilmApertureList.push_back(verticalFilmAperture);
                horizontalFilmOffsetList.push_back(horizontalFilmOffset);
                verticalFilmOffsetList.push_back(verticalFilmOffset);
            }
        }
    }

    // Do the re-projection calculations, using the gathered data.
    assert(tfmMatrixList.length() == m_timeList.length());
    for (unsigned int i = 0; i < tfmMatrixList.length(); ++i) {
        MTime time = timeList[i];
        MMatrix camMatrix = camMatrixList[i];
        MMatrix tfmMatrix = tfmMatrixList[i];

        // Possibly Animated
        focalLength = focalLengthList[i];
        horizontalFilmAperture = horizontalFilmApertureList[i];
        verticalFilmAperture = verticalFilmApertureList[i];
        horizontalFilmOffset = horizontalFilmOffsetList[i];
        verticalFilmOffset = verticalFilmOffsetList[i];

        // Query the reprojection.
        status = reprojection(
                tfmMatrix,
                camMatrix,

                // Camera
                focalLength,
                horizontalFilmAperture,
                verticalFilmAperture,
                horizontalFilmOffset,
                verticalFilmOffset,
                filmFit,
                nearClipPlane,
                farClipPlane,
                cameraScale,

                // Image
                imageWidth,
                imageHeight,

                // Manipulation
                applyMatrix,
                overrideScreenX,
                overrideScreenY,
                overrideScreenZ,
                screenX,
                screenY,
                screenZ,
                depthScale,

                // Outputs
                outCoordX, outCoordY,
                outNormCoordX, outNormCoordY,
                outMarkerCoordX, outMarkerCoordY, outMarkerCoordZ,
                outPixelX, outPixelY,
                outInsideFrustum,
                outPointX, outPointY, outPointZ,
                outWorldPointX, outWorldPointY, outWorldPointZ,
                outMatrix,
                outWorldMatrix,
                outCameraProjectionMatrix,
                outInverseCameraProjectionMatrix,
                outWorldCameraProjectionMatrix,
                outWorldInverseCameraProjectionMatrix,
                outHorizontalPan,
                outVerticalPan);
        CHECK_MSTATUS_AND_RETURN_IT(status);

        if (m_asCameraPoint == true) {
            outResult.append(outPointX);
            outResult.append(outPointY);
            outResult.append(outPointZ);
        }
        if (m_asWorldPoint == true) {
            outResult.append(outWorldPointX);
            outResult.append(outWorldPointY);
            outResult.append(outWorldPointZ);
        }
        if (m_asCoordinate == true) {
            outResult.append(outCoordX);
            outResult.append(outCoordY);
            outResult.append(outPointZ);
        }
        if (m_asNormalizedCoordinate == true) {
            outResult.append(outNormCoordX);
            outResult.append(outNormCoordY);
            outResult.append(outPointZ);
        }
        if (m_asMarkerCoordinate == true) {
            outResult.append(outMarkerCoordX);
            outResult.append(outMarkerCoordY);
            outResult.append(outMarkerCoordZ);
        }
        if (m_asPixelCoordinate == true) {
            outResult.append(outPixelX);
            outResult.append(outPixelY);
            outResult.append(outPointZ);
        }
    }

    MMReprojectionCmd::setResult(outResult);
    return status;
}
