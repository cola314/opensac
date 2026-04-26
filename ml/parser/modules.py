import dspy
from parser.signatures import ProgramExtractor


class ConcertProgramParser(dspy.Module):
    def __init__(self):
        self.extractor = dspy.ChainOfThought(ProgramExtractor)

    def forward(self, detail_text: str):
        return self.extractor(detail_text=detail_text)
