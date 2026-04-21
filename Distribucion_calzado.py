# -*- coding: utf-8 -*-
"""
Distribución con márgenes fijos (tienda vs talla) por modelo.

Entradas esperadas (CSV):
- solicitudes.csv: Tienda, Modelo, Corrida
- stock.csv: Modelo, Talla, Stock
- curva.csv (opcional): modelo, talla, peso

Salidas:
- distribucion.csv: detalle tienda-modelo-talla-asignado
- auditoria_resumen.csv: resumen por modelo (solicitado, stock, asignado)
- auditoria_tiendas.csv: por modelo/tienda (solicitado vs asignado)
- auditoria_tallas.csv: por modelo/talla (stock vs asignado)
- modelos_fallidos.csv: lista de modelos que no pudieron distribuirse y motivo

Autor: Ajustado para márgenes fijos (homologación por curva).
"""
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # carpeta donde está el .py

# -------------------------
# Configuración de archivos
# -------------------------
RUTA_SOLICITUDES = BASE_DIR / "Solicitudes.csv"
RUTA_STOCK = BASE_DIR / "Stock.csv"
RUTA_CURVA = None  # "curva.csv" si quieres usar curva base por modelo

RUTA_SALIDA_DISTRIBUCION = BASE_DIR / "distribucion_footwear.csv"
RUTA_SALIDA_AUDITORIA_RESUMEN = BASE_DIR / "auditoria_resumen_footwear.csv"
RUTA_SALIDA_AUDITORIA_TIENDAS = BASE_DIR / "auditoria_tiendas_footwear.csv"
RUTA_SALIDA_AUDITORIA_TALLAS = BASE_DIR / "auditoria_tallas_footwear.csv"
RUTA_SALIDA_MODELOS_FALLIDOS = BASE_DIR / "modelos_fallidos_footwear.csv"

# --------------------------------
# Utilidades de redondeo y ajuste
# --------------------------------
def largest_remainder_round(values, target_sum, caps=None):
    v = np.array(values, dtype=float)
    v[v < 0] = 0.0
    base = np.floor(v).astype(int)
    if caps is not None:
        caps_arr = np.array(caps, dtype=int)
        base = np.minimum(base, caps_arr)
    else:
        caps_arr = None

    deficit = int(target_sum - base.sum())
    if deficit < 0:
        fracs = v - base
        order = np.argsort(fracs)
        idx = 0
        while deficit < 0 and idx < len(order):
            pos = order[idx]
            if base[pos] > 0:
                base[pos] -= 1
                deficit += 1
            idx += 1
        return base

    fracs = v - base
    order = np.argsort(-fracs)
    i = 0
    n = len(order)
    while deficit > 0 and i < n:
        pos = order[i]
        if caps_arr is None or base[pos] + 1 <= caps_arr[pos]:
            base[pos] += 1
            deficit -= 1
        i += 1

    if deficit > 0 and caps_arr is not None:
        for pos in np.argsort(-v):
            if deficit == 0:
                break
            if base[pos] < caps_arr[pos]:
                base[pos] += 1
                deficit -= 1

    return base


def waterfill_with_caps(weights, caps, total):
    w = np.array(weights, dtype=float)
    c = np.array(caps, dtype=float)
    T = float(total)

    if np.all(w <= 0):
        w = np.ones_like(w)
    w = w / w.sum()

    t = np.minimum(c, T * w)
    remaining = T - t.sum()

    for _ in range(100):
        if remaining <= 1e-9:
            break
        residual_cap = c - t
        mask = residual_cap > 1e-12
        if not np.any(mask):
            break
        w_masked = w[mask]
        w_masked = w_masked / w_masked.sum()
        add = np.minimum(residual_cap[mask], remaining * w_masked)
        t[mask] += add
        remaining = T - t.sum()

    if remaining > 1e-9:
        idx = np.argsort(-(c - t))
        for pos in idx:
            if remaining <= 1e-9:
                break
            delta = min(c[pos] - t[pos], remaining)
            if delta > 0:
                t[pos] += delta
                remaining -= delta

    return t


