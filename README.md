<div align="center">

<img src="docs/source/_static/images/flash_logo.png" width="400px">


**Collection of tasks for fast prototyping, finetuning, and solving applied deep learning problems**

---

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#what-is-flash">About</a> •
  <a href="#predictions">Prediction</a> •
  <a href="#finetuning">Finetuning</a> •
  <a href="#tasks">Tasks</a> •
  <a href="#contribute">Contribute</a> •
  <a href="https://www.pytorchlightning.ai/">Website</a> •
  <a href="#license">License</a>
</p>

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/lightning-flash)](https://pypi.org/project/lightning-flash/)
[![PyPI Status](https://badge.fury.io/py/lightning-flash.svg)](https://badge.fury.io/py/lightning-flash)
[![PyPI Status](https://pepy.tech/badge/lightning-flash)](https://pepy.tech/project/lightning-flash)
[![Slack](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://join.slack.com/t/pytorch-lightning/shared_invite/zt-f6bl2l0l-JYMK3tbAgAmGRrlNr00f1A)
[![Discourse status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fforums.pytorchlightning.ai)](https://forums.pytorchlightning.ai/)
[![license](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/PytorchLightning/pytorch-lightning/blob/master/LICENSE)

</div>

## Installation

Pip / conda

```bash
pip install lightning-flash
```

Master
```bash
pip install git+https://github.com/PytorchLightning/lightning-flash.git@master --upgrade
```

Source

``` bash
git clone https://github.com/PyTorchLightning/lightning-flash.git
cd lightning-flash
pip install -e .
```

## What is Flash
Flash is a framework for applied deep learning focused on:

- Finetuning
- Predictions
- Task-based training

It is built for data scientists, machine learning practicioners, and applied researchers.

### Predictions

```python
# import our libraries
from flash.text import TextClassifier

# 1. Load finetuned task
model = TextClassifier.load_from_checkpoint("https://flash-weights.s3.amazonaws.com/text_classification_model.pt")

# 2. Perform inference from list of sequences
predictions = model.predict([
    "Turgid dialogue, feeble characterization - Harvey Keitel a judge?.",
    "The worst movie in the history of cinema.",
    "I come from Bulgaria where it 's almost impossible to have a tornado."
    "Very, very afraid"
    "This guy has done a great job with this movie!",
])
print(predictions)
```

### Finetuning

```python
import flash
from flash.core.data import download_data
from flash.vision import ImageClassificationData, ImageClassifier


# 1. Download the data
download_data("https://pl-flash-data.s3.amazonaws.com/hymenoptera_data.zip", 'data/')

# 2. Load the data
datamodule = ImageClassificationData.from_folders(
    backbone="resnet18",
    train_folder="data/hymenoptera_data/train/",
    valid_folder="data/hymenoptera_data/val/",
    test_folder="data/hymenoptera_data/test/",
)

# 3. Build the model
model = ImageClassifier(num_classes=datamodule.num_classes)

# 4. Create the trainer. Run once on data
trainer = flash.Trainer(max_epochs=1)

# 5. Finetune the model
trainer.finetune(model, datamodule=datamodule, unfreeze_milestones=(0, 1))

# 6. Use the model
predictions = model.predict('data/hymenoptera_data/val/bees/65038344_52a45d090d.jpg")
print(predictions)

# 7. Save it!
trainer.save_checkpoint("image_classification_model.pt")
```

### Task-based training

Tasks let you focus on solving applied problems without any of the boilerplate. Here's a built-in
task that works for 99% of machine learning problems that data scientists, kagglers and practicioners
encounter.

```python
import flash
from torch import nn, optim
from torch.utils.data import DataLoader, random_split
from torchvision import transforms, datasets
import pytorch_lightning as pl

# model
model = nn.Sequential(
    nn.Flatten(),
    nn.Linear(28 * 28, 128),
    nn.ReLU(),
    nn.Linear(128, 10)
)

# data
dataset = datasets.MNIST('./data_folder', download=True, transform=transforms.ToTensor())
train, val = random_split(dataset, [55000, 5000])

# task
classifier = flash.Task(model, loss_fn=nn.functional.cross_entropy, optimizer=optim.Adam)

# train
flash.Trainer().fit(classifier, DataLoader(train), DataLoader(val))
```

### Infinitely customizable

Tasks can be built in just a few minutes because Flash is built on top of PyTorch Lightning LightningModules, which
are infinitely extensible and let you train across GPUs, TPUs etc without doing any code changes.

```python
import torch
import torch.nn.functional as F
from flash.core.classification import ClassificationTask
from pytorch_lightning import Trainer
​
class LinearClassifier(ClassificationTask):
    def __init__(
        self,
        num_inputs,
        num_classes,
        loss_fn: Callable = F.cross_entropy,
        optimizer: Type[torch.optim.Optimizer] = torch.optim.SGD,
        metrics: Union[Callable, Mapping, Sequence, None] = [Accuracy()],
        learning_rate: float = 1e-3,
    ):
        super().__init__(
            model=None,
            loss_fn=loss_fn,
            optimizer=optimizer,
            metrics=metrics,
            learning_rate=learning_rate,
        )
        self.save_hyperparameters()

        self.linear = torch.nn.Linear(num_inputs, num_classes)

    def forward(self, x):
        return self.linear(x)

classifier = LinearClassifier()
...

```

## Tasks
Flash comes prebuilt with off-the-shelf tasks for common deep learning problems (and many more are being built by the community!).
Here are examples for image, text and tabular.

### Image classification

Flash has an ImageClassification task to tackle any image classification problem. To illustrate, Let's say we wanted to develop a model that could classify between ants and bees.

<img src="https://pl-flash-data.s3.amazonaws.com/images/ant_bee.png" width="300px">
Here we classify ants vs bees.

```python
import flash
from flash.core.data import download_data
from flash.vision import ImageClassificationData, ImageClassifier

# 1. Download the data
download_data("https://pl-flash-data.s3.amazonaws.com/hymenoptera_data.zip", 'data/')

# 2. Load the data
datamodule = ImageClassificationData.from_folders(
    train_folder="data/hymenoptera_data/train/",
    valid_folder="data/hymenoptera_data/val/",
    test_folder="data/hymenoptera_data/test/",
)

# 3. Build the model
model = ImageClassifier(num_classes=datamodule.num_classes)

# 4. Create the trainer. Run once on data
trainer = flash.Trainer(max_epochs=1)

# 5. Train the model
trainer.finetune(model, datamodule=datamodule, unfreeze_milestones=(0, 1))

# 6. Test the model
trainer.test()

# 7. Predict!
predictions = model.predict([
    "data/hymenoptera_data/val/bees/65038344_52a45d090d.jpg",
    "data/hymenoptera_data/val/bees/590318879_68cf112861.jpg",
    "data/hymenoptera_data/val/ants/540543309_ddbb193ee5.jpg",
])
print(predictions)
```
To run the example:
```
python flash_examples/finetuning/image_classifier.py
```
### Text classification

Flash has a TextClassification task to tackle any text classification problem. To illustrate, say you wanted to classify movie reviews as positive or negative. From a train.csv and valid.csv, structured like so:


```python
import flash
from flash.core.data import download_data
from flash.text import TextClassificationData, TextClassifier

# 1. Download the data
download_data("https://pl-flash-data.s3.amazonaws.com/imdb.zip", 'data/')

# 2. Load the data
datamodule = TextClassificationData.from_files(
    train_file="data/imdb/train.csv",
    valid_file="data/imdb/valid.csv",
    test_file="data/imdb/test.csv",
    input="review",
    target="sentiment",
    batch_size=512
)

# 3. Build the model
model = TextClassifier(num_classes=datamodule.num_classes)

# 4. Create the trainer. Run once on data
trainer = flash.Trainer(max_epochs=1)

# 5. Fine-tune the model
trainer.finetune(model, datamodule=datamodule, unfreeze_milestones=(0, 1))

# 6. Test model
trainer.test()

# 7. Classify a few sentences! How was the movie?
predictions = model.predict([
    "Turgid dialogue, feeble characterization - Harvey Keitel a judge?.",
    "The worst movie in the history of cinema.",
    "I come from Bulgaria where it 's almost impossible to have a tornado."
    "Very, very afraid"
    "This guy has done a great job with this movie!",
])
print(predictions)
```
To run the example:
```bash
python flash_examples/finetuning/classify_text.py
```

### Tabular classification

Flash has a TabularClassification task to tackle any tabular classification problem. To illustrate, say we want to build a model to predict if a passenger survived on the Titanic. 

```python
from pytorch_lightning.metrics.classification import Accuracy, Precision, Recall
import flash
from flash.core.data import download_data
from flash.tabular import TabularClassifier, TabularData

# 1. Download the data
download_data("https://pl-flash-data.s3.amazonaws.com/titanic.zip", 'data/')

# 2. Load the data
datamodule = TabularData.from_csv(
    "./data/titanic/titanic.csv",
    test_csv="./data/titanic/test.csv",
    categorical_input=["Sex", "Age", "SibSp", "Parch", "Ticket", "Cabin", "Embarked"],
    numerical_input=["Fare"],
    target="Survived",
    val_size=0.25,
)

# 3. Build the model
model = TabularClassifier.from_data(datamodule, metrics=[Accuracy(), Precision(), Recall()])

# 4. Create the trainer. Run 10 times on data
trainer = flash.Trainer(max_epochs=10)

# 5. Train the model
trainer.fit(model, datamodule=datamodule)

# 6. Test model
trainer.test()

# 7. Predict!
predictions = model.predict("data/titanic/titanic.csv")
print(predictions)
```
To run the example:
```
python flash_examples/finetuning/tabular_data.py
```

---

## Contribute!
The lightning + Flash team is hard at work building more tasks for common deep-learning use cases. But we're looking for incredible contributors like you to submit new tasks!

Join our [Slack](https://join.slack.com/t/pytorch-lightning/shared_invite/zt-f6bl2l0l-JYMK3tbAgAmGRrlNr00f1A) to get help becoming a contributor!

---

## License

Please observe the Apache 2.0 license that is listed in this repository. In addition
the Lightning framework is Patent Pending.

