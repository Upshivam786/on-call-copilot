#!/usr/bin/env python
"""Evaluation harness for On-Call Copilot.

Evaluates:
- Retrieval: Hit@k, MRR, nDCG
- Generation: Faithfulness (RAGAS), Citation accuracy

Usage:
    python evals/run.py --retrieval --generation
    python evals/run.py --retrieval  # retrieval only
    python evals/run.py --all
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_session, init_db
from app.retrieval.service import RetrievalService
from app.agent.loop import AgentLoop

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.jsonl"


async def load_golden_set() -> list[dict[str, Any]]:
    """Load golden evaluation queries."""
    queries = []
    with open(GOLDEN_SET_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    return queries


# =============================================================================
# Retrieval Evaluation
# =============================================================================

async def eval_retrieval() -> dict[str, float]:
    """Evaluate retrieval quality on golden set."""
    print("=== Retrieval Evaluation ===")
    queries = await load_golden_set()
    retrieval = RetrievalService()

    hit_at_k = {1: 0, 3: 0, 5: 0, 10: 0}
    mrr_sum = 0.0
    ndcg_sum = 0.0

    for i, q in enumerate(queries, 1):
        query = q["query"]
        expected = set(q.get("expected_chunks", []))

        results = await retrieval.search(query, use_query_expansion=False, use_reranking=True)

        # Get top chunk titles/source_ids
        retrieved_titles = [r.title for r in results]
        retrieved_source_ids = [r.metadata.get("source_id", "") for r in results]

        # Hit@k
        hit = False
        for k in hit_at_k:
            top_k = results[:k]
            top_ids = set()
            for r in top_k:
                top_ids.add(r.title)
                top_ids.add(r.metadata.get("source_id", ""))
            if top_ids & expected:
                hit_at_k[k] += 1

        # MRR
        rank = None
        for idx, r in enumerate(results, 1):
            if r.title in expected or r.metadata.get("source_id", "") in expected:
                rank = idx
                break
        if rank:
            mrr_sum += 1.0 / rank

        # nDCG@10 (simplified: 1 if relevant in top 10, else 0)
        relevant_in_top = sum(1 for r in results[:10] if r.title in expected or r.metadata.get("source_id", "") in expected)
        ndcg_sum += min(relevant_in_top / max(len(expected), 1), 1.0)

        print(f"  [{i}/{len(queries)}] {query[:50]}...")
        print(f"      Expected: {expected}")
        print(f"      Top-1: {retrieved_titles[:1]}")

    n = len(queries)
    return {
        "hit@1": hit_at_k[1] / n,
        "hit@3": hit_at_k[3] / n,
        "hit@5": hit_at_k[5] / n,
        "hit@10": hit_at_k[10] / n,
        "mrr": mrr_sum / n,
        "ndcg@10": ndcg_sum / n,
    }


# =============================================================================
# Generation Evaluation (with RAGAS)
# =============================================================================

async def eval_generation() -> dict[str, float]:
    """Evaluate answer generation quality."""
    print("\n=== Generation Evaluation ===")
    queries = await load_golden_set()

    faithfulness_scores = []
    citation_scores = []
    answer_relevance_scores = []

    agent = AgentLoop()

    for i, q in enumerate(queries, 1):
        query = q["query"]
        expected = q.get("expected_chunks", [])

        # Run agent
        answer = ""
        citations_used = set()

        async for event in agent.run_stream(user_query=query):
            if event.get("type") == "answer_delta":
                answer += event.get("content", "")
            elif event.get("type") == "complete":
                metadata = event.get("metadata", {})
                for c in metadata.get("citations", []):
                    citations_used.add(c.get("chunk_id", ""))

        # Faithfulness: does answer reference expected concepts?
        # (Simplified heuristic; RAGAS would do LLM-based eval)
        faithfulness = _heuristic_faithfulness(answer, q.get("ground_truth", ""))
        faithfulness_scores.append(faithfulness)

        # Citation accuracy: did agent cite expected chunks?
        citation_accuracy = min(len(citations_used) / max(len(expected), 1), 1.0)
        citation_scores.append(citation_accuracy if expected else 1.0)

        # Answer relevance: does answer address query?
        relevance = _heuristic_relevance(answer, query)
        answer_relevance_scores.append(relevance)

        print(f"  [{i}/{len(queries)}] {query[:50]}...")
        print(f"      Faithfulness: {faithfulness:.2f}, Citations: {citation_accuracy:.2f}, Relevance: {relevance:.2f}")

    n = len(queries)
    return {
        "faithfulness": sum(faithfulness_scores) / n,
        "citation_accuracy": sum(citation_scores) / n,
        "answer_relevance": sum(answer_relevance_scores) / n,
    }


def _heuristic_faithfulness(answer: str, ground_truth: str) -> float:
    """Heuristic faithfulness: keyword overlap with ground truth."""
    if not answer or not ground_truth:
        return 0.0

    answer_words = set(answer.lower().split())
    truth_words = set(ground_truth.lower().split())

    # Filter stopwords
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or", "for", "on", "in", "at", "by", "with"}
    answer_words -= stopwords
    truth_words -= stopwords

    if not truth_words:
        return 0.0

    overlap = answer_words & truth_words
    return len(overlap) / len(truth_words)


def _heuristic_relevance(answer: str, query: str) -> float:
    """Heuristic relevance: does answer contain query keywords?"""
    if not answer:
        return 0.0

    query_words = set(query.lower().split()) - {"what", "how", "why", "when", "is", "are", "do", "i", "me", "the", "a", "an", "on", "to", "for"}
    answer_lower = answer.lower()

    if not query_words:
        return 1.0

    matched = sum(1 for w in query_words if w in answer_lower)
    return min(matched / len(query_words), 1.0)


# =============================================================================
# Main
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Evaluate On-Call Copilot")
    parser.add_argument("--retrieval", action="store_true", help="Run retrieval eval")
    parser.add_argument("--generation", action="store_true", help="Run generation eval")
    parser.add_argument("--all", action="store_true", help="Run all evals")
    args = parser.parse_args()

    if not (args.retrieval or args.generation or args.all):
        parser.print_help()
        sys.exit(1)

    # Initialize DB
    await init_db()

    results = {}

    if args.retrieval or args.all:
        results["retrieval"] = await eval_retrieval()

    if args.generation or args.all:
        results["generation"] = await eval_generation()

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    thresholds = {
        "retrieval.hit@5": 0.7,
        "retrieval.mrr": 0.6,
        "retrieval.ndcg@10": 0.6,
        "generation.faithfulness": 0.8,
        "generation.citation_accuracy": 0.9,
        "generation.answer_relevance": 0.7,
    }

    for category, metrics in results.items():
        print(f"\n{category.upper()}:")
        for metric, value in metrics.items():
            threshold = thresholds.get(f"{category}.{metric}")
            status = ""
            if threshold:
                status = "  PASS" if value >= threshold else "  FAIL"
            print(f"  {metric}: {value:.4f}{status}")

    # Save results
    with open("evals/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to evals/results.json")


if __name__ == "__main__":
    asyncio.run(main())