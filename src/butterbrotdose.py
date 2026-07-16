"""
Butterbrotdose (Schueler-Lunchbox) mit BVB-Emblem und Klappdeckel.

Parametrisches 3D-Modell fuer den Bambu Lab A1 Mini (Bauraum 180x180x180 mm).

Der Deckel ist hinten ueber ein **Einrast-Scharnier** an der Box befestigt:
  * Am Deckel sitzen seitliche Zapfen, die in offene C-Clips (Cradles) hinten
    an der Box von oben einrasten. Die Clip-Maeuler sind enger als der Zapfen
    (Schnappsitz) -> der Deckel haelt sicher, laesst sich aber durch kraeftiges
    Hochziehen bewusst herausnehmen (Verlustsicherung am Scharnier).
  * Vorne haelt ein **Schnappverschluss** (Haken am Deckel greift unter eine
    Nase an der Box) den Deckel zu.

Erzeugte Teile:
  * butterdose_box      : Behaelter mit Scharnier-Clips + Verschlussnase
  * butterdose_lid      : Klappdeckel mit Zapfen + Fronthaken (+ Logo-Tasche)
  * butterdose_logo_bg  : gelbes Inlay (Hintergrund-Kreis)
  * butterdose_logo_fg  : schwarzes Inlay (Ring + Schriftzug "BVB 09")

Der Deckel und die Logo-Inlays werden in GEBRAUCHSLAGE modelliert (Logo oben)
und beim STL/STEP-Export fuer den Druck gewendet, sodass das Logo auf der
glatten Druckbett-Seite liegt. Im Slicer die drei Deckel-Teile per "Assemble"
zusammenfuegen und einfaerben (Deckel/Logo).

Hinweis Markenrecht: Das BVB-Emblem ist stilisiert nachempfunden, nur fuer den
privaten Gebrauch. Kein Verkauf / Vertrieb.

Ausfuehren:
    pip install -r requirements.txt
    python src/butterbrotdose.py
"""

from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    FontStyle,
    Locations,
    Mode,
    Plane,
    Pos,
    RectangleRounded,
    Rot,
    Text,
    add,
    export_step,
    export_stl,
    extrude,
    offset,
)

# ---------------------------------------------------------------------------
# Parameter  (alle Masse in mm) -- hier anpassen
# ---------------------------------------------------------------------------

# --- Behaelter (Aussenmasse) -- Schueler-Brotdose fuer 1-2 belegte Brote -----
BOX_L = 165.0          # Laenge (X)
BOX_W = 118.0          # Breite (Y);  +Y = hinten (Scharnier), -Y = vorne
BOX_H = 65.0           # Hoehe  (Z)
WALL = 2.4             # Wandstaerke (= Bodenstaerke)
CORNER_R = 4.0         # Aussen-Eckenradius (vertikale Kanten)

# --- Deckel ------------------------------------------------------------------
LID_T = 2.6            # Dicke der Deckelplatte (liegt auf dem Box-Rand auf)

# --- Scharnier (Einrast-Zapfen hinten) --------------------------------------
HINGE_PIN_D = 6.0      # Durchmesser der Deckelzapfen
HINGE_CLEAR = 0.40     # Spiel Zapfen <-> Clip-Bohrung
CRADLE_WALL = 2.8      # Wandstaerke der C-Clips
CRADLE_L = 10.0        # axiale Laenge (X) der C-Clips
ARM_W = 6.0            # Breite der Deckel-Scharnierarme (sitzen neben dem Clip)
HINGE_INSET = 20.0     # Abstand der Scharniere von den Box-Enden (X)
MOUTH_FACTOR = 0.80    # Maulbreite / Zapfen-D  (<1 => Schnappsitz/Sicherung)

# --- Frontverschluss (Schnapphaken) -----------------------------------------
LATCH_W = 30.0         # Breite des Verschlusses (X)
LATCH_PROT = 2.4       # wie weit die Box-Nase nach vorne (-Y) ragt
LATCH_BAR_H = 3.0      # Hoehe der Box-Nase
LATCH_CLEAR = 0.40     # Spiel Haken <-> Nase
SKIRT_T = 2.4          # Wandstaerke der Deckel-Frontlasche
CATCH_Z = BOX_H - 11.0 # Hoehe der Nasen-Unterkante (Eingriffshoehe)
HOOK_OVER = 1.4        # wie weit der Haken unter die Nase greift
HOOK_H = 2.6           # Hoehe des Hakens

# --- Logo (flaechenbuendiges Zweifarb-Inlay auf der Deckeloberseite) --------
LOGO_R = 34.0          # Radius des Emblems
INLAY_H = 0.8          # Tiefe/Hoehe des Inlays (= 4 Lagen bei 0.2 mm)
RING_W = 3.5           # Breite des schwarzen Aussenrings
FONT = "DejaVu Sans"
TXT_BOT = "09"
FS_TOP = 24.0          # Schriftgroesse der beiden "B"
FS_V = 21.6            # Schriftgroesse "V" (10% kleiner)
FS_BOT = 13.0          # Schriftgroesse "09"
TXT_TOP_Y = 4.0
TXT_BOT_Y = -15.0
LETTER_DX = 13.5
V_RISE = 10.8

