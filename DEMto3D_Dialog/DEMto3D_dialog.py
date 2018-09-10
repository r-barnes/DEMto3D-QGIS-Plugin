# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DEMto3D
                                 A QGIS plugin
 Impresión 3D de MDE
                              -------------------
        begin                : 2015-08-02
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Francisco Javier Venceslá Simón
        email                : demto3d@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from __future__ import absolute_import
from builtins import str
import math

from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QFileDialog, QApplication
from qgis.PyQt.QtGui import QColor, QCursor
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsRubberBand, QgsMapTool, QgsMessageBar
from osgeo import gdal
import struct

from . import Export_dialog
from . import SelectLayer_dialog
from .DEMto3D_dialog_base import Ui_DEMto3DDialogBase, _fromUtf8
from qgis._core import QgsPointXY, QgsRectangle, QgsProject, QgsGeometry, QgsCoordinateTransform


def get_layer(layer_name):
    layermap = QgsProject.instance().mapLayers()
    for name, layer in layermap.items():
        if layer.name() == layer_name:
            if layer.isValid():
                return layer
            else:
                return None


class DEMto3DDialog(QDialog, Ui_DEMto3DDialogBase):
    # Layer to print
    layer = None
    ''' Region of interest properties '''
    map_crs = None
    roi_x_max = 0
    roi_x_min = 0
    roi_y_max = 0
    roi_y_min = 0
    z_max = 0
    z_min = 0
    ''' Model dimensions '''
    height = 0
    width = 0
    scale = 0
    z_scale = 0
    ''' Raster properties '''
    cell_size = 0
    cols = 0
    rows = 0
    raster_x_max = 0
    raster_x_min = 0
    raster_y_max = 0
    raster_y_min = 0

    def __init__(self, iface):
        """Constructor."""
        QDialog.__init__(self)
        self.ui = Ui_DEMto3DDialogBase()
        self.ui.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        try:
            self.map_crs = self.canvas.mapSettings().destinationCrs()
        except:
            self.map_crs = self.canvas.mapRenderer().destinationCrs()

        # region Layer action
        # fill layer combobox with raster visible layers in mapCanvas
        self.viewLayers = self.canvas.layers()
        self.ui.LayerComboBox.clear()
        for layer in self.viewLayers:
            if layer.type() == 1:
                self.ui.LayerComboBox.addItem(layer.name())
        self.layer = get_layer(self.ui.LayerComboBox.currentText())
        self.get_raster_properties()
        QtCore.QObject.connect(self.ui.LayerComboBox, QtCore.SIGNAL(_fromUtf8("activated(QString)")), self.get_layer)
        # endregion

        # region Extension actions
        self.extent = None
        QtCore.QObject.connect(self.ui.FullExtToolButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.full_extent)
        QtCore.QObject.connect(self.ui.LayerExtToolButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.layer_extent)
        QtCore.QObject.connect(self.ui.CustomExtToolButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.custom_extent)
        QtCore.QObject.connect(self.ui.XMinLineEdit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), self.upload_extent)
        QtCore.QObject.connect(self.ui.XMaxLineEdit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), self.upload_extent)
        QtCore.QObject.connect(self.ui.YMaxLineEdit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), self.upload_extent)
        QtCore.QObject.connect(self.ui.YMinLineEdit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), self.upload_extent)
        # endregion

        # region Dimension actions
        QtCore.QObject.connect(self.ui.HeightLineEdit, QtCore.SIGNAL(_fromUtf8("textEdited(QString)")),
                               self.upload_size_from_height)
        QtCore.QObject.connect(self.ui.WidthLineEdit, QtCore.SIGNAL(_fromUtf8("textEdited(QString)")),
                               self.upload_size_from_width)
        QtCore.QObject.connect(self.ui.ScaleLineEdit, QtCore.SIGNAL(_fromUtf8("textEdited(QString)")),
                               self.upload_size_from_scale)
        # endregion

        QtCore.QObject.connect(self.ui.ZScaleDoubleSpinBox, QtCore.SIGNAL(_fromUtf8("valueChanged(double)")),
                               self.get_height_model)
        QtCore.QObject.connect(self.ui.BaseHeightLineEdit, QtCore.SIGNAL(_fromUtf8("textEdited(QString)")),
                               self.get_height_model)

        # region Cancel, export, print buttons
        QtCore.QObject.connect(self.ui.CancelToolButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.reject)
        QtCore.QObject.connect(self.ui.STLToolButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.do_export)
        close = QtGui.QAction(self)
        self.connect(close, QtCore.SIGNAL('clicked()'), self.reject)
        # endregion

    def do_export(self):
        parameters = self.get_parameters()
        layer_name = self.ui.LayerComboBox.currentText() + '_model.stl'
        if parameters != 0:
            if parameters["spacing_mm"] < 0.5 and self.height > 100 and self.width > 100:
                reply = QMessageBox.question(self, self.tr('Export to STL'),
                                             self.tr('The construction of the STL file could takes several minutes. Do you want to continue?'),
                                             QMessageBox.Yes |
                                             QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    f, __ = QFileDialog.getSaveFileName(self, self.tr('Export to STL'), layer_name, filter=".stl")
                    stl_file = f[0]
                    if stl_file:
                        export_dlg = Export_dialog.Dialog(parameters, stl_file)
                        if export_dlg.exec_():
                            QMessageBox.information(self, self.tr("Attention"), self.tr("STL model generated"))
                        else:
                            QMessageBox.information(self, self.tr("Attention"), self.tr("Process canceled"))
            else:
                f, __ = QFileDialog.getSaveFileName(self, self.tr('Export to STL'), layer_name, filter=".stl")
                stl_file = f[0]
                if stl_file:
                    export_dlg = Export_dialog.Dialog(parameters, stl_file)
                    if export_dlg.exec_():
                        QMessageBox.information(self, self.tr("Attention"), self.tr("STL model generated"))
                    else:
                        QMessageBox.information(self, self.tr("Attention"), self.tr("Process canceled"))
        else:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Fill the data correctly"))

    def get_layer(self, layer_name):
        if self.layer.name() != layer_name:
            self.ini_dialog()
        layermap = QgsProject.instance().mapLayers()
        for name, layer in layermap.items():
            if layer.name() == layer_name:
                if layer.isValid():
                    self.layer = layer
                    self.get_raster_properties()
                else:
                    self.layer = None

    def ini_dialog(self):
        self.ui.XMaxLineEdit.clear()
        self.ui.XMinLineEdit.clear()
        self.ui.YMaxLineEdit.clear()
        self.ui.YMinLineEdit.clear()
        if self.extent:
            self.canvas.scene().removeItem(self.extent)
            self.extent = None
        self.ini_dimensions()

        self.ui.ZMaxLabel.setText('0 m')
        self.ui.ZMinLabel.setText('0 m')

    def ini_dimensions(self):
        self.ui.HeightLineEdit.clear()
        self.height = 0
        self.ui.WidthLineEdit.clear()
        self.width = 0
        self.ui.ScaleLineEdit.clear()
        self.scale = 0
        self.ui.RecomSpacinglabel.setText('0.2 mm')

        self.ui.BaseHeightLineEdit.clear()
        self.ui.HeightModelLabel.setText('0 mm')

    def get_raster_properties(self):
        self.cell_size = self.layer.rasterUnitsPerPixelX()
        self.rows = self.layer.height()
        self.cols = self.layer.width()
        rec = self.layer.extent()
        self.raster_x_max = rec.xMaximum()
        self.raster_x_min = rec.xMinimum()
        self.raster_y_max = rec.yMaximum()
        self.raster_y_min = rec.yMinimum()

    # region Extension functions
    def full_extent(self):
        rec = self.canvas.fullExtent()
        self.paint_extent(rec)
        self.get_z_max_z_min()
        self.ini_dimensions()

    def layer_extent(self):
        layers = self.iface.legendInterface().layers()
        select_layer_dialog = SelectLayer_dialog.Dialog(layers)
        if select_layer_dialog.exec_():
            layer = select_layer_dialog.get_layer()
            if layer:
                rec = get_layer(layer).extent()
                source = self.layer.crs()
                target = self.map_crs
                if source != target:
                    transform = QgsCoordinateTransform(source, target)
                    rec = transform.transform(rec)
                self.paint_extent(rec)
                self.get_z_max_z_min()
                self.ini_dimensions()

    def custom_extent(self):
        self.iface.messageBar().pushMessage("Info", self.tr("Click and drag the mouse to draw print extent"),
                                            level=QgsMessageBar.INFO, duration=3)
        if self.extent:
            self.canvas.scene().removeItem(self.extent)
            self.extent = None
        ct = RectangleMapTool(self.canvas, self.get_custom_extent)
        self.canvas.setMapTool(ct)

    def get_custom_extent(self, rec):
        layer_extension = self.layer.extent()
        source = self.layer.crs()
        target = self.map_crs
        if source != target:
            transform = QgsCoordinateTransform(source, target)
            layer_extension = transform.transform(layer_extension)
        if rec.intersects(layer_extension):
            extension = rec.intersect(layer_extension)
            self.paint_extent(extension)
            self.iface.actionPan().trigger()
            self.get_z_max_z_min()
            self.ini_dimensions()
        else:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Print extent defined outside layer extent"))

    def upload_extent(self):
        try:
            self.roi_x_max = float(self.ui.XMaxLineEdit.text())
            self.roi_x_min = float(self.ui.XMinLineEdit.text())
            self.roi_y_max = float(self.ui.YMaxLineEdit.text())
            self.roi_y_min = float(self.ui.YMinLineEdit.text())
            rec = QgsRectangle(self.roi_x_min, self.roi_y_min, self.roi_x_max, self.roi_y_max)
            self.paint_extent(rec)
            self.get_z_max_z_min()
            self.ini_dimensions()
        except ValueError:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Value entered incorrect"))

    def paint_extent(self, rec):
        self.roi_x_max = rec.xMaximum()
        self.ui.XMaxLineEdit.setText(str(round(rec.xMaximum(), 3)))
        self.roi_y_min = rec.yMinimum()
        self.ui.YMinLineEdit.setText(str(round(rec.yMinimum(), 3)))
        self.roi_x_min = rec.xMinimum()
        self.ui.XMinLineEdit.setText(str(round(rec.xMinimum(), 3)))
        self.roi_y_max = rec.yMaximum()
        self.ui.YMaxLineEdit.setText(str(round(rec.yMaximum(), 3)))

        if self.extent:
            self.canvas.scene().removeItem(self.extent)
            self.extent = None
        self.extent = QgsRubberBand(self.canvas, True)
        points = [QgsPointXY(self.roi_x_max, self.roi_y_min), QgsPointXY(self.roi_x_max, self.roi_y_max),
                  QgsPointXY(self.roi_x_min, self.roi_y_max), QgsPointXY(self.roi_x_min, self.roi_y_min),
                  QgsPointXY(self.roi_x_max, self.roi_y_min)]
        self.extent.setToGeometry(QgsGeometry.fromPolyline(points), None)
        self.extent.setColor(QColor(227, 26, 28, 255))
        self.extent.setWidth(5)
        self.extent.setLineStyle(Qt.PenStyle(Qt.DashLine))
        self.canvas.refresh()

    def get_z_max_z_min(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        roi = QgsRectangle(self.roi_x_min, self.roi_y_min, self.roi_x_max, self.roi_y_max)
        source = self.map_crs
        target = self.layer.crs()
        transform = QgsCoordinateTransform(source, target)
        rec = transform.transform(roi)

        x_max = rec.xMaximum()
        x_min = rec.xMinimum()
        y_max = rec.yMaximum()
        y_min = rec.yMinimum()

        x_off = int(math.floor((x_min - self.raster_x_min) * self.cols / (self.raster_x_max - self.raster_x_min)))
        y_off = int(math.floor((self.raster_y_max - y_max) * self.rows / (self.raster_y_max - self.raster_y_min)))
        col_size = int(math.floor((x_max - x_min) / self.cell_size))
        row_size = int(math.floor((y_max - y_min) / self.cell_size))

        if x_off < 0:
            x_off = 0
        if y_off < 0:
            y_off = 0
        if x_off >= self.cols:
            x_off = self.cols - 1
        if y_off >= self.rows:
            y_off = self.rows - 1

        if x_off + col_size > self.cols:
            col_size = self.cols - x_off
        if row_size + row_size > self.rows:
            row_size = self.rows - y_off

        provider = self.layer.dataProvider()
        path = provider.dataSourceUri()
        path_layer = path.split('|')

        dem_dataset = gdal.Open(path_layer[0])
        data = self.get_dem_z(dem_dataset, x_off, y_off, col_size, row_size)
        if data is not None:
            self.z_max = max(data)
            self.z_min = self.z_max
            no_data = dem_dataset.GetRasterBand(1).GetNoDataValue()

            if min(data) == no_data:
                for z_cell in data:
                    if z_cell != no_data and z_cell < self.z_min:
                        self.z_min = z_cell
            elif math.isnan(min(data)):
                self.z_max = 0
                self.z_min = 0
                for z_cell in data:
                    if not math.isnan(z_cell):
                        if self.z_min > z_cell:
                            self.z_min = z_cell
                        if self.z_max < z_cell:
                            self.z_max = z_cell
            else:
                self.z_min = min(data)

            if self.z_min < 0:
                self.z_min = 0

            self.z_max = round(self.z_max, 3)
            self.z_min = round(self.z_min, 3)
            self.ui.ZMaxLabel.setText(str(self.z_max) + ' m')
            self.ui.ZMinLabel.setText(str(self.z_min) + ' m')
        dem_dataset = None
        band = None
        QApplication.restoreOverrideCursor()
    # endregion

    # region Dimensions function
    def get_min_spacing(self):
        min_spacing = 0
        if self.map_crs.mapUnits() == 0:  # Meters
            if self.layer.crs().mapUnits() == 0:
                width_roi = self.roi_x_max - self.roi_x_min
                min_spacing = round(self.cell_size * self.width / width_roi, 2)
            elif self.layer.crs().mapUnits() == 2:
                width_roi = self.roi_x_max - self.roi_x_min
                cell_size_m = self.cell_size * math.pi / 180 * math.cos(self.roi_y_max * math.pi / 180) * 6371000
                min_spacing = round(cell_size_m * self.width / width_roi, 2)
            # min_spacing = self.cell_size/self.scale
        elif self.map_crs.mapUnits() == 2:  # Degree
            if self.layer.crs().mapUnits() == 0:
                width_roi = self.roi_x_max - self.roi_x_min
                cell_size_deg = self.cell_size / math.pi * 180 / math.cos(self.roi_y_max * math.pi / 180) / 6371000
                min_spacing = round(cell_size_deg * self.width / width_roi, 2)
            elif self.layer.crs().mapUnits() == 2:
                width_roi = self.roi_x_max - self.roi_x_min
                min_spacing = round(self.cell_size * self.width / width_roi, 2)

        if min_spacing < 0.2:
            self.ui.RecomSpacinglabel.setText('0.2 mm')
        else:
            self.ui.RecomSpacinglabel.setText(str(min_spacing) + ' mm')

    def upload_size_from_height(self):
        try:
            width_roi = self.roi_x_max - self.roi_x_min
            height_roi = self.roi_y_max - self.roi_y_min
            self.height = float(self.ui.HeightLineEdit.text())
            self.width = round(width_roi * self.height / height_roi, 2)
            self.ui.WidthLineEdit.setText(str(self.width))
            if self.map_crs.mapUnits() == 0:  # Meters
                scale1 = height_roi / self.height * 1000
                scale2 = width_roi / self.width * 1000
                self.scale = round((scale1 + scale2) / 2, 6)
                self.ui.ScaleLineEdit.setText(str(int(self.scale)))
            elif self.map_crs.mapUnits() == 2:  # Degree
                dist = width_roi * math.pi / 180 * math.cos(self.roi_y_max * math.pi / 180) * 6371000 * 1000
                self.scale = round(dist / self.width, 6)
                self.ui.ScaleLineEdit.setText(str(int(self.scale)))
            self.get_min_spacing()
            self.get_height_model()
        except ZeroDivisionError:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Define print extent"))
            self.ui.HeightLineEdit.clear()

    def upload_size_from_width(self):
        try:
            width_roi = self.roi_x_max - self.roi_x_min
            height_roi = self.roi_y_max - self.roi_y_min
            self.width = float(self.ui.WidthLineEdit.text())
            self.height = round(height_roi * self.width / width_roi, 2)
            self.ui.HeightLineEdit.setText(str(self.height))
            if self.map_crs.mapUnits() == 0:  # Meters
                scale1 = height_roi / self.height * 1000
                scale2 = width_roi / self.width * 1000
                self.scale = round((scale1 + scale2) / 2, 6)
                self.ui.ScaleLineEdit.setText(str(int(self.scale)))
            elif self.map_crs.mapUnits() == 2:  # Degree
                dist = width_roi * math.pi / 180 * math.cos(self.roi_y_max * math.pi / 180) * 6371000 * 1000
                self.scale = round(dist / self.width, 6)
                self.ui.ScaleLineEdit.setText(str(int(self.scale)))
            self.get_min_spacing()
            self.get_height_model()
        except ZeroDivisionError:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Define size model"))
            self.ui.WidthLineEdit.clear()

    def upload_size_from_scale(self):
        try:
            width_roi = self.roi_x_max - self.roi_x_min
            height_roi = self.roi_y_max - self.roi_y_min
            self.scale = float(self.ui.ScaleLineEdit.text())
            if self.map_crs.mapUnits() == 0:  # Meters
                self.height = round(height_roi / self.scale * 1000, 2)
                self.ui.HeightLineEdit.setText(str(self.height))
                self.width = round(width_roi / self.scale * 1000, 2)
                self.ui.WidthLineEdit.setText(str(self.width))
            elif self.map_crs.mapUnits() == 2:  # Degree
                dist = width_roi * math.pi / 180 * math.cos(self.roi_y_max * math.pi / 180) * 6371000 * 1000
                self.width = round(dist / self.scale, 2)
                self.ui.WidthLineEdit.setText(str(self.width))
                self.height = round(height_roi * self.width / width_roi, 2)
                self.ui.HeightLineEdit.setText(str(self.height))
            self.get_min_spacing()
            self.get_height_model()
        except ZeroDivisionError:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Define print extent"))
            self.ui.ScaleLineEdit.clear()
            self.scale = 0
            self.ui.WidthLineEdit.clear()

    # endregion

    def get_height_model(self):
        if self.ui.BaseHeightLineEdit.text() == '':
            return
        try:
            z_base = float(self.ui.BaseHeightLineEdit.text())
            self.z_scale = self.ui.ZScaleDoubleSpinBox.value()
            h_model = round((self.z_max - z_base) / self.scale * 1000 * self.z_scale + 2, 1)
            if h_model == float("inf"):
                QMessageBox.warning(self, self.tr("Attention"), self.tr("Define size model"))
                self.ui.BaseHeightLineEdit.clear()
                return
            if z_base <= self.z_max:
                self.ui.HeightModelLabel.setText(str(h_model) + ' mm')
            else:
                QMessageBox.warning(self, self.tr("Attention"),
                                    self.tr("Height of the base must be lower than DEM highest point"))
                self.ui.BaseHeightLineEdit.clear()
        except ZeroDivisionError:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Define print extent"))
            self.ui.BaseHeightLineEdit.clear()

    def get_parameters(self):
        if self.map_crs.mapUnits() == 0:  # Meters
            projected = True
        elif self.map_crs.mapUnits() == 2:  # Degree
            projected = False
        provider = self.layer.dataProvider()
        path = provider.dataSourceUri()
        path_layer = path.split('|')
        self.z_scale = self.ui.ZScaleDoubleSpinBox.value()
        try:
            spacing_mm = float(self.ui.SpacingLineEdit.text())
            z_base = float(self.ui.BaseHeightLineEdit.text())
        except ValueError:
            return 0
        if self.ui.RevereseZCheckBox.isChecked():
            z_inv = True
        else:
            z_inv = False
        return {"layer": path_layer[0], "roi_x_max": self.roi_x_max, "roi_x_min": self.roi_x_min,
                "roi_y_max": self.roi_y_max, "roi_y_min": self.roi_y_min, "spacing_mm": spacing_mm,
                "height": self.height, "width": self.width, "z_scale": self.z_scale, "scale": self.scale,
                "z_inv": z_inv, "z_base": z_base, "projected": projected, "crs_layer": self.layer.crs(),
                "crs_map": self.map_crs}

    @staticmethod
    def get_dem_z(dem_dataset, x_off, y_off, col_size, row_size):
        band = dem_dataset.GetRasterBand(1)
        data_types = {'Byte': 'B', 'UInt16': 'H', 'Int16': 'h', 'UInt32': 'I', 'Int32': 'i', 'Float32': 'f',
                      'Float64': 'd'}
        data_type = band.DataType
        data = band.ReadRaster(x_off, y_off, col_size, row_size, col_size, row_size, data_type)
        data = struct.unpack(data_types[gdal.GetDataTypeName(band.DataType)] * col_size * row_size, data)
        return data


class RectangleMapTool(QgsMapTool):
    def __init__(self, canvas, callback):
        self.canvas = canvas
        QgsMapTool.__init__(self, self.canvas)
        self.callback = callback
        self.rubberBand = QgsRubberBand(self.canvas, True)
        self.rubberBand.setColor(QColor(227, 26, 28, 255))
        self.rubberBand.setWidth(5)
        self.rubberBand.setLineStyle(Qt.PenStyle(Qt.DashLine))
        self.reset()

    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset(True)

    def canvasPressEvent(self, e):
        self.startPoint = self.toMapCoordinates(e.pos())
        self.endPoint = self.startPoint
        self.isEmittingPoint = True
        self.showRect(self.startPoint, self.endPoint)

    def canvasReleaseEvent(self, e):
        self.isEmittingPoint = False
        r = self.rectangle()
        if r is not None:
            # print "Rectangle:", r.xMinimum(), r.yMinimum(), r.xMaximum(), r.yMaximum()
            self.rubberBand.hide()
            self.callback(r)
            # self.deactivate()
        return None

    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.showRect(self.startPoint, self.endPoint)

    def showRect(self, startPoint, endPoint):
        self.rubberBand.reset(True)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return

        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())

        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, False)
        self.rubberBand.addPoint(point1, True)  # true to update canvas
        self.rubberBand.show()

    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            return None
        return QgsRectangle(self.startPoint, self.endPoint)

    def deactivate(self):
        super(RectangleMapTool, self).deactivate()
        self.emit(QtCore.SIGNAL("deactivated()"))