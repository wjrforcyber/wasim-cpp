import asyncio

class Timer:
    def __init__(self, time, units='ns'):
        self.time = time
        self.units = units

    def to_seconds(self):
        unit_scale = {
            's': 1,
            'ms': 1e-3,
            'us': 1e-6,
            'ns': 1e-9,
            'ps': 1e-12,
        }
        return self.time * unit_scale.get(self.units, 1)

    def __await__(self):
        seconds = self.to_seconds()
        return asyncio.sleep(seconds).__await__()

class RisingEdge:
    def __init__(self, signal):
        self.signal = signal

    def __await__(self):
        fut = asyncio.get_event_loop().create_future()

        def cb(old, new):
            if old == 0 and new == 1:
                if not fut.done():
                    fut.set_result(None)

        self.signal.register_callback(cb)

        # 如果信号当前就是高电平，也先等一次上升沿
        return fut.__await__()

class FallingEdge:
    def __init__(self, signal):
        self.signal = signal

    def __await__(self):
        fut = asyncio.get_event_loop().create_future()

        def cb(old, new):
            if old == 1 and new == 0:
                if not fut.done():
                    fut.set_result(None)

        self.signal.register_callback(cb)
        return fut.__await__()
    

class Clock:
    def __init__(self, value, period, units='ns'):
        self.value = value
        self.period = period
        self.units = units
        self._callbacks = []

    def register_callback(self, cb):
        self._callbacks.append(cb)

    async def start(self, start_low=False):
        half_period = self.period / 2
        while True:
            self.value = int(start_low)
            for cb in self._callbacks:
                cb(int(not start_low), int(start_low))
            await Timer(half_period, units=self.units)
            print("0->1")
            self.value = int(not start_low)
            for cb in self._callbacks:
                cb(int(start_low), int(not start_low))
            await Timer(half_period, units=self.units)
            print("1->0")
