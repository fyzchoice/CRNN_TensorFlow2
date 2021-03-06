import tensorflow as tf
from core.read_dataset import Dataset
from core.make_label import Label
from core.crnn import CRNN
from core.loss import CTCLoss
from core.metric import Accuracy
from core.predict import predict_text
from core.utils import get_num_classes_and_blank_index
from configuration import Config


if __name__ == '__main__':
    # GPU settings
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)

    # dataset
    dataset = Dataset()
    num_classes, blank_index = get_num_classes_and_blank_index()
    train_set, train_size = dataset.train_dataset()
    valid_set, valid_size = dataset.valid_dataset()

    # model
    crnn_model = CRNN(num_classes)

    # loss
    loss = CTCLoss()

    # optimizer
    optimizer = tf.optimizers.Adadelta()

    # metrics
    train_loss_metric = tf.metrics.Mean()
    valid_loss_metric = tf.metrics.Mean()
    accuracy = Accuracy(blank_index)
    train_accuracy = tf.metrics.Mean()
    valid_accuracy = tf.metrics.Mean()

    def train_step(batch_images, batch_labels):
        with tf.GradientTape() as tape:
            pred = crnn_model(batch_images, training=True)
            loss_value = loss(y_true=batch_labels, y_pred=pred)
        gradients = tape.gradient(target=loss_value, sources=crnn_model.trainable_variables)
        optimizer.apply_gradients(grads_and_vars=zip(gradients, crnn_model.trainable_variables))
        train_loss_metric.update_state(values=loss_value)
        train_acc = accuracy(decoded_text=predict_text(pred, blank_index), true_label=batch_labels)
        train_accuracy.update_state(values=train_acc)

    def valid_step(batch_images, batch_labels):
        pred = crnn_model(batch_images, training=False)
        loss_value = loss(y_true=batch_labels, y_pred=pred)
        valid_acc = accuracy(decoded_text=predict_text(pred, blank_index=blank_index), true_label=batch_labels)
        valid_loss_metric.update_state(values=loss_value)
        valid_accuracy.update_state(values=valid_acc)


    for epoch in range(Config.EPOCHS):
        for step, train_data in enumerate(train_set):
            batch_images, batch_labels = Label().make_label(batch_data=train_data)
            train_step(batch_images, batch_labels)
            print("Epoch: {}/{}, step: {}/{}, loss: {}, train accuracy: {}".format(epoch,
                                                                                   Config.EPOCHS,
                                                                                   step,
                                                                                   tf.math.ceil(train_size / Config.BATCH_SIZE),
                                                                                   train_loss_metric.result(),
                                                                                   train_accuracy.result()))

        for valid_data in valid_set:
            batch_images, batch_labels = Label().make_label(batch_data=valid_data)
            valid_step(batch_images, batch_labels)
        print("Epoch: {}/{}, valid_loss: {}, valid_accuracy: {}".format(epoch,
                                                                        Config.EPOCHS,
                                                                        valid_loss_metric.result(),
                                                                        valid_accuracy.result()))

        train_loss_metric.reset_states()
        valid_loss_metric.reset_states()

        train_accuracy.reset_states()
        valid_accuracy.reset_states()

        if epoch % Config.save_frequency == 0:
            crnn_model.save_weights(filepath=Config.save_model_dir+"epoch-{}".format(epoch), save_format="tf")

    crnn_model.save_weights(filepath=Config.save_model_dir+"saved_model", save_format="tf")
