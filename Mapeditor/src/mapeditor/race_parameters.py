"""Project race parameters; one Apply is one undoable project change."""

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                              QDoubleSpinBox, QFormLayout, QGroupBox, QLabel,
                              QMessageBox, QVBoxLayout)
from .i18n import N_, tr


class RaceParametersDialog(QDialog):
    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle(tr("Track race parameters"))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        intro = QLabel(tr("Saved with this project. Manual values override automatic race data when building."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.large_world = QCheckBox(tr("Expand carrier terrain for large tracks (experimental)"))
        self.large_world.setChecked(document.project.raw.get('large_world') is True
                                    or 'weltbereich' in document.project.raw)
        self.large_world.setToolTip(tr("Keeps the original track scale. Rebuild required; in-game compatibility is unverified."))
        layout.addWidget(self.large_world)
        data = document.project.manifest.get("race_parameters", {})
        tyres = QGroupBox(tr("Tyre compounds"))
        form = QFormLayout(tyres)
        self.manual_tyres = QCheckBox(tr("Use manual tyre compounds"))
        form.addRow(self.manual_tyres)
        self.compounds = []
        for i, label in enumerate((N_("Hard"), N_("Medium"), N_("Soft"))):
            box = QComboBox()
            box.addItems(["C%d" % n for n in range(1, 7)])
            box.setCurrentText(data.get("tyres", ["C2", "C3", "C4"])[i])
            self.compounds.append(box)
            form.addRow(tr(label), box)
            self.manual_tyres.toggled.connect(box.setEnabled)
            box.setEnabled("tyres" in data)
        self.manual_tyres.setChecked("tyres" in data)
        layout.addWidget(tyres)
        energy = QGroupBox(tr("Energy recovery per lap"))
        form = QFormLayout(energy)
        self.harvest = {}
        for key, label in (("HarvestLimitMGUK", N_("Race harvest limit")),
                           ("HarvestLimitQualifyingMGUK", N_("Qualifying harvest limit"))):
            check = QCheckBox(tr(label))
            spin = QDoubleSpinBox()
            spin.setRange(0, 1000)
            spin.setDecimals(3)
            spin.setSuffix(" MJ")
            spin.setSingleStep(0.5)
            spin.setValue(data.get("ers", {}).get(key, 0) / 1_000_000)
            spin.setEnabled(key in data.get("ers", {}))
            check.setChecked(key in data.get("ers", {}))
            check.toggled.connect(spin.setEnabled)
            form.addRow(check, spin)
            self.harvest[key] = (check, spin)
        layout.addWidget(energy)
        grip = QGroupBox(tr("Grip conditions"))
        grip_layout = QVBoxLayout(grip)
        note = QLabel(tr("Not editable yet: a verified track grip field is not available. Carrier grip settings are preserved."))
        note.setWordWrap(True)
        grip_layout.addWidget(note)
        layout.addWidget(grip)
        note = QLabel(tr("Unchecked values keep the carrier settings or automatic race data. ERS values are exported in joules; in-game validation is still required."))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not document.project.readonly)
        layout.addWidget(self.buttons)

    def values(self):
        data = {}
        if self.manual_tyres.isChecked():
            data["tyres"] = [box.currentText() for box in self.compounds]
        ers = {key: round(spin.value() * 1_000_000) for key, (check, spin) in self.harvest.items() if check.isChecked()}
        if ers:
            data["ers"] = ers
        return data

    def accept(self):
        if self.document.project.readonly:
            return
        data = self.values()
        if "tyres" in data and not all(int(a[1:]) < int(b[1:]) for a, b in zip(data["tyres"], data["tyres"][1:])):
            QMessageBox.warning(self, tr("Track race parameters"), tr("Tyre compounds must increase from hard to medium to soft."))
            return
        def update(raw, manifest):
            if self.large_world.isChecked():
                raw['large_world'] = True
            else:
                raw.pop('large_world', None)
                raw.pop('weltbereich', None)
            if data:
                manifest["race_parameters"] = data
            else:
                manifest.pop("race_parameters", None)
        self.document.edit(tr("Track race parameters"), update)
        super().accept()
