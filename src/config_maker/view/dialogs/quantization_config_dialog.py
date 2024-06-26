import abc
import os
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QGridLayout, QMessageBox, QComboBox

from tags import (HEADER_POT_PARAMS_TAGS, HEADER_MODEL_PARAMS_ENGINE_TAGS, HEADER_MODEL_PARAMS_MODEL_TAGS,
                  HEADER_MODEL_PARAMS_COMPRESSION_COMMON_TAGS, HEADER_DQ_PARAMS_TAGS, HEADER_AAQ_PARAMS_TAGS,
                  HEADER_INDEPENDENT_PARAMS_TAGS, CONFIG_TARGET_DEVICE_TAG, CONFIG_ALGORITHM_NAME_TAG,
                  CONFIG_PRESET_TAG, CONFIG_STAT_SUBSET_SIZE_TAG, CONFIG_WEIGHTS_BITS_TAG, CONFIG_WEIGHTS_MODE_TAG,
                  CONFIG_WEIGHTS_GRANULARITY_TAG, CONFIG_WEIGHTS_LEVEL_LOW_TAG, CONFIG_WEIGHTS_LEVEL_HIGH_TAG,
                  CONFIG_WEIGHTS_MAX_TYPE_TAG, CONFIG_WEIGHTS_MAX_OUTLIER_PROB_TAG, CONFIG_ACTIVATIONS_BITS_TAG,
                  CONFIG_ACTIVATIONS_MODE_TAG, CONFIG_ACTIVATIONS_GRANULARITY_TAG, CONFIG_ACTIVATIONS_PRESET_TAG,
                  CONFIG_ACTIVATIONS_MIN_CLIPPING_VALUE_TAG, CONFIG_ACTIVATIONS_MIN_AGGREGATOR_TAG,
                  CONFIG_ACTIVATIONS_MIN_TYPE_TAG, CONFIG_ACTIVATIONS_MIN_OUTLIER_PROB_TAG,
                  CONFIG_ACTIVATIONS_MAX_CLIPPING_VALUE_TAG, CONFIG_ACTIVATIONS_MAX_AGGREGATOR_TAG,
                  CONFIG_ACTIVATIONS_MAX_TYPE_TAG, CONFIG_ACTIVATIONS_MAX_OUTLIER_PROB_TAG)


class QuantizationConfigDialog(QDialog):
    def __init__(self, parent, models, data):
        super().__init__(parent)
        self.__title = 'Information about model'
        self.__q_method_dependent_params = {
            'DefaultQuantization': DefaultQuantizationDialog(self),
            'AccuracyAwareQuantization': AccuracyAwareQuantizationDialog(self),
        }
        self.__q_method_independent_params = IndependentParameters(
            self, models, data, self.__q_method_dependent_params.keys(), self.__q_method_choice)
        self.__selected_q_method = 'DefaultQuantization'

        self.__pot_params_tags = HEADER_POT_PARAMS_TAGS

        self.__model_params_tags = []
        self.__model_params_tags.extend(HEADER_MODEL_PARAMS_MODEL_TAGS)
        self.__model_params_tags.extend(HEADER_MODEL_PARAMS_ENGINE_TAGS)
        self.__model_params_tags.extend(HEADER_MODEL_PARAMS_COMPRESSION_COMMON_TAGS)

        self.tags = [*self.__pot_params_tags, *self.__model_params_tags]
        self.__init_ui()
        self.__q_method_independent_params.switch_engine_type(self.__selected_q_method)

    def __init_ui(self):
        self.setWindowTitle(self.__title)
        self.__create_layout()

    def __create_layout(self):
        layout = QGridLayout()
        idx = 0
        independent_idx = self.__q_method_independent_params.attach_to_layout(layout)
        dict_q_method_idx = dict.fromkeys(self.__q_method_dependent_params.keys(), idx)
        for key in self.__q_method_dependent_params:
            dict_q_method_idx[key] = self.__q_method_dependent_params[key].attach_to_layout(layout, False)
        self.__q_method_dependent_params['DefaultQuantization'].show()
        dependent_idx = max(*dict_q_method_idx.values())
        row_idx = max(independent_idx, dependent_idx)
        ok_btn = QPushButton('Ok')
        cancel_btn = QPushButton('Cancel')
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(ok_btn, row_idx, 0)
        layout.addWidget(cancel_btn, row_idx, 1)
        self.setLayout(layout)

    def __q_method_choice(self, q_method):
        for key in self.__q_method_dependent_params:
            if key == q_method:
                self.__q_method_dependent_params[key].show()
                self.__selected_q_method = key
            else:
                self.__q_method_dependent_params[key].hide()
            self.__q_method_independent_params.switch_engine_type(q_method)

    def __calculate_start_index(self, quantization_method):
        start_idx = len(self.tags)
        methods = {
            'DefaultQuantization': len(HEADER_DQ_PARAMS_TAGS),
            'AccuracyAwareQuantization': len(HEADER_AAQ_PARAMS_TAGS),
        }
        for method_name in methods.keys():
            if quantization_method == method_name:
                return start_idx
            start_idx += methods[method_name]

    def get_values(self):
        pot_params, model_params = self.__q_method_independent_params.get_values()
        dependent_params = self.__q_method_dependent_params[self.__selected_q_method].get_values()
        return pot_params, model_params, dependent_params

    def load_values_from_table_row(self, table, row):
        self.__q_method_independent_params.load_values_from_table_row(table, row)
        self.__q_method_dependent_params[self.__selected_q_method].load_values_from_table_row(
            table, row, self.__calculate_start_index(self.__selected_q_method))

    def accept(self):
        is_ok = self.__q_method_independent_params.check()
        is_ok = is_ok and self.__q_method_dependent_params[self.__selected_q_method].check()
        if is_ok:
            super().accept()
        else:
            QMessageBox.warning(
                self,
                'Warning!',
                'Not all needed lines (OutputDir, ModelName, Model, DataSource or Config) are filled!')


