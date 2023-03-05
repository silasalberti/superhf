"""
This file implements the training of a reward model.

The PreferenceDataCollator, passed to the RewardModelTrainer, forms batches
by taking as input a list of tuples (winner_response, loser_response) and
returning a dict {"winner": winner_tokenized, "loser": loser_tokenized}.

RewardModelTrainer.compute_loss(model, inputs) accepts this dict as the
`inputs` argument.
"""


import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset
from transformers import (
    Trainer,
    TrainingArguments,
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModelForCausalLM,
    AutoModel
)
from preference_datasets import AnthropicHelpfulHarmless


class PreferenceLoss(nn.Module):
    """
    This loss function computes the negative-log likelihood (NLL) of correctly
    predicting the winning input sequence out of a winner-loser pair.

    The probability of predicting the winner is defined as:
        sigmoid(reward(winner) - reward(loser))

    `forward`:
        winner_scores: size (batchsize,) tensor
        loser_scores: size (batchsize,) tensor
        Return: mean NLL loss.
    """

    def forward(self, winner_scores: torch.Tensor, loser_scores):
        loss = -F.logsigmoid(winner_scores - loser_scores)
        return loss.mean()  


def compute_metrics(eval_prediction):
    """
    Computes decimal accuracy of predictions during model evaluation.
    """

    reward_scores = eval_prediction.prediction
    total = reward_scores.size[0]
    num_correct = ((reward_scores[:, 0] - reward_scores[:, 1]) > 0).sum()
    accuracy = num_correct / total
    return accuracy


class RewardModelTrainer(Trainer):
    """
    This Hugging Face trainer is used to fine-tune a pretrained language model
    on the task of outputting a reward score given a prompt-response dialogue,
    giving higher reward to dialogues that would be preferred by humans.
    """

    def compute_loss(self, model, inputs, return_outputs=False):
        """
        model : RewardModel for computing loss
        inputs :
            tokenized input batch with features ['winner', 'loser'].
        Returns
        -------
        loss: model's loss over inputs, computed by the PreferenceLoss class.
        reward_scores: size (batch, 2) tensor of reward scores,
            with winner_scores in first column and loser_scores in second.

        """
        batch_size = inputs['input_ids'].shape[0]

        scores = model(**inputs)


        chosen_scores = scores[:(batch_size//2)]
        rejected_scores = scores[(batch_size//2):]


        loss_fct = PreferenceLoss()
        loss = loss_fct(chosen_scores, rejected_scores)
        return loss


class RewardModel(nn.Module):
    """
    The reward model to be trained from a pretrained language model.
    """

    def __init__(self, model_name, frozen_prefixes=()):
        super().__init__()
        self.model = AutoModel.from_pretrained(
            model_name, num_labels=1
        )
        for name, param in self.model.base_model.named_parameters():
            if any(name.startswith(p) for p in frozen_prefixes):
                param.requires_grad = False
        self.v_head = nn.Linear(self.model.config.hidden_size, 1, bias=False)

    def forward(self, **inputs):
        return self.v_head(self.model(**inputs)[0].mean(dim=1))


class PreferenceDataCollator:
    """
    Forms a batch by using a list of dataset elements as input. These elements
    are of the same type as the elements of train_dataset and eval_dataset.
    """

    def __init__(self, tokenizer, padding=True, max_length=None):
        self.tokenizer = tokenizer
        self.padding = padding
        self.max_length = max_length

    def __call__(self, batch):

        responses = []
        for chosen_responess, rejected_responses in batch:
            responses.append(chosen_responess)
            responses.append(rejected_responses)

        outputs = self.tokenizer(
            responses,
            return_tensors='pt',
            padding=self.padding,
            max_length=self.max_length,
            truncation=True
        )

        return outputs


if __name__ == "__main__":

    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name, max_length=256)
    model = RewardModel(model_name)

    model_output_dir = "reward_model_HH"

    arguments = TrainingArguments(
        output_dir=model_output_dir,
        logging_steps=5,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        num_train_epochs=3,
        evaluation_strategy="steps",
        eval_steps=10,
        save_strategy="steps",
        save_steps=100,
        learning_rate=2e-5,
        weight_decay=0.01,
        load_best_model_at_end=True,
        do_eval=True,
        report_to="wandb",
        log_level="debug",
    )

    train_dataset = AnthropicHelpfulHarmless("train")
    eval_dataset = AnthropicHelpfulHarmless("test")

    trainer = RewardModelTrainer(
        model=model,
        args=arguments,
        data_collator=PreferenceDataCollator(tokenizer),
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
    )
    trainer.train()
