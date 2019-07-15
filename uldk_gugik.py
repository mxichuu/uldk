# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UldkGugik
                                 A QGIS plugin
 Wtyczka pozwala na pobieranie geometrii granic działek katastralnych, obrębów, gmin, powiatów i województw.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-05-31
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Michał Włoga & Alicja Konkol - Envirosolutions Sp. z o.o.
        email                : office@envirosolutions.pl
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
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QAction
from qgis.gui import QgsMessageBar, QgsMapToolEmitPoint
from qgis.core import Qgis, QgsVectorLayer, QgsGeometry, QgsFeature, QgsProject, QgsField, \
    QgsCoordinateReferenceSystem, QgsPoint, QgsCoordinateTransform, QgsMessageLog
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .uldk_gugik_dialog import UldkGugikDialog
import os.path
from . import utils, uldk_api, uldk_xy

"""Wersja wtyczki"""
plugin_version = '0.2 White Oak'
plugin_name = 'ULDK GUGiK'

class UldkGugik:
    """QGIS Plugin Implementation."""
    nazwy_warstw = {1:"dzialki_ew_uldk", 2:"obreby_ew_uldk", 3:"gminy_uldk", 4:"powiaty_uldk", 5:"wojewodztwa_uldk"}

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        #DialogOnTop

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'UldkGugik_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Usługa Lokalizacji Działek Katastralnych')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        self.canvas = self.iface.mapCanvas()
        # out click tool will emit a QgsPoint on every click
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.clickTool.canvasClicked.connect(self.clicked)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('UldkGugik', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/uldk_gugik/images/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'ULDK'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True
        self.dlg = UldkGugikDialog()

        # Inicjacja grafik
        self.dlg.img_main.setPixmap(QPixmap(':/plugins/uldk_gugik/images/icon_uldk2.png'))
        self.dlg.img_tab2.setPixmap(QPixmap(':/plugins/uldk_gugik/images/coords.png'))

        # rozmiar okna
        self.dlg.setFixedSize(self.dlg.size())

        # informacje o wersji
        self.dlg.setWindowTitle('%s %s' % (plugin_name, plugin_version))
        self.dlg.lbl_pluginVersion.setText('%s %s' % (plugin_name, plugin_version))

        #eventy
        self.dlg.btn_download_tab1.clicked.connect(self.btn_download_tab1_clicked)
        self.dlg.btn_download_tab2.clicked.connect(self.btn_download_tab2_clicked)
        self.dlg.btn_download_tab3.clicked.connect(self.btn_download_tab3_clicked)
        self.dlg.btn_frommap.clicked.connect(self.btn_frommap_clicked)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Usługa Lokalizacji Działek Katastralnych'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""

        # show the dialog
        self.dlg.show()
        self.dlg.projectionWidget.setCrs(QgsCoordinateReferenceSystem(2180, QgsCoordinateReferenceSystem.EpsgCrsId))

    def btn_download_tab1_clicked(self):
        self.objectType = self.checkedFeatureType()

        objid = self.dlg.edit_id.text().strip()

        if not objid:
            self.iface.messageBar().pushMessage("Błąd formularza:",
                                                'musisz wpisać identyfikator',
                                                level=Qgis.Warning, duration=10)
        elif utils.isInternetConnected():
            self.performRequest(pid=objid)
            self.dlg.hide()

        else:
            self.iface.messageBar().pushMessage("Nie udało się pobrać obiektu:",
                                                'brak połączenia z internetem',
                                                level=Qgis.Critical, duration=10)

    def btn_download_tab2_clicked(self):

        self.canvas.unsetMapTool(self.clickTool)
        self.objectType = self.checkedFeatureType()

        objX = self.dlg.doubleSpinBoxX.text().strip()
        objY = self.dlg.doubleSpinBoxY.text().strip()
        crs = self.dlg.projectionWidget.crs().authid().split(":")[1]

        if not objX:
            self.iface.messageBar().pushMessage("Błąd formularza:",
                                                'musisz wpisać współrzędną X',
                                                level=Qgis.Warning, duration=10)

        if not objY:
            self.iface.messageBar().pushMessage("Błąd formularza:",
                                                'musisz wpisać współrzędną Y',
                                                level=Qgis.Warning, duration=10)

        elif utils.isInternetConnected():
            self.performRequestXY(x=objX, y=objY, coord=crs)
            self.dlg.hide()

        else:
            self.iface.messageBar().pushMessage("Nie udało się pobrać obiektu:",
                                                'brak połączenia z internetem',
                                                level=Qgis.Critical, duration=10)

    def btn_frommap_clicked(self):

        self.canvas.setMapTool(self.clickTool)
        self.dlg.hide()

    def clicked(self, point):

        coords = "{}, {}".format(point.x(), point.y())

        self.dlg.doubleSpinBoxX.setValue(point.x())
        self.dlg.doubleSpinBoxY.setValue(point.y())

        QgsMessageLog.logMessage(str(coords), 'ULDK')
        self.dlg.show()

    def btn_download_tab3_clicked(self):
        pass

    def performRequest(self, pid):

        # layer
        nazwa = self.nazwy_warstw[self.objectType]

        if self.objectType == 1:
            wkt = uldk_api.getParcelById(pid)
        elif self.objectType == 2:
            wkt = uldk_api.getRegionById(pid)
        elif self.objectType == 3:
            wkt = uldk_api.getCommuneById(pid)
        elif self.objectType == 4:
            wkt = uldk_api.getCountyById(pid)
        elif self.objectType == 5:
            wkt = uldk_api.getVoivodeshipById(pid)

        if wkt is None:
            self.iface.messageBar().pushMessage("Nie udało się pobrać obiektu:",
                                                'API nie zwróciło obiektu dla id %s' % pid,
                                                level=Qgis.Critical, duration=10)
        else:
            layers = QgsProject.instance().mapLayersByName(nazwa)
            if layers:
                # jezeli istnieje to dodaj obiekt do warstwy
                layer = layers[0]
            else:
                # jezeli nie istnieje to stworz warstwe
                layer = QgsVectorLayer("Polygon?crs=EPSG:2180", nazwa, "memory")
                QgsProject.instance().addMapLayer(layer)

            provider = layer.dataProvider()
            geom = QgsGeometry().fromWkt(wkt)
            feat = QgsFeature()
            feat.setGeometry(geom)

            box = feat.geometry().boundingBox()
            provider.addFeature(feat)
            layer.updateExtents()

            canvas = self.iface.mapCanvas()
            canvas.setExtent(box)
            canvas.refresh()

            # add attributes
            if layers:
                counter = layer.featureCount()
                idx = layer.fields().indexFromName('identyfikator')
                attrMap = {counter: {idx: pid}}
                provider.changeAttributeValues(attrMap)

            else:
                identyfikatorField = QgsField('identyfikator', QVariant.String, len=30)
                provider.addAttributes([identyfikatorField])
                layer.updateFields()
                idx = layer.fields().indexFromName('identyfikator')
                attrMap = {1: {idx: pid}}
                provider.changeAttributeValues(attrMap)

            self.iface.messageBar().pushMessage("Sukces:",
                                                'pobrano obrys obiektu %s' % (pid),
                                                level=Qgis.Success, duration=10)

    def performRequestXY(self, x, y, coord):

        x = x.replace(",", ".")
        y = y.replace(",", ".")
        geom = QgsPoint(float(x), float(y))
        QgsMessageLog.logMessage(str(coord), 'ULDK')
        sourceCrs = QgsCoordinateReferenceSystem.fromEpsgId(int(coord))
        destCrs = QgsCoordinateReferenceSystem.fromEpsgId(2180)
        tr = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
        QgsMessageLog.logMessage(str(tr.destinationCrs), 'ULDK')
        QgsMessageLog.logMessage(str(tr.sourceCrs), 'ULDK')
        geom.transform(tr)

        QgsMessageLog.logMessage(str(geom.x()), 'ULDK')
        QgsMessageLog.logMessage(str(geom.y()), 'ULDK')

        xNew = geom.x()
        yNew = geom.y()

        pid = str(xNew) + "," + str(yNew)

        # layer
        nazwa = self.nazwy_warstw[self.objectType]

        if self.objectType == 1:
            wkt = uldk_xy.getParcelByXY(pid)
        elif self.objectType == 2:
            wkt = uldk_xy.getRegionByXY(pid)
        elif self.objectType == 3:
            wkt = uldk_xy.getCommuneByXY(pid)
        elif self.objectType == 4:
            wkt = uldk_xy.getCountyByXY(pid)
        elif self.objectType == 5:
            wkt = uldk_xy.getVoivodeshipByXY(pid)

        if wkt is None:
            self.iface.messageBar().pushMessage("Nie udało się pobrać obiektu:",
                                                'API nie zwróciło obiektu dla współrzędnych %s' % pid,
                                                level=Qgis.Critical, duration=10)
        else:
            pid = wkt[1]
            wkt = wkt[0]
            layers = QgsProject.instance().mapLayersByName(nazwa)
            if layers:
                # jezeli istnieje to dodaj obiekt do warstwy
                layer = layers[0]
            else:
                # jezeli nie istnieje to stworz warstwe
                layer = QgsVectorLayer("Polygon?crs=EPSG:2180", nazwa, "memory")
                QgsProject.instance().addMapLayer(layer)

            provider = layer.dataProvider()
            geom = QgsGeometry().fromWkt(wkt)
            feat = QgsFeature()
            feat.setGeometry(geom)
            box = feat.geometry().boundingBox()

            provider.addFeature(feat)
            layer.updateExtents()

            canvas = self.iface.mapCanvas()
            canvas.setExtent(box)
            canvas.refresh()

            # add attributes
            if layers:
                counter = layer.featureCount()
                idx = layer.fields().indexFromName('identyfikator')
                attrMap = {counter: {idx: pid}}
                provider.changeAttributeValues(attrMap)

            else:
                identyfikatorField = QgsField('identyfikator', QVariant.String, len=30)
                provider.addAttributes([identyfikatorField])
                layer.updateFields()
                idx = layer.fields().indexFromName('identyfikator')
                attrMap = {1: {idx: pid}}
                provider.changeAttributeValues(attrMap)

            self.iface.messageBar().pushMessage("Sukces:",
                                                'pobrano obrys obiektu %s' % (pid),
                                                level=Qgis.Success, duration=10)

    def checkedFeatureType(self):
        dlg = self.dlg
        if dlg.rdb_dz.isChecked():
            return 1
        elif dlg.rdb_ob.isChecked():
            return 2
        elif dlg.rdb_gm.isChecked():
            return 3
        elif dlg.rdb_pw.isChecked():
            return 4
        elif dlg.rdb_wo.isChecked():
            return 5
        else:
            return 0
