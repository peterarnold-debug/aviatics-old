"""
Wings-Academy-Logo als mehrfarbiges 3D-Modell fuer den Bambu Lab A1 Mini.

Das Vektor-Logo (EPS) wird hochaufgeloest gerendert, nach den drei Farben
(schwarz / blau / rot) getrennt, vektorisiert und je Farbe als eigenes,
10 mm dickes STL exportiert. Im Slicer die drei Teile per "Assemble"
zusammenfuegen und jeweils ein Filament (schwarz/blau/rot) zuweisen.

Es gibt KEINE Traegerplatte -- nur die Buchstaben/Formen selbst.

Voraussetzungen:  ghostscript (gs) + pip-Pakete aus requirements.txt
Ausfuehren:       python src/wings_logo.py
"""

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy.sparse.csgraph import minimum_spanning_tree
from shapely.affinity import scale as shp_scale
from shapely.affinity import translate as shp_translate
from shapely.geometry import LineString, Polygon
from shapely.ops import nearest_points, unary_union

# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SRC_EPS = ROOT / "assets" / "wingsacademy_logo.eps"
OUT_DIR = ROOT / "output"

THICKNESS_MM = 3.0         # Extrusionsdicke (flaches Relief)
TARGET_WIDTH_MM = 142.0    # Logobreite in der Ebene (~Originalmass, < 180 mm)
RENDER_DPI = 1200          # Aufloesung des Zwischen-Renders (glatte Kanten)
SIMPLIFY_PX = 1.2          # Kontur-Vereinfachung in Pixeln
BRIDGE_W = 1.6             # Breite der Verbindungsstege (mm)

# Referenzfarben (aus der Bildanalyse)
COLORS = {
    "black": (35, 31, 32),
    "blue": (1, 84, 166),
    "red": (182, 29, 34),
}
WHITE = (255, 255, 255)


# ---------------------------------------------------------------------------
def render_eps(dpi):
    """EPS -> hochaufgeloestes RGB-Bild (numpy)."""
    tmp = Path(tempfile.mkdtemp()) / "logo.png"
    subprocess.run(
        ["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dEPSCrop",
         "-sDEVICE=png16m", f"-r{dpi}",
         "-dGraphicsAlphaBits=4", "-dTextAlphaBits=4",
         "-o", str(tmp), str(SRC_EPS)],
        check=True,
    )
    return np.asarray(Image.open(tmp).convert("RGB"))


def classify(img):
    """Jedes Pixel der naechsten Referenzfarbe (inkl. Weiss) zuordnen."""
    refs = np.array([WHITE] + list(COLORS.values()), dtype=np.float32)
    names = ["white"] + list(COLORS.keys())
    flat = img.reshape(-1, 3).astype(np.float32)
    d = ((flat[:, None, :] - refs[None, :, :]) ** 2).sum(axis=2)
    lab = d.argmin(axis=1).reshape(img.shape[:2])
    return {names[i]: (lab == i).astype(np.uint8) * 255 for i in range(len(names))}


def mask_to_polygons(mask, H):
    """Binaermaske -> Liste shapely-Polygone (mit Loechern), in Pixel-Koords
    (y nach oben gespiegelt)."""
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return []
    hier = hier[0]

    def ring(contour):
        c = cv2.approxPolyDP(contour, SIMPLIFY_PX, True).reshape(-1, 2)
        return [(float(x), float(H - y)) for x, y in c] if len(c) >= 3 else None

    polys = []
    for i, c in enumerate(cnts):
        if hier[i][3] != -1:        # nur aeussere Konturen
            continue
        shell = ring(c)
        if shell is None:
            continue
        holes = []
        j = hier[i][2]              # erstes Kind (Loch)
        while j != -1:
            h = ring(cnts[j])
            if h is not None:
                holes.append(h)
            j = hier[j][0]          # naechstes Geschwister
        p = Polygon(shell, holes)
        if not p.is_valid:
            p = p.buffer(0)
        if not p.is_empty and p.area > 1.0:
            polys.append(p)
    return polys


def extrude(multipoly, height):
    """(Multi)Polygon -> 3D-Mesh (mit Loechern)."""
    geoms = getattr(multipoly, "geoms", [multipoly])
    meshes = [trimesh.creation.extrude_polygon(g, height=height)
              for g in geoms if g.area > 0]
    return trimesh.util.concatenate(meshes)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = render_eps(RENDER_DPI)
    H, W = img.shape[:2]
    masks = classify(img)

    # Pixel-Polygone je Farbe
    raw = {c: unary_union(mask_to_polygons(masks[c], H)) for c in COLORS}

    # gemeinsamer Massstab + Zentrierung (alle Farben identisch transformiert)
    s = TARGET_WIDTH_MM / W
    union_all = unary_union([g for g in raw.values() if not g.is_empty])
    minx, miny, maxx, maxy = union_all.bounds
    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0

    def to_mm(geom):
        g = shp_scale(geom, xfact=s, yfact=s, origin=(0, 0))
        return shp_translate(g, xoff=-cx * s, yoff=-cy * s)

    geom = {c: to_mm(raw[c]) for c in COLORS}
    bridges = add_bridges(geom)

    print(f"Render {W}x{H}px  ->  Logo {W*s:.1f} x {H*s:.1f} mm, Dicke {THICKNESS_MM} mm")
    print(f"{sum(bridges.values())} Verbindungsstege ({BRIDGE_W} mm) eingefuegt\n")
    for color in COLORS:
        g = geom[color]
        if g.is_empty:
            print(f"  {color:6s}: leer, uebersprungen")
            continue
        mesh = extrude(g, THICKNESS_MM)
        out = OUT_DIR / f"wings_logo_{color}.stl"
        mesh.export(out)
        b = mesh.bounds
        size = (b[1] - b[0]).round(1)
        n_solids = len(mesh.split(only_watertight=False))
        print(f"  {color:6s}: {out.name:22s} {size.tolist()} mm, "
              f"{len(mesh.faces)} Faces, {n_solids} Teil(e)")

    print("\nFertig. Dateien in:", OUT_DIR)


def add_bridges(geom):
    """Verbindet alle losen Teile (ueber alle Farben) mit duennen Stegen zu
    EINEM zusammenhaengenden Objekt. Aendert `geom` in place; gibt die Anzahl
    der Stege je Farbe zurueck.

    Minimaler Spannbaum ueber alle Einzelteile -> kuerzeste Gesamt-StegLaenge.
    Jeder Steg bekommt die Farbe des flaechengroesseren der beiden Teile.
    """
    pieces = []  # (color, polygon)
    for c in COLORS:
        for poly in getattr(geom[c], "geoms", [geom[c]] if not geom[c].is_empty else []):
            pieces.append((c, poly))
    n = len(pieces)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dist[i, j] = pieces[i][1].distance(pieces[j][1])
    mst = minimum_spanning_tree(dist).toarray()

    new_bars = {c: [] for c in COLORS}
    counts = {c: 0 for c in COLORS}
    for i in range(n):
        for j in range(n):
            if mst[i, j] <= 0:
                continue
            (ca, pa), (cb, pb) = pieces[i], pieces[j]
            qa, qb = nearest_points(pa, pb)
            if qa.distance(qb) < 1e-6:
                continue                      # beruehren sich bereits
            bar = LineString([qa, qb]).buffer(BRIDGE_W / 2, cap_style=3)
            col = ca if pa.area >= pb.area else cb
            new_bars[col].append(bar)
            counts[col] += 1
    for c in COLORS:
        if new_bars[c]:
            geom[c] = unary_union([geom[c], *new_bars[c]])
    return counts


if __name__ == "__main__":
    main()
