from sklearn.base import BaseEstimator , TransformerMixin
from laserembeddings import Laser
from environment import MODE

#constants
from .local_constants import path_to_bpe_vocab,path_to_encoder,path_to_bpe_codes

if MODE == 'local':
    from .local_constants import path_to_bpe_vocab,path_to_encoder,path_to_bpe_codes
else:
    from .dev_constants import path_to_bpe_vocab,path_to_encoder,path_to_bpe_codes

class LaserVectorizer(TransformerMixin,BaseEstimator):
    def __init__(self):
        self.model = Laser(path_to_bpe_codes,path_to_bpe_vocab,path_to_encoder)
        print('Applying Laser Transform')

    def fit(self,X):
        return self

    def transform(self,X):
        x_laser = self.model.embed_sentences(X,lang='en')
        return x_laser

