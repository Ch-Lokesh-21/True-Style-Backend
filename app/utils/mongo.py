from datetime import datetime, timezone

def stamp_create(doc: dict) -> dict:
    now = datetime.now(timezone.utc)
    doc["createdAt"] = now
    doc["updatedAt"] = now
    return doc

def stamp_update(doc: dict) -> dict:
    now = datetime.now(timezone.utc)
    doc["updatedAt"] = now
    return doc 