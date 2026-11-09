import csv,math,sys
import numpy as np
import pytest
from conftest import ROOT
sys.path.insert(0,str(ROOT/'ego-werkzeuge'))
from strecke.track_csv import load
from strecke import definition,mittellinie,querprofil

def sample(path,**changes):
    rows=[]
    for i in range(16):
        a=2*math.pi*i/16
        rows.append(dict(x_m=300*math.cos(a),y_m=300*math.sin(a),height_m=20+2*math.sin(a),
            w_tr_left_m=7,w_tr_right_m=6,bank_deg=3,kerb_left_width_m=1.2,
            wall_left_distance_m=25,runoff_left='gravel',wall_height_m=1.4,**changes))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

def test_geometry_and_sides_reach_generator(tmp_path):
    path=tmp_path/'test.track.csv';sample(path)
    raw=load(path); p=raw['mittellinie']['punkte'][4]
    assert p['y']==22 and p['z']==-300 and p['querneigung_grad']==3
    assert p['breite_links']==7 and p['breite_rechts']==6
    assert raw['barriere']['hoehe']==1.4
    ml=mittellinie.Mittellinie(definition.aus_dict(raw))
    profile=querprofil.querprofil_berechnen(ml,definition.aus_dict(raw).param,[])
    assert raw['seitenraum']['abschnitte'][0]['barriere_abstand']==25
    assert raw['seitenraum']['abschnitte'][0]['auslauf']=='kies'
    assert len(raw['mittellinie']['punkte'])==16
    assert len(raw['seitenraum']['abschnitte'])==16
    assert np.ptp(ml.ref.pos[:,1])>3.9

def test_unknown_fields_and_nonfinite_fail(tmp_path):
    path=tmp_path/'bad.csv';sample(path,wall_type='concrete')
    with pytest.raises(ValueError,match='unsupported'): load(path)
    sample(path)
    path.write_text(path.read_text().replace('1.4','nan'))
    with pytest.raises(ValueError,match='non-finite'): load(path)

def test_global_values_may_not_silently_vary(tmp_path):
    path=tmp_path/'bad.csv';sample(path)
    text=path.read_text();path.write_text(text.replace('1.4','1.5',1))
    with pytest.raises(ValueError,match='global'): load(path)

def test_worker_import_and_ui_entry(app,tmp_path):
    from mapeditor.adapter import run_task
    from mapeditor.templates import TemplateDialog
    path=tmp_path/'input.track.csv';sample(path)
    result=run_task(dict(task='import',kind='track_csv',path=str(path)))
    assert result['manifest']['versatz']==[0,0,0]
    assert result['raw']['mittellinie']['punkte'][4]['y']==22
    assert result['raw']['seitenraum']['abschnitte'][0]['barriere_abstand']==25
    dialog=TemplateDialog()
    dialog.kind.setCurrentIndex(dialog.kind.findData('track_csv'))
    assert dialog.spacing.isHidden() and dialog.fit.isHidden()
