from typing import Dict, Any, List
from backend.app.models.entities import Interview

FOUNDATIONAL_KEYWORDS = [
    "syntax", "loop", "variable", "http status", "get/post", "list", "dict", "basic",
    "table", "primary key", "foreign key", "function", "import", "class"
]

ADVANCED_KEYWORDS = [
    "distributed", "concurrency", "event loop", "profiling", "sharding", "acid", "cap",
    "deadlock", "race condition", "idempotency", "indexing", "vector", "cache invalidation",
    "memory leak", "garbage collection"
]

class KnowledgeGapService:
    @staticmethod
    def build_gap_hierarchy(interview: Interview) -> Dict[str, Any]:
        """
        Categorizes missed concepts into foundational, intermediate, and advanced tiers
        to construct a prioritized learning dependency roadmap.
        """
        all_missing = []
        for q in interview.questions:
            if q.answer and q.answer.evaluation:
                for c in q.answer.evaluation.missing_concepts:
                    all_missing.append({
                        "concept": c,
                        "skill": q.skill_assessed,
                        "question_id": q.id
                    })

        foundational = []
        intermediate = []
        advanced = []

        for item in all_missing:
            c_lower = item["concept"].lower()
            if any(k in c_lower for k in FOUNDATIONAL_KEYWORDS):
                foundational.append(item)
            elif any(k in c_lower for k in ADVANCED_KEYWORDS):
                advanced.append(item)
            else:
                intermediate.append(item)

        roadmap = []
        if foundational:
            roadmap.append({
                "stage": 1,
                "priority": "Critical Prerequisite",
                "summary": "Strengthen fundamental mechanics before advancing to system design.",
                "actions": [f"Review core principles of: {f['concept']} ({f['skill']})" for f in foundational[:3]]
            })
        if intermediate:
            roadmap.append({
                "stage": 2,
                "priority": "Core Competency",
                "summary": "Deepen practical implementation patterns and API design.",
                "actions": [f"Practice hands-on implementation of: {i['concept']} ({i['skill']})" for i in intermediate[:3]]
            })
        if advanced:
            roadmap.append({
                "stage": 3,
                "priority": "High-Impact Mastery",
                "summary": "Tackle concurrency, performance tuning, and architectural resilience.",
                "actions": [f"Benchmark and stress-test: {a['concept']} ({a['skill']})" for a in advanced[:3]]
            })

        return {
            "foundational_gaps": foundational,
            "intermediate_gaps": intermediate,
            "advanced_gaps": advanced,
            "learning_roadmap": roadmap
        }
