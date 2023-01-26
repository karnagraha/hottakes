import numpy as np
import pandas as pd
from datasets import load_dataset
import streamer.tweetdb as tweetdb
from transformers import AutoTokenizer
from transformers import DataCollatorWithPadding
from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer
import evaluate
import sys


# The following lines adjust the granularity of reporting.
pd.options.display.max_rows = 10
pd.options.display.float_format = "{:.1f}".format


def get_dataset(tag):
    # tweets in the TweetDB that have reactions are annotated.  For now we only have two annotations:
    # ❌ and ✅
    annotations = {
        "positive": "✅",
        "negative": "❌",
    }
    reaction_to_annotation = {v: k for k, v in annotations.items()}

    # get the annotated tweets from the database
    db = tweetdb.TweetDB()
    tweets = db.get_annotated(tag, annotations.values())

    # update the reaction field to be the annotation
    for tweet in tweets:
        tweet[3] = reaction_to_annotation[tweet[3]]

    # write out the changes
    with open("annotated_tweets.csv", "w") as f:
        for tweet in tweets:
            text = tweet[1]
            annotation = reaction_to_annotation[tweet[3]]
            # remove all \n and \t from the string
            text = text.replace("\t", " ")
            text = text.replace("\n", " ")
            f.write(f"{text}\t{annotation}\n")

    # load annotated_tweets.csv and split it into a test and train set
    df = pd.read_csv("annotated_tweets.csv", sep="\t")
    df.columns = ["text", "label"]
    # randomize the entries in
    np.random.seed(42)
    df = df.reindex(np.random.permutation(df.index))

    # convert the labels to 0 and 1
    df.loc[df["label"] == "positive", "label"] = 1
    df.loc[df["label"] == "negative", "label"] = 0
    df[: int(len(df) * 0.8)].to_csv("df_train.csv", index=False, sep="\t")
    df[int(len(df) * 0.8) :].to_csv("df_test.csv", index=False, sep="\t")

    id2label = {0: "negative", 1: "positive"}
    label2id = {"negative": 0, "positive": 1}

    dataset = load_dataset(
        "csv",
        data_files={"train": "df_train.csv", "test": "df_test.csv"},
        delimiter="\t",
    )

    return dataset, id2label, label2id


def tokenize_dataset(dataset):
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    def preprocess_function(examples):
        return tokenizer(examples["text"], truncation=True, padding=True)

    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    tokenized_data = dataset.map(preprocess_function, batched=True)
    return tokenizer, tokenized_data, data_collator


def load_model(id2label, label2id):
    model = AutoModelForSequenceClassification.from_pretrained(
        f"distilbert-base-uncased", num_labels=2, id2label=id2label, label2id=label2id
    )
    return model


def train(model, dataset, tag):
    tokenizer, tokenized_data, data_collator = tokenize_dataset(dataset)
    accuracy = evaluate.load("accuracy")

    @torch.no_grad()
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return accuracy.compute(predictions=predictions, references=labels)

    training_args = TrainingArguments(
        output_dir=f"tweet_classifier/{tag}/",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=20,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        push_to_hub=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_data["train"],
        eval_dataset=tokenized_data["test"],
        data_collator=data_collator,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()


def main(tag):
    dataset, id2label, label2id = get_dataset(tag)
    model = load_model(id2label, label2id)
    train(model, dataset, tag)
    model.save_pretrained(f"models/{tag}")


if __name__ == "__main__":
    # get tag from argv and pass to main
    try:
        tag = sys.argv[1]
    except:
        print(f"Usage: python train.py <tag>")
        sys.exit(1)

    sys.exit(main(tag))
