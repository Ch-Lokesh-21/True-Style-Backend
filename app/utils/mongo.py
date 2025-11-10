from datetime import datetime, timezone
"""Helpers for keep track of createdAt and updatedAt for all collections"""
def stamp_create(doc: dict) -> dict:
    now = datetime.now(timezone.utc)
    doc["createdAt"] = now
    doc["updatedAt"] = now
    return doc

def stamp_update(doc: dict) -> dict:
    now = datetime.now(timezone.utc)
    doc["updatedAt"] = now
    return doc 