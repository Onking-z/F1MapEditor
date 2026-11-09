"""Validated, optional project overrides applied after generated race data."""

import copy
import math

DATASETS = ["f1_2025", "sprint_f1_2025", "f1_2026", "sprint_f1_2026"]
COMPOUNDS = tuple("C%d" % n for n in range(1, 7))
HARVEST_FIELDS = ("HarvestLimitMGUK", "HarvestLimitQualifyingMGUK")


def validate(value):
    if not isinstance(value, dict):
        raise ValueError("Track race parameters must be an object")
    if set(value) - {"tyres", "ers"}:
        raise ValueError("Unknown track race parameter")
    result = {}
    if "tyres" in value:
        tyres = value["tyres"]
        if not isinstance(tyres, list) or len(tyres) != 3 or any(t not in COMPOUNDS for t in tyres):
            raise ValueError("Choose three tyre compounds from C1 to C6")
        if not all(int(a[1:]) < int(b[1:]) for a, b in zip(tyres, tyres[1:])):
            raise ValueError("Tyre compounds must increase from hard to medium to soft")
        result["tyres"] = list(tyres)
    if "ers" in value:
        ers = value["ers"]
        if not isinstance(ers, dict) or set(ers) - set(HARVEST_FIELDS):
            raise ValueError("Unknown ERS harvest parameter")
        result["ers"] = {}
        for key, number in ers.items():
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not 0 <= number <= 1_000_000_000:
                raise ValueError("ERS harvest limit must be between 0 and 1000 MJ")
            result["ers"][key] = round(number)
        if not result["ers"]:
            del result["ers"]
    return result


def apply(manifest, generated, parameters):
    """Return race-data extras; ERS lives at manifest root, not in activation.

    Extras are attached after activation-template replacement by the existing
    packager, so manual tyre choices survive both build targets.
    """
    parameters = validate(parameters)
    extra = copy.deepcopy(generated) if generated else {"overrides": [], "track_overrides": []}
    if "tyres" in parameters:
        paths = ["TyreData_0.compound_" + name for name in ("harder", "medium", "softer")]
        extra["overrides"] = [e for e in extra["overrides"] if e.get("path") not in paths]
        extra["overrides"].extend({"datasets": list(DATASETS), "path": path, "value": tyre}
                                  for path, tyre in zip(paths, parameters["tyres"]))
    if parameters.get("ers"):
        manifest.setdefault("ers", {}).update(parameters["ers"])
    return extra
