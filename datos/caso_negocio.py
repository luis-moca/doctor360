"""
ARITMETICA DEL CASO DE NEGOCIO. Toda la cuenta a la vista.

Tres monedas:
  1. Tiempo: horas de preparacion recuperadas (y su equivalente en personas).
     NO se propone recortar gente: es capacidad que vuelve a la cartera.
  2. Churn: ingreso protegido por doctores que NO se van.
  3. Upsell: ingreso nuevo por doctores que suben de plan.

CSAT y NPS no se monetizan: se mueven de forma indirecta y se miden en
el piloto. Decirlo asi es mas creible que inventarles un peso.
"""

import supuestos as S


def arpu(doctores):
    """Ingreso promedio por doctor, calculado de la mezcla real de la base
    a precio de lista. Se reporta tambien con promo por transparencia."""
    n = len(doctores)
    lista = sum(d["mrr_lista"] for d in doctores) / n
    promo = sum(S.PLANES[d["plan"]]["promo"] for d in doctores) / n
    return round(lista), round(promo)


def moneda_tiempo(n_doctores, n_css, sesiones_mes, min_prep_nuevo):
    sesiones = n_doctores * sesiones_mes
    horas_hoy = sesiones * S.MIN_PREP_ACTUAL / 60
    horas_nuevo = sesiones * min_prep_nuevo / 60          # post-rampa
    horas_recuperadas = horas_hoy - horas_nuevo
    # Anio 1 con rampa: los primeros meses la preparacion es MIN_PREP_EN_RAMPA
    horas_rampa = sesiones * S.MIN_PREP_EN_RAMPA / 60
    horas_recuperadas_anio1 = (horas_hoy - horas_rampa) * S.RAMPA_ADOPCION_MESES \
        + horas_recuperadas * (12 - S.RAMPA_ADOPCION_MESES)
    return {
        "sesiones_mes": round(sesiones),
        "min_prep_hoy": S.MIN_PREP_ACTUAL,
        "min_prep_nuevo": min_prep_nuevo,
        "horas_prep_hoy_mes": round(horas_hoy),
        "horas_prep_nuevo_mes": round(horas_nuevo),
        "horas_recuperadas_mes": round(horas_recuperadas),
        "personas_equivalentes": round(horas_recuperadas / 160, 1),
        "horas_por_css_hoy_mes": round(horas_hoy / n_css, 1),
        "horas_por_css_nuevo_mes": round(horas_nuevo / n_css, 1),
        "rampa_meses": S.RAMPA_ADOPCION_MESES,
        "min_prep_en_rampa": S.MIN_PREP_EN_RAMPA,
        "horas_recuperadas_anio1": round(horas_recuperadas_anio1),
        "valor_mxn_anio": round(horas_recuperadas_anio1 * S.COSTO_HORA_CSS),
        "supuesto": f"{sesiones_mes} sesión(es) por doctor al mes, {S.COSTO_HORA_CSS} MXN por hora cargada",
    }


def moneda_churn(n_doctores, arpu_mxn, churn_final, rampa_meses):
    """Mes a mes: el churn baja linealmente del actual al final en
    'rampa_meses' y se queda ahi. Cada mes se comparan los doctores que se
    fueron con la base contra los que se van con el nuevo churn. Los
    retenidos siguen pagando los meses que quedan del anio."""
    actual = S.KPI_ACTUAL["churn_mensual"]
    meses = []
    retenidos_acum = 0
    ingreso = 0
    for m in range(1, 13):
        churn_m = actual - (actual - churn_final) * min(m / rampa_meses, 1)
        se_van_base = n_doctores * actual / 100
        se_van_nuevo = n_doctores * churn_m / 100
        retenidos_mes = se_van_base - se_van_nuevo
        retenidos_acum += retenidos_mes
        ingreso += retenidos_acum * arpu_mxn
        meses.append({"mes": m, "churn_pct": round(churn_m, 2),
                      "retenidos_acum": round(retenidos_acum)})
    return {
        "churn_actual_pct": actual,
        "churn_final_pct": churn_final,
        "rampa_meses": rampa_meses,
        "doctores_perdidos_hoy_mes": round(n_doctores * actual / 100),
        "doctores_perdidos_final_mes": round(n_doctores * churn_final / 100),
        "doctores_retenidos_12m": round(retenidos_acum),
        "ingreso_protegido_12m_mxn": round(ingreso),
        "mrr_protegido_mes_12_mxn": round(retenidos_acum * arpu_mxn),
        "churn_anualizado_hoy_pct": round((1 - (1 - actual / 100) ** 12) * 100, 1),
        "churn_anualizado_final_pct": round((1 - (1 - churn_final / 100) ** 12) * 100, 1),
        "meses": meses,
    }


