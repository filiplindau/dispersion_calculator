"""
Created on 03 Apr 2017

@author: Filip Lindau
"""

from dispersion_calc import DispersionCalculator
from PyQt5 import QtGui, QtCore, QtWidgets
import pyqtgraph as pq
import numpy as np
import sys
import logging
root = logging.getLogger()

while len(root.handlers):
    root.removeHandler(root.handlers[0])

f = logging.Formatter("%(asctime)s - %(module)s.   %(funcName)s - %(levelname)s - %(message)s")
fh = logging.StreamHandler()
fh.setFormatter(f)
root.addHandler(fh)
root.setLevel(logging.CRITICAL)
# warnings.filterwarnings('ignore')


class MyTableModel(QtCore.QAbstractTableModel):
    def __init__(self, material_name=None, material_thickness=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        if material_name is not None:
            self.material_name_list = [material_name]
            self.material_thickness_list = [material_thickness]
        else:
            self.material_name_list = []
            self.material_thickness_list = []

    def rowCount(self, parent=None):
        return self.material_name_list.__len__()

    def columnCount(self, parent=None):
        return 2

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        s = QtCore.QVariant()
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    s = "Material"
                elif section == 1:
                    s = "Thickness \n/ mm"
        return s

    def addData(self, value):
        root.debug("Entering MyTableModel::addData")
        root.debug("Adding material {0}, thickness {1}".format(value[0], value[1]))
        self.material_name_list.append(value[0])
        self.material_thickness_list.append(value[1])
        self.beginResetModel()
        self.endResetModel()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        root.debug("Entering MyTableModel::setData")
        if role == QtCore.Qt.EditRole:
            if index.row() > self.material_name_list.__len__() + 1:
                self.material_name_list.append(value[0])
                self.material_thickness_list.append(value[1])
            else:
                if index.column() == 0:
                    self.material_name_list[index.row()] = str(value)
                else:
                    self.material_thickness_list[index.row()] = value
        root.debug("Entering MyTableModel::setData emitting dataChanged:")
        self.dataChanged.emit(index, index)
        root.debug("Entering MyTableModel::setData emitting dataChanged done")
        return True

    def removeRows(self, row, count, parent=None):
        root.debug("Entering MyTableModel::removeRows")
        self.beginRemoveRows(QtCore.QModelIndex(), row, row+count-1)
        start_ind = np.maximum(0, row)
        end_ind = np.minimum(row+count, self.material_name_list.__len__())
        del self.material_name_list[start_ind:end_ind]
        del self.material_thickness_list[start_ind:end_ind]
        self.endRemoveRows()
        return True

    def flags(self, index):
        if index.column() < 2:
            fl = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        else:
            fl = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        # fl = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        return fl

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        elif role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        else:
            if index.column() == 0:
                # return QtCore.QString(self.material_name_list[index.row()])
                return self.material_name_list[index.row()]
            elif index.column() == 1:
                return QtCore.QVariant(self.material_thickness_list[index.row()])
            else:
                return QtCore.QVariant()


class DispersionCalculatorGui(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.dc = DispersionCalculator()

        self.main_layout = None
        self.material_combobox = None
        self.material_lineedit = None
        self.material_thickness = None
        self.material_add_button = None
        self.material_tableview = None
        self.material_table_model = MyTableModel("fs", 1)
        self.tableview_selected_indexes = None
        self.material_completer_model = QtCore.QStringListModel()
        self.material_completer_model.setStringList(self.dc.materials.keys())
        self.material_plotwidget = None
        self.material_plot = None
        self.pulse_temporal_plotwidget = None
        self.pulse_temporal_plot = None
        self.pulse_spectral_plotwidget = None
        self.pulse_spectral_plot = None
        self.pulse_initial_duration = None
        self.pulse_initial_spectral_width = None
        self.pulse_initial_spectral_width = None
        self.pulse_time_window = None
        self.pulse_number_points = None
        self.pulse_central_wavelength = None
        self.pulse_result_duration = None
        self.pulse_result_expansion2 = None
        self.pulse_result_expansion3 = None
        self.pulse_result_expansion4 = None
        self.setup_layout()

        self.setup_pulse()
        self.propagate_material_list()

    def set_combobox_material(self, material_name=None):
        if material_name is None:
            mat_name = self.material_lineedit.text()
        else:
            mat_name = material_name
        ind = self.material_combobox.findText(mat_name)
        if ind >= 0:
            self.material_combobox.setCurrentIndex(ind)

    def set_material(self):
        l = self.dc.l_mat
        w = 2*np.pi*self.dc.c / l
        name = str(self.material_combobox.currentText())
        n = self.dc.materials[name](w)
        self.material_plot.setData(x=l, y=n)
        self.material_plot.update()
        self.material_plotwidget.setTitle(name)

    def add_material(self):
        root.debug("Entering add_material")
        self.material_table_model.addData([self.material_combobox.currentText(),
                                           self.material_thickness.value(),
                                           0.7])
        root.debug("Now propagating:")
        self.propagate_material_list()

    def propagate_material_list(self):
        root.debug("Entering propagate_material_list")
        t_fwhm = self.pulse_initial_duration.value() * 1e-15
        t_span = self.pulse_time_window.value() * 1e-12
        n_pulse = self.pulse_number_points.value()
        l_0 = self.pulse_central_wavelength.value() * 1e-9
        self.dc.N = n_pulse
        self.dc.generate_pulse(t_fwhm, l_0, t_span, n_pulse, duration_domain='temporal')
        root.debug("Pulse generated")
        self.dc.reset_propagation()
        for row in range(self.material_table_model.rowCount()):
            ind = self.material_table_model.index(row, 0, QtCore.QModelIndex())
            mat = str(self.material_table_model.data(ind, QtCore.Qt.DisplayRole))
            root.debug("Propagating {0}".format(mat))
            ind = self.material_table_model.index(row, 1, QtCore.QModelIndex())
            # thickness = self.material_table_model.data(ind, QtCore.Qt.DisplayRole).toReal()[0]
            thickness = np.double(self.material_table_model.data(ind, QtCore.Qt.DisplayRole).value())
            root.debug("Thickness {0}: {1}".format(mat, thickness))
            self.dc.propagate_material(mat, thickness*1e-3)
        root.debug("Propagation complete")
        # self.material_table_model.reset()
        x = self.dc.get_t()
        y = self.dc.get_temporal_intensity(True)
        self.pulse_temporal_plot.setData(x=x, y=y)
        x = 2*np.pi*self.dc.c/self.dc.get_w()
        y = self.dc.get_spectral_intensity(True)
        self.pulse_spectral_plotwidget.disableAutoRange()
        self.pulse_spectral_plot.setData(x=x, y=y)
        self.pulse_spectral_plotwidget.setXRange(200e-9, 1000e-9)

        x = self.dc.get_w()
        y = self.dc.get_spectral_phase(True)
        good_ind = np.isfinite(y)

        self.pulse_phase_plot.setData(x=x[good_ind], y=y[good_ind])

        t_fwhm = self.dc.get_pulse_duration("temporal") * 1e15
        self.pulse_result_duration.setText("{0:.2f}".format(t_fwhm))

        # Re-calculate pulse with larger bandwidth if necessary to avoid a bad phase expansion
        if self.pulse_initial_spectral_width.value() < 5:
            l_fwhm = 10e-9
            t_span = self.pulse_time_window.value() * 1e-12
            n_pulse = self.pulse_number_points.value()
            l_0 = self.pulse_central_wavelength.value() * 1e-9
            self.dc.N = n_pulse
            self.dc.generate_pulse(l_fwhm, l_0, t_span, n_pulse, duration_domain='spectral')
            for row in range(self.material_table_model.rowCount()):
                ind = self.material_table_model.index(row, 0, QtCore.QModelIndex())
                mat = str(self.material_table_model.data(ind, QtCore.Qt.DisplayRole))
                ind = self.material_table_model.index(row, 1, QtCore.QModelIndex())
                # thickness = self.material_table_model.data(ind, QtCore.Qt.DisplayRole).toReal()[0]
                thickness = np.double(self.material_table_model.data(ind, QtCore.Qt.DisplayRole).value())
                root.debug("Thickness {0}: {1}".format(mat, thickness))
                self.dc.propagate_material(mat, thickness*1e-3)
        root.debug("Re-Propagation complete")
        poly = self.dc.get_spectral_phase_expansion(4, 1e15)
        root.debug("Spectral expansion complete")
        self.pulse_result_expansion2.setText("{0:.2f}".format(poly[-3]))
        self.pulse_result_expansion3.setText("{0:.2f}".format(poly[-4]))
        self.pulse_result_expansion4.setText("{0:.2f}".format(poly[-5]))

    def setup_pulse(self):
        t_fwhm = self.pulse_initial_duration.value() * 1e-15
        t_span = self.pulse_time_window.value() * 1e-12
        n_pulse = self.pulse_number_points.value()
        l_0 = self.pulse_central_wavelength.value() * 1e-9
        print("New pulse: t_fwhm {0:.2e}, l_0 {1:.2e}".format(t_fwhm, l_0))
        self.dc.N = n_pulse
        self.dc.generate_pulse(t_fwhm, l_0, t_span, n_pulse, duration_domain='temporal')
        root.debug("Pulse generated")
        dw = self.dc.get_pulse_duration('spectral')
        root.debug("dw {0}".format(dw))
        dl = dw*l_0**2/(2*np.pi*self.dc.c) * 1e9
        root.debug("dl {0}".format(dl))
        self.pulse_initial_spectral_width.setValue(dl)
        root.debug("Initial spectral width {0}".format(dl))
        self.propagate_material_list()
        root.debug("Propagation finished")

    def setup_pulse_spectral(self):
        fwhm = self.pulse_initial_spectral_width.value() * 1e-9
        t_span = self.pulse_time_window.value() * 1e-12
        n_pulse = self.pulse_number_points.value()
        l_0 = self.pulse_central_wavelength.value() * 1e-9
        self.dc.N = n_pulse
        self.dc.generate_pulse(fwhm, l_0, t_span, n_pulse, duration_domain='spectral')
        dt = self.dc.get_pulse_duration('temporal')
        self.pulse_initial_duration.setValue(dt*1e15)
        self.propagate_material_list()

    def store_model_selection(self):
        root.debug("Entring store_model_selection")
        self.tableview_selected_indexes = self.material_tableview.selectionModel().selection().indexes()

    def restore_model_selection(self):
        root.debug("Entring restore_model_selection")
        if self.tableview_selected_indexes is not None:
            if len(self.tableview_selected_indexes) > 0:
                self.material_tableview.selectionModel().select(self.tableview_selected_indexes[0],
                                                                QtWidgets.QItemSelectionModel.Select)
                self.material_tableview.selectionModel().setCurrentIndex(self.tableview_selected_indexes[0],
                                                                         QtWidgets.QItemSelectionModel.SelectCurrent)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress and source is self.material_tableview:
            if self.material_tableview.state() != QtWidgets.QAbstractItemView.EditingState:
                if event.key() == QtCore.Qt.Key_Delete:
                    selected_indexes = self.material_tableview.selectionModel().selectedIndexes()
                    rows = []
                    for ind in selected_indexes:
                        if ind.row() not in rows:
                            rows.append(ind.row())
                    print(selected_indexes)
                    self.material_table_model.removeRows(min(rows), len(rows), QtCore.QModelIndex())
                elif event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
                    selected_indexes = self.material_tableview.selectionModel().selectedIndexes()
                    self.material_tableview.edit(selected_indexes[0])
        return QtWidgets.QWidget.eventFilter(self, source, event)

    def setup_layout(self):
        self.material_lineedit = QtWidgets.QLineEdit()
        completer = QtWidgets.QCompleter()
        completer.setModel(self.material_completer_model)
        self.material_lineedit.setCompleter(completer)
        self.material_lineedit.editingFinished.connect(self.set_combobox_material)
        self.material_lineedit.setMaximumWidth(100)

        self.material_combobox = QtWidgets.QComboBox()
        for mat in self.dc.materials:
            self.material_combobox.addItem(mat)
        self.material_combobox.model().sort(0)
        self.material_combobox.currentIndexChanged.connect(self.set_material)
        self.material_combobox.setMaximumWidth(120)

        self.material_thickness = QtWidgets.QDoubleSpinBox()
        self.material_thickness.setValue(0.0)
        self.material_thickness.setMaximum(1e6)
        self.material_thickness.setMinimum(0)
        self.material_thickness.setSuffix(" mm")
        self.material_thickness.setMaximumWidth(100)

        self.material_add_button = QtWidgets.QPushButton("Add")
        self.material_add_button.setMaximumWidth(40)
        self.material_add_button.pressed.connect(self.add_material)
        self.material_add_button.setToolTip("Add specified material (combobox+thickness) to material table")

        self.material_tableview = QtWidgets.QTableView()
        self.material_tableview.setModel(self.material_table_model)
        self.material_tableview.verticalHeader().hide()
        self.material_tableview.horizontalHeader().show()
        self.material_table_model.dataChanged.connect(self.propagate_material_list)
        self.material_tableview.installEventFilter(self)
        self.material_tableview.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked |
                                                QtWidgets.QAbstractItemView.SelectedClicked |
                                                QtWidgets.QAbstractItemView.AnyKeyPressed |
                                                QtWidgets.QAbstractItemView.EditKeyPressed)
        sp = self.material_tableview.sizePolicy()
        sp.setVerticalStretch(2)
        self.material_tableview.setSizePolicy(sp)
        self.material_table_model.modelAboutToBeReset.connect(self.store_model_selection)
        self.material_table_model.modelReset.connect(self.restore_model_selection)
        self.material_tableview.setToolTip("Change material or thickness by selecting element and typing, "
                                           "delete material by pressing delete key")

        self.material_plotwidget = pq.PlotWidget(useOpenGL=True,
                                                 labels={'bottom': ('Wavelength', 'm'),
                                                         'left': ('Refractive index', '')})
        self.material_plot = self.material_plotwidget.plot()
        self.material_plot.setPen((50, 200, 50))
        self.material_plotwidget.showGrid(x=True, y=True)
        self.material_plotwidget.setMaximumWidth(400)
        self.material_plotwidget.setYRange(1.3, 1.9)
        sp = self.material_plotwidget.sizePolicy()
        sp.setVerticalStretch(1)
        self.material_plotwidget.setSizePolicy(sp)
        self.material_plotwidget.setToolTip("Material refractive index")
        # self.material_plotwidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)

        material_select_layout = QtWidgets.QHBoxLayout()
        material_select_layout.addWidget(self.material_lineedit)
        material_select_layout.addWidget(self.material_combobox)
        material_select_layout.addWidget(self.material_thickness)
        material_select_layout.addWidget(self.material_add_button)
        material_select_layout.addSpacerItem(QtWidgets.QSpacerItem(
            QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)))
        material_layout = QtWidgets.QVBoxLayout()
        material_layout.addLayout(material_select_layout)
        material_layout.addWidget(self.material_tableview)
        material_layout.addWidget(self.material_plotwidget)

        self.pulse_temporal_plotwidget = pq.PlotWidget(useOpenGL=True,
                                                       labels={'bottom': ('Time', 's'),
                                                               'left': ('Intensity', 'norm')})
        self.pulse_temporal_plot = self.pulse_temporal_plotwidget.plot()
        self.pulse_temporal_plot.setPen((50, 150, 250))
        self.pulse_temporal_plotwidget.showGrid(x=True, y=True)
        self.pulse_temporal_plotwidget.setToolTip("Propagated pulse temporal intensity")

        self.pulse_phase_plotwidget = pq.PlotWidget(useOpenGL=True,
                                                       labels={'bottom': ('Angular freq', 'rad/s'),
                                                               'left': ('Phase', 'rad')})
        self.pulse_phase_plot = self.pulse_phase_plotwidget.plot()
        self.pulse_phase_plot.setPen((50, 150, 250))
        self.pulse_phase_plotwidget.showGrid(x=True, y=True)
        self.pulse_phase_plotwidget.setToolTip("Propagated pulse phase profile. If there are artifacts at the edges "
                                               "try increasing the time span")

        self.pulse_spectral_plotwidget = pq.PlotWidget(useOpenGL=True,
                                                       labels={'bottom': ('Wavelength', 'm'),
                                                               'left': 'Intensity'})
        self.pulse_spectral_plot = self.pulse_spectral_plotwidget.plot()
        self.pulse_spectral_plot.setPen((50, 150, 250))
        self.pulse_spectral_plotwidget.showGrid(x=True, y=True)
        self.pulse_spectral_plotwidget.setToolTip("Initial pulse spectrum")

        self.pulse_initial_duration = QtWidgets.QDoubleSpinBox()
        self.pulse_initial_duration.setMinimum(0.0)
        self.pulse_initial_duration.setMaximum(1e6)
        self.pulse_initial_duration.setValue(50)
        self.pulse_initial_duration.setSuffix(" fs")
        self.pulse_initial_duration.editingFinished.connect(self.setup_pulse)
        self.pulse_initial_duration.setToolTip("Initial full width at half max pulse duration for the generated gaussian pulse")

        self.pulse_initial_spectral_width = QtWidgets.QDoubleSpinBox()
        self.pulse_initial_spectral_width.setMinimum(0.0)
        self.pulse_initial_spectral_width.setMaximum(1e6)
        self.pulse_initial_spectral_width.setValue(19)
        self.pulse_initial_spectral_width.setSuffix(" nm")
        self.pulse_initial_spectral_width.editingFinished.connect(self.setup_pulse_spectral)
        self.pulse_initial_spectral_width.setToolTip("Initial full width at half max pulse spectral width for the generated gaussian pulse")

        self.pulse_central_wavelength = QtWidgets.QDoubleSpinBox()
        self.pulse_central_wavelength.setMinimum(0.0)
        self.pulse_central_wavelength.setMaximum(1e6)
        self.pulse_central_wavelength.setValue(800)
        self.pulse_central_wavelength.setSuffix(" nm")
        self.pulse_central_wavelength.editingFinished.connect(self.setup_pulse)
        self.pulse_central_wavelength.setToolTip("Central wavelength of the generated pulse, 200-2000 nm")

        self.pulse_time_window = QtWidgets.QDoubleSpinBox()
        self.pulse_time_window.setMinimum(0.0)
        self.pulse_time_window.setMaximum(1e6)
        self.pulse_time_window.setValue(20)
        self.pulse_time_window.setSuffix(" ps")
        self.pulse_time_window.editingFinished.connect(self.setup_pulse)
        self.pulse_time_window.setToolTip("<nobr>The propagated pulse is calculated in this time window.<\nobr> "
                                          "If the resulting pulse is too long, there will be aliasing effects.")

        self.pulse_number_points = QtWidgets.QDoubleSpinBox()
        self.pulse_number_points.setMinimum(0.0)
        self.pulse_number_points.setMaximum(1e6)
        self.pulse_number_points.setValue(16384)
        self.pulse_number_points.editingFinished.connect(self.setup_pulse)
        self.pulse_number_points.setToolTip("Number of points in the generated pulse. "
                                            "If too low, the pulse can't resolve field oscillations")

        self.pulse_result_duration = QtWidgets.QLabel()
        self.pulse_result_expansion2 = QtWidgets.QLabel()
        self.pulse_result_expansion3 = QtWidgets.QLabel()
        self.pulse_result_expansion4 = QtWidgets.QLabel()

        pulse_setup_layout = QtWidgets.QGridLayout()
        pulse_setup_layout.addWidget(QtWidgets.QLabel("Central wavelength"), 0, 0)
        pulse_setup_layout.addWidget(self.pulse_central_wavelength, 0, 1)
        pulse_setup_layout.addWidget(QtWidgets.QLabel("Initial duration (FWHM)"), 1, 0)
        pulse_setup_layout.addWidget(self.pulse_initial_duration, 1, 1)
        pulse_setup_layout.addWidget(QtWidgets.QLabel("Initial bandwidth (FWHM)"), 2, 0)
        pulse_setup_layout.addWidget(self.pulse_initial_spectral_width, 2, 1)
        pulse_setup_layout.addWidget(QtWidgets.QLabel("Time span"), 3, 0)
        pulse_setup_layout.addWidget(self.pulse_time_window, 3, 1)
        pulse_setup_layout.addWidget(QtWidgets.QLabel("Number of points"), 4, 0)
        pulse_setup_layout.addWidget(self.pulse_number_points, 4, 1)
        pulse_setup_layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.MinimumExpanding,
                                   QtWidgets.QSizePolicy.MinimumExpanding), 5, 3)

        pulse_result_layout = QtWidgets.QGridLayout()
        pulse_result_layout.addWidget(QtWidgets.QLabel("Result duration (FWHM)"), 0, 0)
        pulse_result_layout.addWidget(self.pulse_result_duration, 0, 1)
        pulse_result_layout.addWidget(QtWidgets.QLabel("fs"), 0, 2)
        pulse_result_layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.MinimumExpanding,
                                    QtWidgets.QSizePolicy.Minimum), 1, 3)
        pulse_result_layout.addWidget(QtWidgets.QLabel("Result expansion"), 2, 0)
        pulse_result_layout.addWidget(self.pulse_result_expansion2, 2, 1)
        pulse_result_layout.addWidget(QtWidgets.QLabel("fs^2"), 2, 2)
        pulse_result_layout.addWidget(self.pulse_result_expansion3, 3, 1)
        pulse_result_layout.addWidget(QtWidgets.QLabel("fs^3"), 3, 2)
        pulse_result_layout.addWidget(self.pulse_result_expansion4, 4, 1)
        pulse_result_layout.addWidget(QtWidgets.QLabel("fs^4"), 4, 2)

        pulse_layout1 = QtWidgets.QVBoxLayout()
        pulse_layout1.addLayout(pulse_setup_layout)
        pulse_layout1.addWidget(self.pulse_spectral_plotwidget)

        pulse_layout2 = QtWidgets.QVBoxLayout()
        pulse_layout2.addLayout(pulse_result_layout)
        pulse_layout2.addWidget(self.pulse_temporal_plotwidget)
        pulse_layout2.addWidget(self.pulse_phase_plotwidget)

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.addLayout(material_layout)
        self.main_layout.addLayout(pulse_layout1)
        self.main_layout.addLayout(pulse_layout2)

        self.set_material()

        self.setWindowTitle('Dispersion Calculator')
        self.setGeometry(200, 200, 1024, 600)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    myapp = DispersionCalculatorGui()
    myapp.show()
    sys.exit(app.exec_())