def build_integer_matrix_with_margins(row_targets, col_targets, guidance=None):
    r = np.array(row_targets, dtype=int)
    t = np.array(col_targets, dtype=int)
    T = int(r.sum())
    if T != int(t.sum()):
        raise AssertionError("Las sumas de filas y columnas deben coincidir.")

    m = len(r)
    n = len(t)

    if guidance is None:
        M = np.outer(r, t) / float(T)
    else:
        G = np.array(guidance, dtype=float)
        G[G < 0] = 0.0
        if G.sum() <= 0:
            G = np.ones((m, n))
        M = G.copy()
        for _ in range(30):
            row_sums = M.sum(axis=1)
            row_sums[row_sums == 0] = 1.0
            M *= (r / row_sums)[:, None]
            col_sums = M.sum(axis=0)
            col_sums[col_sums == 0] = 1.0
            M *= (t / col_sums)[None, :]

    B = np.floor(M).astype(int)
    row_def = r - B.sum(axis=1)
    col_res = t - B.sum(axis=0)

    frac = (M - B).ravel()
    order = np.argsort(-frac)
    X = B.copy().ravel()

    row_def_flat = np.repeat(np.arange(m), n)
    col_idx_flat = np.tile(np.arange(n), m)

    row_def_mut = row_def.copy()
    col_res_mut = col_res.copy()

    for pos in order:
        i = row_def_flat[pos]
        j = col_idx_flat[pos]
        if row_def_mut[i] > 0 and col_res_mut[j] > 0:
            X[pos] += 1
            row_def_mut[i] -= 1
            col_res_mut[j] -= 1

    if row_def_mut.sum() != 0:
        for pos in np.argsort(-M.ravel()):
            if row_def_mut.sum() == 0:
                break
            i = row_def_flat[pos]
            j = col_idx_flat[pos]
            if row_def_mut[i] > 0 and col_res_mut[j] > 0:
                X[pos] += 1
                row_def_mut[i] -= 1
                col_res_mut[j] -= 1

    if row_def_mut.sum() != 0:
        raise AssertionError("No se pudieron cumplir todos los márgenes por fila.")
    if col_res_mut.sum() != 0:
        raise AssertionError("No se cumplieron exactamente los márgenes por columna.")

    return X.reshape((m, n))


# ------------------------
# Pipeline principal
# ------------------------
def cargar_csv_rigido(ruta, required_cols, lower=True):
    df = pd.read_csv(ruta)
    if lower:
        df.columns = [c.strip().lower() for c in df.columns]
    synonym_map = {
        "tienda": ["tienda", "store", "tienda_nombre", "nombre_tienda"],
        "modelo": ["modelo", "sku", "item"],
        "corrida": ["corrida", "solicitado", "total_solicitado", "pares"],
        "talla": ["talla", "size"],
        "stock": ["stock", "disponible", "existencia", "qty"],
        "peso": ["peso", "weight", "w"]
    }
    cols = {}
    for req in required_cols:
        found = None
        for candidate in synonym_map.get(req, [req]):
            if candidate in df.columns:
                found = candidate
                break
        if found is None:
            raise ValueError(f"Columna requerida no encontrada: {req} (en {ruta})")
        cols[req] = found
    df = df.rename(columns={v: k for k, v in cols.items()})
    return df


def normalizar_talla_col(df, col="talla"):
    df[col] = df[col].astype(str).str.strip()
    def to_float_safe(x):
        try:
            return float(str(x).replace(",", "."))
        except:
            return np.nan
    df[col + "_num"] = df[col].map(to_float_safe)
    return df


