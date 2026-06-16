/**
 * Google Apps Script - Sistem Absensi
 * ====================================
 * 
 * SETUP:
 * 1. Buka Google Sheets
 * 2. Buat sheet "DataKartu" dengan kolom: NAMA | UID
 * 3. Buat sheet "Absensi" dengan kolom: NAMA | UID | WAKTU
 * 4. Extensions → Apps Script → Paste kode ini
 * 5. Deploy → New deployment → Web app
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 6. Copy URL deployment, paste ke FastAPI .env
 * 
 * ENDPOINTS:
 *   ?uid=XXXXX       → Absen (tambah row ke Absensi)
 *   ?action=list     → Ambil semua data Absensi sebagai JSON
 */

function doGet(e) {
  var action = e.parameter.action;

  // ── Return attendance data as JSON ──
  if (action == "list") {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var absenSheet = ss.getSheetByName("Absensi");
    var data = absenSheet.getDataRange().getValues();
    var result = [];

    // Skip header row (i=1)
    for (var i = 1; i < data.length; i++) {
      result.push({
        nama: data[i][0],
        uid: String(data[i][1]).replace(/^'/, ""),  // Remove leading apostrophe
        waktu: data[i][2] instanceof Date
          ? Utilities.formatDate(data[i][2], Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss")
          : String(data[i][2])
      });
    }

    return ContentService
      .createTextOutput(JSON.stringify({ success: true, data: result }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  // ── Process attendance (original logic) ──
  var uid = e.parameter.uid;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var dataSheet = ss.getSheetByName("DataKartu");
  var absenSheet = ss.getSheetByName("Absensi");
  var data = dataSheet.getDataRange().getValues();
  var nama = "Tidak Dikenal";

  for (var i = 1; i < data.length; i++) {
    if (String(data[i][1]).trim() == String(uid).trim()) {
      nama = data[i][0];
      break;
    }
  }

  if (nama != "Tidak Dikenal") {
    absenSheet.appendRow([nama, "'" + uid, new Date()]);
  }

  return ContentService.createTextOutput(nama);
}
