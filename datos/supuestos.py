"""
SUPUESTOS DEL CASO. Fuente unica.

Todo numero que no viene del PDF del caso ni de la pagina oficial de
Doctoralia vive aqui, con su origen. Cambiar un supuesto es cambiar una
linea de este archivo; nada mas se toca.

Origen de cada dato:
  CASO     = el PDF del caso practico
  OFICIAL  = pro.doctoralia.com.mx, verificado 18-sep-2026
  SUPUESTO = nuestro, con la logica escrita al lado
"""

from datetime import date

# "Hoy" fijo para que el demo sea reproducible (lunes de la presentacion).
# "Hoy" es la fecha real al correr; se puede fijar con DOCTOR360_HOY=AAAA-MM-DD
# (por ejemplo para ensayar la presentacion con la fecha del lunes).
import os
HOY = date.fromisoformat(os.environ["DOCTOR360_HOY"]) if os.environ.get("DOCTOR360_HOY") else date.today()

# ---------- CASO ----------
N_DOCTORES = 1200            # CASO: clientes activos
N_CSS = 28                   # CASO: Customer Success Specialists
MIN_PREP_ACTUAL = 45         # CASO: minutos de preparacion por reunion
KPI_ACTUAL = {"churn_mensual": 4.8, "csat": 82, "nps": 46, "upsell_rate": 18}
KPI_META = {"churn_mensual": 3.0, "csat": 90, "nps": 60, "upsell_rate": 28}

# ---------- OFICIAL ----------
# Precio de lista + IVA por mes, facturado anualmente. La promo de
# aniversario vigente se guarda aparte; el ingreso recurrente se calcula
# con lista porque la promo es temporal.
PLANES = {
    "Starter": {"lista": 1740, "promo": 1350, "peso": 45,
                "campanas_cupo": 300, "consultorios": 1},
    "Plus":    {"lista": 2340, "promo": 1620, "peso": 40,
                "campanas_cupo": 1000, "consultorios": 2},
    "VIP":     {"lista": 2970, "promo": 2370, "peso": 15,
                "campanas_cupo": 5000, "consultorios": 5},
}
# SUPUESTO: la mezcla de planes (peso) es nuestra. Plus es "el mas popular"
# segun el sitio, asi que Starter y Plus concentran la base.

NOA_NOTES_ADDON = 580        # OFICIAL: complemento mensual + IVA
PERMANENCIA_MESES = 12       # OFICIAL: contratos anuales
VENTANA_DOWNGRADE_DIAS = 30  # OFICIAL: bajar de plan solo hasta 30 dias antes de renovar

PRODUCTOS_POR_PLAN = {       # OFICIAL, nombres tal como los escribe Doctoralia
    "Starter": ["Perfil de pago", "Calendario para consulta online",
                "Recordatorios automáticos", "Reserva con Google"],
    "Plus":    ["Episodios clínicos", "Recordatorios vía WhatsApp/SMS",
                "Pagos online", "Noa Booking"],
    "VIP":     ["Perfil mejorado", "Pagos online con menor comisión",
                "Operaciones masivas y lista de espera", "Recetas digitales"],
}

# ---------- SUPUESTOS DE OPERACION ----------
SESIONES_POR_DOCTOR_MES = 1.0
# SUPUESTO: una sesion mensual por doctor. Con 43 doctores por CSS son ~2
# sesiones por dia habil, que es una carga plausible. El escenario
# conservador usa 0.5 (una cada dos meses).

COSTO_HORA_CSS = 150
# SUPUESTO: costo cargado por hora de un CSS en CDMX (salario ~18k segun
# bandas publicas de Doctoralia MX + carga social + herramientas). Se usa
# solo para poner precio a las horas; la propuesta NO recorta gente.

DESGLOSE_PREP_ACTUAL = {
    # SUPUESTO: donde se van los 45 minutos hoy. El caso lista las fuentes;
    # el reparto es nuestro y se declara en la presentacion.
    "CRM (Salesforce): historial y datos de cuenta": 12,
    "Tickets de soporte (Talkdesk / Zendesk)": 8,
    "Notas de reuniones anteriores": 10,
    "Productos contratados y facturación": 5,
    "Dashboards de uso de la plataforma": 10,
}
assert sum(DESGLOSE_PREP_ACTUAL.values()) == MIN_PREP_ACTUAL

