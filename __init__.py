# -*- coding: utf-8 -*-
"""
/***************************************************************************
 demto3d
                                 A QGIS plugin
 3D Printing of terrain models.
                             -------------------
        begin                : 2017-06-23
        copyright            : (C) 2017 by Francisco Javier Venceslá Simón
        email                : info@demto3d.com
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
    """Load demto3d class from file demto3d.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .demto3d import demto3d
    return demto3d(iface)
