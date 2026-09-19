"""
MOTOR DE PRIORIZACION. Reglas transparentes contra la linea base de cada
doctor. Horizonte: 90 dias. Salida: UNA accion por doctor, con motivo,
agenda sugerida y resumen.

Sin IA generativa aqui, a proposito. La priorizacion es aritmetica:
determinista, auditable y barata. El modelo de lenguaje entra solo en
el resumen de texto no estructurado (tickets, notas), y en el demo ese
resumen sale de plantilla porque un demo publico no lleva clave de API.

Regla dura: el motor NUNCA quita un doctor de la vista del CSS. Solo
ordena y etiqueta. "Atendido reciente" baja prioridad, no oculta.

Prioridad fija entre acciones:
    RESCATAR > RIESGO DOWNGRADE > PROBABLE CRECIMIENTO > SIN ACCION
"""

from datetime import timedelta
import random

import supuestos as S

ORDEN = {"RESCATAR": 0, "RIESGO DOWNGRADE": 1, "PROBABLE CRECIMIENTO": 2, "SIN ACCION": 3}


def variacion(base, reciente):
    """Cambio porcentual contra la propia linea base. Base cero -> 0."""
    if not base:
        return 0.0
    return round((reciente - base) / base * 100, 1)


def evaluar(d):
    """Devuelve dict con accion, motivo, agenda, senales_clave.
    Cada regla dice en su motivo que dato la disparo: nada es caja negra."""
    s, sop, voz = d["senales"], d["soporte"], d["voz"]
    var_res = variacion(s["reservas_base_30d"], s["reservas_rec_30d"])
    var_vis = variacion(s["visitas_perfil_base_30d"], s["visitas_perfil_rec_30d"])
    renov = d["renovacion_dias"]
    molesto = voz["csat_ultima"] <= 60 or voz["nps_categoria"] == "detractor"
    ventana_downgrade = S.VENTANA_DOWNGRADE_DIAS < renov <= S.HORIZONTE_PREDICCION_DIAS
    prod = d["productos"]
    pct_campanas = s["campanas_enviadas_mes"] / s["campanas_cupo_mes"] * 100
    al_tope_consultorios = s["consultorios_usados"] >= s["consultorios_permitidos"]
    incluidos_inactivos = [p for p, activo in prod.items() if not activo]

    # ---------- RESCATAR: riesgo de churn a 90 dias ----------
    if var_res <= -40:
        return _r("RESCATAR",
                  f"Reservas por la plataforma cayeron {abs(var_res)}% contra su propio promedio de 90 días",
                  ["Preguntar qué cambió en su consulta en el último mes, antes de mostrar números",
                   "Revisar si la caída es de visibilidad (visitas) o de conversión (visitas sí, reservas no)",
                   "Salir con una acción concreta y fecha, no con 'seguimiento'"],
                  {"reservas": var_res, "visitas": var_vis})
    if molesto and sop["ticket_abierto"]:
        return _r("RESCATAR",
                  f"CSAT {voz['csat_ultima']} y ticket abierto sin resolver ({sop['ultimo_ticket_tema']})",
                  ["Abrir la sesión con el ticket, no con métricas",
                   "Confirmar en vivo que soporte lo tiene en curso y dar fecha de cierre",
                   "Cerrar con un compromiso propio, no del doctor"],
                  {"csat": voz["csat_ultima"], "ticket": sop["ultimo_ticket_tema"]})
    if renov <= 60 and var_res <= -20:
        return _r("RESCATAR",
                  f"Renueva en {renov} días con reservas a la baja ({var_res}%)",
                  ["Tratar la renovación de frente, no esperar a que la mencione",
                   "Mostrar el valor recibido en el periodo con sus propios números",
                   "Ofrecer ajuste antes de que lo pida: mejor un Starter que un churn"],
                  {"renovacion_dias": renov, "reservas": var_res})

    # ---------- RIESGO DOWNGRADE: ventana comercial de Doctoralia ----------
    # Bajar de plan solo se puede hasta 30 dias antes de renovar. Si esta
    # dentro de la ventana y no usa lo que paga, la decision es inminente.
    if ventana_downgrade and d["plan"] != "Starter" and len(incluidos_inactivos) >= 2:
        return _r("RIESGO DOWNGRADE",
                  f"Renueva en {renov} días, plan {d['plan']}, sin usar: {', '.join(incluidos_inactivos[:2])}",
                  [f"Activar en la misma sesión al menos uno: {incluidos_inactivos[0]}",
                   "Conectar cada función que no usa con un problema que sí tiene",
                   f"Decidir antes del día -{S.VENTANA_DOWNGRADE_DIAS}: después ya no puede bajar de plan y se va molesto"],
                  {"renovacion_dias": renov, "inactivos": incluidos_inactivos})
    if -40 < var_res <= -20:
        return _r("RIESGO DOWNGRADE",
                  f"Reservas a la baja {abs(var_res)}%, todavía sin caída crítica",
                  ["Detectar la causa antes de que se vuelva crítica",
                   "Revisar qué funcionalidades del plan no está usando",
                   "Acordar un objetivo de reservas para la próxima sesión"],
                  {"reservas": var_res})

    # ---------- PROBABLE CRECIMIENTO: senal de expansion ----------
    if d["plan"] != "VIP" and var_res >= 45:
        return _r("PROBABLE CRECIMIENTO",
                  f"Reservas +{var_res}% en plan {d['plan']}: probablemente le queda chico",
                  ["Mostrar su crecimiento con sus propios números",
                   "Presentar el siguiente plan como solución a lo que ya le pasa, no como venta",
                   "Definir qué tendría que ver para que le convenga cambiar"],
                  {"reservas": var_res})
    if d["plan"] != "VIP" and pct_campanas >= 90:
        return _r("PROBABLE CRECIMIENTO",
                  f"Usa {round(pct_campanas)}% del cupo de campañas ({s['campanas_enviadas_mes']} de {s['campanas_cupo_mes']})",
                  ["Preguntar qué resultado le dan las campañas",
                   "El siguiente plan multiplica el cupo: enseñar la cuenta, no el precio",
                   "Proponer prueba con el cupo ampliado un mes"],
                  {"campanas_pct": round(pct_campanas)})
    if d["plan"] != "VIP" and al_tope_consultorios and s["consultorios_permitidos"] > 1:
        return _r("PROBABLE CRECIMIENTO",
                  f"Al tope de consultorios ({s['consultorios_usados']} de {s['consultorios_permitidos']})",
                  ["Preguntar si abrió o abrirá otro consultorio",
                   "Mostrar el plan siguiente por consultorios, no por funciones",
                   "Cerrar con fecha de decisión"],
                  {"consultorios": s["consultorios_usados"]})
    if d["plan"] == "Starter" and s["tasa_conversion_pct"] >= 7.5 and s["reservas_rec_30d"] >= 60:
        return _r("PROBABLE CRECIMIENTO",
                  f"Starter con {s['reservas_rec_30d']} reservas al mes y {s['tasa_conversion_pct']}% de conversión: candidato a Noa Booking",
                  ["Preguntar cuántas llamadas atiende su consultorio al día",
                   "Explicar Noa Booking con su volumen real, no en abstracto",
                   "Proponer Plus con prueba de 30 días"],
                  {"reservas_rec": s["reservas_rec_30d"], "conversion": s["tasa_conversion_pct"]})

    return _r("SIN ACCION", "Dentro de su comportamiento normal",
              ["Confirmar que sigue satisfecho con lo que tiene",
               "Preguntar si hay algo nuevo en su consulta",
               "Sesión corta: no inventar temas donde no los hay"],
              {"reservas": var_res})