OUT_DIR = Path(__file__).resolve().parent.parent / "output"

# ---------------------------------------------------------------------------
# Abgeleitete Masse
# ---------------------------------------------------------------------------
R_PIN = HINGE_PIN_D / 2.0
R_BORE = R_PIN + HINGE_CLEAR
R_OUT = R_BORE + CRADLE_WALL
MOUTH_W = MOUTH_FACTOR * HINGE_PIN_D

X_POST = BOX_L / 2.0 - HINGE_INSET           # X-Lage der beiden Scharniere
HINGE_Y = BOX_W / 2.0 + R_OUT + 0.5          # Y-Lage der Scharnierachse (hinten)
HINGE_Z = BOX_H                              # Achse auf Randhoehe
LID_TOP_Z = BOX_H + LID_T                    # Oberseite des Deckels (Logo)

REAR = BOX_W / 2.0                           # y der Hinterwand-Aussenflaeche
FRONT = -BOX_W / 2.0                         # y der Vorderwand-Aussenflaeche
SKIRT_OUT = -(BOX_W / 2.0) - LATCH_PROT - LATCH_CLEAR - SKIRT_T  # y Aussenkante Lasche


# ---------------------------------------------------------------------------
# Box (Behaelter + Scharnier-Clips + Verschlussnase)  -- Gebrauchslage
# ---------------------------------------------------------------------------
def _cradle(x):
    """Offener C-Clip (Maul nach oben) mit Stuetzsteg zur Hinterwand."""
    at = Pos(x, HINGE_Y, HINGE_Z) * Rot(0, 90, 0)
    # Stuetzsteg: verbindet die untere Clip-Haelfte mit der Hinterwand
    sy0, sy1 = REAR - WALL, HINGE_Y
    stem = Pos(x, (sy0 + sy1) / 2, (BOX_H - 12 + HINGE_Z) / 2) * Box(
        CRADLE_L, sy1 - sy0, HINGE_Z - (BOX_H - 12))
    # erst Vollmaterial (Ring + Steg), DANN Bohrung und Maul abziehen,
    # damit der Steg die Zapfenbohrung nicht zusetzt
    solid = at * Cylinder(R_OUT, CRADLE_L) + stem
    mouth = Pos(x, HINGE_Y, HINGE_Z + R_OUT) * Box(CRADLE_L + 2, MOUTH_W, 2 * R_OUT)
    return solid - at * Cylinder(R_BORE, CRADLE_L + 2) - mouth


def make_box():
    """Oben offener Behaelter mit Scharnier-Clips (hinten) und Nase (vorne)."""
    with BuildPart() as box:
        with BuildSketch(Plane.XY):
            RectangleRounded(BOX_L, BOX_W, CORNER_R)
        extrude(amount=BOX_H)
        top_face = box.faces().sort_by(Axis.Z)[-1]
        offset(amount=-WALL, openings=top_face)
    part = box.part
    # Scharnier-Clips hinten
    part = part + _cradle(+X_POST) + _cradle(-X_POST)
    # Verschlussnase vorne (Unterkante = CATCH_Z, ragt nach -Y)
    catch = Pos(0, FRONT - LATCH_PROT / 2, CATCH_Z + LATCH_BAR_H / 2) * Box(
        LATCH_W, LATCH_PROT, LATCH_BAR_H)
    return part + catch


# ---------------------------------------------------------------------------
# Logo  (in Gebrauchslage: oben auf dem Deckel, seitenrichtig)
# ---------------------------------------------------------------------------
def _logo_fg_sketch():
    """Sketch: Aussenring + 'B V B' (V erhoeht) + '09', auf Hoehe der Oberseite."""
    with BuildSketch(Plane.XY.offset(LID_TOP_Z)) as fg:
        Circle(LOGO_R)
        Circle(LOGO_R - RING_W, mode=Mode.SUBTRACT)
        bold = dict(font=FONT, font_style=FontStyle.BOLD,
                    align=(Align.CENTER, Align.CENTER))
        with Locations((-LETTER_DX, TXT_TOP_Y)):
            Text("B", font_size=FS_TOP, **bold)
        with Locations((0, TXT_TOP_Y + V_RISE)):
            Text("V", font_size=FS_V, **bold)
        with Locations((LETTER_DX, TXT_TOP_Y)):
            Text("B", font_size=FS_TOP, **bold)
        with Locations((0, TXT_BOT_Y)):
            Text(TXT_BOT, font_size=FS_BOT, **bold)
    return fg.sketch


