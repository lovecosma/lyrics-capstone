class LyricsAnalyzer:
    def __init__(self, track):
        self.track = track

    def analyze(self):
        lyric_metric_df = None
        lyric_ngram_df = None
        return lyric_metric_df, lyric_ngram_df