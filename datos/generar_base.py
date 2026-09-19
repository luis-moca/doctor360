"""
BASE SINTETICA. 1,200 doctores, 28 CSS, con las senales que Doctoralia
realmente tiene de cada doctor (visitas al perfil, reservas, conversion,
opiniones, campanas, productos activos, tickets, sesiones).

En produccion este archivo se reemplaza por la extraccion real desde
Salesforce y la plataforma. El motor (motor.py) no cambia: recibe la
misma estructura de datos venga de donde venga.

Todo es inventado. Ningun doctor, nombre o cifra viene de un sistema real.
Solo libreria estandar de Python.
"""

import random
from datetime import timedelta

import supuestos as S

random.seed(2026)

ESPECIALIDADES = [
    "Medicina general", "Pediatría", "Ginecología", "Dermatología",
    "Psicología", "Odontología", "Cardiología", "Nutrición",
    "Traumatología", "Oftalmología", "Psiquiatría", "Endocrinología",
]
CIUDADES = ["CDMX", "Guadalajara", "Monterrey", "Puebla", "Querétaro",
            "Mérida", "Tijuana", "León"]
APELLIDOS = ["Álvarez", "Beltrán", "Cano", "Durán", "Estrada", "Fuentes",
             "Gómez", "Haro", "Islas", "Juárez", "Lara", "Mena", "Nava",
             "Ochoa", "Pardo", "Quiroz", "Rangel", "Solís", "Tapia",
             "Urbina", "Vela", "Zárate", "Arce", "Bravo", "Cruz", "Díaz",
             "Escobar", "Flores", "Guerra", "Herrera", "Ibarra", "Lugo",
             "Marín", "Núñez", "Ortega", "Peña", "Ríos", "Salas", "Torres",
             "Valdez", "Yáñez", "Zúñiga"]
NOMBRES_CSS = ["Ana", "Bruno", "Carla", "Diego", "Elena", "Fabián", "Gaby",
               "Héctor", "Irene", "Jorge", "Karla", "Lucía", "Mariana",
               "Nico", "Olga", "Pablo", "Quetzal", "Rocío", "Sergio",
               "Tania", "Ulises", "Vero", "Willy", "Ximena", "Yael",
               "Zoe", "Abril", "Beto"]

NOTAS_PREVIAS = [
    "Quiere más pacientes de primera vez; le preocupa la competencia en su zona.",
    "Pidió ayuda para configurar recordatorios por WhatsApp; quedó pendiente.",
    "Comentó que su asistente no usa la agenda online; sigue agendando por teléfono.",
    "Satisfecho con las opiniones; quiere saber cómo pedir más.",
    "Mencionó que evaluaría bajar de plan si no ve más reservas.",
    "Interesado en Noa Booking pero no entendió cómo funciona.",
    "Cambió de consultorio; hay que actualizar la dirección del perfil.",
    "Preguntó por facturación; le molestó un cargo que no esperaba.",
    "Sin temas: sesión corta de seguimiento.",
    "Quiere activar consulta online para pacientes foráneos.",
]

# Perfil de comportamiento: hacia donde se mueve la cuenta en los ultimos
# 30 dias contra su propia linea base de 90. Los pesos dan una base con
# ~5% en caida fuerte, coherente con el churn mensual del caso (4.8%).
PERFILES = {
    "cayendo_fuerte": (5,  (0.20, 0.55)),
    "cayendo":        (10, (0.60, 0.80)),
    "estable":        (60, (0.88, 1.12)),
    "creciendo":      (17, (1.20, 1.45)),
    "creciendo_fuerte": (8, (1.50, 2.20)),
}


def elegir_plan():
    nombres = list(S.PLANES)
    pesos = [S.PLANES[n]["peso"] for n in nombres]
    return random.choices(nombres, weights=pesos, k=1)[0]


def elegir_perfil():
    nombres = list(PERFILES)
    pesos = [PERFILES[n][0] for n in nombres]
    return random.choices(nombres, weights=pesos, k=1)[0]


