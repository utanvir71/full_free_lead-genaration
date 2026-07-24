from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.db import schema

router = APIRouter()


@router.get("/runs/{run_id}/exports/{kind}")
def download(request: Request, run_id: str, kind: str) -> FileResponse:
    if kind not in {"qualified", "rejected"}:
        raise HTTPException(status_code=404, detail="Export not found")
    with request.app.state.engine.connect() as connection:
        export = (
            connection.execute(
                select(schema.exports).where(
                    schema.exports.c.run_id == run_id, schema.exports.c.kind == kind
                )
            )
            .mappings()
            .one_or_none()
        )
    if export is None or not Path(export["file_path"]).is_file():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(
        export["file_path"],
        media_type="text/csv",
        filename=Path(export["file_path"]).name,
    )