MIN_PREP_CON_FICHA = {"conservador": 25, "base": 20, "optimista": 15}
# SUPUESTO: la ficha elimina la busqueda (~35 de los 45 min) pero el CSS
# sigue leyendo, pensando y ajustando la agenda, y la adopcion no es
# inmediata. 20 min base = 8 de lectura + 7 de criterio + 5 de ajuste.
# Rampa: los primeros 2 meses se asume 30 min mientras se adopta.

# ---------- SUPUESTOS DE IMPACTO A 12 MESES ----------
ESCENARIOS = {
    # churn_final: a donde llega el churn mensual al final de la rampa
    # rampa_meses: meses para llegar ahi (lineal desde el actual)
    # upsell_final: tasa anual de upsell alcanzada
    # BASE es el unico ancla que se presenta. Los otros dos solo si preguntan.
    # El churn final NO se pone a mano: se deriva de dos palancas medibles,
    # tasa_deteccion (que fraccion de los que se irian marca el motor) y
    # tasa_rescate (que fraccion de los marcados se salva en sesion).
    # churn_final = churn_actual - churn_actual * deteccion * rescate
    "conservador": {"tasa_deteccion": 0.85, "tasa_rescate": 0.28, "rampa_meses": 6,
                    "upsell_final": 22, "csat_final": 84, "nps_final": 49,
                    "sesiones_mes": 0.5, "min_prep": 25},
    "base":        {"tasa_deteccion": 0.90, "tasa_rescate": 0.43, "rampa_meses": 6,
                    "upsell_final": 25, "csat_final": 92, "nps_final": 60,
                    "sesiones_mes": 1.0, "min_prep": 21},
    "optimista":   {"tasa_deteccion": 0.90, "tasa_rescate": 0.45, "rampa_meses": 4,
                    "upsell_final": 29.5, "csat_final": 89, "nps_final": 56,
                    "sesiones_mes": 1.0, "min_prep": 17},
}
CHURN_RESCATABLE_PCT = 60
# SUPUESTO: 60% del churn es rescatable por CS (uso a la baja, valor no
# percibido, molestia, problema de soporte). El resto es estructural: cierre
# de consultorio, mudanza, retiro, cambio de giro. Llegar de 4.8 a 3.0 es
# rescatar 1.8 de 2.9 puntos rescatables: ~62%. Agresivo pero alcanzable.

# REFERENCIAS de las palancas: tasa_deteccion 0.90 se apoya en el backtest
# real de Customer Intelligence (el top 10% concentra 5.5x el churn: el
# metodo detecta). tasa_rescate 0.35 base se apoya en un caso publicado de
# priorizacion automatizada que subio la tasa de rescate de 14% a 51%
# (ustechautomations.com, plataforma de analitica de US$12M ARR). El piloto
# de 8 semanas mide las dos palancas reales.
# DECISION FINAL (Luis, 18-sep): la meta de churn se alcanza en el mes 12.
# Palancas: deteccion 0.90 (backtest real) y rescate 0.42 (dentro del rango
# publicado 14%-51%; y el equipo de training, que es el equipo del puesto,
# es quien sube esa tasa). 4.8 * (1 - 0.90 * 0.42) = 2.99 ~ 3.0.
# CSAT 92: la sesion llega con el ticket visto y agenda sobre lo que duele.
# NPS 60: al rescatar detractores y dejar de perder cuentas, la base que
# contesta la encuesta cambia de composicion; sube por mecanica, no por magia.
# Upsell 25 (NO llega a 28): unica metrica que se queda corta, a proposito.
# El motor prioriza RESCATAR sobre CRECIMIENTO; el tiempo del equipo va
# primero a retener. Subir de plan es decision del doctor y se captura
# tarde. Con el mismo motor, 28 llega en el anio 2.
TASA_RESCATE_META = 0.43
MES_META_CHURN = 6
# CRONOLOGIA (corregida 18-sep): piloto 8 semanas (prueba el mecanismo),
# despliegue a los 28 CSS en semanas 9-12, y el churn mensual llega a 3.0
# en el MES 6 porque el motor avisa con 90 dias: el primer grupo que renueva
# con alerta completa y sesion hecha lo hace 3 meses despues del despliegue.
# Solo upsell rate (anual por definicion) y churn anualizado se leen a 12 meses.
# UN SOLO HORIZONTE DE LECTURA: 6 meses. Es cuando el churn se puede leer
# de verdad (despliegue + 90 dias de aviso). Los demas KPIs se leen en la
# misma fecha; el upsell como tasa anualizada al mes 6. Antes del mes 6
# solo se leen las dos palancas (deteccion y rescate) en el piloto.
CRONOLOGIA = {
    "piloto_semanas": 8,
    "despliegue_semanas": (9, 12),
    "horizonte_lectura_meses": 6,     # con piloto: mes 3 (despliegue) + 90 dias
    "horizonte_sin_piloto_meses": 4,  # si van directo con los 28: 90 dias + 1 mes de lectura
}
# LO QUE SE PUEDE AFIRMAR Y LO QUE NO (para no decirlo mal en la entrevista):
# - Validado con backtest en Customer Intelligence: DETECCION (top 10% del
#   puntaje concentra 5.5x el churn). Metodo: 12 meses de historia, se tapan
#   los ultimos 4, el motor predice con los primeros 8, se destapa y compara.
# - NO validado: cuanto se rescata. Eso depende de la sesion, no del motor.
#   El 3.0 es hipotesis = deteccion (validada) x rescate (referencia externa,
#   se mide en piloto). Nunca decir "ya validamos el 3%".