def productos_activos(plan):
    """Lo que el plan incluye, mas si de verdad lo usa (activo/inactivo).
    Un producto incluido pero inactivo es senal de valor no percibido."""
    incluidos = []
    for p in ["Starter", "Plus", "VIP"]:
        incluidos += S.PRODUCTOS_POR_PLAN[p]
        if p == plan:
            break
    activos = {}
    for prod in incluidos:
        base = 0.85 if prod in S.PRODUCTOS_POR_PLAN["Starter"] else 0.55
        activos[prod] = random.random() < base
    if random.random() < 0.25:
        activos["Noa Notes (complemento)"] = True
    return activos


_NOMBRES_USADOS = set()


def nombre_unico():
    """Dos apellidos y sin repetir en toda la base: en un demo, dos
    'Dr. Herrera' en la misma cartera confunden."""
    while True:
        n = f"{random.choice(['Dra.', 'Dr.'])} {' '.join(random.sample(APELLIDOS, 2))}"
        if n not in _NOMBRES_USADOS:
            _NOMBRES_USADOS.add(n)
            return n


def inventar_doctor(i, css_id):
    plan = elegir_plan()
    perfil = elegir_perfil()
    lo, hi = PERFILES[perfil][1]
    factor = random.uniform(lo, hi)

    antiguedad = random.randint(1, 60)
    # Contratos anuales: la renovacion cae segun cuando entro.
    renovacion_dias = 365 - (antiguedad * 30) % 365
    if renovacion_dias <= 0:
        renovacion_dias += 365

    visitas_base = random.randint(150, 2500)      # visitas al perfil, 30 dias
    reservas_base = max(2, round(visitas_base * random.uniform(0.02, 0.09)))
    visitas_rec = max(0, round(visitas_base * random.uniform(0.85, 1.15) * (0.7 + 0.3 * factor)))
    reservas_rec = max(0, round(reservas_base * factor))
    conversion = round(reservas_rec / visitas_rec * 100, 1) if visitas_rec else 0.0
    # Serie semanal de reservas, 12 semanas: parte de la linea base y llega
    # al valor reciente, con ruido. Es lo que dibuja la tendencia en la ficha.
    serie = []
    for w in range(12):
        t = w / 11
        nivel = reservas_base * (1 - t) + reservas_rec * t
        serie.append(max(0, round(nivel / 4.33 * random.uniform(0.8, 1.2))))

    tickets_90d = random.choices([0, 1, 2, 3, 5, 8], weights=[45, 25, 14, 9, 5, 2])[0]
    ticket_abierto = tickets_90d > 0 and random.random() < 0.3

    # CSAT por doctor: la media de la base debe quedar cerca de 82 (CASO).
    csat = random.choices([40, 60, 80, 100], weights=[5, 12, 41, 42])[0]
    if perfil.startswith("cayendo"):
        csat = random.choices([40, 60, 80, 100], weights=[22, 38, 30, 10])[0]
    # NPS: promotor / pasivo / detractor, calibrado a ~46 (CASO)
    nps_cat = random.choices(["promotor", "pasivo", "detractor"], weights=[64, 27, 9])[0]
    if perfil.startswith("cayendo"):
        nps_cat = random.choices(["promotor", "pasivo", "detractor"], weights=[25, 35, 40])[0]

    cupo = S.PLANES[plan]["campanas_cupo"]
    campanas_mes = round(cupo * random.choices([0, 0.05, 0.2, 0.5, 0.8, 0.97, 1.0],
                                               weights=[20, 20, 25, 18, 10, 4, 3])[0])
    consultorios_permitidos = S.PLANES[plan]["consultorios"]
    # Lo normal es usar menos consultorios de los permitidos; estar al tope
    # es la excepcion (4%) y por eso es senal.
    consultorios_usados = random.randint(1, max(1, consultorios_permitidos - 1))
    if consultorios_permitidos > 1 and random.random() < 0.04:
        consultorios_usados = consultorios_permitidos   # al tope

    ultima_sesion = random.choices([3, 10, 20, 35, 50, 75, 120],
                                   weights=[8, 15, 22, 22, 15, 12, 6])[0]

    return {
        "id": f"DR-{i:04d}",
        "nombre": nombre_unico(),
        "especialidad": random.choice(ESPECIALIDADES),
        "ciudad": random.choice(CIUDADES),
        "css_id": css_id,
        "plan": plan,
        "mrr_lista": S.PLANES[plan]["lista"],
        "en_promo": random.random() < 0.3,
        "antiguedad_meses": antiguedad,
        "renovacion_dias": renovacion_dias,
        "onboarding_personalizado": plan == "VIP",   # OFICIAL: solo VIP lo recibe
        "productos": productos_activos(plan),
        "senales": {
            "visitas_perfil_base_30d": visitas_base,
            "visitas_perfil_rec_30d": visitas_rec,
            "reservas_base_30d": reservas_base,
            "reservas_rec_30d": reservas_rec,
            "tasa_conversion_pct": conversion,
            "reservas_semanales_12s": serie,
            "opiniones_90d": random.randint(0, 30),
            "campanas_enviadas_mes": campanas_mes,
            "campanas_cupo_mes": cupo,
            "consultorios_usados": consultorios_usados,
            "consultorios_permitidos": consultorios_permitidos,
        },
        "soporte": {
            "tickets_90d": tickets_90d,
            "ticket_abierto": ticket_abierto,
            "ultimo_ticket_dias": random.randint(1, 90) if tickets_90d else None,
            "ultimo_ticket_tema": random.choice(
                ["Facturación", "Agenda no sincroniza", "Recordatorios no llegan",
                 "Perfil desactualizado", "Pagos online", "Acceso a la app"]) if tickets_90d else None,
        },
        "voz": {"csat_ultima": csat, "nps_categoria": nps_cat},
        "sesiones": {
            "ultima_hace_dias": ultima_sesion,
            "nota_ultima": random.choice(NOTAS_PREVIAS),
            "programada": None,
        },
        "upsell_12m": random.random() < (S.KPI_ACTUAL["upsell_rate"] / 100),
    }


