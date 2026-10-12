import streamlit as st
import pandas as pd
from datetime import date

from database import (
    init_db,
    insert_movimiento,
    get_estado_cuenta,
    get_arqueo,
    get_all_movimientos,
    get_saldo_actual,
    delete_movimiento,
    DEN_COLS,
    DEN_LABELS,
)
from utils import format_currency, calc_total_from_denominaciones, export_estado_cuenta_excel

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Caja Fuerte",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .saldo-box {
        background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
        border-radius: 12px;
        padding: 20px 28px;
        color: white;
        text-align: center;
        margin-bottom: 8px;
    }
    .saldo-box .label { font-size: 13px; opacity: 0.85; text-transform: uppercase; letter-spacing: 1px; }
    .saldo-box .amount { font-size: 36px; font-weight: 700; margin-top: 4px; }
    .metric-card {
        background: #f0f4f8;
        border-radius: 10px;
        padding: 14px 20px;
        text-align: center;
    }
    .metric-card .label { font-size: 12px; color: #555; text-transform: uppercase; letter-spacing: 0.8px; }
    .metric-card .amount { font-size: 24px; font-weight: 600; margin-top: 4px; }
    .ingreso { color: #1a7a3c; }
    .egreso  { color: #c0392b; }
    div[data-testid="stSidebar"] { background-color: #f7f9fc; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Registro de movimiento
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📝 Registrar Movimiento")
    st.divider()

    tipo = st.radio(
        "Tipo",
        ["INGRESO", "EGRESO"],
        horizontal=True,
        help="Selecciona si es un ingreso o egreso a la caja fuerte.",
    )
    color_tipo = "#1a7a3c" if tipo == "INGRESO" else "#c0392b"
    icono_tipo = "📈" if tipo == "INGRESO" else "📉"
    st.markdown(
        f'<p style="color:{color_tipo}; font-weight:600; margin-top:-8px">'
        f'{icono_tipo} {tipo}</p>',
        unsafe_allow_html=True,
    )

    fecha = st.date_input("📅 Fecha", value=date.today())
    concepto = st.text_input(
        "📌 Concepto",
        placeholder="Ej. Corte diario, Cobranza CxC, Aportación socio…",
    )

    st.markdown("#### 💵 Denominaciones")
    st.caption("Ingresa la cantidad de billetes/monedas por denominación.")

    denominaciones: dict[str, int] = {}
    for col, label in zip(DEN_COLS, DEN_LABELS):
        denominaciones[col] = st.number_input(
            label,
            min_value=0,
            value=0,
            step=1,
            key=f"den_{col}",
        )

    total_calculado = calc_total_from_denominaciones(denominaciones)

    st.divider()
    st.markdown(
        f'<div style="text-align:center; font-size:18px; font-weight:700; '
        f'color:{color_tipo}">Total: {format_currency(total_calculado)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    registrar = st.button("✅ Registrar movimiento", type="primary", use_container_width=True)

    if registrar:
        if not concepto.strip():
            st.error("⚠️ El concepto no puede estar vacío.")
        elif total_calculado <= 0:
            st.error("⚠️ El monto debe ser mayor a $0.00. Ingresa al menos una denominación.")
        else:
            insert_movimiento(
                fecha=fecha.isoformat(),
                tipo=tipo,
                concepto=concepto.strip(),
                monto=total_calculado,
                denominaciones=denominaciones,
            )
            st.success(f"✅ {tipo} de **{format_currency(total_calculado)}** registrado.")
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER — Saldo actual y métricas
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("# 💰 Control de Efectivo — Caja Fuerte")

estado = get_estado_cuenta()
saldo_actual = estado[-1]["SALDO FINAL"] if estado else 0.0
total_ingresos = sum(r["INGRESOS EN EFECTIVO"] for r in estado)
total_egresos  = sum(r["EGRESOS EN EFECTIVO"]  for r in estado)

col_main, col_ing, col_eg = st.columns([2, 1, 1])

with col_main:
    st.markdown(
        f"""
        <div class="saldo-box">
            <div class="label">💰 Saldo en Caja Fuerte</div>
            <div class="amount">{format_currency(saldo_actual)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_ing:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">📈 Total Ingresos</div>
            <div class="amount ingreso">{format_currency(total_ingresos)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_eg:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">📉 Total Egresos</div>
            <div class="amount egreso">{format_currency(total_egresos)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_ec, tab_arq, tab_mov = st.tabs([
    "📊 Estado de Cuenta",
    "🏦 Arqueo de Caja Fuerte",
    "📋 Movimientos Detallados",
])

# ── Tab 1: Estado de Cuenta ───────────────────────────────────────────────────
with tab_ec:
    st.subheader("Estado de Cuenta Diario")

    if not estado:
        st.info("Aún no hay movimientos registrados. Usa el panel lateral para registrar el primero.")
    else:
        df_ec = pd.DataFrame(estado)

        # Formatted display copy
        df_show = df_ec.copy()
        for col in ["SALDO INICIAL", "INGRESOS EN EFECTIVO", "EGRESOS EN EFECTIVO", "SALDO FINAL"]:
            df_show[col] = df_show[col].apply(format_currency)

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "FECHA": st.column_config.DateColumn("FECHA", format="DD/MM/YYYY"),
                "SALDO INICIAL":          st.column_config.TextColumn("SALDO INICIAL",          width="medium"),
                "INGRESOS EN EFECTIVO":   st.column_config.TextColumn("INGRESOS EN EFECTIVO",   width="medium"),
                "EGRESOS EN EFECTIVO":    st.column_config.TextColumn("EGRESOS EN EFECTIVO",    width="medium"),
                "SALDO FINAL":            st.column_config.TextColumn("SALDO FINAL",            width="medium"),
            },
        )

        st.markdown("<br>", unsafe_allow_html=True)
        excel_bytes = export_estado_cuenta_excel(estado)
        st.download_button(
            label="⬇️ Descargar Estado de Cuenta en Excel",
            data=excel_bytes,
            file_name=f"estado_cuenta_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

# ── Tab 2: Arqueo de Caja Fuerte ──────────────────────────────────────────────
with tab_arq:
    st.subheader("Arqueo de Caja Fuerte — Saldo en Denominaciones")

    arqueo = get_arqueo()

    if not arqueo:
        st.info("Aún no hay movimientos registrados.")
    else:
        df_arq = pd.DataFrame(arqueo)

        # Formatted display
        df_arq_show = df_arq.copy()
        df_arq_show["SUBTOTAL"] = df_arq_show["SUBTOTAL"].apply(format_currency)

        st.dataframe(
            df_arq_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "DENOMINACIÓN": st.column_config.TextColumn("DENOMINACIÓN", width="small"),
                "CANTIDAD":     st.column_config.NumberColumn("CANTIDAD",    width="small"),
                "SUBTOTAL":     st.column_config.TextColumn("SUBTOTAL",      width="medium"),
            },
        )

        st.markdown("<br>", unsafe_allow_html=True)

        total_arqueo = sum(row["SUBTOTAL_RAW"] for row in [
            {**r, "SUBTOTAL_RAW": df_arq.loc[i, "SUBTOTAL"]}
            for i, r in enumerate(arqueo)
        ])
        # Use saldo_actual (already computed from DB) as source of truth
        st.markdown(
            f"""
            <div class="saldo-box" style="max-width:400px; margin:0 auto;">
                <div class="label">💰 Efectivo total en Caja Fuerte</div>
                <div class="amount">{format_currency(saldo_actual)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Tab 3: Movimientos Detallados ─────────────────────────────────────────────
with tab_mov:
    st.subheader("Todos los Movimientos Registrados")

    movimientos = get_all_movimientos()

    if not movimientos:
        st.info("Aún no hay movimientos registrados.")
    else:
        df_mov = pd.DataFrame(movimientos)

        # Build display dataframe
        df_display = df_mov[["id", "fecha", "tipo", "concepto", "monto", "created_at"]].copy()
        df_display.columns = ["ID", "FECHA", "TIPO", "CONCEPTO", "MONTO", "REGISTRADO EL"]
        df_display["MONTO"] = df_display["MONTO"].apply(format_currency)

        def color_tipo_row(val):
            if val == "INGRESO":
                return "color: #1a7a3c; font-weight: 600"
            elif val == "EGRESO":
                return "color: #c0392b; font-weight: 600"
            return ""

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID":            st.column_config.NumberColumn("ID",     width="small"),
                "FECHA":         st.column_config.DateColumn("FECHA",    format="DD/MM/YYYY", width="small"),
                "TIPO":          st.column_config.TextColumn("TIPO",     width="small"),
                "CONCEPTO":      st.column_config.TextColumn("CONCEPTO", width="large"),
                "MONTO":         st.column_config.TextColumn("MONTO",    width="medium"),
                "REGISTRADO EL": st.column_config.DatetimeColumn("REGISTRADO EL", format="DD/MM/YYYY HH:mm"),
            },
        )

        st.divider()
        with st.expander("🗑️ Eliminar un movimiento", expanded=False):
            st.warning(
                "⚠️ Eliminar un movimiento recalcula automáticamente todos los saldos posteriores. "
                "Esta acción no se puede deshacer."
            )
            mov_labels = [
                f"ID {m['id']} | {m['fecha']} | {m['tipo']} | {m['concepto']} | {format_currency(m['monto'])}"
                for m in movimientos
            ]
            selected_label = st.selectbox("Selecciona el movimiento a eliminar", mov_labels)
            selected_idx = mov_labels.index(selected_label)
            selected_id = movimientos[selected_idx]["id"]

            if st.button("🗑️ Eliminar movimiento seleccionado", type="secondary"):
                delete_movimiento(selected_id)
                st.success("Movimiento eliminado correctamente.")
                st.rerun()
