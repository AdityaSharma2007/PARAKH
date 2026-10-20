import re
from typing import Dict, Any, List
from backend.app.integrations.llm_base import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    """
    High-fidelity deterministic mock provider for testing, offline environments,
    and fallback when Gemini API key is not configured.
    """

    async def extract_profile(self, raw_text: str) -> Dict[str, Any]:
        # Extract email and phone using regex
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text)
        
        # Simple heuristic skill detection
        common_skills = [
            "Python", "FastAPI", "Django", "JavaScript", "TypeScript", "React", "Node.js",
            "SQL", "PostgreSQL", "Docker", "Kubernetes", "AWS", "Git", "Machine Learning",
            "Redis", "GraphQL", "MongoDB", "Linux", "REST", "CI/CD"
        ]
        detected_skills = [s for s in common_skills if s.lower() in raw_text.lower()]
        if not detected_skills:
            detected_skills = ["Python", "FastAPI", "SQL", "Git"]

        # Detect projects or fallback
        project_titles = []
        for line in raw_text.splitlines():
            if any(k in line.lower() for k in ["project", "app", "system", "platform", "api"]):
                clean = line.strip(" -*#:")
                if 5 < len(clean) < 50:
                    project_titles.append(clean)
        
        projects = []
        if project_titles:
            for p in project_titles[:2]:
                projects.append({
                    "title": p,
                    "description": f"Architected and implemented {p} incorporating modular service design and data persistence.",
                    "technologies": detected_skills[:3],
                    "role": "Lead Developer",
                    "highlights": ["Designed core data pipeline", "Optimized response latencies"]
                })
        else:
            projects = [{
                "title": "PARAKH Evaluation Engine",
                "description": "Full-stack AI assessment system with stateful adaptive questioning and audio processing.",
                "technologies": ["Python", "FastAPI", "SQLite", "Speech-to-Text"],
                "role": "Full Stack Engineer",
                "highlights": ["Built adaptive difficulty state machine", "Integrated structured evaluations"]
            }]

        return {
            "full_name": "Sample Candidate",
            "email": email_match.group(0) if email_match else "candidate@example.com",
            "phone": phone_match.group(0) if phone_match else "+1-555-0199",
            "education": [{
                "degree": "Bachelor of Technology in Computer Science",
                "institution": "University Institute of Technology",
                "year": "2024",
                "field_of_study": "Computer Science & Engineering"
            }],
            "skills": {
                "languages": [s for s in detected_skills if s in ["Python", "JavaScript", "TypeScript", "SQL"]],
                "frameworks": [s for s in detected_skills if s in ["FastAPI", "Django", "React", "Node.js"]],
                "databases_and_tools": [s for s in detected_skills if s in ["PostgreSQL", "Docker", "Git", "Redis", "Linux"]]
            },
            "projects": projects,
            "experience": [{
                "company": "Tech Solutions Inc.",
                "role": "Software Engineering Intern",
                "duration": "6 Months",
                "highlights": ["Developed backend REST APIs", "Wrote automated unit test coverage"]
            }],
            "certifications": ["Certified Python Associate"]
        }

    async def generate_questions(
        self,
        profile_data: Dict[str, Any],
        target_role: str,
        interview_type: str,
        difficulty: str,
        count: int,
        assessed_topics: List[str],
        question_mix: str = "mixed"
    ) -> List[Dict[str, Any]]:
        projects = profile_data.get("projects", [])
        raw_title = "Technical Portfolio Project"
        raw_desc = ""
        raw_techs = []
        if projects and isinstance(projects, list):
            p0 = projects[0]
            raw_title = str(p0.get("title") or raw_title)
            raw_desc = str(p0.get("description") or "")
            raw_techs = p0.get("technologies") or []

        # Strip unicode dashes and artifacts
        for old_c, new_c in [("\u2013", "-"), ("\u2014", "-"), ("\ufffd", "-"), ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"')]:
            raw_title = raw_title.replace(old_c, new_c)
            raw_desc = raw_desc.replace(old_c, new_c)

        skills_dict = profile_data.get("skills", {})
        all_skills = []
        for v in skills_dict.values():
            if isinstance(v, list):
                all_skills.extend(v)
        primary_skill = all_skills[0] if all_skills else "Python"
        secondary_skill = all_skills[1] if len(all_skills) > 1 else "FastAPI"
        tech_str = ", ".join(str(t) for t in raw_techs[:3]) if raw_techs else f"{primary_skill}, {secondary_skill}"
        desc_snippet = (raw_desc[:120] + "...") if len(raw_desc) > 20 else ""

        # Domain classification based on target role, skills, and project context
        role_lower = (target_role or "").lower()
        skills_lower = " ".join(str(s).lower() for s in all_skills) + " " + raw_desc.lower()

        if any(k in role_lower for k in ["vision", "cv"]) or ("vision" in skills_lower and "full stack" not in role_lower and "software" not in role_lower):
            domain = "CV"
        elif any(k in role_lower for k in ["machine learning", "data scientist", "ai engineer", "deep learning"]) or ("scikit" in skills_lower and "full stack" not in role_lower and "software" not in role_lower):
            domain = "ML"
        elif any(k in role_lower for k in ["frontend", "front-end", "ui developer", "react developer"]):
            domain = "FRONTEND"
        elif any(k in role_lower for k in ["devops", "cloud engineer", "sre", "infrastructure"]):
            domain = "DEVOPS"
        else:
            domain = "BACKEND"

        bank: List[Dict[str, Any]] = []

        if domain == "CV":
            bank = [
                # 1. CV Project Deep Dive (SPOKEN)
                {
                    "question_text": f"In your project '{raw_title}', you leveraged {tech_str}. {desc_snippet} Can you walk us through your computer vision pipeline, how you handled frame capture, model inference latency (FPS), and what trade-offs influenced your design?",
                    "skill_assessed": "Computer Vision Pipeline & Real-Time Inference",
                    "category": "project_deep_dive",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["frame rate (FPS)", "inference latency", "pipeline parallelization", "precision vs recall"],
                    "evaluation_rubric": {"pipeline_architecture": 45, "project_grounding": 35, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 2. Object Detection Metrics & NMS (MCQ)
                {
                    "question_text": "When performing Non-Maximum Suppression (NMS) in object detection models (e.g. YOLO), what is the key limitation of traditional IoU, and why is Distance-IoU (DIoU) or Complete-IoU (CIoU) preferred in dense detection scenarios?",
                    "skill_assessed": "Object Detection & NMS Metrics",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "Traditional IoU computes area overlap only; DIoU/CIoU incorporates normalized distance between central points of bounding boxes to prevent erroneously suppressing overlapping objects in dense scenes."},
                        {"id": "B", "text": "Standard IoU runs only on CPU, while DIoU forces CUDA execution."},
                        {"id": "C", "text": "Standard IoU ignores anchor boxes entirely and uses cross-entropy."},
                        {"id": "D", "text": "DIoU eliminates the need for confidence score thresholding."}
                    ],
                    "correct_option": "A",
                    "explanation": "Standard IoU solely calculates overlapping area intersection. In crowded scenes, two separate objects may share significant area overlap, causing standard NMS to suppress a valid prediction. Distance-IoU factors the distance between centroid centers to preserve valid adjacent detections.",
                    "expected_concepts": ["IoU calculation", "bounding box centroids", "Non-Maximum Suppression", "dense object detection"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 3. CV Code Challenge: IoU Calculation (CODE)
                {
                    "question_text": "Implement a Python function to compute the Intersection over Union (IoU) of two 2D axis-aligned bounding boxes boxA and boxB, where each box is specified as [x1, y1, x2, y2]. Return the IoU as a float rounded to 4 decimal places, or 0.0 if there is no overlap.",
                    "skill_assessed": "Bounding Box Geometry & IoU Algorithm",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "CODE",
                    "language": "python",
                    "code_snippet": (
                        "def compute_iou(boxA: list[float], boxB: list[float]) -> float:\n"
                        "    \"\"\"\n"
                        "    Computes the Intersection over Union (IoU) of two bounding boxes.\n"
                        "    boxA: [x1, y1, x2, y2] (top-left, bottom-right)\n"
                        "    boxB: [x1, y1, x2, y2] (top-left, bottom-right)\n"
                        "    # ------------------------------------------------------------------\n"
                        "    # >>> START YOUR CODE HERE <<<\n"
                        "    # ------------------------------------------------------------------\n"
                        "    pass\n"
                    ),
                    "examples": [
                        {
                            "input": "boxA = [0, 0, 2, 2], boxB = [1, 1, 3, 3]",
                            "output": "0.1429",
                            "explanation": "Intersection rectangle is [1, 1, 2, 2] with area (2-1)*(2-1) = 1. BoxA area = 4, BoxB area = 4. Union area = 4 + 4 - 1 = 7. IoU = 1 / 7 ≈ 0.1429."
                        },
                        {
                            "input": "boxA = [0, 0, 5, 5], boxB = [0, 0, 5, 5]",
                            "output": "1.0",
                            "explanation": "Identical boxes share 100% intersection and union, yielding an IoU of exactly 1.0."
                        },
                        {
                            "input": "boxA = [0, 0, 1, 1], boxB = [2, 2, 4, 4]",
                            "output": "0.0",
                            "explanation": "Boxes are completely disjoint with no overlapping area. IoU is 0.0."
                        }
                    ],
                    "constraints": [
                        "Each box has 4 elements: x1, y1, x2, y2",
                        "box[0] < box[2] and box[1] < box[3]",
                        "All coordinates are non-negative numbers",
                        "Expected Time Complexity: O(1), Space Complexity: O(1)"
                    ],
                    "test_cases": [
                        {
                            "name": "Partial Overlap",
                            "input": "boxA=[0,0,2,2], boxB=[1,1,3,3]",
                            "expected": 0.1429,
                            "test_code": "actual = round(float(compute_iou([0, 0, 2, 2], [1, 1, 3, 3])), 4)"
                        },
                        {
                            "name": "Identical Coordinates",
                            "input": "boxA=[0,0,5,5], boxB=[0,0,5,5]",
                            "expected": 1.0,
                            "test_code": "actual = round(float(compute_iou([0, 0, 5, 5], [0, 0, 5, 5])), 4)"
                        },
                        {
                            "name": "Completely Disjoint",
                            "input": "boxA=[0,0,1,1], boxB=[2,2,4,4]",
                            "expected": 0.0,
                            "test_code": "actual = round(float(compute_iou([0, 0, 1, 1], [2, 2, 4, 4])), 4)"
                        }
                    ],
                    "expected_concepts": ["intersection coordinates max/min", "intersection area", "union area inclusion-exclusion", "zero overlap boundary check"],
                    "evaluation_rubric": {"code_correctness": 50, "algorithmic_efficiency": 30, "verbal_walkthrough": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 4. Pointwise 1x1 Convolutions (MCQ)
                {
                    "question_text": "In Convolutional Neural Networks (CNNs), what is the primary role of a 1x1 convolution (Pointwise Convolution) as popularized by ResNet bottleneck blocks and MobileNet?",
                    "skill_assessed": "CNN Architecture & Dimensionality Reduction",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "To increase the spatial height and width of the input feature map."},
                        {"id": "B", "text": "To adjust channel dimensionality and introduce non-linearity with minimal computational cost."},
                        {"id": "C", "text": "To replace the final Softmax activation layer with a linear regression layer."},
                        {"id": "D", "text": "To perform Fourier transform frequency domain filtering directly."}
                    ],
                    "correct_option": "B",
                    "explanation": "1x1 convolutions linearly combine feature channels at each spatial pixel, allowing dimensionality reduction (or expansion) before and after spatial 3x3 convolutions, dramatically reducing floating-point operations (FLOPs).",
                    "expected_concepts": ["channel dimensionality reduction", "FLOP reduction", "feature mixing", "bottleneck layers"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 5. Model Quantization & Edge Deployment (SPOKEN)
                {
                    "question_text": "In production computer vision deployment (e.g. edge cameras, mobile devices), explain how Post-Training Quantization (PTQ) to INT8 reduces memory footprint and increases throughput compared to FP32, and how you calibrate quantization to prevent accuracy loss.",
                    "skill_assessed": "Edge CV & Model Quantization",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["INT8 quantization", "calibration dataset", "dynamic range vs symmetric quantization", "TensorRT / ONNX Runtime"],
                    "evaluation_rubric": {"quantization_depth": 50, "edge_latency_tradeoffs": 30, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                }
            ]

        elif domain == "ML":
            bank = [
                # 1. ML Project Deep Dive (SPOKEN)
                {
                    "question_text": f"In your project '{raw_title}', you leveraged {tech_str}. {desc_snippet} Walk us through your data preprocessing, feature engineering, model selection benchmarks (e.g. Random Forest vs XGBoost vs baseline), and how you ensured strict validation without data leakage.",
                    "skill_assessed": "Machine Learning Lifecycle & Evaluation",
                    "category": "project_deep_dive",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["feature engineering", "data leakage prevention", "cross-validation", "model benchmarking"],
                    "evaluation_rubric": {"methodology_rigor": 45, "project_grounding": 35, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 2. Imbalanced Data & PR-AUC vs ROC-AUC (MCQ)
                {
                    "question_text": "When training a predictive risk classifier where positive cases represent only 0.5% of total samples, why is the Area Under the Precision-Recall Curve (PR-AUC) preferred over ROC-AUC for model evaluation?",
                    "skill_assessed": "Model Evaluation & Imbalanced Datasets",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "ROC-AUC is computationally intractable on datasets with more than 10,000 records."},
                        {"id": "B", "text": "ROC-AUC can be deceptively optimistic because large numbers of True Negatives suppress the False Positive Rate, while PR-AUC focuses on minority positive recovery."},
                        {"id": "C", "text": "PR-AUC does not require thresholding or probability scores."},
                        {"id": "D", "text": "ROC-AUC requires the target label to follow a Gaussian distribution."}
                    ],
                    "correct_option": "B",
                    "explanation": "Because False Positive Rate = FP / (FP + TN), a massive True Negative majority keeps FPR low even with many false alarms. PR-AUC focuses solely on Positive Predictive Value (Precision) and Sensitivity (Recall), exposing true performance on imbalanced classes.",
                    "expected_concepts": ["class imbalance", "PR-AUC vs ROC-AUC", "True Negative skew", "precision-recall tradeoffs"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 3. ML Code Challenge: Confusion Matrix & Metrics (CODE)
                {
                    "question_text": "Implement a Python function to compute Precision, Recall, and F1-Score from binary true labels and predicted labels without importing external machine learning libraries. Return a dictionary containing precision, recall, and f1 rounded to 4 decimals.",
                    "skill_assessed": "Evaluation Metrics Implementation",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "CODE",
                    "language": "python",
                    "code_snippet": (
                        "def compute_classification_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:\n"
                        "    \"\"\"\n"
                        "    Computes Precision, Recall, and F1-Score from binary ground truth and predictions.\n"
                        "    Returns dict: {'precision': float, 'recall': float, 'f1': float} rounded to 4 decimal places.\n"
                        "    Safely returns 0.0 for metrics where the denominator is 0.\n"
                        "    \"\"\"\n"
                        "    if not y_true or len(y_true) != len(y_pred):\n"
                        "        return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}\n\n"
                        "    # ------------------------------------------------------------------\n"
                        "    # >>> START YOUR CODE HERE <<<\n"
                        "    # ------------------------------------------------------------------\n"
                        "    pass\n"
                    ),
                    "examples": [
                        {
                            "input": "y_true = [1, 0, 1, 1, 0, 1], y_pred = [1, 0, 0, 1, 0, 1]",
                            "output": "{\"precision\": 1.0, \"recall\": 0.75, \"f1\": 0.8571}",
                            "explanation": "TP=3, FP=0, FN=1, TN=2. Precision = 3/(3+0) = 1.0. Recall = 3/(3+1) = 0.75. F1 = 2*(1.0*0.75)/(1.0+0.75) = 0.8571."
                        },
                        {
                            "input": "y_true = [1, 1, 1], y_pred = [0, 0, 0]",
                            "output": "{\"precision\": 0.0, \"recall\": 0.0, \"f1\": 0.0}",
                            "explanation": "Zero positive predictions. Division by zero is avoided and returns 0.0."
                        }
                    ],
                    "constraints": [
                        "len(y_true) == len(y_pred) >= 1",
                        "y_true[i] in {0, 1}, y_pred[i] in {0, 1}",
                        "Expected Time Complexity: O(N) single pass, Space Complexity: O(1)"
                    ],
                    "test_cases": [
                        {
                            "name": "Mixed True & Predicted",
                            "input": "y_true=[1,0,1,1,0,1], y_pred=[1,0,0,1,0,1]",
                            "expected": {"precision": 1.0, "recall": 0.75, "f1": 0.8571},
                            "test_code": "res = compute_classification_metrics([1,0,1,1,0,1], [1,0,0,1,0,1])\nactual = {k: round(float(v), 4) for k, v in res.items()}"
                        },
                        {
                            "name": "Zero Positive Predictions",
                            "input": "y_true=[1,1,1], y_pred=[0,0,0]",
                            "expected": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
                            "test_code": "res = compute_classification_metrics([1,1,1], [0,0,0])\nactual = {k: round(float(v), 4) for k, v in res.items()}"
                        },
                        {
                            "name": "100% Correct Match",
                            "input": "y_true=[1,0,1], y_pred=[1,0,1]",
                            "expected": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
                            "test_code": "res = compute_classification_metrics([1,0,1], [1,0,1])\nactual = {k: round(float(v), 4) for k, v in res.items()}"
                        }
                    ],
                    "expected_concepts": ["TP/FP/TN/FN counts", "zero division protection", "F1 harmonic mean", "O(N) single pass"],
                    "evaluation_rubric": {"code_correctness": 50, "algorithmic_efficiency": 30, "verbal_walkthrough": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 4. L1 (Lasso) vs L2 (Ridge) Regularization (MCQ)
                {
                    "question_text": "What is the primary difference in how L1 (Lasso) and L2 (Ridge) regularization penalties affect regression model coefficients?",
                    "skill_assessed": "Regularization & Feature Selection",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "L1 penalty shrinks less important coefficients exactly to zero for feature selection, while L2 shrinks coefficients asymptotically toward zero."},
                        {"id": "B", "text": "L2 regularization eliminates collinearity by discarding random features."},
                        {"id": "C", "text": "L1 regularization increases the variance of the model on unseen test sets."},
                        {"id": "D", "text": "L2 regularization can only be applied to classification decision trees."}
                    ],
                    "correct_option": "A",
                    "explanation": "Because L1 regularization uses the absolute value of coefficients, the diamond-shaped constraint geometry allows optimization contours to intersect axes, driving coefficients exactly to zero. L2 uses squared values, shrinking coefficients smoothly without zeroing them.",
                    "expected_concepts": ["L1 sparsity / feature selection", "L2 weight decay", "loss function penalty geometry", "overfitting prevention"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 5. Production Model Drift & Monitoring (SPOKEN)
                {
                    "question_text": "How do you detect and mitigate Data Drift (covariate shift) and Concept Drift in a production machine learning pipeline? What statistical tests (e.g. KS-test, Population Stability Index) and retraining strategies would you establish?",
                    "skill_assessed": "MLOps & Production Model Monitoring",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["covariate shift vs concept drift", "Population Stability Index (PSI)", "Kolmogorov-Smirnov test", "automated retraining pipelines"],
                    "evaluation_rubric": {"mlops_monitoring": 50, "drift_mitigation": 30, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                }
            ]

        elif domain == "FRONTEND":
            bank = [
                # 1. Frontend Project Deep Dive (SPOKEN)
                {
                    "question_text": f"In your project '{raw_title}', you built with {tech_str}. {desc_snippet} Walk us through your frontend architecture, how you structured state management, component reusability, and client-side rendering performance.",
                    "skill_assessed": "Frontend Architecture & State Management",
                    "category": "project_deep_dive",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["component modularity", "state normalization", "re-render optimization", "bundle size reduction"],
                    "evaluation_rubric": {"architecture_depth": 45, "project_grounding": 35, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 2. Virtual DOM Reconciliation & Keys (MCQ)
                {
                    "question_text": "In modern UI libraries like React, why is assigning array index as a 'key' prop considered an anti-pattern when rendering dynamic, re-orderable lists?",
                    "skill_assessed": "Virtual DOM Reconciliation",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "Indices cause React to crash with a DOMException during state updates."},
                        {"id": "B", "text": "Index keys break component identity on reordering or item deletion, causing incorrect uncontrolled state persistence and unnecessary full re-renders."},
                        {"id": "C", "text": "Indices force the browser to execute synchronous paint cycles."},
                        {"id": "D", "text": "React keys must always be UUID version 4 strings."}
                    ],
                    "correct_option": "B",
                    "explanation": "React uses keys to match existing Virtual DOM nodes with new elements. If keys are indices, inserting or deleting an item shifts indices, making React mistakenly reuse existing stateful DOM nodes for completely different data items.",
                    "expected_concepts": ["reconciliation algorithm", "component identity", "uncontrolled state preservation", "diffing optimization"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 3. Frontend Code Challenge: Safe Deep Object Accessor (CODE)
                {
                    "question_text": "Implement a Python function `safe_get(obj, path, default_val=None)` that safely retrieves a deeply nested value from a dictionary using dot notation (e.g., 'user.profile.name'). If any intermediate key does not exist or is None, it should return default_val without raising an exception.",
                    "skill_assessed": "Deep Object Traversal & Defensive Programming",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "CODE",
                    "language": "python",
                    "code_snippet": (
                        "def safe_get(obj: dict, path: str, default_val=None):\n"
                        "    \"\"\"\n"
                        "    Retrieves the value at a nested path of an object.\n"
                        "    path: dot-separated string, e.g. 'user.profile.name'\n"
                        "    default_val: returned if path cannot be fully resolved\n"
                        "    \"\"\"\n"
                        "    # ------------------------------------------------------------------\n"
                        "    # >>> START YOUR CODE HERE <<<\n"
                        "    # ------------------------------------------------------------------\n"
                        "    pass\n"
                    ),
                    "examples": [
                        {
                            "input": "obj = {'a': {'b': {'c': 42}}}, path = 'a.b.c'",
                            "output": "42",
                            "explanation": "Traverses through a -> b -> c to reach value 42."
                        },
                        {
                            "input": "obj = {'a': {'b': None}}, path = 'a.b.c', default_val = 'N/A'",
                            "output": "'N/A'",
                            "explanation": "Key 'b' points to None, so traversing to 'c' cannot proceed; returns 'N/A'."
                        }
                    ],
                    "constraints": [
                        "path is a string of keys separated by '.'",
                        "obj is a Python dictionary or nested dict",
                        "Expected Time Complexity: O(K) where K is number of path keys"
                    ],
                    "test_cases": [
                        {
                            "name": "Nested Dictionary",
                            "input": "obj={'a': {'b': {'c': 42}}}, path='a.b.c'",
                            "expected": 42,
                            "test_code": "actual = safe_get({'a': {'b': {'c': 42}}}, 'a.b.c')"
                        },
                        {
                            "name": "Missing Intermediate Key Fallback",
                            "input": "obj={'a': 1}, path='a.b.c', default='fallback'",
                            "expected": "fallback",
                            "test_code": "actual = safe_get({'a': 1}, 'a.b.c', 'fallback')"
                        },
                        {
                            "name": "Root Key Lookup",
                            "input": "obj={'role': 'engineer'}, path='role'",
                            "expected": "engineer",
                            "test_code": "actual = safe_get({'role': 'engineer'}, 'role')"
                        }
                    ],
                    "expected_concepts": ["dot path parsing", "dictionary traversal", "None checks", "default fallback"],
                    "evaluation_rubric": {"code_correctness": 50, "algorithmic_efficiency": 30, "verbal_walkthrough": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 4. Browser Rendering & GPU Acceleration (MCQ)
                {
                    "question_text": "Which CSS properties can be animated without triggering a browser Layout (Reflow) or Paint cycle, running directly on the GPU Compositor thread?",
                    "skill_assessed": "Browser Rendering Pipeline & CSS Performance",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "width and height"},
                        {"id": "B", "text": "margin and padding"},
                        {"id": "C", "text": "transform and opacity"},
                        {"id": "D", "text": "top and left"}
                    ],
                    "correct_option": "C",
                    "explanation": "Changing 'transform' and 'opacity' bypasses both Layout (geometry calculation) and Paint (rasterization), allowing the compositor thread on the GPU to handle the transformation directly at 60+ FPS.",
                    "expected_concepts": ["layout / reflow", "repaint", "compositing thread", "GPU acceleration"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 5. Core Web Vitals Optimization (SPOKEN)
                {
                    "question_text": "Explain the three Core Web Vitals metrics: Largest Contentful Paint (LCP), Interaction to Next Paint (INP), and Cumulative Layout Shift (CLS). What concrete engineering steps do you take to achieve 'Good' thresholds for each?",
                    "skill_assessed": "Core Web Vitals & Web Performance",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["LCP asset preloading", "INP long task breakdown", "CLS reserved dimensions", "SSR / hydration trade-offs"],
                    "evaluation_rubric": {"vitals_precision": 50, "remediation_tactics": 30, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                }
            ]

        else:
            # Default BACKEND & Distributed Systems Bank
            bank = [
                # 1. Backend Project Deep Dive (SPOKEN)
                {
                    "question_text": f"In your project '{raw_title}', you leveraged {tech_str}. {desc_snippet} Can you walk us through how you handled service communication, state consistency, and what trade-offs influenced your design?",
                    "skill_assessed": f"{primary_skill} & System Architecture",
                    "category": "project_deep_dive",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["service boundaries", "data consistency", "trade-off analysis", "fault tolerance"],
                    "evaluation_rubric": {"architectural_depth": 40, "project_grounding": 40, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 2. System Architecture / Concurrency (MCQ)
                {
                    "question_text": f"In a high-throughput {primary_skill} service running an asynchronous event loop, what occurs if an endpoint performs a long-running synchronous CPU-bound task directly inside the async route handler?",
                    "skill_assessed": f"{primary_skill} Concurrency & Event Loop",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "The event loop automatically offloads the task to an OS worker thread."},
                        {"id": "B", "text": "The entire event loop is blocked, delaying all concurrent pending I/O tasks and client requests."},
                        {"id": "C", "text": "The runtime throws an unhandled ConcurrencyException immediately."},
                        {"id": "D", "text": "Only the current connection waits while other coroutines proceed uninterrupted."}
                    ],
                    "correct_option": "B",
                    "explanation": "Because Python's asyncio runs a single-threaded cooperative event loop, any synchronous CPU-bound blocking call prevents the loop from scheduling or yielding to other concurrent coroutines until it returns.",
                    "expected_concepts": ["single-threaded event loop", "cooperative multitasking", "blocking I/O vs CPU work", "thread pool offloading"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 3. Practical Coding & Refactoring: First Unique Token (CODE)
                {
                    "question_text": f"Review and optimize the following {primary_skill} function. Identify the quadratic O(N^2) bottleneck and implement `find_first_unique_token` to operate in O(N) linear time using a frequency counter or hash map. Return None if no unique token exists or if the list is empty.",
                    "skill_assessed": "Algorithm Optimization & Hash Map Counting",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "CODE",
                    "language": "python",
                    "code_snippet": (
                        "def find_first_unique_token(tokens: list[str]) -> str | None:\n"
                        "    \"\"\"\n"
                        "    Finds the first non-repeating token in the list in O(N) time.\n"
                        "    Returns None if all tokens repeat or list is empty.\n"
                        "    \"\"\"\n"
                        "    # ------------------------------------------------------------------\n"
                        "    # >>> START YOUR CODE HERE <<<\n"
                        "    # ------------------------------------------------------------------\n"
                        "    pass\n"
                    ),
                    "examples": [
                        {
                            "input": "tokens = ['apple', 'banana', 'apple', 'cherry', 'banana']",
                            "output": "'cherry'",
                            "explanation": "'apple' and 'banana' appear twice; 'cherry' appears once and is the first unique token."
                        },
                        {
                            "input": "tokens = ['a', 'b', 'c']",
                            "output": "'a'",
                            "explanation": "All elements are unique; 'a' is the first."
                        },
                        {
                            "input": "tokens = ['x', 'x', 'y', 'y']",
                            "output": "None",
                            "explanation": "All tokens have duplicates, returning None."
                        }
                    ],
                    "constraints": [
                        "0 <= len(tokens) <= 10^5",
                        "Tokens are non-empty strings",
                        "Expected Time Complexity: O(N), Space Complexity: O(N)"
                    ],
                    "test_cases": [
                        {
                            "name": "First Unique in Middle",
                            "input": "tokens=['apple', 'banana', 'apple', 'cherry', 'banana']",
                            "expected": "cherry",
                            "test_code": "actual = find_first_unique_token(['apple', 'banana', 'apple', 'cherry', 'banana'])"
                        },
                        {
                            "name": "All Distinct",
                            "input": "tokens=['a', 'b', 'c']",
                            "expected": "a",
                            "test_code": "actual = find_first_unique_token(['a', 'b', 'c'])"
                        },
                        {
                            "name": "No Unique Tokens",
                            "input": "tokens=['x', 'x', 'y', 'y']",
                            "expected": None,
                            "test_code": "actual = find_first_unique_token(['x', 'x', 'y', 'y'])"
                        },
                        {
                            "name": "Empty List",
                            "input": "tokens=[]",
                            "expected": None,
                            "test_code": "actual = find_first_unique_token([])"
                        }
                    ],
                    "expected_concepts": ["O(N) time complexity", "hash map / dict counting", "two-pass scan", "space-time trade-off"],
                    "evaluation_rubric": {"code_correctness": 50, "algorithmic_efficiency": 30, "verbal_walkthrough": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 3b. Correct the Code: Fix Blocking Event Loop in Async Microservice (CODE)
                {
                    "question_text": "In this asynchronous FastAPI handler, a blocking synchronous call halts the single-threaded asyncio event loop under concurrent load. Correct the defective blocking operation so it non-blockingly yields control to the event loop.",
                    "skill_assessed": "Async Concurrency & Non-blocking I/O",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "CODE",
                    "language": "python",
                    "code_snippet": (
                        "import asyncio\n"
                        "import time\n\n"
                        "async def fetch_user_data(user_id: int):\n"
                        "    # Defect: Blocking synchronous sleep inside coroutine halts the entire event loop!\n"
                        "    time.sleep(1)\n"
                        "    return {'id': user_id, 'status': 'active'}\n"
                    ),
                    "examples": [
                        {
                            "input": "fetch_user_data(101)",
                            "output": "{'id': 101, 'status': 'active'}",
                            "explanation": "Yields control cooperatively using non-blocking asyncio without stalling concurrent client requests."
                        }
                    ],
                    "constraints": [
                        "Must not invoke blocking synchronous time.sleep inside async coroutine",
                        "Must maintain function signature and return dictionary",
                        "Must execute asynchronously with asyncio"
                    ],
                    "test_cases": [
                        {
                            "name": "Non-blocking Async Concurrency Check",
                            "input": "fetch_user_data(1)",
                            "expected": {"id": 1, "status": "active"},
                            "test_code": "import inspect\nimport asyncio\nsrc = inspect.getsource(fetch_user_data)\nif 'time.sleep' in src:\n    raise AssertionError(\"Defect not resolved: Code still contains blocking synchronous 'time.sleep'. Replace with 'await asyncio.sleep'!\")\nactual = asyncio.run(fetch_user_data(1))"
                        },
                        {
                            "name": "Different User ID Parameter Verification",
                            "input": "fetch_user_data(999)",
                            "expected": {"id": 999, "status": "active"},
                            "test_code": "import inspect\nimport asyncio\nsrc = inspect.getsource(fetch_user_data)\nif 'time.sleep' in src:\n    raise AssertionError(\"Defect not resolved: Code still contains blocking synchronous 'time.sleep'. Replace with 'await asyncio.sleep'!\")\nactual = asyncio.run(fetch_user_data(999))"
                        }
                    ],
                    "expected_concepts": ["event loop cooperative multitasking", "non-blocking I/O", "async/await syntax", "asyncio.sleep"],
                    "evaluation_rubric": {"code_correctness": 60, "concurrency_understanding": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 3c. Small DSA: Target Sum Pair in Sorted Array (CODE)
                {
                    "question_text": "Given a list of sorted integers 'nums' and an integer 'target', implement 'two_sum_sorted' to find the 0-based indices of two numbers that add up to target in O(N) time and O(1) space. Return a list of two indices [idx1, idx2] or an empty list [] if no pair exists.",
                    "skill_assessed": "Array Two Pointers & DSA",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "CODE",
                    "language": "python",
                    "code_snippet": (
                        "def two_sum_sorted(nums: list[int], target: int) -> list[int]:\n"
                        "    \"\"\"\n"
                        "    Finds two indices such that nums[i] + nums[j] == target in O(N) time.\n"
                        "    \"\"\"\n"
                        "    # ------------------------------------------------------------------\n"
                        "    # >>> START YOUR CODE HERE <<<\n"
                        "    # ------------------------------------------------------------------\n"
                        "    pass\n"
                    ),
                    "examples": [
                        {
                            "input": "nums = [2, 7, 11, 15], target = 9",
                            "output": "[0, 1]",
                            "explanation": "nums[0] + nums[1] = 2 + 7 = 9."
                        },
                        {
                            "input": "nums = [1, 2, 3, 4], target = 7",
                            "output": "[2, 3]",
                            "explanation": "nums[2] + nums[3] = 3 + 4 = 7."
                        },
                        {
                            "input": "nums = [1, 3, 5], target = 10",
                            "output": "[]",
                            "explanation": "No two numbers sum to 10."
                        }
                    ],
                    "constraints": [
                        "2 <= len(nums) <= 10^5",
                        "nums is sorted in non-decreasing order",
                        "Expected Time Complexity: O(N), Space Complexity: O(1)"
                    ],
                    "test_cases": [
                        {
                            "name": "Standard Pair Found",
                            "input": "nums=[2, 7, 11, 15], target=9",
                            "expected": [0, 1],
                            "test_code": "actual = two_sum_sorted([2, 7, 11, 15], 9)"
                        },
                        {
                            "name": "Higher Indices Pair",
                            "input": "nums=[1, 2, 3, 4], target=7",
                            "expected": [2, 3],
                            "test_code": "actual = two_sum_sorted([1, 2, 3, 4], 7)"
                        },
                        {
                            "name": "No Pair Exists",
                            "input": "nums=[1, 3, 5], target=10",
                            "expected": [],
                            "test_code": "actual = two_sum_sorted([1, 3, 5], 10)"
                        }
                    ],
                    "expected_concepts": ["two-pointer technique", "sorted array optimization", "O(N) time", "O(1) space"],
                    "evaluation_rubric": {"code_correctness": 50, "algorithmic_efficiency": 30, "verbal_walkthrough": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 4. Database Indexing & Query Tuning (MCQ)
                {
                    "question_text": "You have a relational database table with 10 million records. A query filtering by 'status = active' and ordering by 'created_at DESC' is running very slowly. Which composite index will optimize this query most effectively?",
                    "skill_assessed": "Database Indexing & Query Optimization",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "CREATE INDEX idx_status ON orders (status);"},
                        {"id": "B", "text": "CREATE INDEX idx_created ON orders (created_at DESC);"},
                        {"id": "C", "text": "CREATE INDEX idx_status_created ON orders (status, created_at DESC);"},
                        {"id": "D", "text": "CREATE BITMAP INDEX idx_all ON orders (id, status);"}
                    ],
                    "correct_option": "C",
                    "explanation": "A composite B-tree index on (status, created_at DESC) allows the query planner to filter precisely on status and read rows in already sorted order without an in-memory Sort/Filesort operation.",
                    "expected_concepts": ["composite index column ordering", "equality before range/sort", "avoiding filesort", "index scan"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 5. Production Reliability & Idempotency (SPOKEN)
                {
                    "question_text": f"In a distributed system using {secondary_skill} or message queues, describe how you would design for idempotency when processing payment or order mutations so that duplicate network retries do not cause double-charging.",
                    "skill_assessed": "Distributed Reliability & Idempotency",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["idempotency keys", "unique database constraints", "at-most-once semantics", "distributed locks / transactions"],
                    "evaluation_rubric": {"reliability_design": 45, "edge_case_handling": 35, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 6. Caching Strategies & Thundering Herd (MCQ)
                {
                    "question_text": "In a high-traffic system using Redis, what architectural technique best prevents the 'Cache Stampede' / 'Thundering Herd' effect when a popular cache key expires simultaneously for thousands of concurrent requests?",
                    "skill_assessed": "Distributed Caching & Concurrency",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "MCQ",
                    "options": [
                        {"id": "A", "text": "Set cache TTL to zero so all requests immediately query the database."},
                        {"id": "B", "text": "Use distributed mutex locks (Singleflight/Redlock) or probabilistic early expiration (XFetch) to recompute the value once."},
                        {"id": "C", "text": "Flush all Redis keys synchronously when memory reaches 80% capacity."},
                        {"id": "D", "text": "Replace Redis with synchronous file-system caching."}
                    ],
                    "correct_option": "B",
                    "explanation": "Using mutex locking (or Singleflight pattern) guarantees only one worker hits the primary database to refresh the expired key while others await the result, preventing database connection exhaustion.",
                    "expected_concepts": ["cache stampede mitigation", "distributed mutex / singleflight", "probabilistic early expiration", "connection pool protection"],
                    "evaluation_rubric": {"mcq_correctness": 60, "spoken_rationale": 40},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                },
                # 7. Memory Lifecycle & Garbage Collection (SPOKEN)
                {
                    "question_text": f"In {primary_skill}, explain how the runtime handles memory allocation and deallocation. How does reference counting interact with the cyclic generational garbage collector to prevent memory leaks?",
                    "skill_assessed": f"{primary_skill} Memory Internals",
                    "category": "technical",
                    "difficulty": difficulty,
                    "question_type": "SPOKEN",
                    "expected_concepts": ["reference counting", "generational garbage collection", "circular references", "weak references / __del__ quirks"],
                    "evaluation_rubric": {"runtime_depth": 50, "edge_cases": 30, "clarity": 20},
                    "max_score": 100.0,
                    "generation_source": "mock_generator"
                }
            ]

        # Filter and structure questions based on question_mix
        if question_mix == "spoken_only":
            filtered = [q for q in bank if q.get("question_type") == "SPOKEN"]
        elif question_mix == "coding_mcq":
            filtered = [q for q in bank if q.get("question_type") in ["MCQ", "CODE"]]
        else:
            # Balanced mix of Spoken, MCQ, and Code
            spoken_qs = [q for q in bank if q.get("question_type") == "SPOKEN"]
            mcq_qs = [q for q in bank if q.get("question_type") == "MCQ"]
            code_qs = [q for q in bank if q.get("question_type") == "CODE"]

            interleaved = []
            max_len = max(len(spoken_qs), len(mcq_qs), len(code_qs), 1)
            for i in range(max_len):
                if i < len(spoken_qs):
                    interleaved.append(spoken_qs[i])
                if i < len(mcq_qs):
                    interleaved.append(mcq_qs[i])
                if i < len(code_qs):
                    interleaved.append(code_qs[i])
            filtered = interleaved if interleaved else bank

        # Tile or cycle questions smoothly to satisfy any requested count (1 to 15+)
        result = []
        for i in range(count):
            q_template = dict(filtered[i % len(filtered)])
            q_template["difficulty"] = difficulty
            result.append(q_template)

        return result

    async def generate_followup_question(
        self,
        previous_question: Dict[str, Any],
        candidate_transcript: str
    ) -> Dict[str, Any]:
        return {
            "question_text": f"You mentioned in your answer: '{candidate_transcript[:80]}...'. Could you dive deeper into how you verified that under concurrent stress testing, and what failure modes you encountered?",
            "skill_assessed": previous_question.get("skill_assessed", "System Design"),
            "category": "project_deep_dive",
            "difficulty": previous_question.get("difficulty", "INTERMEDIATE"),
            "question_type": "SPOKEN",
            "expected_concepts": ["load testing", "concurrency limits", "graceful degradation", "metrics/monitoring"],
            "evaluation_rubric": {"depth_of_explanation": 50, "concurrency_handling": 30, "clarity": 20},
            "max_score": 100.0,
            "generation_source": "dynamic_followup",
            "is_followup": True
        }

    async def evaluate_answer(
        self,
        question_data: Dict[str, Any],
        transcript: str,
        selected_option: str | None = None,
        code_submission: str | None = None
    ) -> Dict[str, Any]:
        q_type = question_data.get("question_type", "SPOKEN")
        text = transcript.strip().lower() if transcript else ""
        word_count = len(text.split())
        expected = question_data.get("expected_concepts", [])

        # Universal uncertainty phrases check
        uncertainty_phrases = [
            "don't know", "dont know", "do not know", "no idea", "not sure",
            "haven't worked", "havent worked", "not familiar", "no clue",
            "sorry i don't", "sorry, i don't", "sorry i dont", "can't answer",
            "cant answer", "not aware", "never worked", "never used",
            "haven't used", "havent used", "don't really know", "dont really know",
            "no experience", "not experienced", "i am not sure", "im not sure"
        ]
        is_uncertain = any(phrase in text for phrase in uncertainty_phrases)

        # 1. MCQ Evaluation
        if q_type == "MCQ":
            correct_opt = question_data.get("correct_option")
            
            # Deterministic check for unattempted MCQ (no option chosen)
            if not selected_option:
                return {
                    "overall_score": 0.0,
                    "technical_score": 0.0,
                    "conceptual_score": 0.0,
                    "relevance_score": 0.0,
                    "clarity_score": 0.0,
                    "correct_concepts": [],
                    "missing_concepts": expected,
                    "incorrect_statements": ["No option was selected for this multiple-choice question."],
                    "transcript_evidence": [transcript] if transcript else ["No option selected and no audio provided."],
                    "feedback": f"No option was selected. The correct answer was {correct_opt}: {question_data.get('explanation', '')}",
                    "improvement_tips": [f"Review foundational principles of {question_data.get('skill_assessed')}."],
                    "confidence": 1.0,
                    "reliability_tier": "HIGH",
                    "why_this_score": "Candidate left this multiple-choice question unattempted."
                }

            is_correct = (selected_option is not None and selected_option.strip().upper() == str(correct_opt).strip().upper())
            matched = [c for c in expected if any(k in text for k in c.lower().split())]

            if is_uncertain:
                # Candidate admitted they don't know
                score = 15.0
                why = "Candidate explicitly acknowledged lack of knowledge on this question."
                if is_correct:
                    why += f" Option {selected_option} was selected but appears to be an ungrounded guess."
                else:
                    why += f" Option {selected_option} was selected and is incorrect (correct: {correct_opt})."
                return {
                    "overall_score": score,
                    "technical_score": score,
                    "conceptual_score": 15.0,
                    "relevance_score": 35.0,
                    "clarity_score": 80.0,
                    "correct_concepts": [],
                    "missing_concepts": expected,
                    "incorrect_statements": ["Candidate acknowledged unfamiliarity with the underlying principles."],
                    "transcript_evidence": [transcript] if transcript else [f"Selected option {selected_option}"],
                    "feedback": f"Candidate stated unfamiliarity with {question_data.get('skill_assessed')}. In an interview, walk through process of elimination or discuss related architectural patterns rather than guessing without justification.",
                    "improvement_tips": [f"Review foundational principles of {question_data.get('skill_assessed')}."],
                    "confidence": 0.98,
                    "reliability_tier": "HIGH",
                    "why_this_score": why
                }
            elif is_correct:
                # Correct option without uncertainty
                if len(matched) >= 2:
                    total_score = 92.0
                    why = f"Correctly selected Option {selected_option} and clearly articulated {len(matched)} core architectural concepts."
                elif len(matched) == 1:
                    total_score = 80.0
                    why = f"Correctly selected Option {selected_option} with partial conceptual justification."
                elif word_count > 5:
                    total_score = 70.0
                    why = f"Correctly selected Option {selected_option}, but spoken reasoning was vague."
                else:
                    total_score = 65.0
                    why = f"Correctly selected Option {selected_option} without verbal justification."

                return {
                    "overall_score": total_score,
                    "technical_score": total_score,
                    "conceptual_score": total_score,
                    "relevance_score": 100.0,
                    "clarity_score": 85.0 if word_count > 5 else 60.0,
                    "correct_concepts": matched if matched else [f"Identified correct answer ({correct_opt})"],
                    "missing_concepts": [c for c in expected if c not in matched],
                    "incorrect_statements": [],
                    "transcript_evidence": [transcript] if transcript else [f"Selected option {selected_option}"],
                    "feedback": f"Correct answer selected ({selected_option}). {question_data.get('explanation', '')}",
                    "improvement_tips": ["Continue grounding choices in underlying architectural trade-offs."],
                    "confidence": 0.98,
                    "reliability_tier": "HIGH",
                    "why_this_score": why
                }
            else:
                # Incorrect option
                score = 0.0
                return {
                    "overall_score": score,
                    "technical_score": score,
                    "conceptual_score": 0.0,
                    "relevance_score": 0.0,
                    "clarity_score": 50.0 if text else 0.0,
                    "correct_concepts": [],
                    "missing_concepts": expected,
                    "incorrect_statements": [f"Selected Option {selected_option}, but correct option is Option {correct_opt}."],
                    "transcript_evidence": [transcript] if transcript else [f"Selected Option {selected_option}"],
                    "feedback": f"Incorrect option selected ({selected_option}). The correct answer was Option {correct_opt}: {question_data.get('explanation', '')}",
                    "improvement_tips": [f"Review foundational concepts of {question_data.get('skill_assessed')}."],
                    "confidence": 1.0,
                    "reliability_tier": "HIGH",
                    "why_this_score": f"Option {selected_option} is incorrect. Correct option was {correct_opt}. Incorrect multiple-choice answers receive 0 marks."
                }

        # 2. CODE Evaluation
        if q_type == "CODE":
            code = code_submission.strip() if code_submission else ""
            starter = question_data.get("code_snippet", "").strip()
            matched = [c for c in expected if any(k in text for k in c.lower().split())]

            clean_code = "\n".join(l.strip() for l in code.splitlines() if l.strip() and not l.strip().startswith("#"))
            clean_starter = "\n".join(l.strip() for l in starter.splitlines() if l.strip() and not l.strip().startswith("#"))

            # Detect unattempted code or starter boilerplate unchanged
            is_unattempted = (
                not code or 
                not clean_code or 
                code == starter or 
                clean_code == clean_starter or
                ("pass" in clean_code and not any(k in clean_code for k in ["dict(", "{}", "Counter(", "defaultdict(", "counts", "seen", "freq"]))
            )

            if is_uncertain or is_unattempted:
                score = 10.0
                feedback = (
                    "Candidate indicated unfamiliarity with the code refactoring challenge." 
                    if is_uncertain else 
                    "Code challenge was submitted without implementation (starter template unchanged). You must write an implementation to earn technical score."
                )
                why = "Candidate stated they do not know how to solve this." if is_uncertain else "Candidate submitted unedited starter template without implementing the solution."
                return {
                    "overall_score": score,
                    "technical_score": score,
                    "conceptual_score": 10.0,
                    "relevance_score": 20.0,
                    "clarity_score": 60.0,
                    "correct_concepts": [],
                    "missing_concepts": expected,
                    "incorrect_statements": ["Code optimization was unattempted or left incomplete."],
                    "transcript_evidence": [transcript] if transcript else ["No code implemented."],
                    "feedback": feedback,
                    "improvement_tips": ["Practice implementing hash-map based frequency counting to optimize O(N^2) scans to linear O(N)."],
                    "confidence": 0.98,
                    "reliability_tier": "HIGH",
                    "why_this_score": why
                }

            # Real code quality heuristics: require actual hash map syntax in the implementation
            has_hashmap = any(term in code for term in ["dict(", "{}", "Counter(", "defaultdict(", ".get(", "counts[", "seen[", "freq["])
            has_linear_loop = ("for " in code and any(k in code for k in ["counts", "seen", "freq", "Counter", "dict"]))
            handles_return = "return" in code and ("token" in code or "t" in code) and "count(token)" not in code

            code_score = 25.0
            if has_hashmap:
                code_score += 35.0
            if has_linear_loop:
                code_score += 25.0
            if handles_return:
                code_score += 15.0

            verbal_bonus = min(10.0, len(matched) * 5.0)
            overall = min(100.0, code_score + verbal_bonus)

            evidence = []
            if transcript:
                evidence.append(f"Spoken: {transcript[:100]}")
            if code:
                evidence.append(f"Code: {code[:120].strip()}")

            return {
                "overall_score": overall,
                "technical_score": overall,
                "conceptual_score": overall * 0.95,
                "relevance_score": 90.0,
                "clarity_score": 85.0 if word_count > 10 else 70.0,
                "correct_concepts": matched + (["O(N) Hash Map Optimization"] if has_hashmap else []),
                "missing_concepts": [c for c in expected if c not in matched],
                "incorrect_statements": [] if has_hashmap else ["Code did not achieve optimal O(N) complexity."],
                "transcript_evidence": evidence,
                "feedback": "Successfully implemented hash-based linear optimization." if has_hashmap else "Code submitted, but optimal hash map counting was not achieved.",
                "improvement_tips": ["Always verify edge cases such as empty input arrays and all-duplicate tokens."],
                "confidence": 0.94,
                "reliability_tier": "HIGH",
                "why_this_score": f"Code solution achieved {round(code_score)}% implementation accuracy with verbal walkthrough of {len(matched)} core concepts."
            }

        # 3. SPOKEN Evaluation
        if is_uncertain:
            return {
                "overall_score": 15.0,
                "technical_score": 15.0,
                "conceptual_score": 15.0,
                "relevance_score": 35.0,
                "clarity_score": 85.0,
                "correct_concepts": [],
                "missing_concepts": expected,
                "incorrect_statements": ["Candidate acknowledged unfamiliarity with the required architectural concepts."],
                "transcript_evidence": [transcript] if transcript else ["Candidate indicated lack of knowledge."],
                "feedback": f"Candidate stated unfamiliarity with {question_data.get('skill_assessed')}. In an interview setting, acknowledge the gap and try to reason from first principles or related architectures you have worked on.",
                "improvement_tips": [f"Review foundational design patterns and trade-offs for {question_data.get('skill_assessed')}."],
                "confidence": 0.98,
                "reliability_tier": "HIGH",
                "why_this_score": "Candidate explicitly indicated they do not know the answer to this question."
            }

        matched = [c for c in expected if any(k in text for k in c.lower().split())]
        missing = [c for c in expected if c not in matched]

        if word_count < 10:
            return {
                "overall_score": 25.0,
                "technical_score": 20.0,
                "conceptual_score": 25.0,
                "relevance_score": 30.0,
                "clarity_score": 40.0,
                "correct_concepts": matched,
                "missing_concepts": missing,
                "incorrect_statements": ["Answer was too brief to demonstrate technical competency."],
                "transcript_evidence": [transcript] if transcript else ["No audio transcript detected."],
                "feedback": "The response was very brief. To demonstrate strong technical competency, provide explicit architectural rationale, relevant trade-offs, and concrete examples.",
                "improvement_tips": ["Elaborate on core underlying mechanisms rather than short high-level statements."],
                "confidence": 0.95,
                "reliability_tier": "HIGH",
                "why_this_score": "Score reflects insufficient detail and absence of expected foundational concepts."
            }

        coverage_ratio = len(matched) / max(len(expected), 1)
        if len(matched) == 0:
            overall = 30.0
            tech_score = 25.0
            concept_score = 25.0
            rel_score = 45.0
            clarity_score = 70.0
            feedback = f"Response did not address the expected technical concepts for {question_data.get('skill_assessed')}."
            why_this = "Candidate spoke at length but did not address the required core architectural concepts."
        else:
            base_score = 35.0 + (coverage_ratio * 60.0)
            overall = min(round(base_score, 1), 96.0)
            tech_score = min(round(overall * 0.95 + 4, 1), 98.0)
            concept_score = min(round(overall * 0.98, 1), 95.0)
            rel_score = min(round(overall * 1.02, 1), 100.0)
            clarity_score = 88.0 if word_count > 30 else 72.0
            feedback = f"Strong grasp of {question_data.get('skill_assessed')}. Successfully articulated key principles while remaining directly relevant to the scenario."
            why_this = f"Candidate demonstrated {len(matched)} of {len(expected)} expected concepts with solid clarity and direct relevance."

        quotes = [sentence.strip() for sentence in transcript.split(".") if len(sentence.strip()) > 15]

        return {
            "overall_score": overall,
            "technical_score": tech_score,
            "conceptual_score": concept_score,
            "relevance_score": rel_score,
            "clarity_score": clarity_score,
            "correct_concepts": matched if matched else ["Recognized basic problem domain"],
            "missing_concepts": missing[:2],
            "incorrect_statements": [],
            "transcript_evidence": quotes[:2] if quotes else [transcript[:100]],
            "feedback": feedback,
            "improvement_tips": [f"Deepen familiarity with {missing[0]}" if missing else "Consider citing formal benchmark numbers or metrics."],
            "confidence": 0.92,
            "reliability_tier": "HIGH",
            "why_this_score": why_this
        }

    async def check_knowledge_consistency(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if len(evaluations) < 2:
            return []

        scores = [e.get("overall_score", 0.0) for e in evaluations]
        avg_score = sum(scores) / len(scores)
        max_diff = max(scores) - min(scores)

        if avg_score < 35.0:
            return [{
                "concept_area": "Technical Core Consistency",
                "questions_compared": [e.get("question_id", i + 1) for i, e in enumerate(evaluations[:3])],
                "consistency_score": 0.20,
                "discrepancy_details": f"Candidate consistently struggled across technical fundamentals, conceptual questions, and code challenges (average score: {round(avg_score)}/100).",
                "root_cause": "Critical foundational knowledge gaps across evaluated domains"
            }]
        elif max_diff >= 40.0:
            consistency = round(max(0.15, 1.0 - (max_diff / 100.0)), 2)
            return [{
                "concept_area": "Technical Core Consistency",
                "questions_compared": [e.get("question_id", i + 1) for i, e in enumerate(evaluations[:3])],
                "consistency_score": consistency,
                "discrepancy_details": f"Significant performance discrepancy detected (spread of {round(max_diff)} points between strongest and weakest answer).",
                "root_cause": "Uneven conceptual foundation or guessing without applied grounding"
            }]
        elif avg_score >= 75.0 and max_diff <= 25.0:
            return [{
                "concept_area": "Technical Core Consistency",
                "questions_compared": [e.get("question_id", i + 1) for i, e in enumerate(evaluations[:3])],
                "consistency_score": 0.92,
                "discrepancy_details": "Demonstrated consistent architectural reasoning between foundational knowledge and applied scenarios.",
                "root_cause": "Uniform conceptual foundation"
            }]
        else:
            return [{
                "concept_area": "Technical Core Consistency",
                "questions_compared": [e.get("question_id", i + 1) for i, e in enumerate(evaluations[:3])],
                "consistency_score": 0.65,
                "discrepancy_details": "Demonstrated partial understanding with moderate consistency across topics.",
                "root_cause": "Developing technical competency with specific concept gaps"
            }]

