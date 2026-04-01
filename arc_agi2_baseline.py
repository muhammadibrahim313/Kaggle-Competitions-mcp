import json
import os
from pathlib import Path

import numpy as np


def find_data_root():
    for folder, _, files in os.walk("/kaggle/input"):
        if "arc-agi_test_challenges.json" in files:
            return Path(folder)
    raise FileNotFoundError("ARC data files were not found under /kaggle/input")


root = find_data_root()

with open(root / "arc-agi_training_challenges.json") as f:
    train_tasks = json.load(f)
with open(root / "arc-agi_training_solutions.json") as f:
    train_answers = json.load(f)
with open(root / "arc-agi_evaluation_challenges.json") as f:
    eval_tasks = json.load(f)
with open(root / "arc-agi_evaluation_solutions.json") as f:
    eval_answers = json.load(f)
with open(root / "arc-agi_test_challenges.json") as f:
    test_tasks = json.load(f)

print(f"data root: {root}")
print(f"train={len(train_tasks)} eval={len(eval_tasks)} test={len(test_tasks)}")


def make_predictions(task):
    fallback = task["train"][0]["output"] if task["train"] else task["test"][0]["input"]
    rows = []
    for item in task["test"]:
        rows.append({
            "attempt_1": item["input"],
            "attempt_2": fallback
        })
    return rows


def evaluate(challenges, answers):
    hits = 0
    total = 0
    for task_id, task in challenges.items():
        preds = make_predictions(task)
        truth = answers[task_id]
        for pred, target in zip(preds, truth):
            total += 1
            a1 = np.array(pred["attempt_1"])
            a2 = np.array(pred["attempt_2"])
            gt = np.array(target)
            if np.array_equal(a1, gt) or np.array_equal(a2, gt):
                hits += 1
    score = hits / total if total else 0.0
    print(f"{hits}/{total} = {score:.4f}")
    return score


print("train score")
evaluate(train_tasks, train_answers)

print("eval score")
evaluate(eval_tasks, eval_answers)

submission = {task_id: make_predictions(task) for task_id, task in test_tasks.items()}
out_path = Path("/kaggle/working/submission.json")

with open(out_path, "w") as f:
    json.dump(submission, f)

sample_id = next(iter(submission))
print(f"saved: {out_path}")
print(f"tasks: {len(submission)}")
print(f"sample id: {sample_id}")
print(f"sample keys: {list(submission[sample_id][0].keys())}")
