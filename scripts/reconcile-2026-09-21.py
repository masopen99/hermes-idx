#!/usr/bin/env python3
"""Rekonsiliasi DB vs riwayat Stockbit (screenshot 21 Sep 2026).

Menghapus 2 baris TLKM hantu (TP 9 Sep, SL 11 Sep) yang dibuat auto-close
monitor tapi tidak pernah terjadi di pasar, lalu mencatat kejadian yang nyata:
TLKM dijual 23 lot @2.530 pada 18 Sep; INDF dijual 18 Sep; INCO trade hilang;
deposit 5jt + dividen BBCA 30rb.
"""
from hermes_idx.config import db_path
import sqlite3

conn = sqlite3.connect(db_path())

# 1. TLKM: hapus 2 baris hantu, ganti dengan realita
print("TLKM sebelum:", conn.execute(
    "SELECT id, exit_date, exit_price, pnl_rp FROM trade_closed WHERE ticker='TLKM'").fetchall())
conn.execute("DELETE FROM trade_closed WHERE ticker='TLKM'")
pnl = 5804452 - 5942901                      # -138.449
risk_ps = 2580 - 2530                        # 50/share -> risk total 115.000
conn.execute(
    """INSERT INTO trade_closed
       (ticker, entry_date, exit_date, entry_price, exit_price, lot, pnl_rp, pnl_pct,
        r_multiple, strategy, exit_reason, followed_plan, sl_respected, data_complete)
       VALUES ('TLKM','2026-09-02','2026-09-18',2580.0,2530.0,23,?,?,?,'trio','SL',1,1,1)""",
    (pnl, round(pnl / 5942901 * 100, 2), round(pnl / (risk_ps * 2300), 3)))

# 2. INDF: tanggal dan P/L sebenarnya
pnl_i = 695756 - 696042
conn.execute(
    """UPDATE trade_closed SET exit_date='2026-09-18', exit_price=6975.0,
       pnl_rp=?, pnl_pct=?, r_multiple=NULL WHERE ticker='INDF'""",
    (pnl_i, round(pnl_i / 696042 * 100, 3)))

# 3. INCO: trade yang hilang dari DB
pnl_c = 1047375 - 1076612
conn.execute(
    """INSERT OR IGNORE INTO trade_closed
       (ticker, entry_date, exit_date, entry_price, exit_price, lot, pnl_rp, pnl_pct,
        r_multiple, strategy, exit_reason, followed_plan, sl_respected, data_complete)
       VALUES ('INCO','2026-08-11','2026-08-11',5375.0,5250.0,2,?,?,NULL,NULL,'SELL',NULL,NULL,1)""",
    (pnl_c, round(pnl_c / 1076612 * 100, 2)))

# 4. MDKA: nominal sebenarnya
pnl_m = 1426425 - 1527288
conn.execute("UPDATE trade_closed SET pnl_rp=?, pnl_pct=? WHERE ticker='MDKA'",
             (pnl_m, round(pnl_m / 1527288 * 100, 2)))

# 5. Cash flow yang belum tercatat
def setm(k, v):
    conn.execute(
        "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (k, str(v)))

setm('cash_deposit_2026-09-09', 5000000)
setm('dividend_2026-09-16_BBCA', 30000)
setm('total_deposit', 5000000)

# 6. Ledger transaksi
rows = [
    ('TLKM', '2026-09-18', 'SELL', 23, 2530.0, 14548.0),
    ('INDF', '2026-09-18', 'SELL', 1, 6975.0, 1244.0),
    ('INCO', '2026-08-11', 'BUY', 2, 5375.0, 1612.0),
    ('INCO', '2026-08-11', 'SELL', 2, 5250.0, 2625.0),
    ('MDKA', '2026-08-10', 'BUY', 5, 3050.0, 2288.0),
    ('MDKA', '2026-08-13', 'SELL', 5, 2860.0, 3575.0),
]
for t, d, ty, lot, price, fee in rows:
    conn.execute(
        """INSERT OR IGNORE INTO transaksi(ticker,date,type,lot,price,fee,source,notes)
           VALUES(?,?,?,?,?,?,'stockbit-history','rekonsiliasi 21 Sep 2026')""",
        (t, d, ty, lot, price, fee))

conn.commit()

print("\n=== trade_closed SESUDAH ===")
for r in conn.execute(
        """SELECT ticker, entry_date, exit_date, lot, pnl_rp, pnl_pct, r_multiple, exit_reason
           FROM trade_closed ORDER BY exit_date"""):
    print(r)
n, s = conn.execute("SELECT COUNT(*), ROUND(SUM(pnl_rp),0) FROM trade_closed").fetchone()
print(f"\nTOTAL: {n} trade | realized P/L: Rp{s:,.0f}")
