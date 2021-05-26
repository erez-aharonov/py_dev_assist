class A:

    def __init__(self):
        self._k = 2
        pass

    def _a(self, number):
        if number == 2:
            pass

    def _c(self):
        self._a(2)
        self.b()

    def b(self):
        pass

    def d(self):
        self.b()
        func = self._a
        func(5)

    B = 0