def moneda_upsell(n_doctores, upsell_final):
    actual = S.KPI_ACTUAL["upsell_rate"]
    extra = n_doctores * (upsell_final - actual) / 100
    # Incremento promedio por subir un escalon de plan (lista)
    salto_starter_plus = S.PLANES["Plus"]["lista"] - S.PLANES["Starter"]["lista"]
    salto_plus_vip = S.PLANES["VIP"]["lista"] - S.PLANES["Plus"]["lista"]
    salto = round((salto_starter_plus + salto_plus_vip) / 2)
    ingreso = extra * salto * S.MESES_RESTANTES_PROMEDIO_UPSELL
    return {
        "upsell_actual_pct": actual,
        "upsell_final_pct": upsell_final,
        "upsells_extra_anio": round(extra),
        "incremento_por_upsell_mes_mxn": salto,
        "ingreso_nuevo_12m_mxn": round(ingreso),
        "mrr_nuevo_mes_12_mxn": round(extra * salto),
        "supuesto": f"un upsell cobra en promedio {S.MESES_RESTANTES_PROMEDIO_UPSELL} meses en el año 1",
    }


def churn_derivado(deteccion, rescate):
    """churn_final = actual - actual * deteccion * rescate. Dos palancas medibles."""
    actual = S.KPI_ACTUAL["churn_mensual"]
    return round(actual - actual * deteccion * rescate, 2)


def escenarios(doctores, n_css):
    n = len(doctores)
    arpu_lista, arpu_promo = arpu(doctores)
    salida = {}
    for nombre, e in S.ESCENARIOS.items():
        churn_final = churn_derivado(e["tasa_deteccion"], e["tasa_rescate"])
        t = moneda_tiempo(n, n_css, e["sesiones_mes"], e["min_prep"])
        c = moneda_churn(n, arpu_lista, churn_final, e["rampa_meses"])
        c["tasa_deteccion"] = e["tasa_deteccion"]
        c["tasa_rescate"] = e["tasa_rescate"]
        c["marcados_mes"] = round(n * S.KPI_ACTUAL["churn_mensual"] / 100 * e["tasa_deteccion"])
        c["rescatados_mes"] = round(c["marcados_mes"] * e["tasa_rescate"])
        c["churn_con_rescate_meta"] = churn_derivado(e["tasa_deteccion"], S.TASA_RESCATE_META)
        c["mes_meta"] = S.MES_META_CHURN
        u = moneda_upsell(n, e["upsell_final"])
        total = t["valor_mxn_anio"] + c["ingreso_protegido_12m_mxn"] + u["ingreso_nuevo_12m_mxn"]
        salida[nombre] = {
            "tiempo": t, "churn": c, "upsell": u,
            "csat_final": e["csat_final"], "nps_final": e["nps_final"],
            "total_12m_mxn": total,
            "titular": f"{round(total / 1e6, 1)} M MXN en 12 meses",
        }
    return {
        "n_doctores": n, "n_css": n_css,
        "arpu_lista_mxn": arpu_lista, "arpu_promo_mxn": arpu_promo,
        "mrr_base_mxn": sum(d["mrr_lista"] for d in doctores),
        "desglose_prep_actual": S.DESGLOSE_PREP_ACTUAL,
        "kpi_actual": S.KPI_ACTUAL, "kpi_meta": S.KPI_META,
        "escenarios": salida,
        "supuesto_que_mas_mueve": "el ingreso por doctor (ARPU) y el churn final alcanzado; "
                                  "el tiempo por sesión mueve poco el total",
    }
