def resumir_texto(data):
    """Text summarizer agent (simple extraction)."""
    texto = data.get("texto", "")
    palabras = texto.split()
    total_palabras = len(palabras)

    # Simple extractive summary: first and last sentences
    oraciones = texto.replace("!", ".").replace("?", ".").split(".")
    oraciones = [o.strip() for o in oraciones if o.strip()]

    if len(oraciones) <= 2:
        resumen = texto
    else:
        resumen = f"{oraciones[0]}. {oraciones[-1]}."

    return {
        "resumen": resumen,
        "palabras_originales": total_palabras,
        "palabras_resumen": len(resumen.split()),
        "oraciones_originales": len(oraciones),
        "ratio_compresion": f"{len(resumen.split()) / max(total_palabras, 1) * 100:.0f}%",
    }



# Alias for Chorus Cloud
handler = resumir_texto
