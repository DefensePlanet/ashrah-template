# Mistral Speed Optimization Guide

## Overview

This document covers the speed optimizations applied to Mistral for {{ORCHESTRATOR_NAME}} voice agent responses, targeting **<500ms latency** for conversational AI.

## Optimization Strategy

### 1. **Custom Optimized Model** (`mistral-fast`)

Created a speed-optimized variant of Mistral with aggressive performance tuning:

**Key Parameters:**
- `num_ctx: 4096` - Reduced context window (vs 8192 default) for faster processing
- `num_predict: 150` - Limit output tokens for concise voice responses
- `temperature: 0.7` - Balanced creativity/consistency
- `top_p: 0.9` / `top_k: 40` - Optimized sampling
- `num_batch: 512` - Batch size for prompt processing
- `num_thread: 8` - CPU thread allocation
- `num_gpu: 1` - GPU acceleration when available

**Creation:**
```bash
cd {{CATALYST_ROOT}}/tools/{{ORCHESTRATOR_NAME_LOWER}}-gateway
ollama create mistral-fast -f Modelfile.mistral-fast
```

**Model File:** `Modelfile.mistral-fast`

### 2. **Streaming Response** (TTFT Optimization)

Switched from blocking requests to **streaming** for Time-To-First-Token (TTFT) improvements:

**Before:**
```python
response = await client.post(..., json={"stream": False})
```
- Waits for complete response
- Higher perceived latency

**After:**
```python
async with client.stream("POST", ..., json={"stream": True}) as response:
    async for line in response.aiter_lines():
        # Process tokens as they arrive
```
- Starts processing immediately
- Lower perceived latency
- Better for real-time voice

### 3. **Context Window Management**

**Conversation History Limits:**
- Reduced from 20 messages → **10 messages** max
- Shorter context = faster inference
- Still maintains conversation coherence

**Token Budget:**
- Added `max_history_tokens: 2048` tracking
- Prevents context bloat over long sessions

### 4. **Prompt Engineering**

**System Prompt Optimized for Brevity:**
```
- Keep responses concise (1-3 sentences)
- Brief acknowledgments for simple requests
- More detail only when specifically asked
```

This guides the model toward shorter, faster responses naturally.

### 5. **Code-Level Optimizations**

**voice_agent.py:**
- Default model changed to `mistral-fast`
- Streaming implementation with async iteration
- Reduced history management overhead
- JSON parsing optimizations

**pipecat_gateway.py:**
- Default model changed to `mistral-fast`
- Benefits from Modelfile optimizations automatically

## Performance Benchmarks

### Baseline (mistral:latest)
```
Total: 9.73s
Load: 2.78s
Prompt eval: 4.30s (41.19 tokens/s)
Eval: 2.53s (20.19 tokens/s)
```

### Target (mistral-fast + streaming)
- **TTFT:** <500ms (first token arrives)
- **Total latency:** 4-6s for typical voice response
- **Perceived latency:** <1s (user sees/hears activity immediately)

## Usage

### Environment Variables

```bash
# Use optimized model (default)
export OLLAMA_MODEL=mistral-fast

# Or override if needed
export OLLAMA_MODEL=mistral  # fallback to standard
```

### Testing Performance

```bash
# Quick response test
time ollama run mistral-fast "What time is it?"

# Verbose metrics
ollama run mistral-fast "Hello {{ORCHESTRATOR_NAME}}" --verbose
```

### Integration with {{ORCHESTRATOR_NAME}} Gateway

Both `voice_agent.py` and `pipecat_gateway.py` now default to `mistral-fast`:

```bash
cd {{CATALYST_ROOT}}/tools/{{ORCHESTRATOR_NAME_LOWER}}-gateway
python3 pipecat_gateway.py  # Uses mistral-fast automatically
```

## Further Optimization Opportunities

### 1. **Model Quantization**
- Current: Full precision (4.4GB)
- Potential: 4-bit quantization (Q4_K_M)
- Trade-off: ~50% faster, slight quality loss

```bash
# Create quantized version
ollama pull mistral:7b-instruct-q4_K_M
```

### 2. **GPU Acceleration**
- Current: CPU inference (M3 Max)
- Potential: Metal GPU acceleration
- Ensure `num_gpu: 1` is set (already configured)

Check GPU usage:
```bash
ollama ps  # Shows if GPU is being used
```

### 3. **Smaller Model Alternatives**

If Mistral 7B is still too slow:
- **Phi-3 Mini (3.8B):** Much faster, good quality
- **TinyLlama (1.1B):** Ultra-fast, basic responses
- **Qwen2.5 (3B):** Balanced speed/quality

```bash
# Test alternatives
ollama pull phi3:mini
ollama pull tinyllama
```

### 4. **Prompt Caching**

For repeated queries, implement response caching:
- Cache common questions ("What time is it?", "Set a reminder")
- Skip LLM entirely for exact matches
- Use Redis or in-memory cache

### 5. **Preloading Model**

Reduce cold-start latency:
```bash
# Keep model loaded in memory
ollama run mistral-fast "" --keepalive 24h
```

Or in systemd/launchd service config.

### 6. **Hardware Optimizations**

**Current Hardware (M3 Max):**
- 16-core CPU
- 40-core GPU
- 128GB RAM

**Tuning for M3:**
```
PARAMETER num_thread 12  # Leave cores for other tasks
PARAMETER num_gpu 1      # Metal acceleration
PARAMETER num_batch 1024 # Larger batches on powerful hardware
```

## Monitoring Performance

### Key Metrics to Track

1. **Time To First Token (TTFT)**
   - Target: <500ms
   - Measure: Time from request to first response chunk

2. **Tokens Per Second**
   - Prompt eval: >50 tokens/s
   - Generation: >25 tokens/s

3. **Total Latency**
   - Target: <5s for typical response
   - Includes TTFT + generation + TTS

### Logging

Enable verbose logging in `voice_agent.py`:
```python
logger.info(f"LLM response time: {duration:.2f}s")
logger.info(f"Tokens generated: {token_count}")
logger.info(f"Tokens/sec: {token_count/duration:.2f}")
```

## Troubleshooting

### Model Not Found
```bash
ollama list  # Verify mistral-fast exists
ollama create mistral-fast -f Modelfile.mistral-fast  # Recreate if needed
```

### Slow Performance
1. Check GPU usage: `ollama ps`
2. Verify no other heavy processes running
3. Consider smaller model (phi3:mini)
4. Enable verbose logging to identify bottleneck

### Quality Degradation
If responses are too brief or poor quality:
1. Increase `num_predict` (150 → 200)
2. Raise `temperature` (0.7 → 0.8)
3. Expand context window (4096 → 8192)
4. Revert to `mistral:latest` if needed

## Rollback Plan

To revert optimizations:

```bash
# Use standard Mistral
export OLLAMA_MODEL=mistral

# Or edit code directly
# voice_agent.py line 22: self.model = "mistral"
# pipecat_gateway.py line 55: ollama_model = "mistral"
```

## Conclusion

The combination of:
- Custom optimized model (`mistral-fast`)
- Streaming responses
- Reduced context window
- Prompt engineering

Should achieve **2-3x faster perceived latency** for {{ORCHESTRATOR_NAME}} voice interactions, bringing total response time from ~10s to **<5s**, with first token arriving in **<500ms**.

This makes conversational AI feel much more natural and responsive.

---

**Last Updated:** 2026-02-01
**Optimized By:** {{ORCHESTRATOR_NAME}} (Catalyst System)
