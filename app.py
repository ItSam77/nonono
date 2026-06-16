"""
FastAPI Sistem Absensi - Apps Script Detector
==============================================
Menampilkan data absensi dari Google Spreadsheet via Apps Script.
Hit Apps Script URL untuk absen, dan tampilkan tabel NAMA / UID / WAKTU di website.
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from models import HitRequest, HitResponse
from services import hit_absen, fetch_absensi

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("absensi")

# ── Global State ──
cached_absensi = []

# ── Background Task ──────────────────────────────────────────────────────────
async def poll_apps_script():
    global cached_absensi
    while True:
        try:
            if APPS_SCRIPT_URL:
                new_data = await fetch_absensi(APPS_SCRIPT_URL)
                # Cek apakah ada perubahan jumlah data
                if len(new_data) != len(cached_absensi):
                    cached_absensi = new_data.copy()
                    # Broadcast ke semua client jika ada data baru
                    await manager.broadcast({"type": "update_full", "data": cached_absensi})
        except Exception as e:
            logger.error(f"Polling error: {str(e)}")
        await asyncio.sleep(3)  # Poll setiap 3 detik

# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not APPS_SCRIPT_URL:
        logger.warning("⚠️  APPS_SCRIPT_URL belum di-set! Tambahkan di .env")
    else:
        logger.info(f"🚀 Apps Script URL: {APPS_SCRIPT_URL[:60]}...")
        # Jalankan background poller
        asyncio.create_task(poll_apps_script())
    yield
    logger.info("🛑 Server stopped")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sistem Absensi",
    description="Sistem absensi via Google Apps Script & Spreadsheet",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket Manager ────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()



# ── HTML Page ────────────────────────────────────────────────────────────────
HTML_PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistem Absensi</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --bg-primary: #0a0e1a;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.7);
            --bg-glass: rgba(255, 255, 255, 0.03);
            --border-color: rgba(255, 255, 255, 0.06);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-1: #6366f1;
            --accent-2: #8b5cf6;
            --accent-3: #a78bfa;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --glow: rgba(99, 102, 241, 0.15);
        }

        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Animated background */
        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background:
                radial-gradient(ellipse 80% 50% at 20% 40%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse 60% 40% at 80% 20%, rgba(139, 92, 246, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse 50% 30% at 50% 80%, rgba(16, 185, 129, 0.04) 0%, transparent 50%);
            z-index: 0;
            animation: bgShift 20s ease-in-out infinite alternate;
        }

        @keyframes bgShift {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
            position: relative;
            z-index: 1;
        }

        /* ── Header ── */
        .header {
            text-align: center;
            margin-bottom: 2.5rem;
            animation: fadeInDown 0.8s ease;
        }

        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .header-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            padding: 0.4rem 1rem;
            border-radius: 50px;
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--accent-3);
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 1rem;
        }

        .header-badge .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
            50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #f1f5f9 0%, #a78bfa 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }

        .header p {
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 300;
        }

        /* ── Stats Cards ── */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
            animation: fadeInUp 0.8s ease 0.2s both;
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-1), transparent);
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .stat-card:hover {
            border-color: rgba(99, 102, 241, 0.2);
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .stat-card:hover::before {
            opacity: 1;
        }

        .stat-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1;
            margin-bottom: 0.3rem;
        }

        .stat-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }

        /* ── Action Bar ── */
        .action-bar {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            align-items: center;
            flex-wrap: wrap;
            animation: fadeInUp 0.8s ease 0.3s both;
        }

        .input-group {
            flex: 1;
            min-width: 200px;
            position: relative;
        }

        .input-group input {
            width: 100%;
            padding: 0.85rem 1.2rem 0.85rem 2.8rem;
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            outline: none;
            transition: all 0.3s ease;
        }

        .input-group input:focus {
            border-color: var(--accent-1);
            box-shadow: 0 0 0 3px var(--glow);
        }

        .input-group input::placeholder {
            color: var(--text-muted);
        }

        .input-group .input-icon {
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1rem;
            opacity: 0.5;
        }

        .btn {
            padding: 0.85rem 1.8rem;
            border: none;
            border-radius: 12px;
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            white-space: nowrap;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
            color: white;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 25px rgba(99, 102, 241, 0.4);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .btn-secondary {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
        }

        .btn-secondary:hover {
            border-color: rgba(99, 102, 241, 0.3);
            color: var(--text-primary);
            background: rgba(99, 102, 241, 0.05);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }

        .btn .spinner {
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            display: none;
        }

        .btn.loading .spinner { display: block; }
        .btn.loading .btn-text { display: none; }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* ── Search Bar ── */
        .search-bar {
            margin-bottom: 1rem;
            animation: fadeInUp 0.8s ease 0.35s both;
        }

        .search-bar input {
            width: 100%;
            padding: 0.75rem 1.2rem 0.75rem 2.8rem;
            background: var(--bg-glass);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            outline: none;
            transition: all 0.3s ease;
        }

        .search-bar input:focus {
            border-color: rgba(99, 102, 241, 0.3);
            background: var(--bg-card);
        }

        .search-bar input::placeholder {
            color: var(--text-muted);
        }

        .search-bar {
            position: relative;
        }

        .search-bar .search-icon {
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            opacity: 0.4;
        }

        /* ── Table ── */
        .table-wrapper {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            animation: fadeInUp 0.8s ease 0.4s both;
        }

        .table-header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }

        .table-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .table-count {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            background: rgba(255, 255, 255, 0.02);
        }

        thead th {
            padding: 0.9rem 1.5rem;
            text-align: left;
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            border-bottom: 1px solid var(--border-color);
        }

        tbody tr {
            transition: all 0.2s ease;
            animation: rowFadeIn 0.4s ease both;
        }

        @keyframes rowFadeIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }

        tbody tr:hover {
            background: rgba(99, 102, 241, 0.03);
        }

        tbody td {
            padding: 1rem 1.5rem;
            font-size: 0.88rem;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-secondary);
        }

        tbody tr:last-child td {
            border-bottom: none;
        }

        .col-no {
            width: 60px;
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 500;
        }

        .col-nama {
            font-weight: 600;
            color: var(--text-primary);
        }

        .col-uid {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.82rem;
            color: var(--accent-3);
            background: rgba(99, 102, 241, 0.06);
            padding: 0.3rem 0.7rem;
            border-radius: 6px;
            display: inline-block;
        }

        .col-waktu {
            color: var(--text-muted);
            font-size: 0.82rem;
        }

        /* ── Toast ── */
        .toast-container {
            position: fixed;
            top: 1.5rem;
            right: 1.5rem;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .toast {
            padding: 0.9rem 1.2rem;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            animation: toastIn 0.4s ease;
            backdrop-filter: blur(20px);
            max-width: 380px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        .toast.success {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #6ee7b7;
        }

        .toast.error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }

        .toast.info {
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #a5b4fc;
        }

        @keyframes toastIn {
            from { opacity: 0; transform: translateX(30px); }
            to { opacity: 1; transform: translateX(0); }
        }

        @keyframes toastOut {
            from { opacity: 1; transform: translateX(0); }
            to { opacity: 0; transform: translateX(30px); }
        }

        /* ── Empty State ── */
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
        }

        .empty-state .icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.3;
        }

        .empty-state h3 {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
        }

        .empty-state p {
            font-size: 0.85rem;
        }

        /* ── Loading Skeleton ── */
        .skeleton-row {
            display: grid;
            grid-template-columns: 60px 1fr 1fr 1fr;
            gap: 1rem;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }

        .skeleton {
            height: 16px;
            border-radius: 6px;
            background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s ease-in-out infinite;
        }

        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        /* ── Responsive ── */
        @media (max-width: 768px) {
            .stats-row { grid-template-columns: repeat(3, 1fr); gap: 0.6rem; }
            .stat-card { padding: 1rem; }
            .stat-value { font-size: 1.5rem; }
            .header h1 { font-size: 1.8rem; }
            .action-bar { flex-direction: column; }
            .btn { width: 100%; justify-content: center; }
            thead th, tbody td { padding: 0.7rem 1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-badge">
                <span class="dot"></span>
                Apps Script Connected
            </div>
            <h1>📋 Sistem Absensi</h1>
            <p>Monitor data absensi realtime dari Google Spreadsheet</p>
        </div>

        <!-- Stats -->
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-value" id="totalCount">-</div>
                <div class="stat-label">Total Absen</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📅</div>
                <div class="stat-value" id="todayCount">-</div>
                <div class="stat-label">Hari Ini</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🕐</div>
                <div class="stat-value" id="lastUpdate">-</div>
                <div class="stat-label">Update Terakhir</div>
            </div>
        </div>

        <!-- Action Bar -->
        <div class="action-bar">
            <div class="input-group">
                <span class="input-icon">🪪</span>
                <input type="text" id="uidInput" placeholder="Masukkan UID kartu untuk absen..." autocomplete="off" />
            </div>
            <button class="btn btn-primary" id="hitBtn" onclick="hitAbsen()">
                <span class="spinner"></span>
                <span class="btn-text">⚡ Absen</span>
            </button>
            <button class="btn btn-secondary" id="refreshBtn" onclick="refreshData()">
                <span class="spinner"></span>
                <span class="btn-text">🔄 Refresh</span>
            </button>
        </div>

        <!-- Search -->
        <div class="search-bar">
            <span class="search-icon">🔍</span>
            <input type="text" id="searchInput" placeholder="Cari nama atau UID..." oninput="filterTable()" />
        </div>

        <!-- Table -->
        <div class="table-wrapper">
            <div class="table-header-bar">
                <div class="table-title">📊 Data Absensi</div>
                <div class="table-count" id="tableCount">Memuat data...</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>No</th>
                        <th>Nama</th>
                        <th>UID</th>
                        <th>Waktu</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                    <!-- Loading skeleton -->
                    <tr class="skeleton-row"><td colspan="4"><div class="skeleton" style="width:100%"></div></td></tr>
                    <tr class="skeleton-row"><td colspan="4"><div class="skeleton" style="width:80%"></div></td></tr>
                    <tr class="skeleton-row"><td colspan="4"><div class="skeleton" style="width:90%"></div></td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Toast Container -->
    <div class="toast-container" id="toastContainer"></div>

    <script>
        let allData = [];

        // ── Toast notification ──
        function showToast(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            const icons = { success: '✅', error: '❌', info: 'ℹ️' };
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.animation = 'toastOut 0.3s ease forwards';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        // ── Render table ──
        function renderTable(data) {
            const tbody = document.getElementById('tableBody');
            const countEl = document.getElementById('tableCount');

            if (!data || data.length === 0) {
                tbody.innerHTML = `
                    <tr><td colspan="4">
                        <div class="empty-state">
                            <div class="icon">📭</div>
                            <h3>Belum ada data absensi</h3>
                            <p>Masukkan UID untuk memulai absen</p>
                        </div>
                    </td></tr>
                `;
                countEl.textContent = '0 records';
                return;
            }

            // Reverse so newest is on top
            const reversed = [...data].reverse();

            tbody.innerHTML = reversed.map((row, i) => `
                <tr style="animation-delay: ${Math.min(i * 0.03, 0.5)}s">
                    <td class="col-no">${reversed.length - i}</td>
                    <td class="col-nama">${escapeHtml(row.nama)}</td>
                    <td><span class="col-uid">${escapeHtml(row.uid)}</span></td>
                    <td class="col-waktu">${escapeHtml(row.waktu)}</td>
                </tr>
            `).join('');

            countEl.textContent = `${data.length} records`;
        }

        // ── Update stats ──
        function updateStats(data) {
            document.getElementById('totalCount').textContent = data.length;

            // Count today's entries
            const today = new Date().toISOString().split('T')[0];
            const todayCount = data.filter(r => r.waktu && r.waktu.startsWith(today)).length;
            document.getElementById('todayCount').textContent = todayCount;

            // Last update time
            const now = new Date();
            document.getElementById('lastUpdate').textContent =
                now.getHours().toString().padStart(2, '0') + ':' +
                now.getMinutes().toString().padStart(2, '0');
        }

        // ── Fetch data ──
        async function refreshData() {
            const btn = document.getElementById('refreshBtn');
            btn.classList.add('loading');
            btn.disabled = true;

            try {
                const res = await fetch('/api/absensi');
                const data = await res.json();

                if (data.success) {
                    allData = data.data;
                    renderTable(allData);
                    updateStats(allData);
                    showToast(`Data berhasil dimuat: ${allData.length} records`, 'success');
                } else {
                    showToast(data.error || 'Gagal memuat data', 'error');
                }
            } catch (err) {
                showToast('Gagal terhubung ke server: ' + err.message, 'error');
            } finally {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        }

        // ── Hit absen ──
        async function hitAbsen() {
            const input = document.getElementById('uidInput');
            const uid = input.value.trim();
            const btn = document.getElementById('hitBtn');

            if (!uid) {
                showToast('Masukkan UID terlebih dahulu', 'error');
                input.focus();
                return;
            }

            btn.classList.add('loading');
            btn.disabled = true;

            try {
                const res = await fetch('/api/hit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uid: uid }),
                });
                const data = await res.json();

                if (data.success) {
                    showToast(`Absen berhasil! Nama: ${data.nama}`, 'success');
                    input.value = '';
                } else {
                    showToast(data.error || data.message || 'UID tidak ditemukan', 'error');
                }
            } catch (err) {
                showToast('Gagal mengirim absen: ' + err.message, 'error');
            } finally {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        }

        // ── Filter/Search ──
        function filterTable() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            if (!query) {
                renderTable(allData);
                return;
            }
            const filtered = allData.filter(r =>
                r.nama.toLowerCase().includes(query) ||
                r.uid.toLowerCase().includes(query) ||
                r.waktu.toLowerCase().includes(query)
            );
            renderTable(filtered);
        }

        // ── Escape HTML ──
        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str || '';
            return div.innerHTML;
        }

        // ── Enter key to submit ──
        document.getElementById('uidInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') hitAbsen();
        });

        // ── Load data on page load ──
        window.addEventListener('DOMContentLoaded', () => {
            refreshData();
            setupWebSocket();
        });

        // ── WebSocket for Realtime updates ──
        function setupWebSocket() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

            ws.onmessage = function(event) {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'new_record') {
                        allData.push(msg.data);
                        renderTable(allData);
                        updateStats(allData);
                        showToast(`Absen baru: ${msg.data.nama}`, 'success');
                    } else if (msg.type === 'update_full') {
                        allData = msg.data;
                        renderTable(allData);
                        updateStats(allData);
                    }
                } catch (e) {
                    console.error("WS parse error", e);
                }
            };
            ws.onclose = () => {
                setTimeout(setupWebSocket, 3000); // Reconnect after 3s
            };
        }

        // Tidak lagi butuh setInterval karena akan dipush otomatism via websocket
        // jika ada perubahan data dari background poller backend.
    </script>
</body>
</html>
"""


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("WebSocket Client Connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket Client Disconnected")