def historial_piloto(mios, rng):
    """Acumulado de las semanas de piloto para una cartera: marcados,
    contactados, con desenlace y como terminaron. Simulado alrededor de
    las tasas de supuestos, con variacion por CSS."""
    marcados_hoy = sum(1 for d in mios if d["accion"] == "RESCATAR")
    # cada semana entran marcados nuevos; en 8 semanas se acumula ~1.6x lo de hoy
    marcados = round(marcados_hoy * (1 + S.PILOTO_SEMANAS_CORRIDAS * 0.075))
    contactados = round(marcados * min(1, max(.6, rng.gauss(S.PILOTO_TASA_CONTACTO, .06))))
    con_desenlace = round(contactados * min(1, max(.5, rng.gauss(S.PILOTO_TASA_DESENLACE, .07))))
    tasa = min(.7, max(.2, rng.gauss(S.TASA_RESCATE_META, .08)))
    rescatados = round(con_desenlace * tasa)
    resto = con_desenlace - rescatados
    perdidos = round(resto * 0.55)
    crecidos = round(resto * 0.10)
    no_aplica = resto - perdidos - crecidos
    return {"semanas": S.PILOTO_SEMANAS_CORRIDAS, "marcados": marcados, "contactados": contactados,
            "con_desenlace": con_desenlace, "rescatados": rescatados, "perdidos": perdidos,
            "crecidos": crecidos, "no_aplica": no_aplica,
            "tasa_rescate": round(rescatados / con_desenlace, 2) if con_desenlace else 0}


