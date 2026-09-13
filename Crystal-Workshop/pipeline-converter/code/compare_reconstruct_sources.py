"""
Purpose: Diagnose whether two point exports differ only by removed scene entities.
Streams DXF coordinates into compact integer keys; leaves source files unchanged.
"""
from array import array
from pathlib import Path
import json
import numpy as np


def read_keys(source):
    keys = array("Q")
    entity = None
    coordinates = {}
    inside = False
    with source.open(encoding="utf-8", errors="replace") as stream:
        lines = iter(stream)
        for raw in lines:
            code = raw.strip()
            value = next(lines, "").strip()
            if code == "2" and value == "ENTITIES":
                inside = True
            elif code == "0" and value == "ENDSEC" and inside:
                break
            elif inside and code == "0":
                entity, coordinates = value, {}
            elif inside and entity == "POINT" and code in {"10", "20", "30"}:
                coordinate = float(value) * 100
                if abs(coordinate - round(coordinate)) > 0.001 or not -32768 <= coordinate <= 32767:
                    raise ValueError("Diagnostic requires centimetre-key precision of 0.01 mm and bounded coordinates.")
                coordinates[code] = round(coordinate) + 32768
                if all(key in coordinates for key in ("10", "20", "30")):
                    keys.append((coordinates["10"] << 32) | (coordinates["20"] << 16) | coordinates["30"])
                    coordinates = {}
    return np.frombuffer(keys, dtype=np.uint64).copy()


def bounds(keys):
    return [[float(((keys >> shift) & 65535).min()) / 100 - 327.68,
             float(((keys >> shift) & 65535).max()) / 100 - 327.68] for shift in (32, 16, 0)]


def main():
    root = Path(__file__).resolve().parents[1]
    exports = root.parent / "2.5D-pipeline/reference-gallery/cockpit-files/exported"
    old = read_keys(exports / "DXF-Amma-og-Afi-Tester-Output.dxf")
    new = read_keys(exports / "amma-og-afi-new/amma-og-afi-without-text.dxf")
    common = np.intersect1d(old, new)
    removed = np.setdiff1d(old, new)
    added = np.setdiff1d(new, old)
    old_sample, new_sample = old[3::4], new[3::4]
    common_sample = np.intersect1d(old_sample, new_sample)
    result = {"oldPoints": len(old), "newPoints": len(new), "identicalCoordinates": len(common),
              "oldOnly": len(removed), "newOnly": len(added), "oldBounds": bounds(old), "newBounds": bounds(new),
              "commonStride4": len(common_sample), "oldStride4": len(old_sample), "newStride4": len(new_sample)}
    destination = root / "output/diagnostics/source-comparison"
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in (("old", old), ("new", new), ("removed", removed), ("added", added)):
        np.save(destination / f"{name}.npy", data)
    (destination / "comparison.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
