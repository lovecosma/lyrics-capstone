class FakeVariantBuilder:
    def __init__(self, variant_df=None):
        self._variant_df = variant_df
        self.lexicon_words = None

    def build(self, lexicon_df, _word_column, lexicon_words):
        self.lexicon_words = lexicon_words
        if self._variant_df is None:
            return lexicon_df.iloc[:0]
        return self._variant_df
