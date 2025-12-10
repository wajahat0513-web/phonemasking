from typing import Iterable, Dict, Any, Optional
from fastapi import Request, HTTPException


async def parse_incoming_payload(
    request: Request,
    required_fields: Iterable[str],
    optional_fields: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Normalize inbound webhook payloads from form, JSON, or query params.

    Zapier and Twilio send data using different content types. This helper
    accepts all supported formats and enforces required fields with a clear
    error message instead of the generic "Field required" validation error.
    """
    data: Dict[str, Any] = {}

    content_type = request.headers.get("content-type", "").lower()

    # Prefer JSON if present (Zapier's "Custom Request" uses JSON by default)
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            data = {}

    # Fallback to form data (Twilio sends x-www-form-urlencoded)
    if not data:
        try:
            form = await request.form()
            data = {k: v for k, v in form.items()}
        except Exception:
            data = {}

    # Merge query params without overwriting body values
    for key, value in request.query_params.items():
        data.setdefault(key, value)

    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required field(s): {', '.join(missing)}",
        )

    # Limit output to only the fields we expect if optional_fields provided
    if optional_fields is not None:
        allowed = set(required_fields) | set(optional_fields)
        return {k: v for k, v in data.items() if k in allowed}

    return data

