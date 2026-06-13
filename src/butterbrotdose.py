"""
Butterbrotdose (Schueler-Lunchbox) mit stilisiertem BVB-Emblem.

Parametrisches 3D-Modell fuer den Bambu Lab A1 Mini (Bauraum 180x180x180 mm).
Erzeugt druckfertige STL- und STEP-Dateien fuer:

  * den Behaelter (box)
  * den uebergreifenden Deckel / die Kappe (lid)
  * zwei flaechenbuendige Logo-Inlays fuer den Zweifarbdruck:
      - logo_bg  : gelber Hintergrund-Kreis
      - logo_fg  : schwarzer Ring + Schriftzug "BVB 09"

Die drei Deckel-Teile (lid, logo_bg, logo_fg) sind passgenau und ueberlappungs-
frei modelliert: Im Slicer (Bambu Studio / Orca) laedt man sie als EIN Objekt
("assemble") und weist jedem Teil eine Farbe zu. Da das Logo auf der beim Druck
unten liegenden Deckelflaeche sitzt, wird es glatt und kontrastreich.

Hinweis Markenrecht: Das BVB-Emblem ist hier stilisiert nachempfunden und nur
fuer den privaten Gebrauch gedacht. Das offizielle Logo ist eine eingetragene
Marke; kein Verkauf / Vertrieb.

Ausfuehren:
    pip install -r requirements.txt
    python src/butterbrotdose.py
"""

from pathlib import Path

from build123d import (
    Align,
    Axis,
    BuildPart,
    BuildSketch,
    Circle,
    FontStyle,
    Locations,
    Mode,
    Plane,
    RectangleRounded,
    Text,
    add,
    export_step,
    export_stl,
    extrude,
    mirror,
    offset,
)

# ---------------------------------------------------------------------------
# Parameter  (alle Masse in mm) -- hier anpassen
# ---------------------------------------------------------------------------

# --- Behaelter (Aussenmasse) -- Schueler-Brotdose fuer 1-2 belegte Brote -----
BOX_L = 165.0          # Laenge
BOX_W = 118.0          # Breite
BOX_H = 65.0           # Hoehe
WALL = 2.4             # Wandstaerke (= Bodenstaerke)
CORNER_R = 4.0         # Aussen-Eckenradius (vertikale Kanten)

# --- Deckel als uebergreifende Kappe ----------------------------------------
CLEAR = 0.40           # Spiel zwischen Kappen-Innenwand und Box-Aussenwand
CAP_WALL = 2.4         # Wandstaerke der Kappe
CAP_TOP = 2.4          # Dicke der Deckelplatte
CAP_RIM_H = 14.0       # Hoehe des umlaufenden Kappenrands (greift ueber die Box)

# --- Logo (flaechenbuendiges Zweifarb-Inlay auf der Deckelplatte) ------------
LOGO_R = 34.0          # Radius des Emblems
INLAY_H = 0.8          # Tiefe/Hoehe des Inlays (= 4 Lagen bei 0.2 mm)
RING_W = 3.5           # Breite des schwarzen Aussenrings
FONT = "DejaVu Sans"
TXT_BOT = "09"         # kleiner Schriftzug
FS_TOP = 24.0          # Schriftgroesse "B" / "V" / "B"
FS_BOT = 13.0          # Schriftgroesse "09"
TXT_TOP_Y = 4.0        # vertikale Lage der beiden "B"
TXT_BOT_Y = -15.0      # vertikale Lage "09"
LETTER_DX = 13.5       # horizontaler Abstand der "B" von der Mitte
V_RISE = 12.0          # das mittlere "V" nach oben versetzt (~50% Zeilenhoehe)

OUT_DIR = Path(__file__).resolve().parent.parent / "output"

# ---------------------------------------------------------------------------
# Abgeleitete Masse
# ---------------------------------------------------------------------------
CAP_IN_L = BOX_L + 2 * CLEAR                 # lichte Kappenweite
CAP_IN_W = BOX_W + 2 * CLEAR
CAP_OUT_L = CAP_IN_L + 2 * CAP_WALL          # Kappen-Aussenmass
CAP_OUT_W = CAP_IN_W + 2 * CAP_WALL
CAP_OUT_R = CORNER_R + CAP_WALL              # Aussen-Eckenradius der Kappe
CAP_IN_R = max(CORNER_R, 1.0)                # Innen-Eckenradius der Kappe


