# inspect_brain.py
from agent.brain.memory import EpisodicMemory
import pandas as pd

def inspect():
    print("==================================================")
    print("🧠 BRAIN INSPECTOR")
    print("==================================================")
    
    # Load the real DB
    mem = EpisodicMemory(db_path="./memory_db")
    
    # Get all data
    data = mem.collection.get()
    
    if not data['documents']:
        print("❌ Memory is empty.")
        return

    print(f"📚 Total Memories: {len(data['documents'])}\n")
    
    # Create a pretty table
    df = pd.DataFrame({
        'Memory (Snippet)': [d[:80] + "..." if len(d) > 80 else d for d in data['documents']],
        'Type': [m.get('type', 'unknown') for m in data['metadatas']],
        'Timestamp': [m.get('timestamp', 0) for m in data['metadatas']]
    })
    
    # Sort by time (newest last)
    df = df.sort_values('Timestamp')
    
    print(df[['Type', 'Memory (Snippet)']].to_string(index=False))
    print("==================================================")

if __name__ == "__main__":
    try:
        inspect()
    except ImportError:
        print("Pandas not installed? Just printing raw list:")
        mem = EpisodicMemory(db_path="./memory_db")
        print(mem.collection.get())