def distribuir_por_modelo(solicitudes, stock, curva=None):
    stock = normalizar_talla_col(stock, "talla")
    if curva is not None:
        curva = normalizar_talla_col(curva, "talla")

    modelos = sorted(stock["modelo"].dropna().unique().tolist())
    asignaciones = []
    aud_resumen, aud_tiendas, aud_tallas = [], [], []
    modelos_fallidos = []

    for modelo in modelos:
        try:
            stk = stock[stock["modelo"] == modelo].copy()
            if stk.empty:
                continue

            tallas = stk.sort_values("talla_num")["talla"].tolist()
            cap_por_talla = stk.groupby("talla", as_index=False)["stock"].sum() \
                               .sort_values("talla", key=lambda s: s.map(lambda x: float(x.replace(',', '.')))) \
                               .set_index("talla")["stock"].reindex(tallas).fillna(0).astype(int).values

            sol = solicitudes[solicitudes["modelo"] == modelo].copy()
            if sol.empty:
                for _, r in stk.iterrows():
                    aud_tallas.append({
                        "modelo": modelo,
                        "talla": r["talla"],
                        "stock": int(r.get("stock", 0)),
                        "asignado": 0
                    })
                aud_resumen.append({
                    "modelo": modelo,
                    "total_solicitado": 0,
                    "total_stock": int(cap_por_talla.sum()),
                    "total_asignado": 0
                })
                continue

            sol = sol.groupby("tienda", as_index=False)["corrida"].sum()
            tiendas = sol["tienda"].tolist()
            req_por_tienda = sol["corrida"].astype(int).values

            total_req = int(req_por_tienda.sum())
            total_cap = int(cap_por_talla.sum())
            if total_cap == 0 or total_req == 0:
                aud_resumen.append({
                    "modelo": modelo,
                    "total_solicitado": int(total_req),
                    "total_stock": int(total_cap),
                    "total_asignado": 0
                })
                continue

            if total_cap >= total_req:
                r_rows = req_por_tienda.copy()
                T = int(total_req)
            else:
                scaled = req_por_tienda * (total_cap / float(total_req))
                r_rows = largest_remainder_round(scaled, target_sum=total_cap)
                T = int(r_rows.sum())

            if curva is not None:
                cur = curva[curva["modelo"] == modelo].copy()
                cur = cur.groupby("talla", as_index=False)["peso"].sum()
                cur = cur.set_index("talla").reindex(tallas)["peso"].fillna(0).values
                w_cols = np.array(cur, dtype=float)
            else:
                w_cols = cap_por_talla.astype(float)

            t_cols_real = waterfill_with_caps(weights=w_cols, caps=cap_por_talla, total=T)
            t_cols = largest_remainder_round(t_cols_real, target_sum=T, caps=cap_por_talla)

            M_entera = build_integer_matrix_with_margins(row_targets=r_rows, col_targets=t_cols, guidance=None)

            fila_sums = M_entera.sum(axis=1)
            col_sums = M_entera.sum(axis=0)
            if not np.all(fila_sums == r_rows):
                raise AssertionError(f"[{modelo}] Fila no cuadra")
            if not np.all(col_sums == t_cols):
                raise AssertionError(f"[{modelo}] Columna no cuadra")
            if not np.all(col_sums <= cap_por_talla):
                raise AssertionError(f"[{modelo}] Excede stock por talla")

            for i, tienda in enumerate(tiendas):
                for j, talla in enumerate(tallas):
                    qty = int(M_entera[i, j])
                    if qty > 0:
                        asignaciones.append({
                            "tienda": tienda,
                            "modelo": modelo,
                            "talla": talla,
                            "asignado": qty
                        })

            aud_resumen.append({
                "modelo": modelo,
                "total_solicitado": int(total_req),
                "total_stock": int(total_cap),
                "total_asignado": int(M_entera.sum())
            })
            for i, tienda in enumerate(tiendas):
                aud_tiendas.append({
                    "modelo": modelo,
                    "tienda": tienda,
                    "solicitado": int(req_por_tienda[i]),
                    "asignado": int(fila_sums[i])
                })
            for j, talla in enumerate(tallas):
                aud_tallas.append({
                    "modelo": modelo,
                    "talla": talla,
                    "stock": int(cap_por_talla[j]),
                    "asignado": int(col_sums[j])
                })

        except AssertionError as ae:
            motivo = str(ae)
            modelos_fallidos.append((modelo, motivo))
            aud_resumen.append({
                "modelo": modelo,
                "total_solicitado": int(sol["corrida"].sum()) if 'sol' in locals() and not sol.empty else 0,
                "total_stock": int(cap_por_talla.sum()) if 'cap_por_talla' in locals() else 0,
                "total_asignado": 0,
                "error": motivo
            })
            continue
        except Exception as e:
            modelos_fallidos.append((modelo, repr(e)))
            aud_resumen.append({
                "modelo": modelo,
                "total_solicitado": int(sol["corrida"].sum()) if 'sol' in locals() and not sol.empty else 0,
                "total_stock": int(cap_por_talla.sum()) if 'cap_por_talla' in locals() else 0,
                "total_asignado": 0,
                "error": repr(e)
            })
            continue

    asign_df = pd.DataFrame(asignaciones)
    resumen_df = pd.DataFrame(aud_resumen)
    tiendas_df = pd.DataFrame(aud_tiendas)
    tallas_df = pd.DataFrame(aud_tallas)
    fallidos_df = pd.DataFrame(modelos_fallidos, columns=["modelo", "motivo"]) if modelos_fallidos else pd.DataFrame(columns=["modelo", "motivo"])

    return asign_df, resumen_df, tiendas_df, tallas_df, fallidos_df


