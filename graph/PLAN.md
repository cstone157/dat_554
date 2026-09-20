# LangGraph Plan: AI Function-Code Generator & Evaluator

## Overview

A LangGraph workflow that accepts a **user description** of a Python function, uses an LLM to **generate the code**, writes it to `/tmp`, **executes it live**, then feeds the execution results back to the LLM for **evaluation/correction feedback**.

### Graph Topology (Linear Chain)

```
  [Input] → [PromptUserNode] → [GenerateCodeNode] → [RunCodeNode] → [EvaluateNode] → [End]
```

---

## Nodes

### Node 1 — `prompt_user` (Entry Point)

**Responsibility:** Collect the user's function description.

**Approach options:**

| Option | Pros | Cons |
|--------|------|------|
| A. Interactive CLI (`input()`) | Zero dependencies, immediate | Blocks; no streaming |
| B. LangGraph `interrupt_before` + `AppenderInterruptAction` | Native to LangGraph's human-in-the-loop pattern | Requires `update_state`; slightly more boilerplate |

**Recommendation:** Use **Option A** for simplicity — start with a CLI prompt, upgrade to the interrupt pattern later if interactive streaming is desired.

**State update:**
```python
state["user_description"] = <cli input>
return {"user_description": state["user_description"]}
```

---

### Node 2 — `generate_code`

**Responsibility:** Send the description to an LLM and parse the generated code back out.

**Prompt strategy:**

```
You are a Python coding assistant. Write a complete, runnable Python function
based on this description:

{user_description}

Output ONLY valid Python code between markdown code fences:
```python
<your code here>
```

The function should be self-contained with a `if __name__ == "__main__":` block
that calls the function and prints the result.
```

**Implementation details:**
- Use `langchain-openai` (or another adapter) for the LLM call.
- Parse code from between triple-backticks using regex: `` `(python)?\s*\n(.*?)\n`` `.````
- Save raw text → `state["generated_code"]`.
- **Error handling:** If parsing fails, store an error message and let the next node pass it through (or add a conditional edge back to re-prompt).

**State update:**
```python
response = llm.invoke(prompt)
code = extract_python_code(response.content)
state["generated_code"] = code
return {"generated_code": code}
```

---

### Node 3 — `run_code`

**Responsibility:** Write generated code to `/tmp` and execute it.

**Steps:**

1. Generate a unique filename: `f"/tmp/llm_generated_{uuid.uuid4().hex[:8]}.py"`
2. Write the code: `Path(tmp_path).write_text(state["generated_code"])`
3. Execute via `subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=30)`
4. Capture:
   - `stdout` → `state["execution_stdout"]`
   - `stderr` → `state["execution_stderr"]`
   - `returncode` → `state["execution_returncode"]`
5. On exception (timeout, missing Python, etc.), populate error fields instead.

**State update:**
```python
tmp_path = write_and_run(state["generated_code"])
result = {
    "stdout": result.stdout,
    "stderr": result.stderr,
    "returncode": result.returncode,
}
return {"execution_result": result}
```

> **Security note:** `/tmp` sandboxing limits damage but doesn't eliminate risk. Avoid in production without additional isolation (e.g., Docker containers).

---

### Node 4 — `evaluate`

**Responsibility:** Feed the execution results back to the LLM for analysis.

**Prompt strategy:**

```
The following code was generated from this description:
"{user_description}"

Generated code:
{generated_code}

Execution results:
- Return code: {returncode}
- Stdout: {stdout}
- Stderr: {stderr}

Evaluate the output. If there are errors, explain them and suggest fixes.
If it ran successfully, confirm correctness against the description.
```

**Implementation:**
- Same LLM call pattern as Node 2.
- Store in `state["evaluation"]`.

**State update:**
```python
response = llm.invoke(evaluate_prompt)
return {"evaluation": response.content}
```

---

## Conditional Logic (Future Enhancement)

Add a conditional edge after `evaluate` to create a correction loop:

```
evaluate → should_correct? → generate_code  (loop back on error)
               ↓
          end                    (on success)
```

Decision criterion: LLM returns `"CORRECT"` vs. an error explanation, or simple check on `returncode == 0`.

---

## Dependencies (`requirements.txt`)

```txt
langgraph>=0.2.0
langchain-openai>=0.1.0
python-dotenv>=1.0.0
```

**Runtime env vars (`.env`):**
```env
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini          # or any supported model
```

---

## State Schema (TypedDict)

```python
from typing import TypedDict

class AgentState(TypedDict):
    user_description:   str          # User's function description
    generated_code:     str          # Code returned by the LLM
    execution_result:   dict         # {"stdout": ..., "stderr": ..., "returncode": ...}
    evaluation:         str          # LLM's evaluation feedback
```

---

## Implementation Steps (in order)

| # | Task | Files |
|---|------|-------|
| 1 | Fill `requirements.txt` with dependencies | `graph/requirements.txt` |
| 2 | Create `.env_example` with `OPENAI_API_KEY`, `MODEL_NAME` | `graph/.env_example` |
| 3 | Define `AgentState` TypedDict | `graph/main.py` |
| 4 | Implement `prompt_user` node (CLI input) | `graph/main.py` |
| 5 | Implement `generate_code` node (LLM → code extraction) | `graph/main.py` |
| 6 | Implement `run_code` node (write `/tmp`, `subprocess.run`) | `graph/main.py` |
| 7 | Implement `evaluate` node (LLM evaluation prompt) | `graph/main.py` |
| 8 | Wire the graph: `StateGraph → add_nodes → compile` | `graph/main.py` |
| 9 | Add CLI entry point (`if __name__ == "__main__"`) | `graph/main.py` |
| 10 (optional) | Add conditional correction loop from `evaluate → generate_code` | `graph/main.py` |

---

## File Structure After Implementation

```
graph/
├── .env            # API key (git-ignored)
├── .env_example    # Template for new users
├── main.py         # LangGraph app (~200 lines estimated)
├── requirements.txt
└── PLAN.md         # This file
```
