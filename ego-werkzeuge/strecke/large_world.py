"""Experimental opt-in carrier terrain expansion. Does not rescale the track."""
import math
import numpy as np


def enabled(parameters):
    return parameters.get('large_world') is True


def carrier_raster(reference, meshes):
    """Keep the carrier grid dimensions instead of allocating one node per 100 m.

    Large outer scenery spans tens of kilometres. A fixed metric tile size
    created 150778 render nodes for Le Mans (the carrier had only 256).
    Reusing the carrier's grid count bounds node allocations independently of
    physical extent. Vertex/index buffers still use the writer's u16 splitting.
    """
    from ego.grafik_terrain import TerrainRaster
    if not reference.knoten_zuordnung:
        raise ValueError('Carrier terrain has no grid reference')
    shape=(max(q[3]&0xffff for q in reference.knoten_zuordnung)+1,
           max(q[3]>>16 for q in reference.knoten_zuordnung)+1)
    if max(shape)>32:
        raise ValueError('Carrier terrain grid exceeds the supported reference size')
    used=[np.asarray(mesh.positionen,dtype='<f4')[np.unique(mesh.dreiecke)][:,(0,2)] for mesh in meshes]
    minimum=np.min([p.min(0) for p in used],axis=0)
    maximum=np.max([p.max(0) for p in used],axis=0)
    return TerrainRaster(tuple(map(float,minimum)),tuple(map(float,maximum)),shape)


def bounds(positions, margin=128.0):
    p = np.asarray(positions, dtype=float)
    if p.ndim != 2 or p.shape[1] not in (2,3) or not len(p) or not np.isfinite(p).all():
        raise ValueError('Invalid large-world geometry')
    ground=p[:,(0,2)] if p.shape[1]==3 else p
    lo, hi = ground.min(0), ground.max(0)
    edge = max(2048.0, math.ceil((float(max(hi-lo))+2*margin)/256)*256.0)
    if edge > 16384:
        raise ValueError('Experimental terrain extent exceeds 16 km')
    center = (lo+hi)/2
    return dict(x0=float(center[0]-edge/2), z0=float(center[1]-edge/2), kante=edge)


def expand(archive, target):
    from ego import grafik_terrain as gt, grafik
    from . import spiel_geometrie as geo
    old = geo.loch_lesen(archive)
    if old['ersatz'] or not len(old['rand']):
        raise ValueError('Cannot expand terrain without verified carrier hole geometry')
    meshes = gt.terrain_lesen(archive, geo.AUSSEN)
    reference=grafik.Terrain.aus_bytes(archive.find(geo.AUSSEN).data())
    factor = target['kante']/old['kante']
    old_center=np.array([old['x0']+old['kante']/2,old['z0']+old['kante']/2])
    new_center=np.array([target['x0']+target['kante']/2,target['z0']+target['kante']/2])
    def transform(p):
        p=np.array(p,dtype=float,copy=True)
        p[:,(0,2)]=(p[:,(0,2)]-old_center)*factor+new_center
        return p
    for mesh in meshes:
        mesh.positionen=transform(mesh.positionen).astype('<f4')
        mesh.normalen=None
        mesh.tangenten=None
    raster=carrier_raster(reference,meshes)
    report=gt.terrain_erzeugen(archive,geo.AUSSEN,meshes,raster=raster)
    hole=dict(target,rand=transform(old['rand']),ersatz=False)
    return hole,dict(enabled=True,experimental=True,scale_outer_only=factor,
                     old_hole={k:old[k] for k in ('x0','z0','kante')},
                     new_hole=target,resources=report['ressourcen'],raster_shape=list(raster.anzahl),
                     old_nodes=len(reference.knoten),new_nodes=report['knoten'],new_draws=report['zeichnungen'])
