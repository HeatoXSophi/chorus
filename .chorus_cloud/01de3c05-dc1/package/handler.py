def calcular_impuestos(data):
    """Tax calculator agent."""
    ingreso = data.get("ingreso", 0)
    pais = data.get("pais", "ES")
    tasas = {
        "ES": 0.21,  # Spain IVA
        "US": 0.25,  # US estimated
        "MX": 0.16,  # Mexico IVA
        "UK": 0.20,  # UK VAT
    }
    tasa = tasas.get(pais.upper(), 0.20)
    impuesto = round(ingreso * tasa, 2)
    return {
        "ingreso_bruto": ingreso,
        "tasa_aplicada": f"{tasa*100:.0f}%",
        "pais": pais.upper(),
        "impuesto": impuesto,
        "ingreso_neto": round(ingreso - impuesto, 2),
    }



# Alias for Chorus Cloud
handler = calcular_impuestos
