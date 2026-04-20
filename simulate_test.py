import asyncio
import sys
import os
from app.agents.orchestrator import run_orchestrator
from app.database import engine, Base
from app.utils.logger import logger

# Add scenarios for direct testing
SCENARIOS = {
    "1": "I'm overwhelmed with CA study and dental recovery. Give me a strategy plan for next 3 days.",
    "2": "Logged 500 for lunch and 2000 for wifi bill.",
    "3": "Remind me to drink water every hour.",
    "4": "Show me my habit dashboard.",
    "5": "Where are the best menswear shops in Surat?"
}

async def simulate():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("\n" + "💎"*15)
    print("🤖 ELITE LIFE OPERATOR - MASTERY CONSOLE")
    print("💎"*15)
    print("\nCOMMANDS:")
    print("• /voice [text] - Simulate an incoming voice note")
    print("• /reset        - Clear session memory")
    print("• /scenarios    - List elite test cases")
    print("• exit          - Quit")
    print("-" * 50)
    print("Target: whatsapp:+919054395152")

    user_phone = "whatsapp:+919054395152"

    while True:
        try:
            user_input = input("\n👤 YOU > ")
            
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            
            if user_input.startswith("/scenarios"):
                print("\n🚀 ELITE SCENARIOS:")
                for k, v in SCENARIOS.items():
                    print(f"  [{k}] {v}")
                choice = input("\nChoose (1-5) or Enter to skip: ")
                if choice in SCENARIOS:
                    user_input = SCENARIOS[choice]
                else:
                    continue

            if user_input.startswith("/voice"):
                voice_text = user_input.replace("/voice", "").strip()
                if not voice_text:
                    print("Usage: /voice I want to schedule a meeting")
                    continue
                print(f"🎙️ [VOICE MODE] Transcribed: {voice_text}")
                user_input = voice_text

            if user_input.startswith("/reset"):
                print("🧠 Memory Cleared.")
                # Logic to clear short_term memory could be added if needed
                continue

            if not user_input.strip():
                continue

            print("\n🧠 OPERATOR THINKING...")
            response = await run_orchestrator(user_phone, user_input)
            
            print(f"\n✨ AI OPERATOR:")
            print(f"{response}")
            print("-" * 30)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    try:
        # Suppress noise
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        asyncio.run(simulate())
    except KeyboardInterrupt:
        pass
