import sys
import numpy as np
import pytest
from conftest import ROOT

sys.path.insert(0,str(ROOT/'ego-werkzeuge'))
from strecke import large_world
from ego.grafik_terrain import _huelle


def test_bounds_use_world_coordinates_with_margin():
    points=np.array([[-1400,30,-2700],[1400,80,2700]],float)
    target=large_world.bounds(points)
    assert target['kante']==5888
    assert target==large_world.bounds(points[:,(0,2)])
    assert target['x0']<points[:,0].min()-100
    assert target['z0']+target['kante']>points[:,2].max()+100
    assert np.array_equal(points,[[-1400,30,-2700],[1400,80,2700]])


def test_expansion_is_explicit_and_rejects_invalid_geometry():
    assert not large_world.enabled({})
    assert not large_world.enabled({'large_world':False})
    assert large_world.enabled({'large_world':True})
    for points in ([],[[0,0,float('nan')]],[[0,0,0],[0,0,20000]]):
        with pytest.raises(ValueError):large_world.bounds(points)


def test_large_coordinate_sphere_contains_serialized_vertices():
    points=np.array([[10000,0,0],[10001.001,1,1],[10000,1,0]],dtype='<f4')
    node=np.asarray(_huelle(points))
    assert (np.linalg.norm(points.astype(float)-node[:3],axis=1)<=node[3]).all()


def test_panel_preserves_opt_in_and_undo(app):
    from mapeditor.document import Document
    from mapeditor.project import Project
    from mapeditor.race_parameters import RaceParametersDialog
    doc=Document(Project())
    dialog=RaceParametersDialog(doc)
    assert not dialog.large_world.isChecked()
    dialog.large_world.setChecked(True)
    dialog.accept()
    assert doc.project.raw['large_world'] is True
    assert 'large_world' not in doc.project.manifest
    doc.undo.undo()
    assert 'large_world' not in doc.project.raw


def test_carrier_grid_does_not_grow_with_extent():
    from types import SimpleNamespace
    reference=SimpleNamespace(knoten_zuordnung=[(1,0,0,(15<<16)|15)])
    positions=np.array([[-40000,0,-40000],[40000,0,-40000],[40000,0,40000],[-40000,0,40000]],dtype='<f4')
    mesh=SimpleNamespace(positionen=positions,dreiecke=np.array([[0,1,2],[0,2,3]]))
    raster=large_world.carrier_raster(reference,[mesh])
    assert raster.anzahl==(16,16)
    assert raster.minimum==(-40000,-40000)
    assert raster.maximum==(40000,40000)
    codes=raster.zellen(positions,mesh.dreiecke)
    assert (codes&0xffff).max()<16 and (codes>>16).max()<16
