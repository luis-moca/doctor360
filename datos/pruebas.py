"""
PRUEBAS. Corren solas al final de correr.py. Si una falla, la corrida
falla: no se publica nada roto.
"""

import statistics

import supuestos as S
from motor import ORDEN


def probar(css, doctores, totales, caso):
    fallas = []

    def ok(cond, msg):
        if not cond:
            fallas.append(msg)

    n = len(doctores)
    ok(n == S.N_DOCTORES, f"esperaba {S.N_DOCTORES} doctores, hay {n}")
    ok(len(css) == S.N_CSS, f"esperaba {S.N_CSS} CSS, hay {len(css)}")

    # Una sola accion por doctor y siempre de la lista
    ok(all(d["accion"] in ORDEN for d in doctores), "accion fuera de catalogo")
    ok(all(len(d["agenda"]) == 3 for d in doctores), "agenda no tiene 3 puntos")
    ok(all(d["motivo"] for d in doctores), "doctor sin motivo")
    ok(all(d["resumen"] for d in doctores), "doctor sin resumen")

    # Nadie desaparece: la suma de acciones es la base completa
    ok(sum(totales["acciones"].values()) == n, "la suma de acciones no da la base")

    # Orden: prioridad descendente y RESCATAR primero
    prios = [d["prioridad"] for d in doctores]
    ok(prios == sorted(prios, reverse=True), "no esta ordenado por prioridad")
    ok(doctores[0]["accion"] == "RESCATAR", "el primero no es RESCATAR")

    # Distribuciones plausibles contra el caso
    # El motor mira a 90 dias. Con churn mensual de 4.8%, en 90 dias se va
    # 1 - (1 - 0.048)^3 = 13.7% de la base. RESCATAR debe rondar eso.
    churn_90d = (1 - (1 - S.KPI_ACTUAL["churn_mensual"] / 100) ** 3) * 100
    pct_rescatar = totales["acciones"].get("RESCATAR", 0) / n * 100
    ok(churn_90d - 5 <= pct_rescatar <= churn_90d + 3,
       f"RESCATAR {pct_rescatar:.1f}% lejos del churn a 90 dias ({churn_90d:.1f}%)")
    csat = statistics.mean(d["voz"]["csat_ultima"] for d in doctores)
    ok(76 <= csat <= 88, f"CSAT medio {csat:.1f} lejos del 82 del caso")
    prom = sum(d["voz"]["nps_categoria"] == "promotor" for d in doctores)
    det = sum(d["voz"]["nps_categoria"] == "detractor" for d in doctores)
    nps = (prom - det) / n * 100
    ok(36 <= nps <= 56, f"NPS {nps:.0f} lejos del 46 del caso")
    ups = sum(d["upsell_12m"] for d in doctores) / n * 100
    ok(14 <= ups <= 22, f"upsell {ups:.1f}% lejos del 18% del caso")

    # Reparto equilibrado entre CSS
    cuentas = [c["doctores"] for c in css]
    ok(38 <= min(cuentas) and max(cuentas) <= 49, f"reparto fuera de [38,49]: {min(cuentas)}-{max(cuentas)}")
    ok(sum(cuentas) == n, "el reparto no suma la base")

    # Ventana de downgrade: ningun RIESGO DOWNGRADE por ventana con renovacion <= 30
    for d in doctores:
        if d["accion"] == "RIESGO DOWNGRADE" and "inactivos" in d["senales_clave"]:
            ok(d["renovacion_dias"] > S.VENTANA_DOWNGRADE_DIAS,
               f"{d['id']} marcado por ventana con renovacion {d['renovacion_dias']}")

    # Caso de negocio: aritmetica consistente
    for nombre, e in caso["escenarios"].items():
        ok(e["total_12m_mxn"] == e["tiempo"]["valor_mxn_anio"]
           + e["churn"]["ingreso_protegido_12m_mxn"] + e["upsell"]["ingreso_nuevo_12m_mxn"],
           f"total del escenario {nombre} no suma")
        esperado = round(S.KPI_ACTUAL["churn_mensual"] * (1 - S.ESCENARIOS[nombre]["tasa_deteccion"]
                         * S.ESCENARIOS[nombre]["tasa_rescate"]), 2)
        ok(e["churn"]["meses"][-1]["churn_pct"] == esperado,
           f"escenario {nombre} no llega al churn derivado {esperado}")
    ok(caso["escenarios"]["conservador"]["total_12m_mxn"]
       < caso["escenarios"]["base"]["total_12m_mxn"]
       < caso["escenarios"]["optimista"]["total_12m_mxn"], "escenarios no ordenados")

    return fallas, {"pct_rescatar": round(pct_rescatar, 1), "csat_medio": round(csat, 1),
                    "nps": round(nps), "upsell_pct": round(ups, 1)}
