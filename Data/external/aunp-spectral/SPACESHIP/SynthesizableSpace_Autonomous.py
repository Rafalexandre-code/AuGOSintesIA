"""
Reaction Space Explorer for Active Learning.

Explores reaction parameter space using various acquisition strategies
with robot annotation support.
"""

from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Algorithm.Bayesian.target_space import DiscreteSpace, PropertySpace, TargetSpace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
from BaseModel.gpclassifier import GPC
from BaseModel.vgpclassifier import vGPC
from BaseModel.wvgpclassifier import wvGPC
from BaseModel.logistic import Logistic
from BaseModel.xgboost import Xgboost
from BaseModel.mlp import MLP
from BaseModel.vime import VIME
from BaseModel.widedeep import WideDeep
from BaseModel.widedeep_transfer import WideDeepTransfer
from FileManager import FileManager, ModelManager

MODEL_CLASSES = {
    "GPC": GPC,
    "vGPC": vGPC,
    "wvGPC": wvGPC,
    "logit": Logistic,
    "mlp": MLP,
    "VIME": VIME,
    "xgboost": Xgboost,
    "WideDeep": WideDeep,
}

TRANSFER_UTILITY_TYPES = ["badge", "bald", "weighted_uncertainty", "teacher_student"]


class ReactionSpace:
    """Reaction space explorer with active learning strategies."""

    def __init__(self, configfile: dict) -> None:
        self.configfile = configfile

        self.seed_num = configfile["randomState"]
        self.initial_sampling = configfile["samplingSize"]
        self.additional_sampling = configfile["additionalSamplingSize"]
        self.utility_type = configfile["utilityType"]
        self.batch_size = configfile["batchSize"]
        self.iter_num = configfile["totalCycleNum"]
        self.threshold = configfile["classThreshold"]
        self.surrogate = configfile["surrogateModel"]
        self.loss_target = configfile["loss"]["lossTarget"]
        self.loss_method = configfile["loss"]["lossMethod"]

        base_path = Path(configfile["saveDirPath"])
        self.unlabeled_path = base_path / "unlabeledSet.json"
        self.underlabeling_path = base_path / "underLabelingSet.json"
        self.labeled_path = base_path / "labeledSet.json"
        self.finetuned_path = base_path / "finetuned.json"
        self.valid_path = base_path / "validSet.json"
        self.eval_path = base_path / "evalSet.json"
        self.score_path = base_path / "score.json"
        self.true_path = base_path / "true.json"
        self.predicted_path = base_path / "predicted.json"
        self.proba_path = base_path / "probability.json"
        self.model_path = Path(configfile["ModelPath"])

        self.unlabeled_fm = FileManager(self.unlabeled_path)
        self.underlabeling_fm = FileManager(self.underlabeling_path)
        self.labeled_fm = FileManager(self.labeled_path)
        self.finetuned_fm = FileManager(self.finetuned_path)
        self.valid_fm = FileManager(self.valid_path)
        self.eval_fm = FileManager(self.eval_path)
        self.score_fm = FileManager(self.score_path)
        self.model_fm = ModelManager(self.model_path)
        self.true_fm = FileManager(self.true_path)
        self.predicted_fm = FileManager(self.predicted_path)
        self.proba_fm = FileManager(self.proba_path)

        self.prange = configfile["prangeDict"]
        self.target_condition_dict = configfile["targetConditionDict"]

        self.pbounds = {
            item[0]: (item[1][:2])
            for item in sorted(self.prange.items(), key=lambda x: x[0])
        }
        self._space = TargetSpace(
            target_func=None, pbounds=self.pbounds, random_state=self.seed_num
        )
        self._real_space = DiscreteSpace(
            target_func=None, prange=self.prange, random_state=self.seed_num
        )
        self._property_space = PropertySpace(
            pbounds=self.pbounds, target_condition_dict=self.target_condition_dict
        )
        self.cross_option = None

    @staticmethod
    def _calc_euclidean(list1: list, list2: list) -> float:
        """Calculate Euclidean distance between two points."""
        squared_dist = sum((a - b) ** 2 for a, b in zip(list1, list2))
        return np.sqrt(squared_dist)

    @staticmethod
    def _check_binary_labels(data: list) -> bool:
        """Check if data contains both binary labels (0 and 1)."""
        label_set = {i["label"] for i in data}
        return 0 in label_set and 1 in label_set

    def _random_sampling(self) -> None:
        """Sample one random point from unlabeled data."""
        unlabeled_data = self.unlabeled_fm.load_data()
        underlabeling_data = self.underlabeling_fm.load_data()

        underlabeling_data.append(
            unlabeled_data.pop(random.randint(0, len(unlabeled_data) - 1))
        )

        for item in underlabeling_data:
            item["cycle"] = -1
            item["strategy"] = "R"

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(underlabeling_data)

    def get_data_size(self) -> int:
        """Return the number of labeled data points."""
        return len(self.labeled_fm.load_data())

    def initial_random_sampling(self) -> None:
        """Sample initial random points for model training."""
        unlabeled_data = self.unlabeled_fm.load_data()
        underlabeling_data = self.underlabeling_fm.load_data()

        for item in underlabeling_data:
            item["cycle"] = -1
            item["strategy"] = "R"

        for _ in range(self.initial_sampling):
            underlabeling_data.append(
                unlabeled_data.pop(random.randint(0, len(unlabeled_data) - 1))
            )

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(underlabeling_data)

    def initial_latin_sampling(self) -> None:
        """Sample initial points using Latin hypercube method."""
        unlabeled_data = self.unlabeled_fm.load_data()
        underlabeling_data = self.underlabeling_fm.load_data()

        sample = self._space.latin_sample(n_samples=self.initial_sampling).tolist()

        for _ in range(self.initial_sampling):
            distance_matrix = np.zeros((len(unlabeled_data), len(sample)))
            for j, s in enumerate(sample):
                for i, u in enumerate(unlabeled_data):
                    distance_matrix[i][j] = self._calc_euclidean(u["coordination"], s)

            min_idx = np.argmin(distance_matrix)
            un_idx, sam_idx = np.unravel_index(min_idx, distance_matrix.shape)
            underlabeling_data.append(unlabeled_data.pop(un_idx))
            sample = np.delete(sample, sam_idx, axis=0)

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(underlabeling_data)

    def additional_random_sampling(self) -> None:
        """Sample additional random points for model training."""
        unlabeled_data = self.unlabeled_fm.load_data()
        underlabeling_data = self.underlabeling_fm.load_data()

        for _ in tqdm(range(self.additional_sampling), desc="Extracting"):
            underlabeling_data.append(
                unlabeled_data.pop(random.randint(0, len(unlabeled_data) - 1))
            )

        for item in underlabeling_data:
            item["cycle"] = -1
            item["strategy"] = "AR"

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(underlabeling_data)

    def train_model(self, model_name: str) -> tuple:
        """Train surrogate model and return model with accuracy."""
        labeled_data = self.labeled_fm.load_data()
        valid_data = self.valid_fm.load_data()

        if not self._check_binary_labels(labeled_data):
            return None, 0.0

        model_class = MODEL_CLASSES.get(model_name)
        if model_class is None:
            raise ValueError(f"Unknown model: {model_name}")

        model_obj = model_class(train=labeled_data, test=valid_data)
        model_obj.create_model()

        if self.utility_type in TRANSFER_UTILITY_TYPES:
            finetuned_data = self.finetuned_fm.load_data()
            pretrained_path = "USER/NY/DB/[ReactionSpace]FreeParameter/base_model_seed9.pth"

            teacher_model = None
            if self.utility_type == "teacher_student":
                teacher_model = WideDeepTransfer(
                    train=labeled_data, test=valid_data, pretrained_path=pretrained_path
                )
                teacher_model.create_model()
                teacher_model.load_pretrained()

            model_obj = WideDeepTransfer(
                train=labeled_data, test=valid_data, pretrained_path=pretrained_path
            )
            model_obj.create_model()
            model_obj.load_pretrained()
            model_obj.fit(finetune_data=finetuned_data, epochs=50, lr=0.0005)

            accuracy = model_obj.predict()
            self._save_model_results(model_obj, valid_data, accuracy)

            if self.utility_type == "teacher_student":
                return model_obj, teacher_model, accuracy
            return model_obj, accuracy

        model_obj.fit()
        accuracy = model_obj.predict()
        self._save_model_results(model_obj, valid_data, accuracy)
        return model_obj, accuracy

    def _save_model_results(
        self, model_obj: object, valid_data: list, accuracy: float
    ) -> None:
        """Save model predictions and accuracy."""
        datasize = len(valid_data[0]["coordination"])
        x_valid = torch.Tensor(
            np.array([i["coordination"] for i in valid_data]).reshape(-1, datasize)
        )

        probability = model_obj.probability_model(x_valid)
        proba_data = self.proba_fm.load_data()
        proba_data.append(probability.tolist())
        self.proba_fm.save_data(proba_data)

        score_data = self.score_fm.load_data()
        score_data.append(accuracy)
        self.score_fm.save_data(score_data)

        true_value = [i["label"] for i in valid_data]
        self.true_fm.save_data(true_value)

        predicted_value = model_obj.sample_model(x_valid)
        predicted_data = self.predicted_fm.load_data()
        predicted_data.append(predicted_value.tolist())
        self.predicted_fm.save_data(predicted_data)

    def save_data(self, model_obj: object) -> None:
        """Save model evaluation data."""
        valid_data = self.valid_fm.load_data()
        datasize = len(valid_data[0]["coordination"])
        x_valid = torch.Tensor(
            np.array([i["coordination"] for i in valid_data]).reshape(-1, datasize)
        )

        probability = model_obj.probability_model(x_valid)
        proba_data = self.proba_fm.load_data()
        proba_data.append(probability.tolist())
        self.proba_fm.save_data(proba_data)

        score_data = self.score_fm.load_data()
        accuracy = model_obj.predict()
        score_data.append(accuracy)
        self.score_fm.save_data(score_data)

        true_value = [i["label"] for i in valid_data]
        self.true_fm.save_data(true_value)

        predicted_value = model_obj.sample_model(x_valid)
        predicted_data = self.predicted_fm.load_data()
        predicted_data.append(predicted_value.tolist())
        self.predicted_fm.save_data(predicted_data)

    def _balanced_select(
        self, base_scores: np.ndarray, probs: np.ndarray, batch_size: int, top_k: int = 10
    ) -> list | None:
        """Select samples with class balance consideration."""
        finetuned_data = self.finetuned_fm.load_data()
        labels = [i.get("label") for i in finetuned_data if i.get("label") is not None]

        if len(labels) == 0:
            return None

        counts = {}
        for label in labels:
            counts[int(label)] = counts.get(int(label), 0) + 1

        probs_arr = np.asarray(probs)
        num_classes = probs_arr.shape[1]
        for cls in range(num_classes):
            counts.setdefault(cls, 0)

        remaining_indices = list(range(len(base_scores)))
        scores = np.asarray(base_scores)
        selected = []

        for _ in range(min(batch_size, len(scores))):
            top_n = min(top_k, len(scores))
            top_k_idx = np.argsort(scores)[-top_n:]
            target_class = min(counts, key=counts.get)
            pick_rel = top_k_idx[np.argmax(probs_arr[top_k_idx, target_class])]
            selected.append(remaining_indices[pick_rel])
            counts[target_class] += 1
            scores = np.delete(scores, pick_rel)
            probs_arr = np.delete(probs_arr, pick_rel, axis=0)
            remaining_indices.pop(pick_rel)

        return selected

    def suggest_next_step(self) -> tuple[list, list]:
        """Suggest next experiment points based on acquisition strategy."""
        if self.iter_num < self.initial_sampling:
            self._random_sampling()
        else:
            unlabeled_data = self.unlabeled_fm.load_data()
            underlabeling_data = self.underlabeling_fm.load_data()
            labeled_data = self.labeled_fm.load_data()
            x_unlabeled = [i["coordination"] for i in unlabeled_data]

            handler = self._get_utility_handler()
            handler(unlabeled_data, underlabeling_data, labeled_data, x_unlabeled)

            self.unlabeled_fm.save_data(unlabeled_data)
            self.underlabeling_fm.save_data(underlabeling_data)

        return self.robot_annotation_formatter()

    def _get_utility_handler(self):
        """Return the appropriate handler for the utility type."""
        handlers = {
            "confidence": self._handle_confidence,
            "variance": self._handle_variance,
            "dynamic": self._handle_dynamic,
            "dynamic_time": self._handle_dynamic_time,
            "dynamic_switch": self._handle_dynamic_switch,
            "active": self._handle_active,
            "cross": self._handle_cross,
            "badge": self._handle_badge,
            "bald": self._handle_bald,
            "teacher_student": self._handle_teacher_student,
            "weighted_uncertainty": self._handle_weighted_uncertainty,
        }
        return handlers.get(self.utility_type, self._handle_confidence)

    def _handle_confidence(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle confidence-based acquisition."""
        confidence_model, _ = self.train_model(model_name=self.surrogate)
        self.save_data(confidence_model)

        proba = confidence_model.probability_model(x_unlabeled)
        check_confidence = [float(abs(p - 0.5)) for p in proba]

        for idx, candidate in enumerate(unlabeled_data):
            candidate["confidence"]["not react"] = float(abs(proba[idx] - 1))
            candidate["confidence"]["react"] = float(proba[idx])
            candidate["cycle"] = len(labeled_data) + 1

        for _ in range(self.batch_size):
            max_idx = check_confidence.index(min(check_confidence))
            underlabeling_data.append(unlabeled_data.pop(max_idx))
            check_confidence.pop(max_idx)

    def _handle_variance(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle variance-based acquisition."""
        confidence_model, _ = self.train_model(model_name=self.surrogate)
        self.save_data(confidence_model)

        variance = confidence_model.variance_model(x_unlabeled)
        for _ in range(self.batch_size):
            max_idx = np.argmax(variance)
            unlabeled_data[max_idx]["logit"].append(float(variance[max_idx]))
            unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
            underlabeling_data.append(unlabeled_data.pop(max_idx))
            variance = np.delete(variance, max_idx)

    def _handle_dynamic(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle dynamic acquisition (confidence + variance)."""
        confidence_model, _ = self.train_model(model_name="GPC")
        variance_model, _ = self.train_model(model_name="vGPC")
        self.save_data(confidence_model)

        alpha = 0.5
        confidence = confidence_model.probability_model(x_unlabeled)
        variance = variance_model.variance_model(x_unlabeled)

        dynamic_score = alpha * variance / np.array([abs(x - 0.5) for x in confidence])

        for _ in range(self.batch_size):
            max_idx = np.argmax(dynamic_score)
            unlabeled_data[max_idx]["logit"].append(float(dynamic_score[max_idx]))
            unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
            underlabeling_data.append(unlabeled_data.pop(max_idx))
            dynamic_score = np.delete(dynamic_score, max_idx)

    def _handle_dynamic_time(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle time-based dynamic acquisition."""
        confidence_model, _ = self.train_model(model_name="GPC")
        variance_model, _ = self.train_model(model_name="vGPC")
        self.save_data(confidence_model)

        alpha = 0.5 * 100 / self.iter_num
        confidence = confidence_model.probability_model(x_unlabeled)
        variance = variance_model.variance_model(x_unlabeled)

        dynamic_score = alpha * variance / np.array([abs(x - 0.5) for x in confidence])

        for _ in range(self.batch_size):
            max_idx = np.argmax(dynamic_score)
            unlabeled_data[max_idx]["logit"].append(float(dynamic_score[max_idx]))
            unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
            underlabeling_data.append(unlabeled_data.pop(max_idx))
            dynamic_score = np.delete(dynamic_score, max_idx)

    def _handle_dynamic_switch(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle switching between variance and confidence."""
        confidence_model, _ = self.train_model(model_name="GPC")
        variance_model, _ = self.train_model(model_name="vGPC")

        if self.iter_num < 30:
            self.save_data(variance_model)
            variance = variance_model.variance_model(x_unlabeled)
            for _ in range(self.batch_size):
                max_idx = np.argmax(variance)
                unlabeled_data[max_idx]["logit"].append(float(variance[max_idx]))
                unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
                underlabeling_data.append(unlabeled_data.pop(max_idx))
                variance = np.delete(variance, max_idx)
        else:
            self.save_data(confidence_model)
            confidence = confidence_model.probability_model(x_unlabeled)
            check_confidence = [float(abs(c - 0.5)) for c in confidence]

            for idx, candidate in enumerate(unlabeled_data):
                candidate["confidence"]["not react"] = float(abs(confidence[idx] - 1))
                candidate["confidence"]["react"] = float(confidence[idx])
                candidate["cycle"] = len(labeled_data) + 1

            for _ in range(self.batch_size):
                max_idx = check_confidence.index(min(check_confidence))
                underlabeling_data.append(unlabeled_data.pop(max_idx))
                check_confidence.pop(max_idx)

    def _handle_active(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle active model selection."""
        confidence_model, _ = self.train_model(model_name="GPC")
        variance_model, _ = self.train_model(model_name="vGPC")

        variance_score = variance_model.predict()
        confidence_score = confidence_model.predict()

        if variance_score > confidence_score:
            self.save_data(variance_model)
            variance = variance_model.probability_model(x_unlabeled)
            for _ in range(self.batch_size):
                max_idx = np.argmax(variance)
                unlabeled_data[max_idx]["logit"].append(float(variance[max_idx]))
                unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
                underlabeling_data.append(unlabeled_data.pop(max_idx))
                variance = np.delete(variance, max_idx)
        else:
            self.save_data(confidence_model)
            confidence = confidence_model.probability_model(x_unlabeled)

            for idx, candidate in enumerate(unlabeled_data):
                class_probs = confidence[idx]
                sorted_probs, sorted_indices = torch.sort(
                    torch.Tensor(class_probs), descending=True
                )
                uncertainty = abs(sorted_probs[0].item() - sorted_probs[1].item())

                candidate["confidence"] = {
                    f"class_{i}": float(class_probs[i]) for i in range(len(class_probs))
                }
                candidate["uncertainty"] = uncertainty
                candidate["most_likely_class"] = int(sorted_indices[0].item())
                candidate["second_most_likely_class"] = int(sorted_indices[1].item())
                candidate["cycle"] = len(labeled_data) + 1

            check_confidence = [c["uncertainty"] for c in unlabeled_data]
            for _ in range(self.batch_size):
                max_idx = check_confidence.index(min(check_confidence))
                underlabeling_data.append(unlabeled_data.pop(max_idx))
                check_confidence.pop(max_idx)

    def _handle_cross(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle cross-model acquisition."""
        confidence_model, _ = self.train_model(model_name="GPC")
        variance_model, _ = self.train_model(model_name="vGPC")

        variance_score = variance_model.predict()
        confidence_score = confidence_model.predict()

        if self.cross_option is None and variance_score < confidence_score:
            self.cross_option = True

        if self.cross_option:
            self.save_data(variance_model)
            confidence = variance_model.probability_model(x_unlabeled)
        else:
            self.save_data(confidence_model)
            confidence = confidence_model.probability_model(x_unlabeled)

        check_confidence = [float(abs(c - 0.5)) for c in confidence]

        for idx, candidate in enumerate(unlabeled_data):
            candidate["confidence"]["not react"] = float(abs(confidence[idx] - 1))
            candidate["confidence"]["react"] = float(confidence[idx])
            candidate["cycle"] = len(labeled_data) + 1

        for _ in range(self.batch_size):
            max_idx = check_confidence.index(min(check_confidence))
            underlabeling_data.append(unlabeled_data.pop(max_idx))
            check_confidence.pop(max_idx)

    def _handle_badge(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle BADGE acquisition strategy."""
        widedeep_model, _ = self.train_model(model_name="WideDeep")
        self.save_data(widedeep_model)

        probs = widedeep_model.probability_model(x_unlabeled)
        uncertainty = 1 - np.max(probs, axis=1)

        selected_indices = self._balanced_select(uncertainty, probs, self.batch_size)
        if selected_indices is None:
            selected_indices = np.argsort(uncertainty)[-self.batch_size:][::-1]

        for idx in sorted(selected_indices, reverse=True):
            unlabeled_data[idx]["uncertainty"] = float(uncertainty[idx])
            unlabeled_data[idx]["cycle"] = len(labeled_data) + 1
            unlabeled_data[idx]["strategy"] = "BADGE"
            underlabeling_data.append(unlabeled_data.pop(idx))

    def _handle_bald(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle BALD acquisition strategy."""
        widedeep_model, _ = self.train_model(model_name="WideDeep")
        self.save_data(widedeep_model)

        probs = widedeep_model.probability_model(x_unlabeled)
        bald_scores = -np.sum(probs * np.log(probs + 1e-10), axis=1)

        selected_indices = self._balanced_select(bald_scores, probs, self.batch_size)
        if selected_indices is None:
            selected_indices = np.argsort(bald_scores)[-self.batch_size:][::-1]

        for idx in sorted(selected_indices, reverse=True):
            unlabeled_data[idx]["bald_score"] = float(bald_scores[idx])
            unlabeled_data[idx]["cycle"] = len(labeled_data) + 1
            unlabeled_data[idx]["strategy"] = "BALD"
            underlabeling_data.append(unlabeled_data.pop(idx))

    def _handle_teacher_student(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle Teacher-Student disagreement strategy."""
        student_model, teacher_model, _ = self.train_model(model_name="WideDeep")
        self.save_data(student_model)

        teacher_probs = teacher_model.probability_model(x_unlabeled)
        student_probs = student_model.probability_model(x_unlabeled)

        ts_uncertainty = np.mean(np.abs(teacher_probs - student_probs), axis=1)

        selected_indices = self._balanced_select(ts_uncertainty, student_probs, self.batch_size)
        if selected_indices is None:
            selected_indices = np.argsort(ts_uncertainty)[-self.batch_size:][::-1]

        for idx in sorted(selected_indices, reverse=True):
            unlabeled_data[idx]["ts_uncertainty"] = float(ts_uncertainty[idx])
            unlabeled_data[idx]["cycle"] = len(labeled_data) + 1
            unlabeled_data[idx]["strategy"] = "TeacherStudent"
            underlabeling_data.append(unlabeled_data.pop(idx))

    def _handle_weighted_uncertainty(
        self, unlabeled_data: list, underlabeling_data: list,
        labeled_data: list, x_unlabeled: list
    ) -> None:
        """Handle weighted uncertainty (LC + Margin + Entropy)."""
        widedeep_model, _ = self.train_model(model_name="WideDeep")
        self.save_data(widedeep_model)

        probs = widedeep_model.probability_model(x_unlabeled)

        lc = 1 - np.max(probs, axis=1)
        sorted_probs = np.sort(probs, axis=1)[:, ::-1]
        margin = 1 - (sorted_probs[:, 0] - sorted_probs[:, 1])
        entropy = -np.sum(probs * np.log(probs + 1e-10), axis=1)
        entropy = entropy / np.log(probs.shape[1])

        weighted_scores = 0.4 * lc + 0.3 * margin + 0.3 * entropy

        selected_indices = self._balanced_select(weighted_scores, probs, self.batch_size)
        if selected_indices is None:
            selected_indices = np.argsort(weighted_scores)[-self.batch_size:][::-1]

        for idx in sorted(selected_indices, reverse=True):
            unlabeled_data[idx]["weighted_uncertainty"] = float(weighted_scores[idx])
            unlabeled_data[idx]["cycle"] = len(labeled_data) + 1
            unlabeled_data[idx]["strategy"] = "WeightedUncertainty"
            underlabeling_data.append(unlabeled_data.pop(idx))

    def evaluation(self) -> list:
        """Evaluate models on test set."""
        eval_data = self.eval_fm.load_data()
        x_test = [i["coordination"] for i in eval_data]
        y_test = [i["label"] for i in eval_data]

        result = []
        for n in tqdm(range(20, 300)):
            model = self.model_fm.load_model(n)
            y_eval = model.predict(x_test)
            result.append(accuracy_score(y_test, y_eval))

        return result

    def validation(self) -> list:
        """Validate models on validation set."""
        valid_data = self.valid_fm.load_data()
        x_test = [i["coordination"] for i in valid_data]
        y_test = [i["label"] for i in valid_data]

        result = []
        for n in tqdm(range(20, 300)):
            model = self.model_fm.load_model(n)
            y_valid = model.predict(x_test)
            result.append(accuracy_score(y_test, y_valid))

        return result

    def robot_annotation_formatter(self) -> tuple[list, list]:
        """Format annotation data for robot."""
        underlabeling_data = self.underlabeling_fm.load_data()
        underlabeling_value = [i["coordination"] for i in underlabeling_data]
        parameters = list(self.configfile["prangeDict"].keys())

        norm_recipe = [
            dict(zip(parameters, val)) for val in underlabeling_value
        ]

        prange_lists = [self.configfile["prangeDict"][key] for key in parameters]

        for i, val in enumerate(underlabeling_value):
            for j in range(len(parameters)):
                underlabeling_value[i][j] = np.round(
                    prange_lists[j][0] + val[j] * (prange_lists[j][1] - prange_lists[j][0]),
                    3
                )

        real_recipe = [
            dict(zip(parameters, val)) for val in underlabeling_value
        ]

        return real_recipe, norm_recipe

    def robot_annotation(self, value: int) -> None:
        """Apply robot annotation to underlabeling data."""
        underlabeling_data = self.underlabeling_fm.load_data()

        for item in underlabeling_data:
            item["label"] = int(value)

        labeled_data = self.labeled_fm.load_data()
        finetuned_data = None

        if self.utility_type in TRANSFER_UTILITY_TYPES:
            finetuned_data = self.finetuned_fm.load_data()

        while underlabeling_data:
            labeled_item = underlabeling_data.pop()
            labeled_data.append(labeled_item)
            if finetuned_data is not None:
                finetuned_data.append(labeled_item)

        self.underlabeling_fm.save_data(underlabeling_data)
        self.labeled_fm.save_data(labeled_data)

        if finetuned_data is not None:
            self.finetuned_fm.save_data(finetuned_data)

        print("Annotation completed")

    @property
    def space(self):
        """Return the target space."""
        return self._space

    @property
    def res(self) -> list:
        """Return labeled results."""
        return self._get_results()

    def _get_results(self) -> list:
        """Get labeled data as result format."""
        labeled_data = self.labeled_fm.load_data()
        labeled_value = [i["coordination"] for i in labeled_data]
        parameters = list(self.configfile["algorithm"]["prangeDict"].keys())

        result = []
        for i, val in enumerate(labeled_value):
            temp_result = dict(zip(parameters, val))
            temp_result["label"] = labeled_data[i]["label"]
            result.append(temp_result)

        return result

    def output_space(self, dirname: str, filename: str) -> None:
        """Output normalized space as CSV file."""
        total_path = Path(dirname) / f"{filename}.csv"
        Path(dirname).mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(data=self.space.params, columns=self.space.keys)
        df["Target"] = self.space.target
        df.to_csv(total_path, index=False)

    def output_space_real_condition(self, dirname: str, filename: str) -> None:
        """Output real condition space as CSV file."""
        total_path = Path(dirname) / f"{filename}.csv"
        Path(dirname).mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(data=self._real_space.params, columns=self._real_space.keys)
        df["Target"] = self._real_space.target
        df.to_csv(total_path, index=False)

    def output_space_property(self, dirname: str, filename: str) -> None:
        """Output property space as CSV file."""
        total_path = Path(dirname) / f"{filename}.csv"
        Path(dirname).mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            data=self._property_space.params, columns=self._property_space.keys
        )
        df.to_csv(total_path, index=False)

    def _register(self, space: object, params: dict, target: int) -> None:
        """Register point to space."""
        space.register(params, target)

    def register_point(
        self,
        input_next_points: list,
        norm_input_next_points: list,
        property_list: list,
        input_result_list: list,
    ) -> None:
        """Register experiment points and results."""
        for idx, real_next_point in enumerate(input_next_points):
            optimal_value = input_result_list[idx]
            self._register(space=self._real_space, params=real_next_point, target=optimal_value)

        for idx, property_dict in enumerate(property_list):
            optimal_value = input_result_list[idx]
            self._property_space._keys = (
                list(input_next_points[idx].keys()) + list(property_dict.keys())
            )
            self._register(
                space=self._property_space,
                params=list(input_next_points[idx].values()) + list(property_dict.values()),
                target=optimal_value,
            )

        for idx, norm_next_point in enumerate(norm_input_next_points):
            optimal_value = input_result_list[idx]
            self._register(space=self.space, params=norm_next_point, target=optimal_value)

        if self.utility_type in TRANSFER_UTILITY_TYPES:
            underlabeling_data = self.underlabeling_fm.load_data()
            finetuned_data = self.finetuned_fm.load_data()
            move_count = min(len(underlabeling_data), len(input_result_list))

            for idx in range(move_count):
                underlabeling_data[idx]["label"] = int(input_result_list[idx])
                finetuned_data.append(underlabeling_data[idx])

            if move_count > 0:
                underlabeling_data = underlabeling_data[move_count:]
                self.finetuned_fm.save_data(finetuned_data)
                self.underlabeling_fm.save_data(underlabeling_data)

    def recovery(self) -> None:
        """Recover data by moving labeled data back to unlabeled."""
        labeled_data = self.labeled_fm.load_data()
        unlabeled_data = self.unlabeled_fm.load_data()

        while len(labeled_data) > 20:
            unlabeled_data.append(labeled_data.pop(20))

        for item in unlabeled_data:
            item["label"] = None

        self.labeled_fm.save_data(labeled_data)
        self.unlabeled_fm.save_data(unlabeled_data)


if __name__ == "__main__":
    with open("USER/NY/job_script/Free/test_RS.json") as f:
        testdict = json.load(f)

    RS = ReactionSpace(testdict)

    for i in tqdm(range(20, 21)):
        RS.suggest_next_step()
