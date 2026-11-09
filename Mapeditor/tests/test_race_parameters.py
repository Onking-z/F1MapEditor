import copy
import sys

import pytest
from PySide6.QtWidgets import QDialog

from conftest import ROOT
from mapeditor.document import Document
from mapeditor.project import Project
from mapeditor.race_parameters import RaceParametersDialog

sys.path.insert(0, str(ROOT / "ego-werkzeuge"))
from strecke import rennparameter, streckencode


def test_dialog_save_reopen_undo_and_clear(app, tmp_path):
    doc = Document(Project())
    dialog = RaceParametersDialog(doc)
    dialog.manual_tyres.setChecked(True)
    for combo, value in zip(dialog.compounds, ["C3", "C4", "C5"]):
        combo.setCurrentText(value)
    check, spin = dialog.harvest["HarvestLimitMGUK"]
    check.setChecked(True)
    spin.setValue(7.5)
    dialog.accept()
    assert dialog.result() == QDialog.Accepted
    expected = {"tyres": ["C3", "C4", "C5"], "ers": {"HarvestLimitMGUK": 7500000}}
    assert doc.project.manifest["race_parameters"] == expected
    doc.project.save(tmp_path)
    assert Project.open(tmp_path).manifest["race_parameters"] == expected
    doc.undo.undo()
    assert "race_parameters" not in doc.project.manifest
    doc.undo.redo()
    again = RaceParametersDialog(doc)
    assert again.harvest["HarvestLimitMGUK"][1].value() == 7.5
    again.manual_tyres.setChecked(False)
    again.harvest["HarvestLimitMGUK"][0].setChecked(False)
    again.accept()
    assert "race_parameters" not in doc.project.manifest


def test_invalid_tyres_and_cancel_do_not_modify_project(app, monkeypatch):
    doc = Document(Project())
    dialog = RaceParametersDialog(doc)
    dialog.manual_tyres.setChecked(True)
    dialog.compounds[0].setCurrentText("C5")
    monkeypatch.setattr("mapeditor.race_parameters.QMessageBox.warning", lambda *a: None)
    dialog.accept()
    assert doc.undo.count() == 0
    dialog.reject()
    assert "race_parameters" not in doc.project.manifest


def test_readonly_project(app):
    doc = Document(Project(manifest={"schema": 999}))
    dialog = RaceParametersDialog(doc)
    dialog.manual_tyres.setChecked(True)
    dialog.accept()
    assert "race_parameters" not in doc.project.manifest


@pytest.mark.parametrize("value", [None, [], {"grip": 1.2}, {"tyres": ["C3", "C2", "C4"]},
    {"tyres": ["C1", "C2", "C7"]}, {"ers": {"HarvestLimitMGUK": -1}},
    {"ers": {"HarvestLimitMGUK": float("nan")}}, {"ers": {"HarvestLimitMGUK": True}},
    {"ers": {"unknown": 3}}, {"ers": {"HarvestLimitMGUK": 1_000_000_001}}])
def test_invalid_project_values_rejected(value):
    with pytest.raises(ValueError):
        rennparameter.validate(value)


@pytest.mark.parametrize("generated", [None, {"overrides": [
    {"path": "TyreData_0.compound_harder", "value": "C1"},
    {"path": "TrackGeneralData_0.number_of_laps", "value": "65,65,65"}], "track_overrides": []}])
def test_manual_export_survives_activation_template_replacement(generated):
    before = copy.deepcopy(generated)
    manifest = {"track_code": "portimao", "ers": {"HotLapDeployFactor": 0.7}}
    extra = rennparameter.apply(manifest, generated, {"tyres": ["C2", "C3", "C4"],
        "ers": {"HarvestLimitMGUK": 9000000, "HarvestLimitQualifyingMGUK": 7500000}})
    assert generated == before
    result = streckencode.manifest_umbenennen(manifest, streckencode.Umbenennung("portimao", "sochi"),
                                              aktivierung_vorlage="portimao", zusatz=extra)
    tyres = [v for v in result["activation"]["overrides"] if v["path"].startswith("TyreData_0.")]
    assert [t["value"] for t in tyres] == ["C2", "C3", "C4"]
    assert all(t["datasets"] == rennparameter.DATASETS for t in tyres)
    assert result["ers"] == {"HotLapDeployFactor": 0.7, "HarvestLimitMGUK": 9000000,
                             "HarvestLimitQualifyingMGUK": 7500000}


def test_inherit_has_no_effect():
    manifest = {"ers": {"HarvestLimitMGUK": 7000000}}
    before = copy.deepcopy(manifest)
    assert rennparameter.apply(manifest, None, {}) == {"overrides": [], "track_overrides": []}
    assert manifest == before


def test_project_menu_opens_panel(app, monkeypatch):
    from mapeditor.window import MainWindow
    from mapeditor.i18n import tr
    from PySide6.QtGui import QAction
    window = MainWindow(Project())
    opened = []
    monkeypatch.setattr(RaceParametersDialog, "exec", lambda self: opened.append(self.document))
    action = next(a for a in window.findChildren(QAction) if a.text() == tr("Track race parameters …"))
    action.trigger()
    assert opened == [window.document]


def test_cli_loads_project_parameters_and_rejects_invalid_values(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("race_build_tool", ROOT / "ego-werkzeuge/neue_strecke_tool.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    project = Project(manifest={"schema": 1, "definition": "definition.json", "runde_geschlossen": True,
                               "race_parameters": {"ers": {"HarvestLimitMGUK": 7500000}}})
    project.save(tmp_path)
    args = tool.argumente(["bauen", "--projekt", str(tmp_path), "--ausgabe", str(tmp_path / "build")])
    assert args.race_parameters == project.manifest["race_parameters"]
    project.manifest["race_parameters"] = {"ers": {"HarvestLimitMGUK": -1}}
    project.save()
    with pytest.raises(tool.BauFehler):
        tool.argumente(["bauen", "--projekt", str(tmp_path)])
