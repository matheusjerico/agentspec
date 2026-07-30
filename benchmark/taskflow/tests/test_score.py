from benchmark.taskflow.score import weighted_total


def test_weighted_total_uses_approved_weights():
    categories = {
        "correctness": 100,
        "requirements_planning": 80,
        "tests": 60,
        "code_quality": 40,
        "review_pr": 20,
        "efficiency": 0,
    }
    assert weighted_total(categories) == 68.0


def test_persistence_failure_caps_total():
    categories = {
        "correctness": 100,
        "requirements_planning": 100,
        "tests": 100,
        "code_quality": 100,
        "review_pr": 100,
        "efficiency": 100,
    }
    assert weighted_total(categories, persistence_passed=False) == 60.0