@app.get("/", response_class=HTMLResponse)
async def index():
    """Halaman utama - tampilkan tabel absensi."""
    return HTML_PAGE


@app.get("/api/absensi")
async def get_absensi():
    """Ambil semua data absensi dari Apps Script / Spreadsheet."""
    if not APPS_SCRIPT_URL:
        raise HTTPException(status_code=500, detail="APPS_SCRIPT_URL belum di-set di .env")

    # Kembalikan data dari cache jika ada, kalau kosong baru fetch sekali.
    global cached_absensi
    if not cached_absensi:
        cached_absensi = await fetch_absensi(APPS_SCRIPT_URL)
        
    return {"success": True, "data": cached_absensi, "total": len(cached_absensi)}


@app.post("/api/hit", response_model=HitResponse)
async def post_hit(request: HitRequest):
    """Hit Apps Script URL untuk mencatat absensi."""
    if not APPS_SCRIPT_URL:
        raise HTTPException(status_code=500, detail="APPS_SCRIPT_URL belum di-set di .env")

    result = await hit_absen(APPS_SCRIPT_URL, request.uid)
    
    if result.get("success"):
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = {
            "nama": result.get("nama"),
            "uid": request.uid,
            "waktu": now_str
        }
        await manager.broadcast({"type": "new_record", "data": new_row})
        
    return HitResponse(**result)


@app.get("/health")
async def health():
    return {"status": "ok", "apps_script_configured": bool(APPS_SCRIPT_URL)}


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8020, reload=True)
