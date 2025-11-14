# Battle Bot Unit Tests

Lightweight unit tests for battle bot logic components. These tests don't require the full emulator environment and run quickly.

---

## 🎯 Test Files

### `test_species_extraction.py` ⭐ **Core Logic Test**
**Purpose**: Test species extraction from VLM dialogue  
**Coverage**:
- ✅ "sent out" pattern matching
- ✅ "Wild X appeared" pattern matching
- ✅ VLM misspelling corrections
- ✅ Type effectiveness logic (ABSORB vs POUND)

**No dependencies**: Pure Python logic testing

**Run it**:
```bash
python tests/battle/unit/test_species_extraction.py
```

**Expected output**:
```
✅ PASS: 'YOUNGSTER CALVIN sent out POOCHYENA!' → POOCHYENA
✅ PASS: 'Wild ZIGZAGOON appeared!' → ZIGZAGOON
✅ PASS: POOCHYENA → ABSORB
✅ PASS: TAILLOW → POUND
```

---

### `test_fuzzy_matching.py` 🔧 **Algorithm Test**
**Purpose**: Test fuzzy string matching for Pokemon names  
**Coverage**:
- ✅ Extra letters: `POOOCHYENA` → `POOCHYENA`
- ✅ Missing letters: `POCHYENA` → `POOCHYENA`
- ✅ Substituted letters: `POOCHIVIRA` → `POOCHYENA`
- ✅ Transposed letters: `POOCHEYNA` → `POOCHYENA`

**Algorithm**: Python's `difflib.get_close_matches()` with 60% similarity threshold

**Run it**:
```bash
python tests/battle/unit/test_fuzzy_matching.py
```

**Expected output**:
```
✅ PASS: 'POOCHENNA' → 'POOCHYENA'
✅ PASS: 'POOHVENA' → 'POOCHYENA' (82.35% similar)
19/20 tests passed
```

---

### `test_sent_pattern.py` 🔍 **Pattern Matching Test**
**Purpose**: Test dialogue pattern recognition  
**Coverage**:
- ✅ "sent out" pattern (standard)
- ✅ "sent" pattern (VLM drops "out")
- ✅ Trainer name validation
- ✅ False positive rejection

**Run it**:
```bash
python tests/battle/unit/test_sent_pattern.py
```

---

### `test_full_flow.py` 🌊 **Integration Test**
**Purpose**: Test complete flow from VLM output to move selection  
**Flow**: `VLM dialogue → Extract species → Fuzzy match → Type check → Move decision`

**Run it**:
```bash
python tests/battle/unit/test_full_flow.py
```

**Example output**:
```
📝 VLM says: 'YOUNGSTER CALVIN sent out POOCHENNA!'
   📤 Extracted: 'POOCHENNA'
   🔧 Fuzzy matched: 'POOCHENNA' → 'POOCHYENA'
   ✅ Corrected: 'POOCHYENA'
   ✅ PASS: Species=POOCHYENA, Move=ABSORB
```

---

## 📊 Running All Unit Tests

```bash
# Run all unit tests sequentially
cd /home/kevin/Documents/pokeagent-speedrun
python tests/battle/unit/test_species_extraction.py
python tests/battle/unit/test_fuzzy_matching.py
python tests/battle/unit/test_sent_pattern.py
python tests/battle/unit/test_full_flow.py
```

---

## 🔗 Related Documentation

- **Fuzzy Matching Design**: `docs/development/FUZZY_MATCHING.md`
- **Species Extraction Implementation**: `docs/development/SPECIES_EXTRACTION_FIX.md`
- **Battle Bot Code**: `agent/battle_bot.py`

---

## ✅ Success Criteria

All tests should pass with:
- ✅ Species extraction accuracy
- ✅ Fuzzy matching corrections (19/20 minimum)
- ✅ Correct move selection (ABSORB vs POUND)
- ✅ No false positives in pattern matching

---

## 🚀 Quick Test

To verify everything works:
```bash
cd /home/kevin/Documents/pokeagent-speedrun
python tests/battle/unit/test_species_extraction.py && echo "✅ Unit tests passing!"
```