# DECISION (Luis, 18-sep): la base LLEGA al churn (3.0) y baja la preparacion
# de 45 a 21 min por reunion, pero se queda en 25% de upsell contra 28.
# Es la unica metrica que no llega, y se explica: (1) rescatar esta en manos
# del CSS, subir de plan esta en manos del doctor; (2) la prioridad del motor
# manda el tiempo del equipo a RESCATAR primero; (3) el upsell se captura
# tarde, un doctor que crece hoy sube de plan en 2-3 meses.
# CSAT y NPS: estimados por mecanismo indirecto (sesion personalizada, ticket
# atendido antes de que escale). NPS mueve mas lento que CSAT porque mide la
# relacion, no la ultima interaccion. Se declaran como esperado, se miden en
# el piloto. Ir en blanco es peor que ir con estimado declarado.

RAMPA_ADOPCION_MESES = 2
MIN_PREP_EN_RAMPA = 30
# SUPUESTO: los primeros 2 meses la preparacion se queda en 30 min mientras
# los 28 CSS cambian el habito. Toda mejora lleva rampa; decirlo suma
# credibilidad. El valor "post-rampa" es el que se reporta.

MESES_RESTANTES_PROMEDIO_UPSELL = 6
# SUPUESTO: un upsell ocurre en promedio a mitad del anio, asi que en el
# anio 1 se cobran ~6 meses del incremento.

HORIZONTE_PREDICCION_DIAS = 90
# DECISION: el motor predice el desenlace a 90 dias. A 30 ya es tarde
# (la ventana de downgrade de Doctoralia cierra a -30). A 180 es otro
# modelo, fase posterior.

RECALCULO_DIAS = 7           # DECISION: el motor re-puntua semanal
ATENDIDO_RECIENTE_DIAS = 7   # DECISION: sesion en los ultimos 7 dias baja prioridad, nunca oculta

# Historial simulado del piloto (para la vista del Team Leader). Se etiqueta
# como simulacion en pantalla; en produccion sale de Salesforce.
PILOTO_SEMANAS_CORRIDAS = 8      # SUPUESTO: el demo muestra el equipo al cierre del piloto
PILOTO_TASA_CONTACTO = 0.85      # SUPUESTO: marcados que el CSS alcanza a contactar
PILOTO_TASA_DESENLACE = 0.75     # SUPUESTO: contactados con desenlace ya registrado
SESIONES_HOY_HECHAS_PCT = 0.40   # SUPUESTO: sesiones de hoy ya marcadas como hechas a media manana
CSS_DEMO = 11                    # DECISION: la cartera que se abre en la presentacion (Karla) conserva su sesion urgente pendiente