# ---------------------------------------------------------------------------
# Bauteile
# ---------------------------------------------------------------------------
def make_box():
    """Oben offener Behaelter, Boden auf z=0 (Druckorientierung: offen nach oben)."""
    with BuildPart() as box:
        with BuildSketch(Plane.XY):
            RectangleRounded(BOX_L, BOX_W, CORNER_R)
        extrude(amount=BOX_H)
        top_face = box.faces().sort_by(Axis.Z)[-1]
        offset(amount=-WALL, openings=top_face)
    return box.part


def _logo_fg_sketch():
    """Sketch des Vordergrunds: Aussenring + Schriftzug 'BVB' / '09'."""
    with BuildSketch(Plane.XY) as fg:
        # Aussenring
        Circle(LOGO_R)
        Circle(LOGO_R - RING_W, mode=Mode.SUBTRACT)
        # Schriftzug "B V B" -- das mittlere V ist nach oben versetzt
        # (wie im echten BVB-Emblem)
        bold = dict(font=FONT, font_style=FontStyle.BOLD,
                    align=(Align.CENTER, Align.CENTER))
        with Locations((-LETTER_DX, TXT_TOP_Y)):
            Text("B", font_size=FS_TOP, **bold)
        with Locations((0, TXT_TOP_Y + V_RISE)):
            Text("V", font_size=FS_TOP, **bold)
        with Locations((LETTER_DX, TXT_TOP_Y)):
            Text("B", font_size=FS_TOP, **bold)
        with Locations((0, TXT_BOT_Y)):
            Text(TXT_BOT, font_size=FS_BOT, font=FONT, font_style=FontStyle.BOLD,
                 align=(Align.CENTER, Align.CENTER))
        # Das Logo sitzt auf der beim Druck UNTEN liegenden Deckelflaeche.
        # Damit es nach dem Wenden des Deckels seitenrichtig lesbar ist, wird
        # es hier horizontal gespiegelt (x -> -x).
        mirror(about=Plane.YZ, mode=Mode.REPLACE)
    return fg.sketch


def make_logo_fg():
    """Schwarzes Inlay (Ring + Schrift), fuellt z = 0 .. INLAY_H."""
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            add(_logo_fg_sketch())
        extrude(amount=INLAY_H)
    return part.part


def make_logo_bg():
    """Gelbes Inlay (Kreis minus Vordergrund), fuellt z = 0 .. INLAY_H."""
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            Circle(LOGO_R)
            add(_logo_fg_sketch(), mode=Mode.SUBTRACT)
        extrude(amount=INLAY_H)
    return part.part


def make_lid():
    """Uebergreif-Kappe in Druckorientierung: Platte auf z=0, Rand nach oben.

    In die beim Druck unten liegende Platte ist eine kreisrunde Tasche
    (Tiefe INLAY_H) gefraest, die von logo_bg + logo_fg exakt gefuellt wird.
    """
    with BuildPart() as lid:
        # Deckelplatte  (z = 0 .. CAP_TOP)
        with BuildSketch(Plane.XY):
            RectangleRounded(CAP_OUT_L, CAP_OUT_W, CAP_OUT_R)
        extrude(amount=CAP_TOP)
        # umlaufender Rand nach oben  (z = CAP_TOP .. CAP_TOP + CAP_RIM_H)
        with BuildSketch(Plane.XY.offset(CAP_TOP)):
            RectangleRounded(CAP_OUT_L, CAP_OUT_W, CAP_OUT_R)
            RectangleRounded(CAP_IN_L, CAP_IN_W, CAP_IN_R, mode=Mode.SUBTRACT)
        extrude(amount=CAP_RIM_H)
        # Logo-Tasche in die Plattenunterseite fraesen  (z = 0 .. INLAY_H)
        with BuildSketch(Plane.XY):
            Circle(LOGO_R)
        extrude(amount=INLAY_H, mode=Mode.SUBTRACT)
    return lid.part


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    parts = {
        "butterdose_box": make_box(),
        "butterdose_lid": make_lid(),
        "butterdose_logo_bg": make_logo_bg(),
        "butterdose_logo_fg": make_logo_fg(),
    }

    for name, part in parts.items():
        stl_path = OUT_DIR / f"{name}.stl"
        export_stl(part, str(stl_path))
        bb = part.bounding_box()
        size = bb.size
        print(f"{name:22s} -> {stl_path.name:28s} "
              f"({size.X:6.1f} x {size.Y:6.1f} x {size.Z:6.1f} mm)")

    # STEP nur fuer die beiden Hauptteile (parametrisch weiterverwendbar)
    export_step(parts["butterdose_box"], str(OUT_DIR / "butterdose_box.step"))
    export_step(parts["butterdose_lid"], str(OUT_DIR / "butterdose_lid.step"))

    print("\nFertig. Dateien liegen in:", OUT_DIR)


if __name__ == "__main__":
    main()
