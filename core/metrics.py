import threading
import time
from collections import defaultdict, deque
from typing import Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


class MetricType:
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class Metric:
    __slots__ = ("name", "type", "value", "unit", "labels", "timestamp")

    def __init__(self, name: str, mtype: str, value: float, unit: str = "", labels: Optional[dict] = None):
        self.name = name
        self.type = mtype
        self.value = value
        self.unit = unit
        self.labels = labels or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "value": round(self.value, 4),
            "unit": self.unit,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


class MetricsEngine:
    def __init__(self, history_size: int = 300):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self._timers: dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._collect_interval = 5.0

    # ── Counter operations ──

    def increment(self, name: str, value: float = 1, labels: Optional[dict] = None):
        with self._lock:
            self._counters[name] += value

    def get_counter(self, name: str) -> float:
        with self._lock:
            return self._counters.get(name, 0)

    # ── Gauge operations ──

    def set_gauge(self, name: str, value: float):
        with self._lock:
            self._gauges[name] = value

    def get_gauge(self, name: str) -> Optional[float]:
        with self._lock:
            return self._gauges.get(name)

    # ── Histogram operations ──

    def observe(self, name: str, value: float):
        with self._lock:
            self._histograms[name].append(value)

    def get_histogram_stats(self, name: str) -> dict:
        with self._lock:
            values = list(self._histograms.get(name, []))

        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        return {
            "count": n,
            "min": round(sorted_vals[0], 4),
            "max": round(sorted_vals[-1], 4),
            "avg": round(sum(sorted_vals) / n, 4),
            "p50": round(sorted_vals[n // 2], 4),
            "p95": round(sorted_vals[int(n * 0.95)], 4),
            "p99": round(sorted_vals[min(int(n * 0.99), n - 1)], 4),
        }

    # ── Timer operations ──

    def record_latency(self, name: str, duration_ms: float):
        self.observe(f"latency.{name}", duration_ms)

    def timer(self, name: str):
        """Context manager for timing code blocks."""
        return _TimerContext(self, name)

    # ── System metrics collection ──

    def start_collection(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

    def stop_collection(self):
        self._running = False

    def _collect_loop(self):
        while self._running:
            self._collect_system_metrics()
            time.sleep(self._collect_interval)

    def _collect_system_metrics(self):
        if not _HAS_PSUTIL:
            return

        try:
            self.set_gauge("system.cpu_percent", psutil.cpu_percent(interval=0.5))
            self.set_gauge("system.ram_percent", psutil.virtual_memory().percent)
            self.set_gauge("system.ram_used_mb", psutil.virtual_memory().used / (1024 * 1024))
            self.set_gauge("system.ram_total_mb", psutil.virtual_memory().total / (1024 * 1024))

            disk = psutil.disk_usage("/")
            self.set_gauge("system.disk_percent", disk.percent)
            self.set_gauge("system.disk_used_gb", disk.used / (1024 ** 3))
            self.set_gauge("system.disk_free_gb", disk.free / (1024 ** 3))

            net = psutil.net_io_counters()
            self.set_gauge("system.net_bytes_sent", net.bytes_sent)
            self.set_gauge("system.net_bytes_recv", net.bytes_recv)

            self.set_gauge("system.thread_count", threading.active_count())
        except Exception:
            pass

    # ── Snapshot ──

    def snapshot(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)

        histograms = {}
        for name in self._histograms:
            histograms[name] = self.get_histogram_stats(name)

        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
            "timestamp": time.time(),
        }

    def performance_summary(self) -> dict:
        snap = self.snapshot()
        gauges = snap["gauges"]
        histograms = snap["histograms"]

        result = {}
        for name, stats in histograms.items():
            if name.startswith("latency."):
                key = name.replace("latency.", "")
                result[key] = {
                    "avg_ms": stats["avg"],
                    "p95_ms": stats["p95"],
                    "p99_ms": stats["p99"],
                    "count": stats["count"],
                }

        result["cpu_percent"] = gauges.get("system.cpu_percent", 0)
        result["ram_percent"] = gauges.get("system.ram_percent", 0)
        result["ram_used_mb"] = gauges.get("system.ram_used_mb", 0)
        result["disk_percent"] = gauges.get("system.disk_percent", 0)
        result["thread_count"] = gauges.get("system.thread_count", 0)

        return result


class _TimerContext:
    __slots__ = ("engine", "name", "_start")

    def __init__(self, engine: MetricsEngine, name: str):
        self.engine = engine
        self.name = name
        self._start = 0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self._start) * 1000
        self.engine.record_latency(self.name, duration_ms)
        return False


metrics = MetricsEngine()