COMPROMISOS = {
    "RESCATAR": ["Enviar paso a paso de la agenda online", "Confirmar fecha de cierre del ticket",
                 "Mandar comparativo de reservas del trimestre", "Agendar llamada con soporte y el doctor"],
    "RIESGO DOWNGRADE": ["Enviar guía de la función que no usa", "Activar recordatorios y revisar no-shows",
                         "Mandar resumen de valor recibido en el periodo"],
    "PROBABLE CRECIMIENTO": ["Enviar comparativo del siguiente plan", "Preparar propuesta VIP con sus números",
                             "Mandar cotización de consultorio adicional"],
    "SIN ACCION": ["Compartir tips de perfil", "Enviar novedades del trimestre"],
}
OPORTUNIDADES = ["Referido: colega interesado", "Segundo consultorio", "Interés en Noa Booking", "Quiere más campañas", None, None, None]


def post_sesion(d, rng):
    """Lo que la IA estructura de la ultima sesion: compromiso, vencimiento,
    sentimiento y oportunidad. Simulado con plantillas por accion."""
    csat = d["voz"]["csat_ultima"]
    sentimiento = "molesto" if csat <= 60 else ("neutral" if csat < 85 else "positivo")
    if rng.random() < 0.15:
        sentimiento = rng.choice(["positivo", "neutral", "molesto"])
    vence_en = rng.choice([-3, -2, -1, 0, 1, 2, 3, 5, 7])
    nombre = d["nombre"]
    NOTAS = {
        "RESCATAR": [
            f"{nombre} comenta que su asistente sigue agendando por teléfono y casi no revisa la agenda online. Se queja de un ticket que lleva semanas abierto. Acepta probar la agenda si le mandamos el paso a paso.",
            f"{nombre} dice que bajaron los pacientes nuevos este mes y que no ve qué cambió. Reconoce que no ha actualizado su perfil en meses. Quedamos de revisar juntos sus números en la próxima llamada.",
        ],
        "RIESGO DOWNGRADE": [
            f"{nombre} quiere bajar de plan porque no usa varias funciones que paga. Nunca activó los recordatorios. Acepta probarlos dos semanas antes de decidir.",
            f"{nombre} pregunta si vale la pena seguir en su plan. Le mostramos lo que no tiene activado y aceptó una prueba antes de la renovación.",
        ],
        "PROBABLE CRECIMIENTO": [
            f"{nombre} abrió un consultorio adicional y ya no le alcanzan las campañas del mes. Le interesa el siguiente plan pero le preocupa el precio; pide un comparativo con lo que gasta hoy en anuncios.",
            f"{nombre} está recibiendo más reservas que nunca y pregunta por Noa Booking para no perder llamadas. Pide una cotización con su volumen real.",
        ],
        "SIN ACCION": [
            f"{nombre} está conforme con lo que tiene. Pregunta cómo pedir más opiniones a sus pacientes. Sesión corta.",
        ],
    }
    RIESGOS = {"RESCATAR": "Agenda online sin adopción", "RIESGO DOWNGRADE": "Intención de bajar de plan",
               "PROBABLE CRECIMIENTO": "Objeción de precio", "SIN ACCION": None}
    PROXIMOS = {"RESCATAR": "Abrir con el estado del ticket, no con métricas", "RIESGO DOWNGRADE": "Revisar no-shows con recordatorios activos",
                "PROBABLE CRECIMIENTO": "Cerrar con el comparativo en mano", "SIN ACCION": "Confirmar que sigue satisfecho"}
    return {
        "nota": rng.choice(NOTAS[d["accion"]]),
        "riesgo": RIESGOS[d["accion"]],
        "proximo": PROXIMOS[d["accion"]],
        "compromiso": rng.choice(COMPROMISOS[d["accion"]]),
        "vence_en_dias": vence_en,
        "cumplido": rng.random() < 0.45 if vence_en < 0 else False,
        "sentimiento": sentimiento,
        "oportunidad": rng.choice(OPORTUNIDADES),
        "hace_dias": 0 if d["sesiones"].get("hecha") else d["sesiones"]["ultima_hace_dias"],
    }


def _r(accion, motivo, agenda, senales):
    return {"accion": accion, "motivo": motivo, "agenda": agenda, "senales_clave": senales}


def resumen(d, ev):
    """Resumen en lenguaje natural. En produccion lo genera un modelo de
    lenguaje en el lote semanal a partir de tickets y notas; aqui, plantilla."""
    s, sop, ses = d["senales"], d["soporte"], d["sesiones"]
    partes = [
        f"{d['nombre']}, {d['especialidad'].lower()} en {d['ciudad']}, plan {d['plan']} "
        f"desde hace {d['antiguedad_meses']} meses.",
        ev["motivo"] + ".",
        f"Últimos 30 días: {s['visitas_perfil_rec_30d']} visitas al perfil, "
        f"{s['reservas_rec_30d']} reservas, conversión {s['tasa_conversion_pct']}%.",
    ]
    if sop["tickets_90d"]:
        partes.append(f"{sop['tickets_90d']} ticket(s) en 90 días, el último sobre {sop['ultimo_ticket_tema'].lower()}"
                      + (", aún abierto." if sop["ticket_abierto"] else "."))
    if "enueva" not in ev["motivo"]:
        partes.append(f"Renueva en {d['renovacion_dias']} días.")
    partes.append(f"Última sesión hace {ses['ultima_hace_dias']} días: {ses['nota_ultima']}")
    return " ".join(partes)


