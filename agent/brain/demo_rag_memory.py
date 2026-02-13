# demo_rag_memory.py
from agent.brain.memory import EpisodicMemory

def run_demo():
    print("==================================================")
    print("🧠 POKEMON AGENT: RAG MEMORY SYSTEM DEMO (PHASE 2)")
    print("==================================================")
    
    # 1. Initialize (use demo-specific path to avoid wiping real data)
    memory = EpisodicMemory(db_path="./memory_db_demo")
    memory.clear_memory() # Start fresh for the demo
    
    # 2. Logging Phase (Simulating Gameplay)
    print("\n--- PHASE 1: LOGGING EVENTS ---")
    events = [
        "Started game in Littleroot Town.",
        "Mom gave me the Running Shoes.",
        "Route 101 has wild Poochyena.",
        "Arrived in Oldale Town.",
        "Spoke to an NPC who is sketching footprints.",
        "The Sketch Artist says: 'I am sketching rare footprints. Don't disturb me.'",
        "Route 103 is blocked by the Sketch Artist.",
        "Bought 5 Potions at the Mart."
    ]
    
    for text in events:
        memory.log_event(text, {"type": "game_log"})
        print(f"📝 Logged: {text}")

    # 3. Retrieval Phase (The "Magic")
    print("\n--- PHASE 2: SEMANTIC RETRIEVAL ---")
    
    # Notice: The query does NOT contain the words "Sketch" or "Artist"
    query = "Why can't I go North?"
    print(f"❓ Agent Query: '{query}'")
    
    context = memory.retrieve_relevant(query, n_results=2)
    
    print("\n📂 RETRIEVED CONTEXT:")
    print(context)
    
    # 4. Validation
    expected_hits = [
        "Route 103 is blocked by the Sketch Artist.",
        "The Sketch Artist says: 'I am sketching rare footprints. Don't disturb me.'",
    ]
    if any(hit in context for hit in expected_hits):
        print("\n✅ SUCCESS: The system linked 'can't go North' to the blocking NPC.")
    else:
        print("\n❌ FAIL: Context did not contain the answer.")

if __name__ == "__main__":
    run_demo()