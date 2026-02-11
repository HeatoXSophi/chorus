"""
╔══════════════════════════════════════════════════════════════╗
║  🚀 CHORUS — Operación Éxodo: Serverless Demo               ║
║     Deploy agents to the cloud — fire and forget!            ║
╚══════════════════════════════════════════════════════════════╝

This demo shows how a developer can publish an agent with
serverless=True and walk away. The agent lives 24/7 in the
Chorus Cloud without the developer's machine running.

Prerequisites:
  1. Registry Service:  uvicorn services.registry_service:app --port 8001
  2. Ledger Service:    uvicorn services.ledger_service:app --port 8002
  3. Deploy Service:    uvicorn services.deploy_service:app --port 8003

Usage:
  python demo/serverless_demo.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chorus_sdk as chorus


# ═════════════════════════════════════════════════════════════
# STEP 0: Define your AI functions (this is all you need!)
# ═════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════
# MAIN DEMO
# ═════════════════════════════════════════════════════════════

def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  🚀 OPERACIÓN ÉXODO — Serverless Deployment Demo           ║")
    print("║     Deploy agents to Chorus Cloud: fire & forget!          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    # ─── Step 1: Connect ──────────────────────────────
    print("=" * 60)
    print("  STEP 1: Connect to Chorus Network")
    print("=" * 60)
    print()
    
    print("  >>> chorus.connect(owner_id=\"exodus_developer\")")
    try:
        status = chorus.connect(owner_id="exodus_developer")
        print(f"  ✅ Connected! {status.agents_online} agents online")
    except Exception as e:
        print(f"  ❌ Cannot connect: {e}")
        print(f"\n  Make sure services are running:")
        print(f"    uvicorn services.registry_service:app --port 8001")
        print(f"    uvicorn services.ledger_service:app --port 8002") 
        print(f"    uvicorn services.deploy_service:app --port 8003")
        return
    
    print()
    
    # ─── Step 2: Deploy serverless agents ─────────────
    print("=" * 60)
    print("  STEP 2: Deploy Serverless Agents (☁️ → Cloud)")
    print("=" * 60)
    print()
    
    agents_to_deploy = [
        ("HolaMundoServerless", "saludar", saludar, 0.001),
        ("TaxCalculator-Cloud", "calcular_impuestos", calcular_impuestos, 0.01),
        ("ResumidorTexto-Cloud", "resumir_texto", resumir_texto, 0.02),
    ]
    
    deployed = []
    for name, skill, handler, cost in agents_to_deploy:
        print(f"  >>> chorus.publish(name=\"{name}\", skill=\"{skill}\", serverless=True)")
        try:
            info = chorus.publish(
                name=name,
                skill=skill,
                cost=cost,
                handler=handler,
                owner_id="exodus_developer",
                serverless=True,
            )
            print(f"  ☁️  Deployed! Endpoint: {info.get('endpoint', 'N/A')}")
            deployed.append(info)
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            if "Deploy Service" in str(e):
                print(f"\n  The Deploy Service is not running. Start it:")
                print(f"    uvicorn services.deploy_service:app --port 8003")
                return
    
    print()
    print(f"  🎉 {len(deployed)} agents deployed to Chorus Cloud!")
    print(f"  💤 You can now close your terminal. They run 24/7.")
    print()
    
    # ─── Step 3: Verify they work ─────────────────────
    print("=" * 60)
    print("  STEP 3: Test the Serverless Agents")
    print("=" * 60)
    print()
    
    time.sleep(1)
    
    # Test saludar
    print("  >>> chorus.hire_best(\"saludar\", {\"nombre\": \"Pablo\", \"idioma\": \"es\"})")
    try:
        result = chorus.hire_best("saludar", {"nombre": "Pablo", "idioma": "es"}, budget=1.0)
        print(f"  ✅ {result}")
        print(f"     Respuesta: {result.output.get('mensaje', 'N/A')}")
    except Exception as e:
        print(f"  ⚠️  {e}")
    print()
    
    # Test calcular_impuestos
    print("  >>> chorus.hire_best(\"calcular_impuestos\", {\"ingreso\": 50000, \"pais\": \"ES\"})")
    try:
        result = chorus.hire_best("calcular_impuestos", {"ingreso": 50000, "pais": "ES"}, budget=1.0)
        print(f"  ✅ {result}")
        out = result.output
        print(f"     Ingreso: {out.get('ingreso_bruto')} → Neto: {out.get('ingreso_neto')} ({out.get('tasa_aplicada')} impuesto)")
    except Exception as e:
        print(f"  ⚠️  {e}")
    print()
    
    # Test resumir_texto
    largo_texto = (
        "El ecosistema de inteligencia artificial está creciendo a un ritmo sin precedentes. "
        "Las empresas están adoptando modelos de lenguaje para automatizar tareas complejas. "
        "Sin embargo, el costo de entrenar y mantener estos modelos sigue siendo elevado. "
        "Chorus propone una solución: un marketplace abierto donde los desarrolladores pueden "
        "publicar y monetizar sus agentes de IA. Con la nueva capacidad serverless, publicar "
        "un agente es tan simple como escribir una función."
    )
    print(f"  >>> chorus.hire_best(\"resumir_texto\", {{\"texto\": \"[artículo largo...]\"}})")
    try:
        result = chorus.hire_best("resumir_texto", {"texto": largo_texto}, budget=1.0)
        print(f"  ✅ {result}")
        out = result.output
        print(f"     Resumen: {out.get('resumen')}")
        print(f"     Compresión: {out.get('ratio_compresion')}")
    except Exception as e:
        print(f"  ⚠️  {e}")
    print()
    
    # ─── Step 4: Check economy ────────────────────────
    print("=" * 60)
    print("  STEP 4: Check Cloud Economics")
    print("=" * 60)
    print()
    
    balance = chorus.get_balance("exodus_developer")
    dev_earnings = chorus.get_balance("exodus_developer")
    economy = chorus.get_economy()
    
    print(f"  >>> chorus.get_balance(\"exodus_developer\")")
    print(f"  💰 Developer balance: {balance:.4f} credits")
    print()
    print(f"  📊 Network economy:")
    print(f"     Accounts: {economy.total_accounts}")
    print(f"     Transactions: {economy.total_transactions}")
    print(f"     Total volume: {economy.total_volume:.4f} credits")
    print()
    
    # ─── Finale ───────────────────────────────────────
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  ✨ Operación Éxodo — Complete!                             ║")
    print("║                                                              ║")
    print("║  What just happened:                                         ║")
    print("║    1. Defined 3 Python functions                    ← Easy   ║")
    print("║    2. Published them with serverless=True           ← 1 line ║")
    print("║    3. They deployed to Chorus Cloud automatically   ← Magic  ║")
    print("║    4. Hired them from another user's perspective    ← Works! ║")
    print("║    5. Payments processed automatically              ← $$     ║")
    print("║                                                              ║")
    print("║  The developer can now CLOSE THEIR TERMINAL.                 ║")
    print("║  The agents run 24/7 in the Chorus Cloud. 🚀                ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
