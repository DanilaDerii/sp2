"""Build a page-grounded retrieval and answer evaluation set for ml.pdf."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = Path.home() / "Desktop" / "ml.pdf"
OUTPUT_PATH = REPO_ROOT / "evaluation" / "ml_pdf_eval_200.jsonl"

# Each topic stays in one split to prevent paraphrases of the same slide fact
# appearing in both validation and held-out evaluation data.
TOPICS = [
    ("samuel_definition", "train", [4], "Arthur Samuel's definition of machine learning", "Machine learning is the field of study that gives computers the ability to learn without being explicitly programmed."),
    ("mitchell_learning_problem", "train", [5], "Tom Mitchell's well-posed learning problem", "A well-posed learning problem has a clear task, a defined performance measure, and available experience. A program learns when its performance on task T, measured by P, improves with experience E."),
    ("spam_task", "train", [6], "the task T in the spam-filtering example", "The task is classifying emails as spam or not spam."),
    ("ml_uses", "train", [7], "the main uses of machine learning", "The lecture lists prediction, classification, and clustering."),
    ("well_posed_examples", "train", [8], "examples of well-posed learning problems", "Examples include spam filtering, handwritten digit recognition, playing checkers, object recognition, machine translation, and driving a robot car."),
    ("learning_types", "train", [9], "supervised and unsupervised learning", "Supervised learning teaches the computer to do something, while unsupervised learning lets it learn structure by itself. The lecture also names reinforcement learning and recommender systems."),
    ("supervised_tasks", "train", [10], "regression and classification in supervised learning", "Regression handles continuous variables and the lecture gives linear regression as an example. Classification handles categorical variables and the lecture gives k-nearest neighbors as an example."),
    ("linear_regression", "train", [11], "linear regression", "Linear regression learns a linear relationship between input X and output Y from data."),
    ("housing_formula", "train", [13], "the housing-price linear-regression example", "The example gives Price = 100 + 50 times the number of rooms."),
    ("regression_examples", "train", [16], "examples of regression targets", "The lecture lists tomorrow's stock-market price, a YouTube viewer's age, PSA amount, and temperature inside a building."),
    ("knn", "train", [17], "the k-nearest-neighbors classification algorithm", "KNN stores available cases and classifies a new case using a similarity measure such as a distance function. It is a non-parametric technique."),
    ("classification_output", "train", [18], "classification output in the breast-cancer example", "Classification has a discrete-valued output. The example labels breast cancer as malignant or benign, represented as 0 or 1."),
    ("classification_features", "train", [19], "features used in the classification example", "The visible features are clump thickness, uniformity of cell size, and uniformity of cell shape."),
    ("classification_examples", "train", [21], "examples of classification", "Examples are deciding whether email is spam, whether an image is a cat or dog, and categorizing YouTube videos."),
    ("supervised_apps", "train", [22], "applications of supervised learning", "The lecture lists bioinformatics, speech recognition, spam detection, and object recognition for vision."),
    ("clustering", "train", [24], "clustering in unsupervised learning", "Clustering has no predefined classes. It groups data points into clusters to find structure, and the lecture names k-means."),
    ("unsupervised_apps", "train", [28], "applications of unsupervised learning", "The lecture lists uses in grocery or e-commerce, social media, services, banking, politics, data visualization, entertainment, image segmentation, content, and structural discovery."),
    ("lifecycle", "val", [29], "the machine-learning life cycle", "The steps are: identify the problem and business understanding; prepare data by collecting and cleaning; choose an algorithm and build the model; train; test; and deploy."),
    ("business_understanding", "val", [30], "business understanding in the machine-learning life cycle", "The first life-cycle stage is identifying the problem through business understanding, including determining, understanding, and mapping the problem."),
    ("data_preparation", "val", [31], "data preparation", "Data preparation is the second life-cycle stage and includes identifying, collecting, and processing data."),
    ("diabetes_attributes", "val", [32], "the diabetes-prediction example attributes", "The listed attributes are pregnancies, glucose concentration, blood pressure, skinfold thickness, BMI, diabetes pedigree function, age, and income."),
    ("algorithm_choice", "test", [34], "choosing a machine-learning algorithm", "The lecture organizes algorithm choice into supervised learning, with regression and classification, and unsupervised learning, with clustering."),
    ("train_test_split", "test", [35], "the training and testing split", "The slide shows an 80 percent and 20 percent split for training and testing the model."),
    ("feature_engineering", "test", [36], "feature engineering", "Feature engineering is critical for correctly predicting the target value, goes beyond feature selection, and improves machine-learning model performance."),
    ("fit_and_metrics", "test", [37, 38, 39, 40], "underfitting, overfitting, and model evaluation", "Underfitting has high bias and overfitting has high variance. The lecture lists ways to reduce each and evaluates classification with confusion-matrix metrics and regression with error metrics such as MAE, MSE, RMSE, and MAPE."),
]

QUESTION_TEMPLATES = [
    "What is {topic}?",
    "Can you explain {topic} in simple terms?",
    "I am revising for an exam. What should I remember about {topic}?",
    "How does this lecture describe {topic}?",
    "Give me a concise answer about {topic} based on the slides.",
    "What is the main idea of {topic} in this material?",
    "Please summarize what the lecture says about {topic}.",
    "A classmate asked me about {topic}. How should I answer from this lecture?",
]

UNANSWERABLE = [
    ("unanswerable_1", "train", "What learning rate should I use for gradient descent?"),
    ("unanswerable_2", "train", "How does a random forest choose its trees?"),
    ("unanswerable_3", "train", "What is the formula for logistic regression?"),
    ("unanswerable_4", "val", "How many hidden layers should a neural network have?"),
    ("unanswerable_5", "test", "What does ROC-AUC measure?"),
]


def _source_sha256() -> str:
    return hashlib.sha256(SOURCE_PDF.read_bytes()).hexdigest()


def build_samples() -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    for topic_id, split, pages, topic, expected_answer in TOPICS:
        for variant, template in enumerate(QUESTION_TEMPLATES, start=1):
            samples.append(
                {
                    "id": f"ml-{topic_id}-{variant:02d}",
                    "split": split,
                    "answerable": True,
                    "question": template.format(topic=topic),
                    "expected_answer": expected_answer,
                    "supporting_pages": pages,
                    "expected_citations": [f"ml.pdf p. {page}" for page in pages],
                    "topic_group": topic_id,
                }
            )

    for sample_id, split, question in UNANSWERABLE:
        samples.append(
            {
                "id": f"ml-{sample_id}",
                "split": split,
                "answerable": False,
                "question": question,
                "expected_answer": "The PDF does not provide enough information to answer this question.",
                "supporting_pages": [],
                "expected_citations": [],
                "topic_group": sample_id,
            }
        )

    if len(samples) != 205:
        raise ValueError(f"Expected 205 samples, found {len(samples)}")
    samples = [sample for sample in samples if sample["id"] not in {
        "ml-samuel_definition-08",
        "ml-mitchell_learning_problem-08",
        "ml-spam_task-08",
        "ml-ml_uses-08",
        "ml-well_posed_examples-08",
    }]
    test_groups = {
        "samuel_definition",
        "algorithm_choice",
        "train_test_split",
        "feature_engineering",
        "fit_and_metrics",
        "unanswerable_5",
    }
    for sample in samples:
        sample["split"] = "test" if sample["topic_group"] in test_groups else "val"
    return samples


def main() -> None:
    if not SOURCE_PDF.is_file():
        raise FileNotFoundError(f"Source PDF not found: {SOURCE_PDF}")

    samples = build_samples()
    counts = {split: sum(item["split"] == split for item in samples) for split in ("val", "test")}
    if len(samples) != 200 or counts != {"val": 160, "test": 40}:
        raise ValueError(f"Unexpected split counts: total={len(samples)}, splits={counts}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "dataset": "ml_pdf_eval_200",
        "source_pdf": str(SOURCE_PDF),
        "source_sha256": _source_sha256(),
        "sample_count": len(samples),
        "splits": counts,
    }
    with OUTPUT_PATH.open("w", encoding="utf-8") as output:
        output.write(json.dumps({"_metadata": metadata}, ensure_ascii=True) + "\n")
        for sample in samples:
            output.write(json.dumps(sample, ensure_ascii=True) + "\n")

    print(f"Wrote {len(samples)} samples to {OUTPUT_PATH}")
    print(f"Split counts: {counts}")


if __name__ == "__main__":
    main()
