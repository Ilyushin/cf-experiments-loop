import os
import functools
import shutil
import urllib
import zipfile
import six
import pandas as pd
from sklearn.model_selection import train_test_split
import tensorflow as tf
from signal_transformation import helpers

GENRE_COLUMN = "genres"
ITEM_COLUMN = "item_id"  # movies
RATING_COLUMN = "rating"
TIMESTAMP_COLUMN = "timestamp"
TITLE_COLUMN = "titles"
USER_COLUMN = "user_id"

RATING_COLUMNS = [USER_COLUMN, ITEM_COLUMN, RATING_COLUMN, TIMESTAMP_COLUMN]
MOVIE_COLUMNS = [ITEM_COLUMN, TITLE_COLUMN, GENRE_COLUMN]


def prepare_data(
        dataset_type=None,
        clear=False,
        movielens_path=None,
        train_data_path=None,
        eval_data_path=None,
        test_data_path=None
):
    if clear:
        shutil.rmtree(movielens_path, ignore_errors=True)
        shutil.rmtree(train_data_path, ignore_errors=True)
        shutil.rmtree(eval_data_path, ignore_errors=True)
        shutil.rmtree(test_data_path, ignore_errors=True)

    helpers.create_dir(movielens_path)
    helpers.create_dir(train_data_path)
    helpers.create_dir(eval_data_path)
    helpers.create_dir(test_data_path)

    data_url = "http://files.grouplens.org/datasets/movielens/"
    raitings_file = "ratings.csv"
    movies_file = "movies.csv"
    url = "{}{}.zip".format(data_url, dataset_type)

    zip_path = os.path.join(movielens_path, "{}.zip".format(dataset_type))
    zip_path, _ = urllib.request.urlretrieve(url, zip_path)

    zipfile.ZipFile(zip_path, "r").extractall(movielens_path)

    os.remove(zip_path)

    working_dir = os.path.join(movielens_path, dataset_type)

    _transform_csv(
        input_path=os.path.join(working_dir, "ratings.dat"),
        output_path=os.path.join(working_dir, raitings_file),
        names=RATING_COLUMNS, skip_first=False, separator="::"
    )

    _transform_csv(
        input_path=os.path.join(working_dir, "movies.dat"),
        output_path=os.path.join(working_dir, movies_file),
        names=MOVIE_COLUMNS, skip_first=False, separator="::"
    )

    shutil.copyfile(os.path.join(working_dir, raitings_file), os.path.join(movielens_path, raitings_file))
    shutil.copyfile(os.path.join(working_dir, movies_file), os.path.join(movielens_path, movies_file))
    tf.io.gfile.rmtree(working_dir)

    dataset = pd.read_csv(os.path.join(movielens_path, raitings_file))
    users_number = len(dataset.user_id.unique())
    items_number = len(dataset.item_id.unique())

    train_data, test_data = train_test_split(dataset, test_size=0.2, random_state=42)

    return train_data, test_data, users_number, items_number


def _transform_csv(input_path, output_path, names, skip_first, separator=","):
    """Transform csv to a regularized format.

    Args:
      input_path: The path of the raw csv.
      output_path: The path of the cleaned csv.
      names: The csv column names.
      skip_first: Boolean of whether to skip the first line of the raw csv.
      separator: Character used to separate fields in the raw csv.
    """
    if six.PY2:
        names = [six.ensure_text(n, "utf-8") for n in names]

    with tf.io.gfile.GFile(output_path, "wb") as f_out, \
            tf.io.gfile.GFile(input_path, "rb") as f_in:

        # Write column names to the csv.
        f_out.write(",".join(names).encode("utf-8"))
        f_out.write(b"\n")
        for i, line in enumerate(f_in):
            if i == 0 and skip_first:
                continue  # ignore existing labels in the csv

            line = six.ensure_text(line, "utf-8", errors="ignore")
            fields = line.split(separator)
            if separator != ",":
                fields = ['"{}"'.format(field) if "," in field else field
                          for field in fields]
            f_out.write(",".join(fields).encode("utf-8"))