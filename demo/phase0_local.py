"""
===================================================================
  🎵 PROYECTO CHORUS — Phase 0: Local Prototype Demo
===================================================================

This demo simulates the full Chorus ecosystem in-memory, without
any network. It demonstrates:

  1. Agent Registration — 4 specialized agents announce their skills
  2. Task Decomposition — A complex task is broken into sub-tasks
  3. Agent Discovery — The orchestrator finds the best agent per skill
  4. Job Execution — Each agent processes its assigned work
  5. Payment Settlement — Credits transfer from employer to agents
  6. Reputation Updates — Scores adjust based on success/failure

The 4 specialist agents:
  • TextAnalyzer    — Extracts numbers and entities from text
  • MathEngine      — Performs financial calculations
  • TranslatorAgent — Translates text between languages
  • SynthesizerAgent — Produces a formatted executive summary
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chorus.agent import AgentContainer
from chorus.orchestrator import Orchestrator, TaskPipeline, SubTask
from chorus.registry import Registry
from chorus.ledger import Ledger
from chorus.reputation import ReputationEngine


# =============================================================================
# AI Logic Functions (simulate specialized AI capabilities)
# =============================================================================

def logic_text_analyzer(input_data: dict) -> dict:
    """
    Simulates an NLP agent: extracts numbers and key entities from text.
    In production, this would call a real NLP model.
    """
    text = input_data.get("text", "")
    
    # Extract all numbers from text
    numbers = []
    for word in text.replace(",", "").replace(".", " ").split():
        # Handle currency symbols
        cleaned = word.strip("$€£")
        if cleaned.isdigit():
            numbers.append(int(cleaned))

    # Extract entities (simplified)
    entities = []
    keywords = {
        "ingresos": "revenue", "ventas": "sales", "ganancias": "profit",
        "costos": "costs", "Q1": "Q1", "Q2": "Q2", "Q3": "Q3", "Q4": "Q4",
        "trimestre": "quarter", "anual": "annual", "mensual": "monthly",
    }
    for word in text.split():
        clean = word.strip(".,;:")
        if clean in keywords:
            entities.append({"original": clean, "english": keywords[clean]})

    primary_number = numbers[0] if numbers else 0

    return {
        "primary_number": primary_number,
        "all_numbers": numbers,
        "entities": entities,
        "source_text": text[:100],
    }


def logic_math_engine(input_data: dict) -> dict:
    """
    Simulates a financial computation agent.
    Calculates projections, growth rates, and ROI.
    """
    number = input_data.get("primary_number", 0)
    growth_rate = input_data.get("growth_rate", 0.15)  # 15% default growth
    periods = input_data.get("periods", 4)  # 4 quarters

    projection = number * (1 + growth_rate) ** periods
    total_growth = projection - number
    roi_percentage = (total_growth / number * 100) if number > 0 else 0

    return {
        "original_value": number,
        "projected_value": round(projection, 2),
        "growth_rate": f"{growth_rate:.0%}",
        "periods": periods,
        "total_growth": round(total_growth, 2),
        "roi_percentage": round(roi_percentage, 2),
    }


def logic_translator(input_data: dict) -> dict:
    """
    Simulates a translation agent.
    Translates key financial terms and summaries to English.
    """
    translations = {
        "ingresos": "revenue", "netos": "net", "brutos": "gross",
        "ventas": "sales", "ganancias": "profit", "pérdidas": "losses",
        "crecimiento": "growth", "proyección": "projection",
        "trimestre": "quarter", "anual": "annual",
        "dólares": "dollars", "euros": "euros",
        "fueron": "were", "los": "the", "para": "for",
        "el": "the", "de": "of", "en": "in", "y": "and",
    }

    original = input_data.get("original_value", 0)
    projected = input_data.get("projected_value", 0)
    roi = input_data.get("roi_percentage", 0)
    growth_rate = input_data.get("growth_rate", "15%")
    periods = input_data.get("periods", 4)

    summary_en = (
        f"Financial Projection Report: "
        f"Original value ${original:,.2f} → "
        f"Projected value ${projected:,.2f} "
        f"({growth_rate} growth over {periods} periods). "
        f"Expected ROI: {roi}%."
    )

    return {
        "translated_summary": summary_en,
        "language": "en",
        "original_value": original,
        "projected_value": projected,
    }


def logic_synthesizer(input_data: dict) -> dict:
    """
    Simulates a report synthesis agent.
    Combines all previous results into a formatted executive summary.
    """
    summary = input_data.get("translated_summary", "N/A")
    original = input_data.get("original_value", 0)
    projected = input_data.get("projected_value", 0)
    roi = input_data.get("roi_percentage", 0)
    entities = input_data.get("entities", [])

    report = f"""
