# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'DEMto3D_Dialog/demto3d_dialog_base.ui'
#
# Created: Mon Jun 26 20:30:07 2017
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_demto3dDialogBase(object):
    def setupUi(self, demto3dDialogBase):
        demto3dDialogBase.setObjectName(_fromUtf8("demto3dDialogBase"))
        demto3dDialogBase.resize(400, 300)
        self.button_box = QtGui.QDialogButtonBox(demto3dDialogBase)
        self.button_box.setGeometry(QtCore.QRect(30, 240, 341, 32))
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.button_box.setObjectName(_fromUtf8("button_box"))
        self.pushButton = QtGui.QPushButton(demto3dDialogBase)
        self.pushButton.setGeometry(QtCore.QRect(60, 110, 75, 23))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))

        self.retranslateUi(demto3dDialogBase)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("accepted()")), demto3dDialogBase.accept)
        QtCore.QObject.connect(self.button_box, QtCore.SIGNAL(_fromUtf8("rejected()")), demto3dDialogBase.reject)
        QtCore.QMetaObject.connectSlotsByName(demto3dDialogBase)

    def retranslateUi(self, demto3dDialogBase):
        demto3dDialogBase.setWindowTitle(_translate("demto3dDialogBase", "DEMto3D", None))
        self.pushButton.setText(_translate("demto3dDialogBase", "prueba", None))