def cambios_desde_ultima_sesion(d, ev):
    """Lo que dispara una entrada en la bandeja diaria aunque no tenga
    sesion: cambios relevantes desde la ultima vez que el CSS lo vio."""
    cambios = []
    sop, s = d["soporte"], d["senales"]
    if sop["ticket_abierto"] and sop["ultimo_ticket_dias"] and sop["ultimo_ticket_dias"] <= d["sesiones"]["ultima_hace_dias"]:
        cambios.append(f"Ticket nuevo: {sop['ultimo_ticket_tema']}")
    if ev["senales_clave"].get("reservas", 0) <= -40:
        cambios.append("Caída fuerte de reservas")
    if d["renovacion_dias"] <= 60:
        cambios.append(f"Renueva en {d['renovacion_dias']} días")
    if ev["accion"] == "PROBABLE CRECIMIENTO":
        cambios.append("Señal de crecimiento nueva")
    return cambios


def puntuar(css, doctores):
    """Aplica el motor a toda la base. Muta cada doctor con su evaluacion
    y devuelve totales. No asume cantidad de doctores ni de CSS."""
    for d in doctores:
        ev = evaluar(d)
        d.update(ev)
        d["resumen"] = resumen(d, ev)
        d["atendido_reciente"] = d["sesiones"]["ultima_hace_dias"] <= S.ATENDIDO_RECIENTE_DIAS
        d["cambios"] = cambios_desde_ultima_sesion(d, ev)
        # prioridad numerica: severidad de la accion x ingreso en juego
        d["prioridad"] = (4 - ORDEN[ev["accion"]]) * 1000 + d["mrr_lista"] / 3 \
            - (500 if d["atendido_reciente"] else 0)

    # Sesiones programadas esta semana: ~10 por CSS, primero lo urgente.
    for c in css:
        mios = sorted((d for d in doctores if d["css_id"] == c["id"]),
                      key=lambda d: -d["prioridad"])
        for k, d in enumerate(mios[:10]):
            d["sesiones"]["programada"] = (S.HOY + timedelta(days=k // 2)).isoformat()
            d["sesiones"]["hecha"] = False
            d["sesiones"]["orden_dia"] = k % 2

    # Estado a media manana: algunas sesiones de hoy ya se hicieron, y el
    # piloto lleva semanas corriendo. Generador propio para no mover la base.
    rng = random.Random(11)
    con_dos = 0
    for c in css:
        mios = [d for d in doctores if d["css_id"] == c["id"]]
        hoy_c = [d for d in mios if d["sesiones"]["programada"] == S.HOY.isoformat()]
        for d in hoy_c:
            # la segunda sesion del dia ya pudo hacerse; la primera (la urgente)
            # solo en unas pocas carteras, que ya van 2 de 2
            if d["sesiones"].get("orden_dia") == 1 and rng.random() < S.SESIONES_HOY_HECHAS_PCT * 2:
                d["sesiones"]["hecha"] = True
        # hasta 3 carteras ya van 2 de 2; la de la presentacion no
        if (con_dos < 3 and c["id"] != S.CSS_DEMO
                and all(d["sesiones"]["hecha"] for d in hoy_c if d["sesiones"].get("orden_dia") == 1) and rng.random() < 0.5):
            for d in hoy_c:
                d["sesiones"]["hecha"] = True
            con_dos += 1
        c["piloto"] = historial_piloto(mios, rng)
        for d in mios:
            if d["sesiones"].get("hecha") or d["sesiones"]["ultima_hace_dias"] <= 7:
                d["post_sesion"] = post_sesion(d, rng)

    doctores.sort(key=lambda d: -d["prioridad"])

    acciones = {}
    for d in doctores:
        acciones[d["accion"]] = acciones.get(d["accion"], 0) + 1
    return {
        "acciones": acciones,
        "mrr_total": sum(d["mrr_lista"] for d in doctores),
        "mrr_en_riesgo": sum(d["mrr_lista"] for d in doctores
                             if d["accion"] in ("RESCATAR", "RIESGO DOWNGRADE")),
        "mrr_en_crecimiento": sum(d["mrr_lista"] for d in doctores
                                  if d["accion"] == "PROBABLE CRECIMIENTO"),
    }
