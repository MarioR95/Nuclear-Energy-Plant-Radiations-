# -*- coding: utf-8 -*-
"""
/***************************************************************************
 energy_plant_radiation_class
                                 A QGIS plugin
 This plugin is built for GIS exam in order to the dynamically change of the produced radiation in real time by energy plants. The new radiation values came from sensors. The plugin using mqtt protocol to receive the new radiation values 
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-12-17
        copyright            : (C) 2019 by Marino Domenico, Ruggiero Mario
        email                : domenicomarino42@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load energy_plant_radiation_class class from file energy_plant_radiation_class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .nuclear_energy_plant_radiation_module import energy_plant_radiation_class
    return energy_plant_radiation_class(iface)
