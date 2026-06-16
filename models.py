from pydantic import BaseModel, Field
from typing import Optional


class AbsenRecord(BaseModel):
    """Satu record absensi dari spreadsheet."""
    nama: str
    uid: str
    waktu: str


class HitRequest(BaseModel):
    """Request untuk hit Apps Script dengan UID."""
    uid: str = Field(..., description="UID kartu untuk absen")


class HitResponse(BaseModel):
    """Response setelah hit Apps Script."""
    success: bool
    nama: str
    uid: str
    message: Optional[str] = None
    error: Optional[str] = None
