"""
Synthesizable Space Explorer

Active learning framework for exploring synthesizable spaces using various
surrogate models and acquisition strategies (confidence, variance, etc.).
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Algorithm.Bayesian.target_space import DiscreteSpace, PropertySpace, TargetSpace

from BaseModel.basemodel.ensemble_bo import EnsembleBO
from BaseModel.gpclassifier import GPC
from BaseModel.logistic import Logistic
from BaseModel.mlp import MLP
from BaseModel.tabm import TabMClassifier
from BaseModel.vgpclassifier import vGPC
from BaseModel.vime import VIME
from BaseModel.widedeep import WideDeep
from BaseModel.wvgpclassifier import wvGPC
from BaseModel.xgboost import Xgboost
from FileManager import fileManager, modelManager
from VirtualAnnotation import Surface_Maker

MODEL_CLASSES = {
    "GPC": GPC,
    "vGPC": vGPC,
    "wvGPC": wvGPC,
    "logit": Logistic,
    "mlp": MLP,
    "VIME": VIME,
    "xgboost": Xgboost,
    "EnsembleBO": EnsembleBO,
    "TabM": TabMClassifier,
    "WideDeep": WideDeep,
}


class SynthesizableSpace:
    """Synthesizable space exploration with active learning."""

    def __init__(self, configfile: dict) -> None:
        self.configfile = configfile

        self.seed_num = configfile["algorithm"]["randomState"]
        self.sampling_option = configfile["algorithm"]["sampling_method"]
        self.initial_sampling = configfile["algorithm"]["samplingSize"]
        self.additional_sampling = configfile["algorithm"]["additionalSamplingSize"]
        self.utility_type = configfile["algorithm"]["utilityType"]
        self.batch_size = configfile["metadata"]["batchSize"]
        self.time_limit = configfile["algorithm"]["searchTime"]
        self.iter_num = configfile["metadata"]["todayIterNum"]
        self.threshold = configfile["algorithm"]["classThreshold"]
        self.surrogate = configfile["algorithm"]["surrogateModel"]

        base_path = Path(configfile["metadata"]["saveDirPath"])
        self.unlabeled_data_path = base_path / "unlabeledSet.json"
        self.underlabeling_data_path = base_path / "underLabelingSet.json"
        self.labeled_data_path = base_path / "labeledSet.json"
        self.valid_data_path = base_path / "validSet.json"
        self.eval_data_path = base_path / "evalSet.json"
        self.score_path = base_path / "score.json"
        self.true_path = base_path / "true.json"
        self.predicted_path = base_path / "predicted.json"
        self.proba_path = base_path / "probability.json"
        self.model_path = configfile["algorithm"]["ModelPath"]

        self.unlabeled_fm = fileManager(str(self.unlabeled_data_path))
        self.underlabeling_fm = fileManager(str(self.underlabeling_data_path))
        self.labeled_fm = fileManager(str(self.labeled_data_path))
        self.valid_fm = fileManager(str(self.valid_data_path))
        self.eval_fm = fileManager(str(self.eval_data_path))
        self.score_fm = fileManager(str(self.score_path))
        self.model_fm = modelManager(self.model_path)
        self.true_fm = fileManager(str(self.true_path))
        self.predicted_fm = fileManager(str(self.predicted_path))
        self.proba_fm = fileManager(str(self.proba_path))

        self.prange = configfile["algorithm"]["prangeDict"]
        self.target_condition_dict = configfile["algorithm"]["targetConditionDict"]

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

        self.valid_surface = Surface_Maker(configfile["algorithm"]["searchface"])
        self.eval_surface = Surface_Maker(configfile["algorithm"]["searchface"])
        self.underlabeling_surface = Surface_Maker(configfile["algorithm"]["searchface"])
        self.cross_option = None

    @staticmethod
    def _calc_euclidean(list1: list, list2: list) -> float:
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(list1, list2)))

    @staticmethod
    def _check_one_label(data: list[dict]) -> bool:
        label_set = {i["label"] for i in data}
        return 1 in label_set and 0 in label_set

    def _random_sampling(self) -> None:
        unlabeled_data = self.unlabeled_fm.load_data()
        under_labeling_data = self.underlabeling_fm.load_data()

        under_labeling_data.append(
            unlabeled_data.pop(random.randint(0, len(unlabeled_data) - 1))
        )

        for item in under_labeling_data:
            item["cycle"] = -1
            item["strategy"] = "R"

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(under_labeling_data)

    def _real_to_norm(self, data: list[dict]) -> list[list]:
        data_value = [i["coordination"] for i in data]
        prange_dict = self.configfile["algorithm"]["prangeDict"]

        for i, item in enumerate(data):
            for j, key in enumerate(prange_dict):
                prange = prange_dict[key]
                data_value[i][j] = (data_value[i][j] - prange[0]) / (prange[1] - prange[0])
        return data_value

    def get_data_size(self) -> int:
        return len(self.labeled_fm.load_data())

    def initial_random_labeling(self) -> None:
        """Suggest initial random points for model training."""
        unlabeled_data = self.unlabeled_fm.load_data()
        under_labeling_data = self.underlabeling_fm.load_data()

        for item in under_labeling_data:
            item["cycle"] = -1
            item["strategy"] = "R"

        for _ in range(self.initial_sampling):
            under_labeling_data.append(
                unlabeled_data.pop(random.randint(0, len(unlabeled_data) - 1))
            )

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(under_labeling_data)

    def initial_latin_sampling(self) -> None:
        """Suggest initial points using Latin hypercube sampling."""
        unlabeled_data = self.unlabeled_fm.load_data()
        under_labeling_data = self.underlabeling_fm.load_data()

        sample = self._space.latin_sample(n_samples=self.initial_sampling).tolist()

        for _ in range(self.initial_sampling):
            distance_matrix = np.array([
                [self._calc_euclidean(u["coordination"], s) for s in sample]
                for u in unlabeled_data
            ])
            min_idx = np.argmin(distance_matrix)
            un, sam = np.unravel_index(min_idx, distance_matrix.shape)
            under_labeling_data.append(unlabeled_data.pop(un))
            sample = np.delete(sample, sam, axis=0).tolist()

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(under_labeling_data)

    def additional_random_labeling(self) -> None:
        """Suggest additional random points for model training."""
        unlabeled_data = self.unlabeled_fm.load_data()
        under_labeling_data = self.underlabeling_fm.load_data()

        for _ in tqdm(range(self.additional_sampling), desc="Extracting"):
            under_labeling_data.append(
                unlabeled_data.pop(random.randint(0, len(unlabeled_data) - 1))
            )

        for item in under_labeling_data:
            item["cycle"] = -1
            item["strategy"] = "AR"

        self.unlabeled_fm.save_data(unlabeled_data)
        self.underlabeling_fm.save_data(under_labeling_data)

    def train_model(self, model_name: str) -> tuple:
        """Train a surrogate model and return accuracy."""
        labeled_data = self.labeled_fm.load_data()
        valid_data = self.valid_fm.load_data()

        if not self._check_one_label(labeled_data):
            raise ValueError("Need both positive and negative labels")

        model_class = MODEL_CLASSES.get(model_name)
        if not model_class:
            raise ValueError(f"Unknown model: {model_name}")

        model_obj = model_class(train=labeled_data, test=valid_data)
        model_obj.create_model()
        model_obj.fit()
        accuracy = model_obj.predict()

        return model_obj, accuracy

    def save_data(self, model_obj) -> None:
        """Save model predictions and accuracy scores."""
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

    def suggest_next_step(self, iter_num: int) -> tuple[list, list]:
        """
        Suggest next sampling points based on acquisition strategy.

        Args:
            iter_num: Current iteration number

        Returns:
            Tuple of (normalized points, real points)
        """
        if iter_num < self.initial_sampling:
            self._random_sampling()
        else:
            unlabeled_data = self.unlabeled_fm.load_data()
            under_labeling_data = self.underlabeling_fm.load_data()
            labeled_data = self.labeled_fm.load_data()
            x_unlabeled_set = [i["coordination"] for i in unlabeled_data]

            if self.utility_type not in ("confidence", "variance"):
                confidence_model, _ = self.train_model(model_name="GPC")
                variance_model, _ = self.train_model(model_name="vGPC")
            else:
                confidence_model, _ = self.train_model(model_name=self.surrogate)
                variance_model = None

            handler_map = {
                "fine-tuned": self._handle_fine_tuned,
                "confidence": self._handle_confidence,
                "variance": self._handle_variance,
                "dynamic": self._handle_dynamic,
                "dynamic_time": self._handle_dynamic_time,
                "dynamic_switch": self._handle_dynamic_switch,
                "active": self._handle_active,
                "cross": self._handle_cross,
            }

            handler = handler_map.get(self.utility_type)
            if handler:
                if self.utility_type in ("dynamic", "dynamic_time", "dynamic_switch", "active", "cross"):
                    handler(
                        confidence_model, variance_model, unlabeled_data,
                        under_labeling_data, labeled_data, x_unlabeled_set,
                        iter_num if "time" in self.utility_type or "switch" in self.utility_type else None
                    )
                else:
                    handler(
                        confidence_model, unlabeled_data, under_labeling_data,
                        labeled_data, x_unlabeled_set
                    )

            self.unlabeled_fm.save_data(unlabeled_data)
            self.underlabeling_fm.save_data(under_labeling_data)

        return self.robot_annotation_formater()

    def _handle_fine_tuned(
        self, model, unlabeled_data, under_labeling_data, labeled_data, x_unlabeled_set
    ) -> None:
        """Handle fine-tuned acquisition strategy."""
        self.save_data(model)
        proba = model.probability_model(x_unlabeled_set)

        least_confidence_scores = 1 - np.max(proba, axis=1)
        sorted_proba = np.sort(proba, axis=1)[:, ::-1]
        margin_scores = 1 - (sorted_proba[:, 0] - sorted_proba[:, 1])
        entropy_scores = -np.sum(proba * np.log(proba + 1e-10), axis=1)

        def normalize(x):
            x_min, x_max = x.min(), x.max()
            return np.zeros_like(x) if x_max - x_min == 0 else (x - x_min) / (x_max - x_min)

        scores = (
            0.3 * normalize(least_confidence_scores)
            + 0.3 * normalize(margin_scores)
            + 0.4 * normalize(entropy_scores)
        )

        for idx, candidate in enumerate(unlabeled_data):
            candidate["acquisition_score"] = float(scores[idx])
            candidate["cycle"] = len(labeled_data) + 1

        for _ in range(self.batch_size):
            max_idx = int(np.argmax(scores))
            under_labeling_data.append(unlabeled_data.pop(max_idx))
            scores = np.delete(scores, max_idx)

    def _handle_confidence(
        self, model, unlabeled_data, under_labeling_data, labeled_data, x_unlabeled_set
    ) -> None:
        """Handle confidence-based acquisition strategy."""
        self.save_data(model)
        proba = model.probability_model(x_unlabeled_set)
        check_confidence_list = []

        for idx, candidate in enumerate(unlabeled_data):
            conf = float(proba[idx])
            check_confidence_list.append(abs(conf - 0.5))
            candidate["confidence"] = {"not react": abs(conf - 1), "react": conf}
            candidate["cycle"] = len(labeled_data) + 1

        for _ in range(self.batch_size):
            min_idx = check_confidence_list.index(min(check_confidence_list))
            under_labeling_data.append(unlabeled_data.pop(min_idx))
            check_confidence_list.pop(min_idx)

    def _handle_variance(
        self, model, unlabeled_data, under_labeling_data, labeled_data, x_unlabeled_set
    ) -> None:
        """Handle variance-based acquisition strategy."""
        self.save_data(model)
        variance = model.variance_model(x_unlabeled_set)

        for _ in range(self.batch_size):
            max_idx = int(np.argmax(variance))
            unlabeled_data[max_idx]["logit"].append(float(variance[max_idx]))
            unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
            under_labeling_data.append(unlabeled_data.pop(max_idx))
            variance = np.delete(variance, max_idx)

    def _handle_dynamic(
        self, confidence_model, variance_model, unlabeled_data,
        under_labeling_data, labeled_data, x_unlabeled_set, *args
    ) -> None:
        """Handle dynamic (confidence + variance) acquisition strategy."""
        self.save_data(confidence_model)
        confidence = confidence_model.probability_model(x_unlabeled_set)
        variance = variance_model.variance_model(x_unlabeled_set)

        dynamic_score = 0.5 * variance / np.array([abs(x - 0.5) + 1e-10 for x in confidence])

        for _ in range(self.batch_size):
            max_idx = int(np.argmax(dynamic_score))
            unlabeled_data[max_idx]["logit"].append(float(dynamic_score[max_idx]))
            unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
            under_labeling_data.append(unlabeled_data.pop(max_idx))
            dynamic_score = np.delete(dynamic_score, max_idx)

    def _handle_dynamic_time(
        self, confidence_model, variance_model, unlabeled_data,
        under_labeling_data, labeled_data, x_unlabeled_set, iter_num
    ) -> None:
        """Handle time-decaying dynamic acquisition strategy."""
        self.save_data(confidence_model)
        alpha = 50 / iter_num
        confidence = confidence_model.probability_model(x_unlabeled_set)
        variance = variance_model.variance_model(x_unlabeled_set)

        dynamic_score = alpha * variance / np.array([abs(x - 0.5) + 1e-10 for x in confidence])

        for _ in range(self.batch_size):
            max_idx = int(np.argmax(dynamic_score))
            unlabeled_data[max_idx]["logit"].append(float(dynamic_score[max_idx]))
            unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
            under_labeling_data.append(unlabeled_data.pop(max_idx))
            dynamic_score = np.delete(dynamic_score, max_idx)

    def _handle_dynamic_switch(
        self, confidence_model, variance_model, unlabeled_data,
        under_labeling_data, labeled_data, x_unlabeled_set, iter_num
    ) -> None:
        """Handle switching acquisition strategy (variance then confidence)."""
        if iter_num < 30:
            self.save_data(variance_model)
            variance = variance_model.variance_model(x_unlabeled_set)
            for _ in range(self.batch_size):
                max_idx = int(np.argmax(variance))
                unlabeled_data[max_idx]["logit"].append(float(variance[max_idx]))
                unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
                under_labeling_data.append(unlabeled_data.pop(max_idx))
                variance = np.delete(variance, max_idx)
        else:
            self._handle_confidence(
                confidence_model, unlabeled_data, under_labeling_data,
                labeled_data, x_unlabeled_set
            )

    def _handle_active(
        self, confidence_model, variance_model, unlabeled_data,
        under_labeling_data, labeled_data, x_unlabeled_set, *args
    ) -> None:
        """Handle active learning acquisition strategy."""
        variance_model_score = variance_model.predict()
        confidence_model_score = confidence_model.predict()

        if variance_model_score > confidence_model_score:
            self.save_data(variance_model)
            variance = variance_model.probability_model(x_unlabeled_set)

            for _ in range(self.batch_size):
                max_idx = int(np.argmax(variance))
                unlabeled_data[max_idx]["logit"].append(float(variance[max_idx]))
                unlabeled_data[max_idx]["cycle"] = len(labeled_data) + 1
                under_labeling_data.append(unlabeled_data.pop(max_idx))
        else:
            self.save_data(confidence_model)
            confidence = confidence_model.probability_model(x_unlabeled_set)
            check_confidence_list = []

            for idx, candidate in enumerate(unlabeled_data):
                class_probs = confidence[idx]
                sorted_probs, sorted_indices = torch.sort(
                    torch.tensor(class_probs), descending=True
                )

                uncertainty = abs(sorted_probs[0].item() - sorted_probs[1].item())
                check_confidence_list.append(uncertainty)

                candidate["confidence"] = {
                    f"class_{i}": float(class_probs[i]) for i in range(len(class_probs))
                }
                candidate["uncertainty"] = uncertainty
                candidate["most_likely_class"] = int(sorted_indices[0].item())
                candidate["second_most_likely_class"] = int(sorted_indices[1].item())
                candidate["cycle"] = len(labeled_data) + 1

            for _ in range(self.batch_size):
                min_idx = check_confidence_list.index(min(check_confidence_list))
                under_labeling_data.append(unlabeled_data.pop(min_idx))
                check_confidence_list.pop(min_idx)

    def _handle_cross(
        self, confidence_model, variance_model, unlabeled_data,
        under_labeling_data, labeled_data, x_unlabeled_set, *args
    ) -> None:
        """Handle cross-validation based acquisition strategy."""
        variance_model_score = variance_model.predict()
        confidence_model_score = confidence_model.predict()

        if self.cross_option is None and variance_model_score < confidence_model_score:
            self.cross_option = True

        if self.cross_option:
            self.save_data(variance_model)
            confidence = variance_model.probability_model(x_unlabeled_set)
        else:
            self.save_data(confidence_model)
            confidence = confidence_model.probability_model(x_unlabeled_set)

        check_confidence_list = []
        for idx, candidate in enumerate(unlabeled_data):
            conf = float(confidence[idx])
            check_confidence_list.append(abs(conf - 0.5))
            candidate["confidence"] = {"not react": abs(conf - 1), "react": conf}
            candidate["cycle"] = len(labeled_data) + 1

        for _ in range(self.batch_size):
            min_idx = check_confidence_list.index(min(check_confidence_list))
            under_labeling_data.append(unlabeled_data.pop(min_idx))
            check_confidence_list.pop(min_idx)

    def evaluation(self) -> list[float]:
        """Evaluate model on test set across iterations."""
        eval_data = self.eval_fm.load_data()
        x_test_set = [i["coordination"] for i in eval_data]
        y_test_set = [i["label"] for i in eval_data]

        return [
            accuracy_score(y_test_set, self.model_fm.loadModel(n).predict(x_test_set))
            for n in tqdm(range(20, 300))
        ]

    def validation(self) -> list[float]:
        """Validate model on validation set across iterations."""
        valid_data = self.valid_fm.load_data()
        x_test_set = [i["coordination"] for i in valid_data]
        y_test_set = [i["label"] for i in valid_data]

        return [
            accuracy_score(y_test_set, self.model_fm.loadModel(n).predict(x_test_set))
            for n in tqdm(range(20, 300))
        ]

    def get_learning_curve(self) -> None:
        """Plot learning curves for validation and evaluation sets."""
        eval_score = self.evaluation()
        valid_score = self.validation()

        plt.style.use("seaborn-v0_8")
        plt.plot(valid_score, label="Validation scores mean")
        plt.plot(eval_score, label="Evaluation scores mean")
        plt.ylabel("Accuracy", fontsize=14)
        plt.xlabel("Training set size", fontsize=14)
        plt.title("Learning curves", fontsize=18, y=1.03)
        plt.legend()
        plt.ylim(-0.03, 1.03)
        plt.show()

    def robot_annotation_formater(self) -> tuple[list, list]:
        """Format data for robot annotation."""
        under_labeling_data = self.underlabeling_fm.load_data()
        underlabeling_value = [i["coordination"] for i in under_labeling_data]
        prange_dict = self.configfile["algorithm"]["prangeDict"]
        parameter = list(prange_dict.keys())

        real_recipe = [
            dict(zip(parameter, value)) for value in underlabeling_value
        ]

        norm_values = [
            [
                (value[j] - prange_dict[key][0]) / (prange_dict[key][1] - prange_dict[key][0])
                for j, key in enumerate(parameter)
            ]
            for value in underlabeling_value
        ]

        norm_recipe = [dict(zip(parameter, value)) for value in norm_values]

        return real_recipe, norm_recipe

    def _assign_label(self, result: float) -> int:
        """Assign label based on threshold."""
        if isinstance(self.threshold, list):
            if result < self.threshold[0]:
                return 2
            elif result < self.threshold[1]:
                return 1
            return 0
        return 1 if result < self.threshold else 0

    def virtual_annotation(self) -> None:
        """Perform virtual annotation using surface function."""
        under_labeling_data = self.underlabeling_fm.load_data()
        underlabeling_value = [i["coordination"] for i in under_labeling_data]

        surface_obj = self.valid_surface.setSurface()
        result_list = surface_obj.run(underlabeling_value)

        for i, item in enumerate(under_labeling_data):
            item["label"] = self._assign_label(result_list[i][0])

        labeled_data = self.labeled_fm.load_data()
        cycle = len(labeled_data)

        while under_labeling_data:
            labeled_data.append(under_labeling_data.pop())

        self.underlabeling_fm.save_data(under_labeling_data)
        self.labeled_fm.save_data(labeled_data)

        while cycle + 1 != len(self.labeled_fm.load_data()):
            time.sleep(1)

    def human_annotation(self) -> None:
        """Perform manual human annotation."""
        under_labeling_data = self.underlabeling_fm.load_data()

        for item in under_labeling_data:
            label = input(f"Label of experiment_{item['coordination']}: ")
            if label in ("0", "1"):
                item["label"] = int(label)
            else:
                label = input(f"Label of experiment_{item['coordination']}: ")
                if label in ("0", "1"):
                    item["label"] = int(label)

        labeled_data = self.labeled_fm.load_data()
        while under_labeling_data:
            labeled_data.append(under_labeling_data.pop())

        self.underlabeling_fm.save_data(under_labeling_data)
        self.labeled_fm.save_data(labeled_data)
        print("Termination(Annotation)")

    def human_annotation_virtual(self) -> None:
        """Perform virtual human annotation using surface function."""
        under_labeling_data = self.underlabeling_fm.load_data()
        under_labeling_data_value = [i["coordination"] for i in under_labeling_data]

        surface_obj = self.underlabeling_surface.setSurface()
        result_list = surface_obj.run(under_labeling_data_value)

        for i, item in enumerate(under_labeling_data):
            item["label"] = self._assign_label(result_list[i][0])

        labeled_data = self.labeled_fm.load_data()
        while under_labeling_data:
            labeled_data.append(under_labeling_data.pop())

        self.underlabeling_fm.save_data(under_labeling_data)
        self.labeled_fm.save_data(labeled_data)

    def valid_human_annotation_virtual(self) -> None:
        """Perform virtual annotation on validation set."""
        valid_data = self.valid_fm.load_data()
        valid_data_value = [i["coordination"] for i in valid_data]

        surface_obj = self.valid_surface.setSurface()
        result_list = surface_obj.run(valid_data_value)

        for i, item in enumerate(valid_data):
            item["label"] = self._assign_label(result_list[i][0])

        self.valid_fm.save_data(valid_data)

    def eval_human_annotation_virtual(self) -> None:
        """Perform virtual annotation on evaluation set."""
        eval_data = self.eval_fm.load_data()
        eval_data_value = [i["coordination"] for i in eval_data]

        surface_obj = self.eval_surface.setSurface()
        result_list = surface_obj.run(eval_data_value)

        for i, item in enumerate(eval_data):
            item["label"] = self._assign_label(result_list[i][0])

        self.eval_fm.save_data(eval_data)

    def valid_human_annotation(self) -> None:
        """Perform manual annotation on validation set."""
        valid_data = self.valid_fm.load_data()

        for item in valid_data:
            label = input(f"Label of experiment_{item['coordination']}: ")
            if label in ("0", "1"):
                item["label"] = int(label)
            else:
                label = input(f"Label of experiment_{item['coordination']}: ")
                if label in ("0", "1"):
                    item["label"] = int(label)

        self.valid_fm.save_data(valid_data)
        print("Termination(Annotation)")

    def eval_human_annotation(self) -> None:
        """Perform manual annotation on evaluation set."""
        eval_data = self.eval_fm.load_data()

        for item in eval_data:
            label = input(f"Label of experiment_{item['coordination']}: ")
            if label in ("0", "1"):
                item["label"] = int(label)
            else:
                label = input(f"Label of experiment_{item['coordination']}: ")
                if label in ("0", "1"):
                    item["label"] = int(label)

        self.eval_fm.save_data(eval_data)
        print("Termination(Annotation)")

    @property
    def space(self):
        return self._space

    @property
    def res(self) -> list[dict]:
        """Get results in BO format."""
        labeled_data = self.labeled_fm.load_data()
        parameter = list(self.configfile["algorithm"]["prangeDict"].keys())

        return [
            {**dict(zip(parameter, item["coordination"])), "label": item["label"]}
            for item in labeled_data
        ]

    def output_space(self, dirname: str, filename: str) -> None:
        """Output complete space as CSV file."""
        path = Path(dirname)
        path.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(data=self.space.params, columns=self.space.keys)
        df["Target"] = self.space.target
        df.to_csv(path / f"{filename}.csv", index=False)

    def output_space_real_condition(self, dirname: str, filename: str) -> None:
        """Output space with real conditions as CSV file."""
        path = Path(dirname)
        path.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(data=self._real_space.params, columns=self._real_space.keys)
        df["Target"] = self._real_space.target
        df.to_csv(path / f"{filename}.csv", index=False)

    def output_space_property(self, dirname: str, filename: str) -> None:
        """Output space with properties as CSV file."""
        path = Path(dirname)
        path.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            data=self._property_space.params, columns=self._property_space.keys
        )
        df.to_csv(path / f"{filename}.csv", index=False)

    def register_point(
        self,
        input_next_points: list[dict],
        norm_input_next_points: list[dict],
        property_list: list[dict],
        input_result_list: list,
    ) -> None:
        """Register observed points to the spaces."""
        for process_idx, real_next_point in enumerate(input_next_points):
            self._real_space.register(real_next_point, input_result_list[process_idx])

        for process_idx, property_dict in enumerate(property_list):
            self._property_space._keys = (
                list(input_next_points[process_idx].keys())
                + list(property_dict.keys())
            )
            self._property_space.register(
                list(input_next_points[process_idx].values())
                + list(property_dict.values()),
                input_result_list[process_idx],
            )

        for process_idx, norm_next_point in enumerate(norm_input_next_points):
            self.space.register(norm_next_point, input_result_list[process_idx])

    def recovery(self) -> None:
        """Recover labeled data back to unlabeled state."""
        labeled_data = self.labeled_fm.load_data()
        unlabeled_data = self.unlabeled_fm.load_data()

        while len(labeled_data) > 20:
            item = labeled_data.pop(20)
            item["label"] = None
            unlabeled_data.append(item)

        self.labeled_fm.save_data(labeled_data)
        self.unlabeled_fm.save_data(unlabeled_data)


if __name__ == "__main__":
    methods = ["Random", "RS", "Sampling"]
    s_method = methods[0]

    for surface in ("HyperEllipsoid", "Rosenbrock"):
        for sampling_method in ("random",):
            for model in ("TabPFN",):
                for initial_sampling_size in (20, 30):
                    for balance in (50,):
                        for _ in ("Random",):
                            for var in (2, 3):
                                dis = 1 if var == 2 else 5
                                for idx in range(10):
                                    config_path = (
                                        f"C:\\Users\\user\\Desktop\\RS\\config\\{s_method}\\"
                                        f"{surface}_{sampling_method}_var{var}_dis{dis}_{model}_"
                                        f"{initial_sampling_size}_{balance}({idx}).json"
                                    )
                                    with open(config_path, encoding="utf-8") as f:
                                        testdict = json.load(f)

                                    rs = SynthesizableSpace(testdict)
                                    rs.human_annotation_virtual()
                                    rs.valid_human_annotation_virtual()
                                    rs.eval_human_annotation_virtual()
                                    time.sleep(4)
                                    print(
                                        f"{surface}_{sampling_method}_var{var}_dis{dis}_"
                                        f"{model}_{initial_sampling_size}_{balance}({idx})"
                                    )
