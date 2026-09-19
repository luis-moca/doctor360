"""
Corre todo en orden y escribe la salida que lee el dashboard.

    python3 correr.py

1. Genera la base sintetica (en produccion: extraccion real).
2. Puntua con el motor.
3. Calcula el caso de negocio.
4. Corre las pruebas. Si algo falla, no escribe nada.
5. Escribe salida/doctores.json y salida/caso_negocio.json.
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "datos"))

import supuestos as S            # noqa: E402
from generar_base import generar  # noqa: E402
from motor import puntuar         # noqa: E402
from caso_negocio import escenarios  # noqa: E402
from pruebas import probar        # noqa: E402


def main():
    css, doctores = generar()
    totales = puntuar(css, doctores)
    caso = escenarios(doctores, len(css))
    fallas, medidas = probar(css, doctores, totales, caso)

    if fallas:
        print("PRUEBAS FALLIDAS:")
        for f in fallas:
            print("  -", f)
        sys.exit(1)

    salida_dir = os.path.join(AQUI, "salida")
    os.makedirs(salida_dir, exist_ok=True)

    with open(os.path.join(salida_dir, "doctores.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "hoy": S.HOY.isoformat(),
            "horizonte_dias": S.HORIZONTE_PREDICCION_DIAS,
            "recalculo_dias": S.RECALCULO_DIAS,
            "nota": "Datos 100% sintéticos. Planes y precios oficiales de Doctoralia al 18-sep-2026; todo lo demás es supuesto declarado en datos/supuestos.py.",
            "totales": {**totales, "doctores": len(doctores), "css": len(css),
                        "doctores_por_css": round(len(doctores) / len(css), 1),
                        "medidas_base": medidas},
            "css": css,
            "doctores": doctores,
        }, fh, ensure_ascii=False, indent=1)

    with open(os.path.join(salida_dir, "caso_negocio.json"), "w", encoding="utf-8") as fh:
        json.dump(caso, fh, ensure_ascii=False, indent=1)

    # El demo lee un .js en vez de un .json para que index.html abra con
    # doble clic (file://) sin servidor. Mismo contenido, envuelto en una variable.
    demo_dir = os.path.join(AQUI, "dashboard")
    os.makedirs(demo_dir, exist_ok=True)
    with open(os.path.join(salida_dir, "doctores.json"), encoding="utf-8") as fh:
        datos = fh.read()
    with open(os.path.join(demo_dir, "datos.js"), "w", encoding="utf-8") as fh:
        fh.write("window.DATOS = " + datos + ";\n")
        fh.write("window.CASO = " + json.dumps(caso, ensure_ascii=False) + ";\n")

    # Version de un solo archivo, para mandar por correo o WhatsApp:
    # el mismo index.html con los datos incrustados en lugar del <script src>.
    ruta_index = os.path.join(demo_dir, "index.html")
    if os.path.exists(ruta_index):
        with open(ruta_index, encoding="utf-8") as fh:
            html = fh.read()
        with open(os.path.join(demo_dir, "datos.js"), encoding="utf-8") as fh:
            js = fh.read()
        html = html.replace('<script src="datos.js"></script>', "<script>" + js + "</script>")
        with open(os.path.join(demo_dir, "Doctor360-todo-en-uno.html"), "w", encoding="utf-8") as fh:
            fh.write(html)

    print(f"OK  {len(doctores)} doctores · {len(css)} CSS · {totales['acciones']}")
    print(f"    base: {medidas}")
    print(f"    MRR total {totales['mrr_total']:,} · en riesgo {totales['mrr_en_riesgo']:,} · en crecimiento {totales['mrr_en_crecimiento']:,}")
    for nombre, e in caso["escenarios"].items():
        print(f"    {nombre:12s} {e['titular']:22s} tiempo {e['tiempo']['valor_mxn_anio']:>10,} · "
              f"churn {e['churn']['ingreso_protegido_12m_mxn']:>10,} · upsell {e['upsell']['ingreso_nuevo_12m_mxn']:>9,}")
    print("    pruebas: todas pasaron")


if __name__ == "__main__":
    main()
