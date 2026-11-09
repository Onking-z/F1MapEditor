"""Track CSV v1: explicit generator-supported information, TUM plane axes."""
import csv
import math
from pathlib import Path
import numpy as np
from . import definition, mittellinie

REQUIRED = ('x_m','y_m','w_tr_left_m','w_tr_right_m')
POINT = {'height_m':'y','bank_deg':'querneigung_grad'}
SIDE = {'kerb_{}_width_m':'randstein_breite','verge_{}_width_m':'gruenstreifen_breite',
        'runoff_{}':'auslauf','side_{}_slope_deg':'rand_neigung','wall_{}_distance_m':'barriere_abstand'}
GLOBAL = {'wall_height_m':('barriere','hoehe'),'wall_thickness_m':('barriere','dicke'),
          'edge_line_width_m':('fahrbahn','randlinie_breite')}
ALLOWED = set(REQUIRED)|set(POINT)|set(GLOBAL)|{key.format(side) for key in SIDE for side in ('left','right')}


def load(path):
    """Strict CSV. Blank optional cells mean generator defaults, not carry-forward.
    Side values hold until next sample. Stations use the actual spline arc length.
    """
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        lines=[line for line in stream if line.strip() and not line.lstrip().startswith('#')]
    reader=csv.DictReader(lines)
    header=reader.fieldnames or []
    if len(set(header))!=len(header) or not set(REQUIRED)<=set(header) or set(header)-ALLOWED:
        raise ValueError('Track CSV: missing, duplicate or unsupported columns')
    rows=list(reader)
    if len(rows)<8:
        raise ValueError('Track CSV needs at least 8 samples')
    values=[]
    for index,row in enumerate(rows,2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError('Track CSV: inconsistent row length at row %d' % index)
        parsed={}
        for key,text in row.items():
            text=text.strip()
            if not text:
                if key in REQUIRED: raise ValueError('Track CSV: empty required cell at row %d' % index)
                continue
            if key.startswith('runoff_'):
                if text not in ('grass','gravel','asphalt'): raise ValueError('Track CSV: invalid runoff type at row %d' % index)
                parsed[key]={'grass':'gras','gravel':'kies','asphalt':'asphalt'}[text]
                continue
            number=float(text)
            if not math.isfinite(number): raise ValueError('Track CSV: non-finite value at row %d' % index)
            if key.startswith('w_tr_') and number<=0: raise ValueError('Track CSV: track half-width must be positive')
            if ('width_m' in key or key in ('wall_height_m','wall_thickness_m')) and number<0:
                raise ValueError('Track CSV: widths and wall dimensions cannot be negative')
            if key.startswith('wall_') and key.endswith('_distance_m') and number<.5:
                raise ValueError('Track CSV: wall distance must be at least 0.5 m')
            if key=='bank_deg' and abs(number)>=80: raise ValueError('Track CSV: bank angle must be below 80 degrees')
            parsed[key]=number
        values.append(parsed)
    # A repeated closing sample must agree completely; do not discard metadata.
    if all(values[0][k]==values[-1][k] for k in ('x_m','y_m')):
        if values[0]!=values[-1]: raise ValueError('Track CSV: closing sample differs from first sample')
        values.pop()
    if len(values)<8: raise ValueError('Track CSV needs at least 8 samples')
    points=[]
    for v in values:
        p=dict(x=v['x_m'],z=-v['y_m'],y=v.get('height_m',0),
               breite_links=v['w_tr_left_m'],breite_rechts=v['w_tr_right_m'])
        if 'bank_deg' in v:p['querneigung_grad']=v['bank_deg']
        points.append(p)
    raw=dict(name=Path(path).stem,mittellinie=dict(art='kontrollpunkte',punkte=points,
             approximation_m=0,hoehen_glaettung_m=0,glaettung_m=0))
    for key,(group,field) in GLOBAL.items():
        entries=[v[key] for v in values if key in v]
        if entries:
            if any(n!=entries[0] for n in entries): raise ValueError('Track CSV: global setting varies: %s' % key)
            raw.setdefault(group,{})[field]=entries[0]
    # Reject consecutive duplicate positions instead of silently losing rows.
    xz=np.array([[p['x'],p['z']] for p in points])
    if np.any(np.linalg.norm(np.roll(xz,-1,axis=0)-xz,axis=1)<1e-6):
        raise ValueError('Track CSV: adjacent samples have duplicate planar positions')
    ml=mittellinie.Mittellinie(definition.aus_dict(raw))
    sections=[]
    for i,v in enumerate(values):
        for side,german in (('left','links'),('right','rechts')):
            fields={field:v[key.format(side)] for key,field in SIDE.items() if key.format(side) in v}
            if fields:
                sections.append(dict(von_s=float(ml.s_eingabe[i]),
                    bis_s=float(ml.s_eingabe[i+1]) if i+1<len(values) else float(ml.laenge-1e-7),
                    seite=german,**fields))
    raw['seitenraum']={'abschnitte':sections}
    definition.aus_dict(raw)  # Validate side slopes and all global parameters too.
    raw['editor_import']=dict(schema='track-csv/1',art='track_csv',datei=Path(path).name,
        laenge_m=float(ml.laenge),punkte=len(points),massstab=1,versatz_m=[0,0,0],
        warnungen=['Track CSV preserves samples; the generator may smooth side areas and move walls to avoid overlaps.'])
    return raw
