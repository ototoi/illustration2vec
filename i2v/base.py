from abc import ABCMeta, abstractmethod
import json
import numpy as np


class Illustration2VecBase(object):

    __metaclass__ = ABCMeta

    def __init__(self, net, tags=None):
        self.net = net
        if tags is not None:
            self.tags = np.array(tags)
            self.index = {t: i for i, t in enumerate(tags)}
        else:
            self.tags = None

    @abstractmethod
    def _extract(self, inputs, layername):
        pass

    def _estimate(self, images):
        assert(self.tags is not None)
        imgs = [np.asarray(img, dtype=np.float32) for img in images]
        prob = self._extract(imgs, layername="prob")
        prob = prob.reshape(prob.shape[0], -1)
        return prob

    def estimate_specific_tags(self, images, tags):
        prob = self._estimate(images)
        return [{t: float(prob[i, self.index[t]]) for t in tags}
                for i in range(prob.shape[0])]

    def estimate_top_tags(self, images, n_tag=10):
        prob = self._estimate(images)
        general_prob = prob[:, :512]
        character_prob = prob[:, 512:1024]
        copyright_prob = prob[:, 1024:1536]
        rating_prob = prob[:, 1536:]
        general_arg = np.argsort(-general_prob, axis=1)[:, :n_tag]
        character_arg = np.argsort(-character_prob, axis=1)[:, :n_tag]
        copyright_arg = np.argsort(-copyright_prob, axis=1)[:, :n_tag]
        rating_arg = np.argsort(-rating_prob, axis=1)
        result = []
        for i in range(prob.shape[0]):
            result.append({
                "general": zip(
                    self.tags[general_arg[i]],
                    general_prob[i, general_arg[i]].tolist()),
                "character": zip(
                    self.tags[512 + character_arg[i]],
                    character_prob[i, character_arg[i]].tolist()),
                "copyright": zip(
                    self.tags[1024 + copyright_arg[i]],
                    copyright_prob[i, copyright_arg[i]].tolist()),
                "rating": zip(
                    self.tags[1536 + rating_arg[i]],
                    rating_prob[i, rating_arg[i]].tolist()),
            })
        return result

    def estimate_plausible_tags(self, images, threshold=0.25):
        preds = self.estimate_top_tags(images, n_tag=512)
        result = []
        for pred in preds:
            general = [(t, p) for t, p in pred["general"] if p > threshold]
            character = [
                (t, p) for t, p in pred["character"] if p > threshold]
            copyright = [
                (t, p) for t, p in pred["copyright"] if p > threshold]
            result.append({
                "general": general,
                "character": character,
                "copyright": copyright,
                "rating": pred["rating"],
            })
        return result

    def extract_feature(self, images):
        feature = self._extract(images, layername="encode1")
        return feature

    def extract_binary_feature(self, images):
        feature = self._extract(images, layername="encode1neuron")
        binary_feature = np.zeros_like(feature, dtype=np.uint8)
        binary_feature[feature > 0.5] = 1
        return np.packbits(feature, axis=1)