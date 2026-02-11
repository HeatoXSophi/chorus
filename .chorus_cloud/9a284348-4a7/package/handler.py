def saludar(data):
    """A simple greeter agent."""
    nombre = data.get("nombre", "Mundo")
    idioma = data.get("idioma", "es")
    saludos = {
        "es": f"¡Hola, {nombre}! Soy un agente serverless de Chorus.",
        "en": f"Hello, {nombre}! I'm a serverless Chorus agent.",
        "fr": f"Bonjour, {nombre}! Je suis un agent serverless de Chorus.",
        "pt": f"Olá, {nombre}! Sou um agente serverless do Chorus.",
    }
    return {
        "mensaje": saludos.get(idioma, saludos["es"]),
        "idioma": idioma,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }



# Alias for Chorus Cloud
handler = saludar
