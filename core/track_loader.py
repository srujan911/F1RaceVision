import xml.etree.ElementTree as ET
import numpy as np
from typing import Dict, List, Tuple


# ============================================================
# Utility: convert SVG → numpy array of points
# ============================================================

def parse_points(points_str: str) -> List[Tuple[float, float]]:
    pts = []
    for pair in points_str.strip().split():
        if "," in pair:
            x, y = pair.split(",")
            pts.append((float(x), float(y)))
    return pts


# ============================================================
# Normalization: center & scale SVG to internal coordinates
# ============================================================

def normalize_points(points: List[Tuple[float, float]]) -> np.ndarray:
    pts = np.array(points, dtype=float)

    min_x, min_y = pts.min(axis=0)
    max_x, max_y = pts.max(axis=0)

    # translate to origin
    pts[:, 0] -= min_x
    pts[:, 1] -= min_y

    # scale longest side to 1.0
    scale = max(max_x - min_x, max_y - min_y)
    pts /= (scale + 1e-9)

    return pts


# ============================================================
# Load a track SVG
# ============================================================

def load_track_svg(path: str) -> Dict:
    """
    Reads an SVG file and extracts:
      - centerline
      - left/right edges
      - S1/S2 indices
      - SF line index
      - DRS zones
      - GP + circuit name
    """

    tree = ET.parse(path)
    root = tree.getroot()

    # ------------ metadata ------------
    gp_name = ""
    circuit_name = ""

    metadata = root.find("metadata")
    if metadata is not None:
        gp_el = metadata.find("gp_name")
        circuit_el = metadata.find("circuit_name")
        gp_name = gp_el.text if gp_el is not None else ""
        circuit_name = circuit_el.text if circuit_el is not None else ""

    # ------------ track polylines ------------
    centerline = []
    left_edge = []
    right_edge = []

    for poly in root.iter():
        tag = poly.tag.split("}")[-1]  # remove namespace if present
        if tag == "polyline":
            pid = poly.attrib.get("id", "")
            pts = parse_points(poly.attrib.get("points", ""))

            if pid == "centerline":
                centerline = pts
            elif pid == "left_edge":
                left_edge = pts
            elif pid == "right_edge":
                right_edge = pts

    # ------------ sector markers ------------
    s1_idx = None
    s2_idx = None

    for circ in root.iter():
        tag = circ.tag.split("}")[-1]
        if tag == "circle":
            cid = circ.attrib.get("id", "")
            cx = float(circ.attrib.get("cx"))
            cy = float(circ.attrib.get("cy"))

            if cid == "s1_marker":
                s1_idx = (cx, cy)
            elif cid == "s2_marker":
                s2_idx = (cx, cy)

    # ------------ start/finish line ------------
    sf_pos = None
    for line in root.iter():
        tag = line.tag.split("}")[-1]
        if tag == "line" and line.attrib.get("id", "") == "start_finish":
            x = float(line.attrib.get("x1"))
            y = float(line.attrib.get("y1"))
            sf_pos = (x, y)

    # ------------ DRS zones ------------
    drs_zones = []
    for line in root.iter():
        tag = line.tag.split("}")[-1]
        if tag == "line" and line.attrib.get("class", "") == "drs":
            x1 = float(line.attrib["x1"])
            y1 = float(line.attrib["y1"])
            x2 = float(line.attrib["x2"])
            y2 = float(line.attrib["y2"])
            drs_zones.append(((x1, y1), (x2, y2)))

    # ============================================================
    # Normalize & convert to internal index-based system
    # ============================================================

    if not centerline:
        raise ValueError(f"SVG {path} missing centerline points!")

    center_norm = normalize_points(centerline)
    left_norm = normalize_points(left_edge) if left_edge else None
    right_norm = normalize_points(right_edge) if right_edge else None

    # Convert sector/SF positions into nearest index on centerline
    def nearest_index(pt_xy):
        if pt_xy is None:
            return None
        cx, cy = pt_xy
        cx, cy = (cx - min(p[0] for p in centerline)) / \
                 (max(p[0] for p in centerline) - min(p[0] for p in centerline) + 1e-9), \
                 (cy - min(p[1] for p in centerline)) / \
                 (max(p[1] for p in centerline) - min(p[1] for p in centerline) + 1e-9)
        diffs = center_norm - np.array([cx, cy])
        idx = np.argmin(np.linalg.norm(diffs, axis=1))
        return int(idx)

    s1_idx = nearest_index(s1_idx)
    s2_idx = nearest_index(s2_idx)
    sf_idx = nearest_index(sf_pos)

    # Convert DRS zones into fraction ranges
    drs_ranges = []
    for (p1, p2) in drs_zones:
        i1 = nearest_index(p1)
        i2 = nearest_index(p2)
        if i1 is not None and i2 is not None:
            drs_ranges.append((i1, i2))

    # ============================================================
    # Build final structure
    # ============================================================

    return {
        "gp_name": gp_name,
        "circuit_name": circuit_name,
        "centerline": center_norm.tolist(),
        "left_edge": left_norm.tolist() if left_norm is not None else [],
        "right_edge": right_norm.tolist() if right_norm is not None else [],
        "s1_index": s1_idx,
        "s2_index": s2_idx,
        "sf_index": sf_idx,
        "drs_zones": drs_ranges
    }
