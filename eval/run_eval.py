"""
eval/run_eval.py

This module contains the Automated Evaluation Suite for InsightStream.

In a Retrieval-Augmented Generation (RAG) system, it is difficult to know if
changes to chunking, embeddings, or prompts actually improve the system or
break it. To solve this, we use an LLM as a "judge" to automatically grade
our system's answers against a baseline set of questions.

We use LangChain to orchestrate the LLM call, and we use Pydantic to enforce
"Structured Output". Normally, an LLM returns unstructured text. By providing a
Pydantic schema, we force the LLM to return a strict JSON object (e.g., {"score": 1, "reasoning": "..."})
which prevents our evaluation script from crashing due to unexpected formatting.
"""

import os
import json
import requests
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import LangChain primitives for OpenAI and Prompting
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# ── 1. Environment & Setup ────────────────────────────────────────────────────
# Load environment variables (OPENAI_API_KEY and API_SECRET_KEY)
load_dotenv()

# We need the API_SECRET_KEY to authenticate against our own FastAPI backend
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
if not API_SECRET_KEY:
    raise ValueError("API_SECRET_KEY is missing from .env")

# The URL of our local RAG query endpoint
API_URL = "http://localhost:8000/api/v1/intelligence/query"


# ── 2. Define the Desired Output Structure (Pydantic) ─────────────────────────
class EvaluationResult(BaseModel):
    """
    This Pydantic model defines the exact shape of the JSON we want the
    evaluator LLM to return. LangChain will automatically convert this schema
    into the format OpenAI expects for "tool calling" or "structured output".
    
    Attributes:
        score: An integer representing whether the system answered correctly.
        reasoning: A brief explanation of why the LLM judge gave that score.
    """
    score: int = Field(
        description="Must be exactly 1 if the answer directly and correctly responds to the question, or exactly 0 if it does not."
    )
    reasoning: str = Field(
        description="A 1-sentence explanation justifying the score."
    )


# ── 3. Evaluation Logic ───────────────────────────────────────────────────────
def run_evaluation():
    """
    Main function to run the evaluation suite.
    Flow:
      1. Load the baseline questions from eval/baseline_results.json.
      2. Set up the LangChain LLM Judge with structured output.
      3. For each question, send a request to our local FastAPI server.
      4. Compare the server's answer to the original question using the LLM Judge.
      5. Save the final graded results to a new JSON file and print a summary.
    """
    
    # Check if the FastAPI server is actually running before we start
    try:
        requests.get("http://localhost:8000/docs", timeout=30)
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to FastAPI server.")
        print("Please start the server using 'uvicorn main:app --reload' in another terminal.")
        return

    # Load the baseline questions. This file was created earlier and contains
    # questions specifically about the 3Blue1Brown neural network video.
    baseline_path = os.path.join("eval", "baseline_results.json")
    with open(baseline_path, "r", encoding="utf-8") as file:
        questions = json.load(file)

    # Initialize the LangChain chat model. We use gpt-4o-mini for speed and cost.
    # We set temperature=0 so the LLM acts deterministically (less creative, more analytical).
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Bind the Pydantic schema to the model. This is the crucial step that
    # guarantees the `.invoke()` method will return an EvaluationResult object
    # instead of a raw string.
    structured_llm = llm.with_structured_output(EvaluationResult)
    
    # Create the prompt template instructing the LLM on how to behave as a judge.
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an impartial, strict evaluator grading a Retrieval-Augmented Generation (RAG) system. Grade whether the provided 'System Answer' directly and correctly responds to the 'User Question'."),
        ("user", "User Question: {question}\n\nSystem Answer: {answer}\n\nEvaluate the system's answer.")
    ])
    
    # Create a LangChain Expression Language (LCEL) chain.
    # Data flows from the prompt -> to the structured LLM.
    eval_chain = eval_prompt | structured_llm

    # Track overall performance
    results_to_save = []
    total_score = 0
    total_questions = len(questions)

    print("\n🚀 Starting Automated Evaluation Suite...")
    print("-" * 60)

    # Required headers for our FastAPI endpoint (API Key authentication)
    headers = {
        "X-API-Key": API_SECRET_KEY, 
        "Content-Type": "application/json"
    }

    # Iterate through every question in the baseline file
    for item in questions:
        question_id = item["id"]
        question_text = item["question"]
        
        print(f"\n[Question {question_id}]: {question_text}")
        
        try:
            # Step A: Ask our RAG system the question
            api_response = requests.post(
                API_URL, 
                headers=headers, 
                json={"query": question_text},
                timeout=30 # Allow 30 seconds for the RAG pipeline to run
            )
            api_response.raise_for_status() # Raise exception for 4xx/5xx HTTP codes
            
            # Extract the literal answer string from the FastAPI JSON response
            system_answer = api_response.json().get("answer", "")
            print(f"[System Answer]: {system_answer[:100]}...") # Print a truncated preview
            
            # Step B: Ask the LLM Judge to grade the answer
            # We invoke the LCEL chain, passing in the required prompt variables.
            # `eval_result` will be an instance of the EvaluationResult Pydantic class.
            eval_result: EvaluationResult = eval_chain.invoke({
                "question": question_text,
                "answer": system_answer
            })
            
            # Access the strongly-typed fields defined in our Pydantic schema
            current_score = eval_result.score
            reasoning = eval_result.reasoning
            
            print(f"[Grade]: {current_score}/1")
            print(f"[Reasoning]: {reasoning}")
            
            total_score += current_score
            
            # Record the full execution state for this question
            results_to_save.append({
                "id": question_id,
                "question": question_text,
                "answer": system_answer,
                "score": current_score,
                "reasoning": reasoning
            })
            
        except Exception as e:
            # If the API request times out, or the LLM fails, catch it so we
            # don't crash the entire loop. Give it a score of 0.
            print(f"❌ Error processing question {question_id}: {e}")
            results_to_save.append({
                "id": question_id,
                "question": question_text,
                "answer": f"ERROR: {e}",
                "score": 0,
                "reasoning": "Pipeline failure occurred prior to evaluation."
            })

    # ── 4. Save and Summarize ─────────────────────────────────────────────────
    # Write the detailed grading report to a new JSON file
    output_path = os.path.join("eval", "eval_results_stage3.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results_to_save, f, indent=2)

    # Calculate metrics
    # In earlier steps, the baseline file had empty auto-scores. For demonstration,
    # we assume the baseline score was originally 0. If it had real scores, we
    # would calculate the sum of those here.
    baseline_score = sum(q.get("score") or 0 for q in questions)
    
    if baseline_score > 0:
        improvement = ((total_score - baseline_score) / baseline_score) * 100
        improvement_str = f"{improvement:.1f}%"
    else:
        # If baseline was 0, absolute percentage is used
        improvement_str = f"{total_score * 10}%"

    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print(f"Total Score:     {total_score} / {total_questions}")
    print(f"Baseline Score:  {baseline_score} / {total_questions}")
    print(f"Improvement:     {improvement_str}")
    print("=" * 60)
    print(f"\n✅ Detailed results saved to: {output_path}")

if __name__ == "__main__":
    # Execute the evaluation when this script is run directly from the terminal.
    run_evaluation()
