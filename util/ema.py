class Ema:
    ema: float
    ratio: float

    def __init__(self, n: int):
        self.ema = 1
        self.ratio = 2 / (n + 1)

    def update(self, x: bool):
        self.ema = self.ema * (1 - self.ratio) + x * self.ratio

    @property
    def value(self):
        return self.ema
