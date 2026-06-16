import httpx
import logging

logger = logging.getLogger(__name__)


async def hit_absen(apps_script_url: str, uid: str, timeout: float = 30.0) -> dict:
    """
    Hit Apps Script doGet dengan parameter uid untuk mencatat absensi.
    URL: {apps_script_url}?uid={uid}
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(
                apps_script_url,
                params={"uid": uid},
            )

        nama = response.text.strip()
        is_known = nama != "Tidak Dikenal"

        logger.info(f"Absen | uid={uid} → nama={nama} | status={response.status_code}")

        return {
            "success": is_known,
            "nama": nama,
            "uid": uid,
            "message": f"Absen berhasil: {nama}" if is_known else "UID tidak ditemukan",
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error hit absen | uid={uid} | {str(e)}")
        return {
            "success": False,
            "nama": "Error",
            "uid": uid,
            "message": None,
            "error": str(e),
        }


async def fetch_absensi(apps_script_url: str, timeout: float = 30.0) -> list[dict]:
    """
    Fetch semua data absensi dari Apps Script.
    URL: {apps_script_url}?action=list
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(
                apps_script_url,
                params={"action": "list"},
            )

        logger.info(f"Apps Script response | status={response.status_code} | len={len(response.text)} | body={response.text[:300]}")

        result = response.json()

        if result.get("success"):
            logger.info(f"Fetched {len(result['data'])} absensi records")
            return result["data"]
        else:
            logger.error(f"Apps Script returned error: {result}")
            return []

    except Exception as e:
        logger.error(f"Error fetching absensi | {str(e)}")
        return []