def main():
    solicitudes = cargar_csv_rigido(RUTA_SOLICITUDES, required_cols=["tienda", "modelo", "corrida"])
    stock = cargar_csv_rigido(RUTA_STOCK, required_cols=["modelo", "talla", "stock"])
    curva = None
    if RUTA_CURVA and Path(RUTA_CURVA).exists():
        curva = cargar_csv_rigido(RUTA_CURVA, required_cols=["modelo", "talla", "peso"])

    solicitudes["corrida"] = solicitudes["corrida"].fillna(0).astype(int)
    stock["stock"] = stock["stock"].fillna(0).astype(int)

    asign_df, resumen_df, tiendas_df, tallas_df, fallidos_df = distribuir_por_modelo(solicitudes, stock, curva)

    Path(RUTA_SALIDA_DISTRIBUCION).parent.mkdir(parents=True, exist_ok=True)

    if not asign_df.empty:
        asign_df.to_csv(RUTA_SALIDA_DISTRIBUCION, index=False, encoding="utf-8-sig")
    resumen_df.to_csv(RUTA_SALIDA_AUDITORIA_RESUMEN, index=False, encoding="utf-8-sig")
    tiendas_df.to_csv(RUTA_SALIDA_AUDITORIA_TIENDAS, index=False, encoding="utf-8-sig")
    tallas_df.to_csv(RUTA_SALIDA_AUDITORIA_TALLAS, index=False, encoding="utf-8-sig")
    fallidos_df.to_csv(RUTA_SALIDA_MODELOS_FALLIDOS, index=False, encoding="utf-8-sig")

    if not asign_df.empty:
        check_tm = (asign_df.groupby(["modelo", "tienda"])["asignado"].sum()
                    .reset_index().merge(
                        solicitudes.groupby(["modelo", "tienda"])["corrida"].sum().reset_index(),
                        on=["modelo", "tienda"], how="right", suffixes=("_asignado", "_solicitado")))
        check_ms = (asign_df.groupby(["modelo", "talla"])["asignado"].sum()
                    .reset_index().merge(
                        stock.groupby(["modelo", "talla"])["stock"].sum().reset_index(),
                        on=["modelo", "talla"], how="right", suffixes=("_asignado", "_stock")))
        print("Distribución generada.")
        print(f"- Filas en distribucion.csv: {len(asign_df)}")
        print("- Validación ejemplo (primeras filas):")
        print(check_tm.head())
        print(check_ms.head())
    else:
        print("No hubo asignaciones (revisa insumos).")

    if not fallidos_df.empty:
        print(f"Modelos fallidos: {len(fallidos_df)}. Archivo: {RUTA_SALIDA_MODELOS_FALLIDOS}")
    else:
        print("No hubo modelos fallidos.")

if __name__ == "__main__":
    main()