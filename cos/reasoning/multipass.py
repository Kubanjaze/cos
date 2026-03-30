"""COS multi-pass reasoning — deeper reasoning through multiple passes. Phase 156."""

import time
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.reasoning.multipass")


class MultiPassReasoner:
    """Runs multiple reasoning passes for deeper analysis."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def reason(self, query: str, passes: int = 3, investigation_id: str = "default") -> dict:
        """Run multi-pass reasoning: synthesize → challenge → refine."""
        results = {"query": query, "passes": [], "total_passes": passes}
        start = time.time()

        for i in range(passes):
            pass_start = time.time()
            pass_result = {"pass": i + 1, "actions": []}

            if i == 0:
                # Pass 1: Synthesis
                from cos.reasoning.synthesis import synthesis_engine
                syn = synthesis_engine.synthesize(query, investigation_id=investigation_id)
                pass_result["actions"].append({"type": "synthesis", "sources": syn.source_count})

            elif i == 1:
                # Pass 2: Pattern detection
                from cos.reasoning.patterns import pattern_detector
                patterns = pattern_detector.detect_all()
                total_patterns = sum(len(v) if isinstance(v, list) else 0 for v in patterns.values())
                pass_result["actions"].append({"type": "pattern_detection", "patterns_found": total_patterns})

            elif i == 2:
                # Pass 3: Insight extraction
                from cos.reasoning.insights import insight_extractor
                insights = insight_extractor.extract(investigation_id=investigation_id)
                pass_result["actions"].append({"type": "insight_extraction", "insights": len(insights)})

            pass_result["duration_s"] = round(time.time() - pass_start, 3)
            results["passes"].append(pass_result)

        results["total_duration_s"] = round(time.time() - start, 3)
        logger.info(f"Multi-pass reasoning: {passes} passes in {results['total_duration_s']:.3f}s")
        return results

    def stats(self) -> dict:
        return {"available_passes": ["synthesis", "pattern_detection", "insight_extraction"],
                "max_passes": 3}


multipass_reasoner = MultiPassReasoner()