def make_logo_fg():
    """Schwarzes Inlay (Ring + Schrift), fuellt z = LID_TOP_Z-INLAY .. LID_TOP_Z."""
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(LID_TOP_Z)):
            add(_logo_fg_sketch())
        extrude(amount=-INLAY_H)
    return part.part


def make_logo_bg():
    """Gelbes Inlay (Kreis minus Vordergrund)."""
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(LID_TOP_Z)):
            Circle(LOGO_R)
            add(_logo_fg_sketch(), mode=Mode.SUBTRACT)
        extrude(amount=-INLAY_H)
    return part.part


# ---------------------------------------------------------------------------
# Deckel (Klappdeckel + Zapfen + Fronthaken)  -- Gebrauchslage
# ---------------------------------------------------------------------------
def _pin_arm(x):
    """Scharnierzapfen am Deckel + Arm (sitzt INNEN neben dem Clip)."""
    sign = 1.0 if x > 0 else -1.0       # innen = Richtung Boxmitte
    x_out = x + sign * (CRADLE_L / 2 - 0.5)     # aeusseres Zapfenende (im Clip)
    x_in = x - sign * (CRADLE_L / 2 + ARM_W)    # inneres Zapfenende (am Arm)
    pin = Pos((x_out + x_in) / 2, HINGE_Y, HINGE_Z) * Rot(0, 90, 0) * Cylinder(
        R_PIN, abs(x_out - x_in))
    arm_x = x - sign * (CRADLE_L / 2 + ARM_W / 2)
    arm = Pos(arm_x, (REAR + HINGE_Y) / 2, (HINGE_Z + LID_TOP_Z) / 2) * Box(
        ARM_W, HINGE_Y - REAR, LID_TOP_Z - HINGE_Z)
    return pin + arm


def make_lid():
    """Klappdeckel in Gebrauchslage (Platte z=BOX_H..LID_TOP_Z, Logo oben)."""
    with BuildPart() as lid:
        with BuildSketch(Plane.XY.offset(BOX_H)):
            RectangleRounded(BOX_L, BOX_W, CORNER_R)
        extrude(amount=LID_T)
        # Logo-Tasche in die Oberseite
        with BuildSketch(Plane.XY.offset(LID_TOP_Z)):
            Circle(LOGO_R)
        extrude(amount=-INLAY_H, mode=Mode.SUBTRACT)
    part = lid.part
    # Scharnierzapfen + Arme hinten
    part = part + _pin_arm(+X_POST) + _pin_arm(-X_POST)
    # Frontlasche mit Schnapphaken
    #  - Lippe (verbindet Platte mit der Lasche, ragt nach vorne)
    lip = Pos(0, (FRONT + SKIRT_OUT) / 2, (BOX_H + LID_TOP_Z) / 2) * Box(
        LATCH_W, FRONT - SKIRT_OUT, LID_T)
    #  - senkrechte Lasche
    skirt_bottom = CATCH_Z - HOOK_H - 0.4
    skirt = Pos(0, SKIRT_OUT + SKIRT_T / 2, (skirt_bottom + BOX_H) / 2) * Box(
        LATCH_W, SKIRT_T, BOX_H - skirt_bottom)
    #  - Haken (nach innen +Y, greift unter die Nase)
    hook = Pos(0, SKIRT_OUT + SKIRT_T + HOOK_OVER / 2, skirt_bottom + HOOK_H / 2) * Box(
        LATCH_W, HOOK_OVER, HOOK_H)
    return part + lip + skirt + hook


# ---------------------------------------------------------------------------
# Export  (Deckel + Logo werden fuer den Druck gewendet: Logo nach unten)
# ---------------------------------------------------------------------------
def _flip_for_print(parts):
    """Dreht Teile 180 Grad um X (Logo nach unten) und setzt sie auf z=0."""
    flipped = [p.rotate(Axis.X, 180) for p in parts]
    z0 = min(p.bounding_box().min.Z for p in flipped)
    return [p.translate((0, 0, -z0)) for p in flipped]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    box = make_box()
    lid = make_lid()
    bg = make_logo_bg()
    fg = make_logo_fg()

    # Deckelgruppe gemeinsam wenden (bleibt zueinander passgenau)
    lid_p, bg_p, fg_p = _flip_for_print([lid, bg, fg])

    parts = {
        "butterdose_box": box,
        "butterdose_lid": lid_p,
        "butterdose_logo_bg": bg_p,
        "butterdose_logo_fg": fg_p,
    }
    for name, part in parts.items():
        export_stl(part, str(OUT_DIR / f"{name}.stl"))
        s = part.bounding_box().size
        print(f"{name:22s} -> {name + '.stl':28s} "
              f"({s.X:6.1f} x {s.Y:6.1f} x {s.Z:6.1f} mm)")

    export_step(box, str(OUT_DIR / "butterdose_box.step"))
    export_step(lid_p, str(OUT_DIR / "butterdose_lid.step"))
    print("\nFertig. Dateien liegen in:", OUT_DIR)


if __name__ == "__main__":
    main()
