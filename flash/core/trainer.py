# Copyright The PyTorch Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import warnings
from argparse import ArgumentParser
from functools import wraps
from typing import Callable, List, Optional, Union

import torch
from pytorch_lightning import LightningDataModule, LightningModule
from pytorch_lightning import Trainer as PlTrainer
from pytorch_lightning.callbacks import BaseFinetuning
from pytorch_lightning.utilities import rank_zero_warn
from pytorch_lightning.utilities.argparse import add_argparse_args, get_init_arguments_and_types, parse_env_variables
from pytorch_lightning.utilities.exceptions import MisconfigurationException
from torch.utils.data import DataLoader

import flash
from flash.core.finetuning import _DEFAULTS_FINETUNE_STRATEGIES, instantiate_default_finetuning_callbacks


def _defaults_from_env_vars(fn: Callable) -> Callable:
    """Copy of ``pytorch_lightning.trainer.connectors.env_vars_connector._defaults_from_env_vars``. Required to fix
    build error in readthedocs."""

    @wraps(fn)
    def insert_env_defaults(self, *args, **kwargs):
        cls = self.__class__  # get the class
        if args:  # inace any args passed move them to kwargs
            # parse only the argument names
            cls_arg_names = [arg[0] for arg in get_init_arguments_and_types(cls)]
            # convert args to kwargs
            kwargs.update({k: v for k, v in zip(cls_arg_names, args)})
        env_variables = vars(parse_env_variables(cls))
        # update the kwargs by env variables
        kwargs = dict(list(env_variables.items()) + list(kwargs.items()))

        # all args were already moved to kwargs
        return fn(self, **kwargs)

    return insert_env_defaults


class Trainer(PlTrainer):

    @_defaults_from_env_vars
    def __init__(self, *args, **kwargs):
        if flash._IS_TESTING:
            if torch.cuda.is_available():
                kwargs["gpus"] = 1
                kwargs["max_epochs"] = 3
                kwargs["limit_train_batches"] = 1.0
                kwargs["limit_val_batches"] = 1.0
                kwargs["limit_test_batches"] = 1.0
                kwargs["fast_dev_run"] = False
            else:
                kwargs["fast_dev_run"] = True
        super().__init__(*args, **kwargs)

    def fit(
        self,
        model: LightningModule,
        train_dataloader: Optional[DataLoader] = None,
        val_dataloaders: Optional[Union[DataLoader, List[DataLoader]]] = None,
        datamodule: Optional[LightningDataModule] = None,
    ):
        r"""
        Runs the full optimization routine. Same as :meth:`pytorch_lightning.Trainer.fit`

        Args:
            datamodule: A instance of :class:`LightningDataModule`.

            model: Model to fit.

            train_dataloader: A Pytorch DataLoader with training samples. If the model has
                a predefined train_dataloader method this will be skipped.

            val_dataloaders: Either a single Pytorch Dataloader or a list of them, specifying validation samples.
                If the model has a predefined val_dataloaders method this will be skipped
        """
        if any(isinstance(c, BaseFinetuning) for c in self.callbacks):
            # TODO: if we find a finetuning callback in the trainer should we remove it? or just warn the user?
            warnings.warn("Warning: You are calling fit(), but your trainer is using a fine-tuning callback")
        return super().fit(model, train_dataloader, val_dataloaders, datamodule)

    def finetune(
        self,
        model: LightningModule,
        train_dataloader: Optional[DataLoader] = None,
        val_dataloaders: Optional[Union[DataLoader, List[DataLoader]]] = None,
        datamodule: Optional[LightningDataModule] = None,
        strategy: Optional[Union[str, BaseFinetuning]] = None,
    ):
        r"""

        Runs the full optimization routine. Same as :meth:`pytorch_lightning.Trainer.fit`, but unfreezes layers
        of the backbone throughout training layers of the backbone throughout training.

        Args:
            datamodule: A instance of :class:`LightningDataModule`.

            model: Model to fit.

            train_dataloader: A PyTorch DataLoader with training samples. If the model has
                a predefined train_dataloader method this will be skipped.

            val_dataloaders: Either a single PyTorch Dataloader or a list of them, specifying validation samples.
                If the model has a predefined val_dataloaders method this will be skipped

            strategy: Should either be a string or a finetuning callback subclassing
                :class:`pytorch_lightning.callbacks.BaseFinetuning`.

                Default strategies can be enabled with these strings:

                - ``"no_freeze"``,
                - ``"freeze"``,
                - ``"freeze_unfreeze"``,
                - ``"unfreeze_milestones"``.
        """
        self._resolve_callbacks(model, strategy)
        return super().fit(model, train_dataloader, val_dataloaders, datamodule)

    def _resolve_callbacks(self, model, strategy):
        """
        This function is used to select the `BaseFinetuning` to be used for finetuning.
        """
        if strategy is not None and not isinstance(strategy, (str, BaseFinetuning)):
            raise MisconfigurationException(
                "strategy should be a ``pytorch_lightning.callbacks.BaseFinetuning``"
                f"callback or a str within {list(_DEFAULTS_FINETUNE_STRATEGIES.keys())}"
            )

        if isinstance(strategy, BaseFinetuning):
            callback = [strategy]
        else:
            # todo: change to ``configure_callbacks`` when merged to Lightning.
            model_callback = model.configure_finetune_callback()
            if len(model_callback) > 1:
                raise MisconfigurationException(
                    f"{model} configure_finetune_callback should create a list with only 1 callback"
                )
            if len(model_callback) == 1:
                if strategy is not None:
                    rank_zero_warn(
                        "The model contains a default finetune callback. The provided {strategy} will be overriden.\n"
                        " HINT: Provide a `BaseFinetuning` callback as strategy to make it prioritized. ", UserWarning
                    )
                callback = model_callback
            else:
                callback = instantiate_default_finetuning_callbacks(strategy)

        self.callbacks = self._merge_callbacks(self.callbacks, callback)

    @staticmethod
    def _merge_callbacks(old_callbacks: List, new_callbacks: List) -> List:
        """
        This function keeps only 1 instance of each callback type,
        extending new_callbacks with old_callbacks
        """
        if len(new_callbacks) == 0:
            return old_callbacks
        new_callbacks_types = set(type(c) for c in new_callbacks)
        old_callbacks_types = set(type(c) for c in old_callbacks)
        override_types = new_callbacks_types.intersection(old_callbacks_types)
        new_callbacks.extend(c for c in old_callbacks if type(c) not in override_types)
        return new_callbacks

    @classmethod
    def add_argparse_args(cls, *args, **kwargs) -> ArgumentParser:
        # the lightning trainer implementation does not support subclasses.
        # context: https://github.com/PyTorchLightning/lightning-flash/issues/342#issuecomment-848892447
        return add_argparse_args(PlTrainer, *args, **kwargs)
