"""
RAGAS Evaluation Script for InsightStream RAG Pipeline

Measures:
  - Faithfulness      : Is the answer grounded in retrieved chunks?
  - Answer Relevancy  : Does the answer address the question?
  - Context Precision : Are retrieved chunks relevant to the query?
  - Context Recall    : Did we retrieve all important information?

Usage:
  python eval/run_ragas_eval.py
"""

import json
import os
import requests
from datetime import datetime
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from dotenv import load_dotenv

load_dotenv()

API_URL     = "http://localhost:8000/api/v1/intelligence/query"
API_KEY     = os.getenv("API_SECRET_KEY")
HEADERS     = {"Content-Type": "application/json", "X-API-Key": API_KEY}
EVAL_FILE   = "eval/baseline_results.json"

def collect_pipeline_outputs():
    """Run all eval questions through the pipeline and collect outputs."""
    # Clear Redis cache directly so all questions hit the full pipeline
    # (the eval script is standalone — cannot import from the FastAPI app)
    import redis as _redis
    _r = _redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    _keys = _r.keys("insightstream:*")
    if _keys:
        _r.delete(*_keys)
        print(f"Cleared {len(_keys)} cached entries before eval.\n")

    with open(EVAL_FILE) as f:
        questions = json.load(f)

    questions_list = []
    answers_list   = []
    contexts_list  = []
    ground_truths  = []

    print(f"Running {len(questions)} questions through pipeline...\n")

    for i, item in enumerate(questions):
        question = item["question"]
        print(f"[{i+1}/{len(questions)}] {question[:60]}...")

        try:
            response = requests.post(
                API_URL,
                json={"query": question},
                headers=HEADERS,
                timeout=60
            )
            data = response.json()

            answer   = data.get("report", "")
            contexts = data.get("contexts", [])

            # Skip cached responses — they have no contexts
            if data.get("cache_hit"):
                print(f"  Cache hit — skipping for RAGAS")
                continue

            if not contexts:
                print(f"  No contexts returned — skipping")
                continue

            questions_list.append(question)
            answers_list.append(answer)
            contexts_list.append(contexts)

            # Use existing answer from baseline as ground truth
            # If empty — use the pipeline answer itself as reference
            gt = item.get("answer", "")
            ground_truths.append(gt if gt else answer)

            print(f"  Got {len(contexts)} contexts — answer length: {len(answer)} chars")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    return questions_list, answers_list, contexts_list, ground_truths


def run_ragas(questions, answers, contexts, ground_truths):
    """Run RAGAS evaluation and return scores."""
    print(f"\nRunning RAGAS evaluation on {len(questions)} samples...")

    dataset = Dataset.from_dict({
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts,
        "ground_truth": ground_truths
    })

    # Explicitly instantiate LangChain models and wrap them for RAGAS
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    try:
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        # Configure generous max_tokens and timeout for eval tasks
        eval_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", max_tokens=8192, timeout=120))
        eval_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())
    except ImportError:
        # Fallback for older Ragas versions
        eval_llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=8192, timeout=120)
        eval_embeddings = OpenAIEmbeddings()

    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ],
        llm=eval_llm,
        embeddings=eval_embeddings
    )

    return result


def save_results(result, questions, answers):
    """Save RAGAS scores to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def safe_mean(key):
        val = result[key]
        if isinstance(val, (list, tuple)):
            clean = [x for x in val if x is not None and not (isinstance(x, float) and x != x)]
            return round(sum(clean) / len(clean), 4) if clean else 0.0
        return round(float(val), 4)

    output    = {
        "timestamp": timestamp,
        "sample_count": len(questions),
        "scores": {
            "faithfulness":      safe_mean("faithfulness"),
            "answer_relevancy":  safe_mean("answer_relevancy"),
            "context_precision": safe_mean("context_precision"),
            "context_recall":    safe_mean("context_recall"),
        },
        "interpretation": {
            "faithfulness":      "Hallucination rate — higher is better",
            "answer_relevancy":  "Query alignment — higher is better",
            "context_precision": "Chunk relevance — higher is better",
            "context_recall":    "Information completeness — higher is better"
        },
        "samples": [
            {"question": q, "answer_preview": a[:200]}
            for q, a in zip(questions, answers)
        ]
    }

    output_file = f"eval/ragas_results_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    return output, output_file


def print_summary(output):
    """Print formatted results summary."""
    scores = output["scores"]

    print("\n" + "=" * 60)
    print("RAGAS EVALUATION RESULTS — InsightStream RAG Pipeline")
    print("=" * 60)
    print(f"\nSamples evaluated: {output['sample_count']}")
    print(f"Timestamp: {output['timestamp']}")
    print()

    print(f"  Faithfulness      : {scores['faithfulness']:.4f}")
    print(f"  → How grounded answers are in retrieved chunks")
    print(f"  → {scores['faithfulness']*100:.1f}% of claims supported by context")
    print()
    print(f"  Answer Relevancy  : {scores['answer_relevancy']:.4f}")
    print(f"  → How well answers address the question")
    print()
    print(f"  Context Precision : {scores['context_precision']:.4f}")
    print(f"  → How relevant the retrieved chunks were")
    print()
    print(f"  Context Recall    : {scores['context_recall']:.4f}")
    print(f"  → How much important info was captured")
    print()

    avg = sum(scores.values()) / len(scores)
    print(f"  Average Score     : {avg:.4f}")
    print("=" * 60)

    # Interpretation
    if scores['faithfulness'] < 0.7:
        print("\nWARNING: Faithfulness below 0.7 — hallucination rate is high")
        print("Consider: more specific prompts, better chunk retrieval")
    if scores['context_precision'] < 0.7:
        print("\nWARNING: Context precision below 0.7 — irrelevant chunks retrieved")
        print("Consider: reducing top_k, improving embedding quality")


if __name__ == "__main__":
    print("InsightStream RAGAS Evaluation")
    print("Make sure FastAPI server is running on localhost:8000\n")

    questions, answers, contexts, ground_truths = collect_pipeline_outputs()

    if len(questions) < 2:
        print("Not enough valid samples for RAGAS — need at least 2")
        print("Make sure data is ingested and server is running")
        exit(1)

    result  = run_ragas(questions, answers, contexts, ground_truths)
    output, output_file = save_results(result, questions, answers)
    print_summary(output)

    print(f"\nFull results saved to: {output_file}")
    print("\nAdd these scores to README.md under Eval Results section.")
