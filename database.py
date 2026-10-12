import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cash_manager.db")

DENOMINACIONES = [1000, 500, 200, 100, 50, 20, 10, 5, 2, 1, 0.50]
DEN_COLS = ["d_1000", "d_500", "d_200", "d_100", "d_50", "d_20", "d_10", "d_5", "d_2", "d_1", "d_050"]
DEN_LABELS = ["$1,000", "$500", "$200", "$100", "$50", "$20", "$10", "$5", "$2", "$1", "$0.50"]


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       DATE    NOT NULL,
                tipo        TEXT    NOT NULL CHECK(tipo IN ('INGRESO', 'EGRESO')),
                concepto    TEXT    NOT NULL,
                monto       REAL    NOT NULL,
                d_1000      INTEGER DEFAULT 0,
                d_500       INTEGER DEFAULT 0,
                d_200       INTEGER DEFAULT 0,
                d_100       INTEGER DEFAULT 0,
                d_50        INTEGER DEFAULT 0,
                d_20        INTEGER DEFAULT 0,
                d_10        INTEGER DEFAULT 0,
                d_5         INTEGER DEFAULT 0,
                d_2         INTEGER DEFAULT 0,
                d_1         INTEGER DEFAULT 0,
                d_050       INTEGER DEFAULT 0,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def insert_movimiento(fecha: str, tipo: str, concepto: str, monto: float, denominaciones: dict):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO movimientos
                (fecha, tipo, concepto, monto,
                 d_1000, d_500, d_200, d_100, d_50, d_20,
                 d_10, d_5, d_2, d_1, d_050)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha, tipo, concepto, monto,
            denominaciones.get("d_1000", 0),
            denominaciones.get("d_500", 0),
            denominaciones.get("d_200", 0),
            denominaciones.get("d_100", 0),
            denominaciones.get("d_50", 0),
            denominaciones.get("d_20", 0),
            denominaciones.get("d_10", 0),
            denominaciones.get("d_5", 0),
            denominaciones.get("d_2", 0),
            denominaciones.get("d_1", 0),
            denominaciones.get("d_050", 0),
        ))
        conn.commit()


def get_all_movimientos() -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM movimientos ORDER BY fecha ASC, created_at ASC"
        )
        return [dict(row) for row in cursor.fetchall()]


def get_estado_cuenta() -> list[dict]:
    """Daily summary with running balance: saldo_inicial, ingresos, egresos, saldo_final."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT
                fecha,
                SUM(CASE WHEN tipo = 'INGRESO' THEN monto ELSE 0 END) AS ingresos,
                SUM(CASE WHEN tipo = 'EGRESO'  THEN monto ELSE 0 END) AS egresos
            FROM movimientos
            GROUP BY fecha
            ORDER BY fecha ASC
        """)
        rows = cursor.fetchall()

    result = []
    saldo_anterior = 0.0
    for fecha, ingresos, egresos in rows:
        saldo_inicial = saldo_anterior
        saldo_final = saldo_inicial + ingresos - egresos
        result.append({
            "FECHA": fecha,
            "SALDO INICIAL": saldo_inicial,
            "INGRESOS EN EFECTIVO": ingresos,
            "EGRESOS EN EFECTIVO": egresos,
            "SALDO FINAL": saldo_final,
        })
        saldo_anterior = saldo_final

    return result


def get_arqueo() -> list[dict]:
    """Net denomination breakdown (INGRESOS - EGRESOS) currently in the vault."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT
                SUM(CASE WHEN tipo='INGRESO' THEN d_1000 ELSE -d_1000 END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_500  ELSE -d_500  END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_200  ELSE -d_200  END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_100  ELSE -d_100  END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_50   ELSE -d_50   END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_20   ELSE -d_20   END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_10   ELSE -d_10   END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_5    ELSE -d_5    END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_2    ELSE -d_2    END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_1    ELSE -d_1    END),
                SUM(CASE WHEN tipo='INGRESO' THEN d_050  ELSE -d_050  END)
            FROM movimientos
        """)
        row = cursor.fetchone()

    if not row:
        return []

    result = []
    for i, (den, label) in enumerate(zip(DENOMINACIONES, DEN_LABELS)):
        cantidad = int(row[i] or 0)
        result.append({
            "DENOMINACIÓN": label,
            "CANTIDAD": cantidad,
            "SUBTOTAL": den * cantidad,
        })
    return result


def get_saldo_actual() -> float:
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT
                SUM(CASE WHEN tipo = 'INGRESO' THEN monto ELSE -monto END)
            FROM movimientos
        """)
        val = cursor.fetchone()[0]
    return val or 0.0


def delete_movimiento(movimiento_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
        conn.commit()