def repartir(n_doctores, n_css, minimo=38, maximo=49):
    """Cuantos doctores lleva cada CSS. Campana cerrada alrededor de la media
    (43): la mayoria en 42-44, pocos en los extremos, y siempre dentro de
    [minimo, maximo]. La suma da exacto. Usa su propio generador aleatorio
    para que cambiar el reparto no cambie a los doctores (nombres, senales)."""
    media = n_doctores / n_css
    # Se consumen los mismos sorteos del generador global que antes, para que
    # la base (nombres, senales, acciones) no se mueva al cambiar el reparto.
    for _ in range(n_css):
        random.gauss(media, 2.2)
    rng = random.Random(7)
    tamanos = [int(round(rng.gauss(media, 1.4))) for _ in range(n_css)]
    tamanos = [min(maximo, max(minimo, t)) for t in tamanos]
    # Ajustar la suma sin salirse del rango
    diff = n_doctores - sum(tamanos)
    i = 0
    while diff != 0:
        j = i % n_css
        if diff > 0 and tamanos[j] < maximo:
            tamanos[j] += 1; diff -= 1
        elif diff < 0 and tamanos[j] > minimo:
            tamanos[j] -= 1; diff += 1
        i += 1
    return tamanos


def generar(n_doctores=S.N_DOCTORES, n_css=S.N_CSS):
    """Devuelve (css, doctores). Parametrizado: no asume tope."""
    css = [{"id": i + 1, "nombre": NOMBRES_CSS[i % len(NOMBRES_CSS)], "doctores": 0}
           for i in range(n_css)]
    tamanos = repartir(n_doctores, n_css)
    doctores = []
    i = 0
    for c, t in zip(css, tamanos):
        for _ in range(t):
            i += 1
            doctores.append(inventar_doctor(i, c["id"]))
            c["doctores"] += 1
    return css, doctores


if __name__ == "__main__":
    css, docs = generar()
    print(len(docs), "doctores;", len(css), "CSS")
