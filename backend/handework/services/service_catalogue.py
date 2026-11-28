import json
from pathlib import Path

CATALOGUE = json.loads(Path(__file__).with_name("service_catalogue.json").read_text(encoding="utf-8"))
LEGACY = {"plumbing", "carpentry", "welding", "painting", "masonry", "tailoring", "hairdressing", "makeup artist", "catering", "electrical", "digital design", "architect"}

def normalize(value):
    return " ".join((value or "").casefold().split())

def specific_service(value):
    key = normalize(value)
    if key in LEGACY:
        return None
    return next((row for row in CATALOGUE if key in {normalize(row["name"]), row["id"], *(normalize(alias) for alias in row["aliases"])}), None)

def capability_matches(row, trade, secondary):
    accepted = {normalize(row["name"]), row["id"], *(normalize(alias) for alias in row["aliases"] if " is " not in alias and "not working" not in alias and "leaking" not in alias)}
    return any(normalize(value) in accepted for value in [trade, *(secondary or "").split(",")])