class ParametersDialog(metaclass=abc.ABCMeta):
    def __init__(self, parent, tags):
        self._parent = parent
        self._tags = tags
        self._labels = []
        self._edits = []
        self._ignored_idx = []
        self.__init_ui()

    def __init_ui(self):
        self.__create_labels()
        self._create_edits()

    def __create_labels(self):
        self._labels = {}
        for idx, tag in enumerate(self._tags[1:]):
            self._labels[1 + idx] = QLabel(tag, self._parent)
        self._labels[0] = QLabel(self._tags[0], self._parent)

    @abc.abstractmethod
    def _create_edits(self):
        pass

    @abc.abstractmethod
    def get_values(self):
        pass

    @abc.abstractmethod
    def load_values_from_table_row(self, table, row, start_idx=0):
        pass

    def hide(self):
        self._labels[0].hide()
        for tag in range(1, len(self._tags)):
            self._labels[tag].hide()
            self._edits[tag].hide()

    def show(self):
        self._labels[0].show()
        for tag in range(1, len(self._tags)):
            self._labels[tag].show()
            self._edits[tag].show()

    def _set_qcombobox_edit(self, idx, values, f=None):
        self._edits[idx] = QComboBox(self._parent)
        self._edits[idx].addItems(values)
        if f is not None:
            self._edits[idx].activated[str].connect(f)
            self._edits[idx].currentTextChanged[str].connect(f)
        self._ignored_idx.append(idx)

    @abc.abstractmethod
    def attach_to_layout(self, layout, show=True):
        pass


