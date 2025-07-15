import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import os


def register_custom_layer(name):
    def decorator(cls):
        tf.keras.utils.get_custom_objects()[name] = cls
        return cls
    return decorator

@register_custom_layer('CTCLayer')
class CTCLayer(layers.Layer):
    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)  # Передаем все аргументы дальше
        self.loss_fn = self.ctc_batch_cost

    def get_config(self):
        config = super().get_config()
        return config

    def ctc_batch_cost(self, y_true, y_pred, input_length, label_length):
        label_length = tf.cast(tf.squeeze(label_length, axis=-1), dtype="int32")
        input_length = tf.cast(tf.squeeze(input_length, axis=-1), dtype="int32")
        sparse_labels = tf.cast(
            self.ctc_label_dense_to_sparse(y_true, label_length), dtype="int32"
        )

        y_pred = tf.math.log(tf.transpose(y_pred, perm=[1, 0, 2]) + keras.backend.epsilon())

        return tf.expand_dims(
            tf.compat.v1.nn.ctc_loss(
                inputs=y_pred, labels=sparse_labels, sequence_length=input_length
            ),
            1,
        )

    def ctc_label_dense_to_sparse(self, labels, label_lengths):
        label_shape = tf.shape(labels)
        num_batches_tns = tf.stack([label_shape[0]])
        max_num_labels_tns = tf.stack([label_shape[1]])

        def range_less_than(old_input, current_input):
            return tf.expand_dims(tf.range(tf.shape(old_input)[1]), 0) < tf.fill(
                max_num_labels_tns, current_input
            )

        init = tf.cast(tf.fill([1, label_shape[1]], 0), dtype="bool")
        dense_mask = tf.compat.v1.scan(
            range_less_than, label_lengths, initializer=init, parallel_iterations=1
        )
        dense_mask = dense_mask[:, 0, :]

        label_array = tf.reshape(
            tf.tile(tf.range(0, label_shape[1]), num_batches_tns), label_shape
        )
        label_ind = tf.compat.v1.boolean_mask(label_array, dense_mask)

        batch_array = tf.transpose(
            tf.reshape(
                tf.tile(tf.range(0, label_shape[0]), max_num_labels_tns),
                tf.reverse(label_shape, [0]),
            )
        )
        batch_ind = tf.compat.v1.boolean_mask(batch_array, dense_mask)
        indices = tf.transpose(
            tf.reshape(tf.concat([batch_ind, label_ind], axis=0), [2, -1])
        )

        vals_sparse = tf.compat.v1.gather_nd(labels, indices)

        return tf.SparseTensor(
            tf.cast(indices, dtype="int64"),
            vals_sparse,
            tf.cast(label_shape, dtype="int64"),
        )

    def call(self, y_true, y_pred):
        batch_len = tf.cast(tf.shape(y_true)[0], dtype="int64")
        input_length = tf.cast(tf.shape(y_pred)[1], dtype="int64")
        label_length = tf.cast(tf.shape(y_true)[1], dtype="int64")

        input_length = input_length * tf.ones(shape=(batch_len, 1), dtype="int64")
        label_length = label_length * tf.ones(shape=(batch_len, 1), dtype="int64")

        loss = self.loss_fn(y_true, y_pred, input_length, label_length)
        self.add_loss(loss)

        return y_pred


class CaptchaRecognizer:
    def __init__(self, model_path="captcha_ocr_model.keras", img_width=150, img_height=80):
        # Загрузка модели с кастомными объектами
        self.model = keras.models.load_model(
            model_path,
            custom_objects={'CTCLayer': CTCLayer}
        )

        # Создание prediction модели
        self.prediction_model = keras.models.Model(
            self.model.input[0],
            self.model.get_layer(name="dense2").output
        )

        self.img_width = img_width
        self.img_height = img_height
        self.max_length = 5  # Максимальная длина CAPTCHA (настройте под ваши данные)

        # Инициализация словарей символов
        self._initialize_characters()

    def _initialize_characters(self):
        """Инициализация преобразований символов"""
        # Замените на ваш реальный набор символов
        self.characters = sorted(list("0123456789"))
        self.char_to_num = layers.StringLookup(
            vocabulary=list(self.characters), mask_token=None
        )
        self.num_to_char = layers.StringLookup(
            vocabulary=self.char_to_num.get_vocabulary(),
            mask_token=None,
            invert=True
        )

    def preprocess_image(self, img_path):
        """Предобработка изображения"""
        img = tf.io.read_file(img_path)
        img = tf.io.decode_png(img, channels=1)
        img = tf.image.convert_image_dtype(img, tf.float32)
        img = tf.image.resize(img, [self.img_height, self.img_width])
        img = tf.transpose(img, perm=[1, 0, 2])
        return img

    def decode_predictions(self, pred):
        """Декодирование предсказаний"""
        input_len = np.ones(pred.shape[0]) * pred.shape[1]
        results = keras.backend.ctc_decode(
            pred,
            input_length=input_len,
            greedy=True
        )[0][0][:, :self.max_length]

        output_text = []
        for res in results:
            res = tf.strings.reduce_join(self.num_to_char(res)).numpy().decode("utf-8")
            output_text.append(res)
        return output_text

    def recognize_captcha(self, img_path, show_image=False):
        """Распознавание CAPTCHA"""
        img = self.preprocess_image(img_path)
        img_batch = tf.expand_dims(img, axis=0)
        preds = self.prediction_model.predict(img_batch)
        pred_text = self.decode_predictions(preds)[0]

        if show_image:
            import matplotlib.pyplot as plt
            plt.imshow(img[:, :, 0].numpy().T, cmap='gray')
            plt.title(f"Prediction: {pred_text}")
            plt.axis('off')
            plt.show()

        return pred_text


if __name__ == "__main__":
    # Пример использования
    recognizer = CaptchaRecognizer()

    test_image = "captcha_0001.jpg"

    if os.path.exists(test_image):
        result = recognizer.recognize_captcha(test_image, show_image=False)
        print(f"Распознанный текст: {result}")
    else:
        print(f"Файл {test_image} не найден!")