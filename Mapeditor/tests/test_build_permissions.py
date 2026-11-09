import sys
from pathlib import Path
import importlib.util
from conftest import ROOT
from mapeditor.project import Project
from mapeditor.build import build_folders, probe_build_folder


def test_unsaved_build_uses_local_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert build_folders(Project()) == (tmp_path/'Mapeditor/bauten',tmp_path/'Mapeditor/pakete')


def test_write_probe_cleans_up(tmp_path):
    folder=tmp_path/'build'
    probe_build_folder(folder)
    assert folder.is_dir() and list(folder.iterdir())==[]


def test_snapshot_permission_denied_is_json_error(tmp_path,monkeypatch,capsys):
    sys.path.insert(0,str(ROOT/'ego-werkzeuge'))
    spec=importlib.util.spec_from_file_location('permission_build_tool',ROOT/'ego-werkzeuge/neue_strecke_tool.py')
    tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    def denied(*args,**kwargs):raise PermissionError('blocked output')
    monkeypatch.setattr(tool,'schnappschuss',denied)
    assert tool.main(['bauen','--ereignisse-json','--definition',str(ROOT/'ego-werkzeuge/strecke/beispiele/teststrecke.json'),
                      '--ausgabe',str(tmp_path/'output')]) != 0
    import json
    error=json.loads(capsys.readouterr().out)
    assert error['typ']=='fehler' and 'blocked output' in error['text']
