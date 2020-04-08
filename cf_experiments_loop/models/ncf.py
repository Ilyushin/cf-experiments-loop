import functools
import tensorflow as tf

mf_dim = 8


def mf_slice_fn(x):
    x = tf.squeeze(x, [1])
    return x[:, :mf_dim]


def mlp_slice_fn(x):
    x = tf.squeeze(x, [1])
    return x[:, mf_dim:]


def ncf_model(num_users, num_items, layers=[256, 256, 128, 64], reg_layers=[0, 0], rating_column='rating'):
    user_input = tf.keras.layers.Input(shape=(1,), dtype='int32', name='user_input')
    item_input = tf.keras.layers.Input(shape=(1,), dtype='int32', name='item_input')

    # Initializer for embedding layers
    embedding_initializer = 'glorot_uniform'

    embedding_user = tf.keras.layers.Embedding(
        input_dim=num_users,
        output_dim=layers[0] / 2,
        name='user_embedding',
        embeddings_initializer=embedding_initializer,
        embeddings_regularizer=tf.keras.regularizers.l2(),
        input_length=1
    )(user_input)
    embedding_item = tf.keras.layers.Embedding(
        input_dim=num_items,
        output_dim=layers[0] / 2,
        name='item_embedding',
        embeddings_initializer=embedding_initializer,
        embeddings_regularizer=tf.keras.regularizers.l2(),
        input_length=1
    )(item_input)

    # GMF part
    mf_user_latent = tf.keras.layers.Lambda(
        mf_slice_fn, name="embedding_user_mf"
    )(embedding_user)
    mf_item_latent = tf.keras.layers.Lambda(
        mf_slice_fn, name="embedding_item_mf"
    )(embedding_item)

    # MLP part
    mlp_user_latent = tf.keras.layers.Lambda(
        mlp_slice_fn, name="embedding_user_mlp"
    )(embedding_user)
    mlp_item_latent = tf.keras.layers.Lambda(
        mlp_slice_fn, name="embedding_item_mlp"
    )(embedding_item)

    # Element-wise multiply
    mf_vector = tf.keras.layers.multiply([mf_user_latent, mf_item_latent])

    # Concatenation of two latent features
    mlp_vector = tf.keras.layers.concatenate([mlp_user_latent, mlp_item_latent])

    num_layer = len(layers)  # Number of layers in the MLP
    for layer in range(1, num_layer):
        model_layer = tf.keras.layers.Dense(
            layers[layer],
            kernel_regularizer=tf.keras.regularizers.l2(),
            activation='relu')
        mlp_vector = model_layer(mlp_vector)

    # Concatenate GMF and MLP parts
    predict_vector = tf.keras.layers.concatenate([mf_vector, mlp_vector])

    # Final prediction layer
    logits = tf.keras.layers.Dense(
        1,
        activation=None,
        kernel_initializer='lecun_uniform',
        name=rating_column
    )(predict_vector)

    # Print model topology.
    model = tf.keras.models.Model([user_input, item_input], logits)

    return model