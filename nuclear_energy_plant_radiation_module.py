from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction
import csv
import random
from .mqttSubscriber import mqttSubscriber
from .mqttPublisher import mqttPublisher
from qgis._core import QgsPointXY, QgsFeature, QgsGeometry, QgsProject, Qgis, QgsApplication, QgsHeatmapRenderer, \
    QgsStyle
from .nuclear_energy_plant_radiation_module_dialog import energy_plant_radiation_classDialog
import os.path
import threading
from shutil import copyfile
from gi.repository import GObject
import urllib.request
import time
from qgis.PyQt.QtWidgets import QProgressBar
from qgis.PyQt.QtCore import *
NUMB_ENERGY_PLANT = 199

class energy_plant_radiation_class:
    publisher = mqttPublisher()
    subscriber = mqttSubscriber()
    upddateRadiation = None
    radiationRate = 1
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'energy_plant_radiation_class_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&energy_plant_radiation')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

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
        return QCoreApplication.translate('energy_plant_radiation_class', message)

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
        dirname = os.path.dirname(__file__)
        icon_path = os.path.join(dirname, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Nuclear Energy Plants\' Radiations'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&energy_plant_radiation'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        self.loadProject()
        self.init_state()
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = energy_plant_radiation_classDialog()
            self.dlg.start_radiation.clicked.connect(self.run_pub_sub)
            self.dlg.sb.valueChanged.connect(self.setTimeRate)

        def updteRadiation():
            energy_plant_radiation_class.upddateRadiation = threading.Timer(energy_plant_radiation_class.radiationRate,
                                                                            schedule_update)
            if not energy_plant_radiation_class.subscriber.isEmpty():

                #Retrieve heatmap
                layer = QgsProject.instance().mapLayersByName('radiation_heatmap copy_energy_plant')[0]
                radiations= energy_plant_radiation_class.subscriber.getRadiationList()
                layer.startEditing()
                index=0
                it = layer.getFeatures()
                for feat in it:
                    layer.changeAttributeValue(feat.id(), 5, radiations[index])
                    index= index + 1
                layer.commitChanges()
            energy_plant_radiation_class.upddateRadiation.start()

        def schedule_update():
            GObject.idle_add(updteRadiation)

        updteRadiation()


        layer = QgsProject.instance().mapLayersByName('radiation_heatmap copy_energy_plant')[0]
        layer.reload()
        self.progressBar()
        #set windows dialog to bottom center
        self.dlg.setGeometry(850,850,376,163)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if Close was pressed
        if result == 0:
            energy_plant_radiation_class.upddateRadiation.cancel()
            self.stopTask()
            self.unloadProject()
            self.iface.messageBar().clearWidgets()
            print("End Nuclear Energy Plant Plugin")
            pass

    # read from dataset and finally fill attribute table
    def init_state(self):
        dirname = os.path.dirname(__file__)
        layer = QgsProject.instance().mapLayersByName('copy_energy_plant')[0]
        if layer.featureCount() < NUMB_ENERGY_PLANT:
            filename = os.path.join(dirname, 'dataset/global_power_plant_database.csv')
            layer.startEditing()
            with open(filename, 'r') as file:
                reader = csv.reader(file)
                for i, row in enumerate(reader):
                    if i > 0 and row[7] == "Nuclear":
                        pr = layer.dataProvider()
                        # insert in attribute table
                        poly = QgsFeature(layer.fields())
                        poly.setAttribute("Country", row[0])
                        poly.setAttribute("count_long", row[1])
                        poly.setAttribute("name", row[2])
                        poly.setAttribute("qppd_idnr", row[3])
                        poly.setAttribute("cap_mw", row[4])
                        poly.setAttribute("latitude", row[5])
                        poly.setAttribute("longitude", row[6])
                        poly.setAttribute("Radiation", random.randint(1, 200))
                        poly.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(row[6]), float(row[5]))))
                        pr.addFeatures([poly])
                layer.updateExtents()
                layer.commitChanges()
                layer.reload()
        #widget = self.iface.messageBar().createMessage("Insertion Energy Plants", "Done")
        #self.iface.messageBar().pushWidget(widget, Qgis.Success)

    # run thread subscriber and publisher
    def run_pub_sub(self):
        if energy_plant_radiation_class.checkConnection(self):
            # create task for pub and Pub
            if QgsApplication.taskManager().countActiveTasks() < 2:
                QgsApplication.taskManager().addTask(energy_plant_radiation_class.publisher)
                QgsApplication.taskManager().addTask(energy_plant_radiation_class.subscriber)
                print("Pub and Sub started")
                energy_plant_radiation_class.popupMessage(self,"Radiation Stream:","Is started","success")
            else:
                print("already running")
                energy_plant_radiation_class.popupMessage(self,"Radiation Stream:","Already running","warning")

        else:
            print("Your device must be connected to a network")
    # stop thread subscriber and publisher
    def stopTask(self):
        if QgsApplication.taskManager().countActiveTasks() > 1:
            energy_plant_radiation_class.publisher.stopPub(0)
            energy_plant_radiation_class.subscriber.stopSub(1)
            energy_plant_radiation_class.subscriber.flushRadiationList()
            energy_plant_radiation_class.publisher = mqttPublisher()
            energy_plant_radiation_class.subscriber = mqttSubscriber()
            print("Radiation stream stopped")
            energy_plant_radiation_class.popupMessage(self, "Radiation Stream:", "Is stopped", "success")

        else:
            print("Radiation streaming not running")
            energy_plant_radiation_class.popupMessage(self, "Radiation Stream:", "Is already stopped", "warning")

    def setTimeRate(self, newTime):
        print(newTime)
        energy_plant_radiation_class.radiationRate = newTime
        energy_plant_radiation_class.publisher.setTimeRatePub(newTime)
        energy_plant_radiation_class.popupMessage(self, "New time rate:", str(newTime), "info")

    def loadProject(self):
        # Get the project instance
        project = QgsProject.instance()
        # Load another project
        dirname = os.path.dirname(__file__)

        #copy all qgis_project folder file in temp_file for not modify it
        copyfile(os.path.join(dirname, 'qgis_project/Map.qgs'), os.path.join(dirname, 'qgis_project/temp_file/TempMap.qgs'))
        copyfile(os.path.join(dirname, 'qgis_project/Energy_Plant.shp'), os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.shp'))
        copyfile(os.path.join(dirname, 'qgis_project/Energy_Plant.dbf'), os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.dbf'))
        copyfile(os.path.join(dirname, 'qgis_project/Energy_Plant.prj'), os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.prj'))
        copyfile(os.path.join(dirname, 'qgis_project/Energy_Plant.qpj'), os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.qpj'))
        copyfile(os.path.join(dirname, 'qgis_project/Energy_Plant.shx'), os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.shx'))

        copy_map = os.path.join(dirname, 'qgis_project/temp_file/TempMap.qgs')
        copy_energy_plant = os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.shp')
        project.read(copy_map)

        heatmap_layer_path = os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.shp')

        self.iface.addVectorLayer(heatmap_layer_path, "radiation_heatmap", "ogr")
        self.iface.addVectorLayer(copy_energy_plant, "", "ogr")

        layer = QgsProject.instance().mapLayersByName('radiation_heatmap copy_energy_plant')[0]
        layer.setOpacity(0.5)

        renderer = QgsHeatmapRenderer()
        renderer.setRenderQuality(1)
        renderer.setRadius(20)
        renderer.setWeightExpression("Radiation")

        style = QgsStyle.defaultStyle()
        defaultColorRampNames = style.colorRampNames()

        ramp = style.colorRamp(defaultColorRampNames[8])
        ramp.setColor1(QColor(0,0,4,0))
        renderer.setColorRamp(ramp)
        layer.setRenderer(renderer)

    def progressBar(self):
        progressMessageBar = self.iface.messageBar().createMessage("Project setup...")
        progress = QProgressBar()
        progress.setMaximum(5)
        progress.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        self.iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)

        for i in range(5):
            time.sleep(1)
            progress.setValue(i + 1)

        self.iface.messageBar().clearWidgets()
        energy_plant_radiation_class.popupMessage(self, "Project setup:", "Completed with success", "success")
        print("Project Loaded")
    def unloadProject(self):
        QgsProject.instance().removeAllMapLayers()
        try:
            dirname = os.path.dirname(__file__)
            os.remove(os.path.join(dirname, 'qgis_project/temp_file/TempMap.qgs'))
            os.remove(os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.shp'))
            os.remove(os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.dbf'))
            os.remove(os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.prj'))
            os.remove(os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.qpj'))
            os.remove(os.path.join(dirname, 'qgis_project/temp_file/copy_energy_plant.shx'))
            os.remove(os.path.join(dirname, 'qgis_project/temp_file/TempMap.qgs~'))
        except OSError:
            pass

        self.iface.mapCanvas().refreshAllLayers()

    def checkConnection(self):
        try:
            urllib.request.urlopen("http://google.com")
            print("Network connection is running")
            energy_plant_radiation_class.popupMessage(self, "Network connection:", "Is Running", "success")

            return True
        except urllib.error.URLError as err:
            print("Network connection is not running")
            energy_plant_radiation_class.popupMessage(self, "Network connection:", "Is not Running", "critical")

            return False

    def popupMessage(self,title, body, level):
        if level == "info":
            self.iface.messageBar().pushMessage(title, body, level=Qgis.Info,
                                       duration=3)
        elif level == "warning":
            self.iface.messageBar().pushMessage(title, body, level=Qgis.Warning,
                                                duration=3)
        elif level == "critical":
            self.iface.messageBar().pushMessage(title, body, level=Qgis.Critical,
                                                duration=3)
        elif level == "success":
            self.iface.messageBar().pushMessage(title, body, level=Qgis.Success,
                                                duration=3)