class IndependentParameters(ParametersDialog):
    def __init__(self, parent, models, data, q_methods, q_method_choice):
        self.__models = models
        self.__data = [dataset.split(';')[1] for dataset in data]
        self.__q_methods = q_methods
        self.__q_method_choice = q_method_choice
        self.__qmodel = None
        super().__init__(parent, ['QuantizationMethodIndependent:', *HEADER_INDEPENDENT_PARAMS_TAGS])

    def _create_edits(self):
        self._edits = {}
        self._ignored_idx = []
        self._create_pot_edits()
        self._create_model_params_edits()
        self._create_engine_params_edits()
        self._create_compression_params_edits()

    def _create_pot_edits(self):
        pot_start_idx = len(['QuantizationMethodIndependent:'])
        pot_len = len(['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS)

        self._set_qcombobox_edit(pot_start_idx + 1, ('', str(False), str(True)))
        self._set_qcombobox_edit(pot_start_idx + 3, ('', str(True), str(False)))
        self._set_qcombobox_edit(pot_start_idx + 4, ('', 'INFO', 'CRITICAL', 'ERROR', 'WARNING', 'DEBUG'))
        self._set_qcombobox_edit(pot_start_idx + 5, ('', str(False), str(True)))
        self._set_qcombobox_edit(pot_start_idx + 6, ('', str(False), str(True)))
        self._set_qcombobox_edit(pot_start_idx + 7, ('', str(False), str(True)))

        for tag in range(pot_start_idx, pot_len):
            if tag not in self._ignored_idx:
                self._edits[tag] = QLineEdit(self._parent)

    def _create_model_params_edits(self):
        model_start_idx = len(['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS)
        model_len = len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        self._set_qcombobox_edit(model_start_idx + 1, [''] + self.__models, self.__choose_model)
        self._edits[model_start_idx + 1].setFixedWidth(300)

        for tag in range(model_start_idx, model_len):
            if tag not in self._ignored_idx:
                self._edits[tag] = QLineEdit(self._parent)

    def __choose_model(self, model):
        model_name_idx = len(['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS)
        output_dir_idx = len(['QuantizationMethodIndependent:']) + 2

        model_data = model.split(';')
        self._edits[model_name_idx].setText(model_data[1])

        model_dir = os.path.dirname(model_data[-1])
        precision = os.path.basename(model_dir)
        output_dir = model_dir.replace(precision, 'INT8')
        self._edits[output_dir_idx].setText(output_dir)

        model_data[-1] = output_dir
        self.__qmodel = ';'.join(model_data)
        self.__qmodel.replace(precision, 'INT8')

    def get_qmodel_str(self):
        if self.__qmodel is not None:
            return self.__qmodel
        else:
            return ''

    def _create_engine_params_edits(self):
        engine_start_idx = len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        engine_len = len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS + HEADER_MODEL_PARAMS_ENGINE_TAGS)

        self._set_qcombobox_edit(engine_start_idx + 3, ('simplified', 'accuracy_checker'), self.__choose_engine_type)

        self._set_qcombobox_edit(engine_start_idx + 4, [''] + self.__data, self.__choose_engine_type)
        self._edits[engine_start_idx + 4].setFixedWidth(300)

        for tag in range(engine_start_idx, engine_len):
            if tag not in self._ignored_idx:
                self._edits[tag] = QLineEdit(self._parent)

    def switch_engine_type(self, q_type):
        ac_config_idx = 2 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        engine_type_idx = 3 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        data_source_idx = 4 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        if q_type == 'DefaultQuantization':
            self._labels[ac_config_idx].hide()
            self._edits[ac_config_idx].hide()
            self._labels[engine_type_idx].show()
            self._edits[engine_type_idx].show()
            self._labels[data_source_idx].hide()
            self._edits[data_source_idx].hide()
            if self._edits[engine_type_idx].currentText() == 'simplified':
                self._labels[data_source_idx].show()
                self._edits[data_source_idx].show()
                self._labels[ac_config_idx].hide()
                self._edits[ac_config_idx].hide()
            if self._edits[engine_type_idx].currentText() == 'accuracy_checker':
                self._labels[data_source_idx].hide()
                self._edits[data_source_idx].hide()
                self._labels[ac_config_idx].show()
                self._edits[ac_config_idx].show()
        if q_type == 'AccuracyAwareQuantization':
            self._labels[ac_config_idx].show()
            self._edits[ac_config_idx].show()
            self._labels[engine_type_idx].hide()
            self._edits[engine_type_idx].hide()
            self._labels[data_source_idx].hide()
            self._edits[data_source_idx].hide()

    def __choose_engine_type(self, engine_type):
        ac_config_idx = 2 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        data_source_idx = 4 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        if engine_type == 'simplified':
            self._labels[data_source_idx].show()
            self._edits[data_source_idx].show()
            self._labels[ac_config_idx].hide()
            self._edits[ac_config_idx].hide()
        if engine_type == 'accuracy_checker':
            self._labels[data_source_idx].hide()
            self._edits[data_source_idx].hide()
            self._labels[ac_config_idx].show()
            self._edits[ac_config_idx].show()

    def _create_compression_params_edits(self):
        start_idx = len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS + HEADER_MODEL_PARAMS_ENGINE_TAGS)

        self._set_qcombobox_edit(start_idx + 0, ('ANY', 'CPU', 'GPU'))
        self._set_qcombobox_edit(start_idx + 1, self.__q_methods, self.__q_method_choice)
        self._set_qcombobox_edit(start_idx + 2, ('mixed', 'performance', 'accuracy'))
        self._set_qcombobox_edit(start_idx + 5, ('', 'symmetric', 'asymmetric'))
        self._set_qcombobox_edit(start_idx + 6, ('', 'perchannel', 'pertensor'))
        self._set_qcombobox_edit(start_idx + 9, ('', 'quantile', 'min', 'max', 'abs_max', 'abs_quantile'))
        self._set_qcombobox_edit(start_idx + 12, ('', 'symmetric', 'asymmetric'))
        self._set_qcombobox_edit(start_idx + 13, ('', 'perchannel', 'pertensor'))
        self._set_qcombobox_edit(start_idx + 14, ('', 'quantile', 'min', 'max', 'abs_max', 'abs_quantile'))
        self._set_qcombobox_edit(
            start_idx + 16,
            ('', 'mean', 'max', 'min', 'median', 'mean_no_outliers', 'median_no_outliers', 'hl_estimator'),
        )
        self._set_qcombobox_edit(start_idx + 17, ('', 'quantile', 'min', 'max', 'abs_max', 'abs_quantile'))
        self._set_qcombobox_edit(
            start_idx + 20,
            ('', 'mean', 'max', 'min', 'median', 'mean_no_outliers', 'median_no_outliers', 'hl_estimator'),
        )
        self._set_qcombobox_edit(start_idx + 21, ('', 'quantile', 'min', 'max', 'abs_max', 'abs_quantile'))

        stop_iter_idx = len(self._tags)
        start_iter_idx = stop_iter_idx - len(HEADER_MODEL_PARAMS_COMPRESSION_COMMON_TAGS)
        for tag in range(start_iter_idx, stop_iter_idx):
            if tag not in self._ignored_idx:
                self._edits[tag] = QLineEdit(self._parent)

        self._edits[start_iter_idx + 3].setText(str(100))

    def get_values(self):
        pot_values = []
        for tag in range(1, 1 + len(HEADER_POT_PARAMS_TAGS)):
            if tag not in self._ignored_idx:
                pot_values.append(self._edits[tag].text())
            else:
                pot_values.append(self._edits[tag].currentText())
        model_values = []
        for tag in range(1 + len(HEADER_POT_PARAMS_TAGS), len(self._tags)):
            if tag not in self._ignored_idx:
                model_values.append(self._edits[tag].text())
            else:
                model_values.append(self._edits[tag].currentText())
        return pot_values, model_values

    def load_values_from_table_row(self, table, row, start_idx=0):
        shift = 0
        for column, tag in enumerate(range(1, len(self._tags))):
            if (self._tags[tag] == 'Model'):
                shift += 1
                continue
            if tag not in self._ignored_idx:
                self._edits[tag].setText(table.item(row, column + shift).text())
            else:
                self._edits[tag].setCurrentText(table.item(row, column + shift).text())

    def check(self):
        # check <OutputDir>
        start_idx = len(['QuantizationMethodIndependent:'])
        if (self._edits[start_idx + 2].text() == ''):
            return False

        # check <Model.ModelName>, <Model.Model>, <Model.Weights>
        model_start_idx = len(['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS)
        model_len = len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        for tag in range(model_start_idx, model_len):
            if (tag not in self._ignored_idx) and (self._edits[tag].text() == ''):
                return False

        # check <Engine.Config> or <Engine.DataSource>
        ac_config_idx = 2 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        engine_type_idx = 3 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS)
        q_method_idx = 1 + len(
            ['QuantizationMethodIndependent:'] + HEADER_POT_PARAMS_TAGS
            + HEADER_MODEL_PARAMS_MODEL_TAGS + HEADER_MODEL_PARAMS_ENGINE_TAGS)

        if self._edits[q_method_idx].currentText() == 'DefaultQuantization':
            if (self._edits[engine_type_idx].currentText() == 'accuracy_checker'
                    and self._edits[ac_config_idx].text() == ''):
                return False
        if self._edits[q_method_idx].currentText() == 'AccuracyAwareQuantization':
            if (self._edits[ac_config_idx].text() == ''):
                return False
        return True

    def attach_to_layout(self, layout, show=True):
        self_idx_1 = 1
        self_idx_2 = 1

        idx = [0] * 11
        idx[0] = 1
        idx[1] = idx[0] + len(HEADER_POT_PARAMS_TAGS)
        idx[2] = idx[1] + len(HEADER_MODEL_PARAMS_MODEL_TAGS)
        idx[3] = idx[2] + len(HEADER_MODEL_PARAMS_ENGINE_TAGS)
        idx[4] = idx[3] + len([
            CONFIG_TARGET_DEVICE_TAG, CONFIG_ALGORITHM_NAME_TAG, CONFIG_PRESET_TAG,
            CONFIG_STAT_SUBSET_SIZE_TAG,
        ])
        idx[5] = idx[4] + len([
            CONFIG_WEIGHTS_BITS_TAG, CONFIG_WEIGHTS_MODE_TAG,
            CONFIG_WEIGHTS_GRANULARITY_TAG, CONFIG_WEIGHTS_LEVEL_LOW_TAG, CONFIG_WEIGHTS_LEVEL_HIGH_TAG,
        ])
        idx[6] = idx[5] + len([CONFIG_WEIGHTS_MAX_TYPE_TAG, CONFIG_WEIGHTS_MAX_OUTLIER_PROB_TAG])
        idx[7] = idx[6] + len([
            CONFIG_ACTIVATIONS_BITS_TAG, CONFIG_ACTIVATIONS_MODE_TAG,
            CONFIG_ACTIVATIONS_GRANULARITY_TAG,
        ])
        idx[8] = idx[7] + len([CONFIG_ACTIVATIONS_PRESET_TAG])
        idx[9] = idx[8] + len([
            CONFIG_ACTIVATIONS_MIN_CLIPPING_VALUE_TAG,
            CONFIG_ACTIVATIONS_MIN_AGGREGATOR_TAG, CONFIG_ACTIVATIONS_MIN_TYPE_TAG,
            CONFIG_ACTIVATIONS_MIN_OUTLIER_PROB_TAG,
        ])
        idx[10] = idx[9] + len([
            CONFIG_ACTIVATIONS_MAX_CLIPPING_VALUE_TAG,
            CONFIG_ACTIVATIONS_MAX_AGGREGATOR_TAG, CONFIG_ACTIVATIONS_MAX_TYPE_TAG,
            CONFIG_ACTIVATIONS_MAX_OUTLIER_PROB_TAG,
        ])

        base_tab = '    '

        layout.addWidget(self._labels[0], 0, 0)
        layout.addWidget(QLabel(0 * base_tab + 'Pot Parameters:', self._parent), self_idx_1, 0)
        self_idx_1 += 1
        for tag in range(idx[0], idx[1]):
            self._labels[tag].setText(1 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_1, 0)
            layout.addWidget(self._edits[tag], self_idx_1, 1)
            self_idx_1 += 1

        layout.addWidget(QLabel(0 * base_tab + 'Model Parameters:', self._parent), self_idx_1, 0)
        self_idx_1 += 1
        for tag in range(idx[1], idx[2]):
            self._labels[tag].setText(1 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_1, 0)
            layout.addWidget(self._edits[tag], self_idx_1, 1)
            self_idx_1 += 1

        layout.addWidget(QLabel(0 * base_tab + 'Engine Parameters:', self._parent), self_idx_1, 0)
        self_idx_1 += 1
        for tag in range(idx[2], idx[3]):
            self._labels[tag].setText(1 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_1, 0)
            layout.addWidget(self._edits[tag], self_idx_1, 1)
            self_idx_1 += 1

        layout.addWidget(QLabel(0 * base_tab + 'Compression Parameters:', self._parent), self_idx_1, 0)
        self_idx_1 += 1
        for tag in range(idx[3], idx[4]):
            self._labels[tag].setText(1 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_1, 0)
            layout.addWidget(self._edits[tag], self_idx_1, 1)
            self_idx_1 += 1

        layout.addWidget(QLabel(1 * base_tab + 'Weights Parameters:', self._parent), self_idx_2, 2)
        self_idx_2 += 1
        for tag in range(idx[4], idx[5]):
            self._labels[tag].setText(2 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_2, 2)
            layout.addWidget(self._edits[tag], self_idx_2, 3)
            self_idx_2 += 1

        layout.addWidget(QLabel(2 * base_tab + 'RE Parameters:', self._parent), self_idx_2, 2)
        self_idx_2 += 1
        layout.addWidget(QLabel(3 * base_tab + 'Max Parameters:', self._parent), self_idx_2, 2)
        self_idx_2 += 1
        for tag in range(idx[5], idx[6]):
            self._labels[tag].setText(4 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_2, 2)
            layout.addWidget(self._edits[tag], self_idx_2, 3)
            self_idx_2 += 1

        layout.addWidget(QLabel(1 * base_tab + 'Activations Parameters:', self._parent), self_idx_2, 2)
        self_idx_2 += 1
        for tag in range(idx[6], idx[7]):
            self._labels[tag].setText(2 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_2, 2)
            layout.addWidget(self._edits[tag], self_idx_2, 3)
            self_idx_2 += 1

        layout.addWidget(QLabel(2 * base_tab + 'RE Parameters:', self._parent), self_idx_2, 2)
        self_idx_2 += 1
        for tag in range(idx[7], idx[8]):
            self._labels[tag].setText(3 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_2, 2)
            layout.addWidget(self._edits[tag], self_idx_2, 3)
            self_idx_2 += 1
        layout.addWidget(QLabel(3 * base_tab + 'Min Parameters:', self._parent), self_idx_2, 2)
        self_idx_2 += 1
        for tag in range(idx[8], idx[9]):
            self._labels[tag].setText(4 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_2, 2)
            layout.addWidget(self._edits[tag], self_idx_2, 3)
            self_idx_2 += 1

        layout.addWidget(QLabel(3 * base_tab + 'Max Parameters:', self._parent), self_idx_2, 2)
        self_idx_2 += 1
        for tag in range(idx[9], idx[10]):
            self._labels[tag].setText(4 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_2, 2)
            layout.addWidget(self._edits[tag], self_idx_2, 3)
            self_idx_2 += 1

        if show:
            self.show()
        else:
            self.hide()
        return max(self_idx_1, self_idx_2)


class DependentParameters(ParametersDialog):
    def __init__(self, parent, tags):
        super().__init__(parent, tags)

    def _create_edits(self):
        self._edits = {}
        self._ignored_idx = []
        self._create_compression_params_edits()

    def _create_compression_params_edits(self):
        for tag in range(1, len(self._tags)):
            if tag not in self._ignored_idx:
                self._edits[tag] = QLineEdit(self._parent)

    def get_values(self):
        values = []
        for tag in range(1, len(self._tags)):
            if tag not in self._ignored_idx:
                values.append(self._edits[tag].text())
            else:
                values.append(self._edits[tag].currentText())
        return values

    def load_values_from_table_row(self, table, row, start_idx=0):
        for column, tag in enumerate(range(1, len(self._tags))):
            if tag not in self._ignored_idx:
                self._edits[tag].setText(table.item(row, start_idx + column).text())
            else:
                self._edits[tag].setCurrentText(table.item(row, start_idx + column).text())

    def check(self):
        return True

    def attach_to_layout(self, layout, show=True):
        self_idx_3 = 1

        idx = [0] * 2
        idx[0] = 1
        idx[1] = len(self._tags)

        base_tab = '    '

        layout.addWidget(self._labels[0], 0, 4)
        for tag in range(idx[0], idx[1]):
            self._labels[tag].setText(1 * base_tab + self._labels[tag].text())
            layout.addWidget(self._labels[tag], self_idx_3, 4)
            layout.addWidget(self._edits[tag], self_idx_3, 5)
            self_idx_3 += 1

        if show:
            self.show()
        else:
            self.hide()
        return self_idx_3


class DefaultQuantizationDialog(DependentParameters):
    def __init__(self, parent):
        super().__init__(parent, ['DefaultQuantization', *HEADER_DQ_PARAMS_TAGS])

    def _create_edits(self):
        self._edits = {}
        self._ignored_idx = []
        self._create_compression_params_edits()

    def _create_compression_params_edits(self):
        start_idx = len(['DefaultQuantization:'])
        self._set_qcombobox_edit(start_idx + 0, ('', str(False), str(True)))

        for tag in range(1, len(self._tags)):
            if tag not in self._ignored_idx:
                self._edits[tag] = QLineEdit(self._parent)

    def check(self):
        return True


class AccuracyAwareQuantizationDialog(DependentParameters):
    def __init__(self, parent):
        super().__init__(parent, ['AccuracyAwareQuantization:', *HEADER_AAQ_PARAMS_TAGS])

    def _create_edits(self):
        self._edits = {}
        self._ignored_idx = []
        self._create_compression_params_edits()

    def _create_compression_params_edits(self):
        start_idx = len(['AccuracyAwareQuantization:'])
        self._set_qcombobox_edit(start_idx + 3, ('', 'absolute', 'relative'))
        self._set_qcombobox_edit(start_idx + 4, ('', str(False), str(True)))
        self._set_qcombobox_edit(start_idx + 5, (['DefaultQuantization']))
        self._set_qcombobox_edit(start_idx + 6, ('', str(False), str(True)))
        self._set_qcombobox_edit(start_idx + 8, ('', str(False), str(True)))
        self._set_qcombobox_edit(start_idx + 10, ('', str(False), str(True)))

        for tag in range(1, len(self._tags)):
            if tag not in self._ignored_idx:
                self._edits[tag] = QLineEdit(self._parent)

    def check(self):
        return True
