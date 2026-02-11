"""
===================================================================
  🎵 CHORUS SDK — Developer Experience Demo
===================================================================

This demo shows the complete developer journey:

  1. Connect to the network
  2. Publish your OWN agents (just a Python function!)
  3. Discover agents by skill
  4. Hire the best one with one line
  5. Chain agents into a pipeline
  6. Check your earnings

This is how the SDK makes it "insultingly easy" to join Chorus.

PREREQUISITES:
  Terminal 1: uvicorn services.registry_service:app --port 8001
  Terminal 2: uvicorn services.ledger_service:app --port 8002
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chorus_sdk as chorus


# =============================================================================
# Step 1: Define your AI functions (this is ALL a developer needs to write)
# =============================================================================

def sentiment_analyzer(data: dict) -> dict:
    """Analyzes sentiment of text. (Simulated)"""
    text = data.get("text", "").lower()
    positive = ["great", "good", "excellent", "amazing", "love", "happy", "profit", "growth"]
    negative = ["bad", "terrible", "loss", "decline", "hate", "poor", "fail"]

    pos_count = sum(1 for w in positive if w in text)
    neg_count = sum(1 for w in negative if w in text)
    total = pos_count + neg_count or 1

    score = (pos_count - neg_count) / total
    label = "POSITIVE" if score > 0 else "NEGATIVE" if score < 0 else "NEUTRAL"

    return {
        "sentiment": label,
        "score": round(score, 2),
        "confidence": round(0.7 + abs(score) * 0.3, 2),
        "positive_signals": pos_count,
        "negative_signals": neg_count,
    }


def keyword_extractor(data: dict) -> dict:
    """Extracts keywords from text. (Simulated)"""
    text = data.get("text", "")
    # Simple keyword extraction: words > 5 chars, deduplicated
    words = text.replace(",", "").replace(".", "").replace(":", "").split()
    keywords = list(set(w.lower() for w in words if len(w) > 5 and w[0].isupper()))
    return {
        "keywords": keywords[:10],
        "count": len(keywords[:10]),
    }


def report_generator(data: dict) -> dict:
    """Generates a formatted report. (Simulated)"""
    sentiment = data.get("sentiment", "UNKNOWN")
    score = data.get("score", 0)
    confidence = data.get("confidence", 0)
    keywords = data.get("keywords", [])

    report = (
        f"=== ANALYSIS REPORT ===\n"
        f"Sentiment: {sentiment} (score: {score}, confidence: {confidence})\n"
        f"Keywords: {', '.join(keywords) if keywords else 'none detected'}\n"
        f"Recommendation: {'Proceed with caution' if sentiment == 'NEGATIVE' else 'Outlook favorable'}"
    )
    return {"report": report, "actionable": sentiment != "NEUTRAL"}


# =============================================================================
# Main Demo
# =============================================================================

def main():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  🎵 CHORUS SDK — Developer Experience Demo          ║")
    print("║     See how easy it is to join the AI marketplace   ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # -----------------------------------------------------------------
    # 1. Connect to the network (ONE LINE)
    # -----------------------------------------------------------------
    print("=" * 55)
    print("  STEP 1: Connect to Chorus Network")
    print("=" * 55)
    print()
    print('  >>> chorus.connect(owner_id="demo_developer")')

    try:
        status = chorus.connect(owner_id="demo_developer", initial_credits=50.0)
        print(f"  ✅ Connected! {status.agents_online} agents online, "
              f"{status.total_skills} skills available")
        if status.available_skills:
            print(f"     Skills: {', '.join(status.available_skills)}")
    except chorus.ConnectionError as e:
        print(f"  ❌ {e.message}")
        print("  Start the services first:")
        print("    uvicorn services.registry_service:app --port 8001")
        print("    uvicorn services.ledger_service:app --port 8002")
        return

    # -----------------------------------------------------------------
    # 2. Publish YOUR OWN agents (THREE LINES per agent!)
    # -----------------------------------------------------------------
    print()
    print("=" * 55)
    print("  STEP 2: Publish Your Agents (just a function!)")
    print("=" * 55)
    print()

    agents_to_publish = [
        ("SentimentBot-Pro", "analyze_sentiment", 0.08, sentiment_analyzer, "Analyzes text sentiment"),
        ("KeywordExtractor", "extract_keywords", 0.05, keyword_extractor, "Extracts key terms"),
        ("ReportWriter-AI", "generate_report", 0.10, report_generator, "Generates analysis reports"),
    ]

    for name, skill, cost, handler, desc in agents_to_publish:
        print(f'  >>> chorus.publish(name="{name}", skill="{skill}", cost={cost})')
        try:
            info = chorus.publish(
                name=name,
                skill=skill,
                cost=cost,
                handler=handler,
                owner_id="indie_dev_pablo",
                description=desc,
            )
            print(f"  ✅ Published! Port: {info['port']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    time.sleep(1)

    # -----------------------------------------------------------------
    # 3. Discover agents on the network
    # -----------------------------------------------------------------
    print()
    print("=" * 55)
    print("  STEP 3: Discover Agents")
    print("=" * 55)
    print()

    print('  >>> agents = chorus.discover("analyze_sentiment")')
    agents = chorus.discover("analyze_sentiment")
    print(f"  Found {len(agents)} agent(s):")
    for a in agents:
        print(f"    🤖 {a}")

    # -----------------------------------------------------------------
    # 4. Hire an agent (ONE LINE)
    # -----------------------------------------------------------------
    print()
    print("=" * 55)
    print("  STEP 4: Hire an Agent")
    print("=" * 55)
    print()

    test_text = (
        "The company reported excellent growth in Q3 with amazing "
        "profit margins. Revenue growth exceeded expectations."
    )

    print(f'  >>> result = chorus.hire_best("analyze_sentiment", {{"text": "..."}})')

    try:
        result = chorus.hire_best(
            "analyze_sentiment",
            {"text": test_text},
            budget=0.50,
        )
        print(f"  ✅ {result}")
        print(f"     Sentiment: {result['sentiment']} (score: {result['score']})")
        print(f"     Confidence: {result['confidence']}")
    except chorus.ChorusError as e:
        print(f"  ❌ {e.message}")

    # -----------------------------------------------------------------
    # 5. Pipeline — chain multiple agents
    # -----------------------------------------------------------------
    print()
    print("=" * 55)
    print("  STEP 5: Pipeline — Chain Agents Together")
    print("=" * 55)
    print()

    print("  >>> pipeline = chorus.Pipeline('Full Text Analysis')")
    print("  ...   .step('analyze_sentiment', ...)")
    print("  ...   .step('extract_keywords', ...)")
    print("  ...   .step('generate_report', ...)")
    print("  ...   .run({...}, budget=1.0)")
    print()

    pipeline_result = (
        chorus.Pipeline("Full Text Analysis")
        .step(
            "analyze_sentiment",
            lambda ctx: {"text": ctx["text"]},
            budget_fraction=0.3,
            label="Sentiment Analysis",
        )
        .step(
            "extract_keywords",
            lambda ctx: {"text": ctx["text"]},
            budget_fraction=0.3,
            label="Keyword Extraction",
        )
        .step(
            "generate_report",
            lambda ctx: {
                "sentiment": ctx.get("sentiment", ""),
                "score": ctx.get("score", 0),
                "confidence": ctx.get("confidence", 0),
                "keywords": ctx.get("keywords", []),
            },
            budget_fraction=0.4,
            label="Report Generation",
        )
        .run(
            context={
                "text": (
                    "The quarterly earnings call revealed excellent results. "
                    "Revenue Growth surpassed Analyst Expectations, and the "
                    "Board declared a special Dividend. However, International "
                    "Markets showed some decline in Consumer Spending."
                )
            },
            budget=1.0,
        )
    )

    if pipeline_result.success and "report" in pipeline_result.context:
        print(f"\n  📄 Final Report:")
        for line in pipeline_result.context["report"].split("\n"):
            print(f"     {line}")

    # -----------------------------------------------------------------
    # 6. Check your finances
    # -----------------------------------------------------------------
    print()
    print("=" * 55)
    print("  STEP 6: Check Your Earnings")
    print("=" * 55)
    print()

    print('  >>> chorus.get_balance("demo_developer")')
    user_balance = chorus.get_balance("demo_developer")
    print(f"  💰 User balance: {user_balance:.2f} credits")

    print('  >>> chorus.get_balance("indie_dev_pablo")')
    dev_balance = chorus.get_balance("indie_dev_pablo")
    print(f"  💰 Developer earnings: {dev_balance:.2f} credits")

    economy = chorus.get_economy()
    print(f"\n  📊 Network economy:")
    print(f"     Accounts: {economy.total_accounts}")
    print(f"     Transactions: {economy.total_transactions}")
    print(f"     Volume: {economy.total_volume:.2f} credits")

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  ✨ SDK Demo Complete!                               ║")
    print("║                                                      ║")
    print("║  What we just did:                                   ║")
    print("║    1. Connected to Chorus       → 1 line             ║")
    print("║    2. Published 3 AI agents     → 3 lines each       ║")
    print("║    3. Discovered agents         → 1 line             ║")
    print("║    4. Hired an agent            → 1 line             ║")
    print("║    5. Chained 3 agents          → Pipeline (fluent)  ║")
    print("║    6. Checked earnings          → 1 line             ║")
    print("║                                                      ║")
    print("║  From zero to AI marketplace in minutes. 🎵          ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
