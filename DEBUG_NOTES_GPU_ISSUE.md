# GPU Processing Debug Notes - Aug 2, 2025

## ISSUE SUMMARY
Template processing shows LLM HTTP calls happening but ALL question responses are empty ("No response provided"). Score parsing warnings appear constantly.

## SYMPTOMS
1. ✅ LLM calls happening: `HTTP Request: POST http://127.0.0.1:11434/api/generate "HTTP/1.1 200 OK"`
2. ❌ All responses empty: "No response provided" in final output
3. ❌ Score parsing failing: `WARNING - Could not parse score from response:`
4. ❌ Default scores: All questions get 3/7 default score

## LOGS FROM LAST RUN (Deck 115)
- 23 slides processed
- All 7 chapters processed (Problem Analysis, Solution, PMF, Monetization, Financials, Use of Funds, Organization)
- Progressive delivery working (sending chapter results)
- But question responses are empty

## SUSPECTED ROOT CAUSE
In `/gpu_processing/utils/healthcare_template_analyzer.py` around lines 1269-1295:

```python
try:
    response = ollama.generate(...)
    question_response = response['response']
    # Store in self.question_results[question_id]
except Exception as e:
    logger.error(f"Error analyzing question {question_id}: {e}")
    # BUT question_results[question_id] is NEVER SET in except block!
```

## DEBUGGING PLAN
1. Check GPU logs for `Error analyzing question` messages
2. Add detailed logging to see what exceptions are happening
3. Check if Ollama response format changed
4. Verify `response['response']` key exists
5. Check if model (phi4:latest) is working properly

## FRONTEND/BACKEND FIXES COMPLETED
- ✅ Fixed frontend to recognize 'dojo_template_processing' source
- ✅ Fixed backend to format chapter data properly (not raw JSON)
- ✅ Progressive delivery infrastructure working
- ✅ API returning properly formatted markdown

## NEED TO DEBUG ON GPU
- Question response generation failing
- Score parsing issues
- Possible Ollama/model problems

## TEST DECK
- Deck ID: 115 (20+ pages)
- Last processed: Aug 2, 21:41-21:42
- Located on GPU production server