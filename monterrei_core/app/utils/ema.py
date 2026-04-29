"""EMA simple para suavizar valores."""

class EMA:
    def __init__(self, alpha: float = 0.15):
        self.alpha = alpha
        self.value: float = 0.0
        self.initialized = False

    def update(self, x: float) -> float:
        if not self.initialized:
            self.value = x
            self.initialized = True
        else:
            self.value = self.alpha * x + (1.0 - self.alpha) * self.value
        return self.value

    def reset(self):
        self.value = 0.0
        self.initialized = False
