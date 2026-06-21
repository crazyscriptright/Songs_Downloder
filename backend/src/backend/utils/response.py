"""Standardized API response helpers.

Every API endpoint returns:
```json
{
  "success": true|false,
  "message": "Human-readable status message",
  "data": { ... } | null,
  "meta": { ... }   // optional (pagination, timestamps, etc.)
}
```
"""

from typing import Any, Optional

from flask import jsonify


def success(
    data: Any = None,
    message: str = "Success",
    meta: Optional[dict] = None,
    status: int = 200,
):
    """Return a standardized success response."""
    body: dict[str, Any] = {"success": True, "message": message, "data": data}
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def error(
    message: str = "Error",
    status: int = 400,
    data: Any = None,
):
    """Return a standardized error response."""
    return jsonify({"success": False, "message": message, "data": data}), status