╔══════════════════════════════════════════════════════╗
║         CHORUS EXECUTIVE SUMMARY REPORT             ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  📊 Analysis Summary (EN):                           ║
║  {summary:<53s}║
║                                                      ║
║  📈 Key Metrics:                                     ║
║    • Original Value:  ${original:>12,.2f}              ║
║    • Projected Value: ${projected:>12,.2f}              ║
║    • Expected ROI:    {roi:>12.2f}%                 ║
║                                                      ║
║  🏷️  Detected Entities: {len(entities):>3d}                       ║
║                                                      ║
║  ✅ Status: ANALYSIS COMPLETE                        ║
║  🎵 Powered by Chorus Protocol v0.1                  ║
║                                                      ║
╚══════════════════════════════════════════════════════╝"""

    return {
        "executive_report": report,
        "status": "complete",
        "confidence": 0.95,
    }


# =============================================================================
# Main Demo
# =============================================================================

def main():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  🎵 PROYECTO CHORUS — Phase 0 Local Prototype       ║")
    print("║     The AI Skills Marketplace Protocol              ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # -------------------------------------------------------------------------
    # 1. Initialize the ecosystem
    # -------------------------------------------------------------------------
    reputation_engine = ReputationEngine()
    registry = Registry(reputation_engine)
    ledger = Ledger()

    orchestrator = Orchestrator(
        registry=registry,
        ledger=ledger,
        owner_id="chorus_user_001",
    )

    # Fund the user account
    ledger.create_account("chorus_user_001", initial_balance=10.0)

    # -------------------------------------------------------------------------
    # 2. Create and register 4 specialized agents
    # -------------------------------------------------------------------------
    agents = [
        AgentContainer(
            name="📝 Text-Analyst-3000",
            owner_id="nlp_solutions_inc",
            skill_name="analyze_text",
            skill_description="Extracts numbers and entities from unstructured text",
            cost=0.10,
            logic=logic_text_analyzer,
        ),
        AgentContainer(
            name="🔢 Math-Engine-9000",
            owner_id="quant_labs_llc",
            skill_name="calculate_projection",
            skill_description="Performs financial projections and ROI calculations",
            cost=0.08,
            logic=logic_math_engine,
        ),
        AgentContainer(
            name="🌐 Universal-Translator",
            owner_id="polyglot_ai_co",
            skill_name="translate_report",
            skill_description="Translates financial summaries to English",
            cost=0.05,
            logic=logic_translator,
        ),
        AgentContainer(
            name="📊 Report-Synthesizer",
            owner_id="executive_ai_group",
            skill_name="synthesize_report",
            skill_description="Combines analyses into executive summaries",
            cost=0.12,
            logic=logic_synthesizer,
        ),
    ]

    print("📡 Registering agents on the Chorus network...\n")
    for agent in agents:
        orchestrator.register_local_agent(agent)

    print(f"\n🌐 Network Status: {registry.count_agents()} agents | "
          f"{len(registry.list_all_skills())} skills available")
    print(f"   Skills: {', '.join(registry.list_all_skills())}")

    # -------------------------------------------------------------------------
    # 3. Define the complex task pipeline
    # -------------------------------------------------------------------------
    pipeline = TaskPipeline("Financial Analysis Pipeline", [
        SubTask(
            skill_name="analyze_text",
            build_input=lambda ctx: {"text": ctx["raw_report"]},
            description="Extract numbers and entities from the sales report",
            budget_fraction=0.25,
        ),
        SubTask(
            skill_name="calculate_projection",
            build_input=lambda ctx: {
                "primary_number": ctx.get("primary_number", 0),
                "growth_rate": 0.15,
                "periods": 4,
            },
            description="Calculate financial projections with 15% growth rate",
            budget_fraction=0.25,
        ),
        SubTask(
            skill_name="translate_report",
            build_input=lambda ctx: {
                "original_value": ctx.get("original_value", 0),
                "projected_value": ctx.get("projected_value", 0),
                "roi_percentage": ctx.get("roi_percentage", 0),
                "growth_rate": ctx.get("growth_rate", "15%"),
                "periods": ctx.get("periods", 4),
            },
            description="Translate the financial summary to English",
            budget_fraction=0.20,
        ),
        SubTask(
            skill_name="synthesize_report",
            build_input=lambda ctx: {
                "translated_summary": ctx.get("translated_summary", ""),
                "original_value": ctx.get("original_value", 0),
                "projected_value": ctx.get("projected_value", 0),
                "roi_percentage": ctx.get("roi_percentage", 0),
                "entities": ctx.get("entities", []),
            },
            description="Generate the final executive summary report",
            budget_fraction=0.30,
        ),
    ])

    # -------------------------------------------------------------------------
    # 4. Execute the pipeline
    # -------------------------------------------------------------------------
    initial_context = {
        "raw_report": (
            "Los ingresos netos para el Q3 fueron 42000 dólares, "
            "con ventas brutas de 58000 dólares y costos operativos de 16000 dólares. "
            "Las ganancias representan un crecimiento del 12% respecto al trimestre anterior."
        )
    }

    result = orchestrator.execute(
        pipeline=pipeline,
        initial_context=initial_context,
        budget=1.00,
    )

    # -------------------------------------------------------------------------
    # 5. Show the executive report
    # -------------------------------------------------------------------------
    if result.success and "executive_report" in result.final_output:
        print("\n" + result.final_output["executive_report"])

    # -------------------------------------------------------------------------
    # 6. Network economy report
    # -------------------------------------------------------------------------
    print("\n" + "="*60)
    print("💰 CHORUS ECONOMY REPORT")
    print("="*60)

    balances = ledger.get_all_balances()
    for owner, balance in sorted(balances.items()):
        print(f"   {owner:.<35s} {balance:>8.2f} credits")

    print(f"\n   📊 Total transactions: {ledger.get_transaction_count()}")
    print(f"   📊 Total volume: {ledger.get_total_volume():.2f} credits")

    # -------------------------------------------------------------------------
    # 7. Reputation leaderboard
    # -------------------------------------------------------------------------
    print("\n" + "="*60)
    print("⭐ REPUTATION LEADERBOARD")
    print("="*60)

    leaderboard = reputation_engine.get_leaderboard()
    for rank, (agent_id, score) in enumerate(leaderboard, 1):
        # Find agent name
        agent_info = registry.get_agent(agent_id)
        name = agent_info.agent_name if agent_info else agent_id[:8]
        stats = reputation_engine.get_stats(agent_id)
        print(f"   #{rank} {name:.<35s} {score:>5.1f} pts "
              f"({stats['successes']}✅ {stats['failures']}❌)")

    # -------------------------------------------------------------------------
    # 8. Audit log
    # -------------------------------------------------------------------------
    print("\n" + "="*60)
    print("📜 AUDIT LOG (All Transactions)")
    print("="*60)

    for record in ledger.get_audit_log():
        print(f"   {record.from_owner} → {record.to_owner}: "
              f"{record.amount:.2f} credits (job: {record.job_id[:8]}...)")

    print("\n✨ Phase 0 Prototype Demo Complete!")
    print("   The Chorus Protocol works. Ready for Phase 1: Network Alpha.\n")


if __name__ == "__main__":
    main()
