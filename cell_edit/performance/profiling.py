"""
Provides tools for memory and CPU profiling of the Cell Editor application.
Helps identify memory leaks, excessive allocations, and CPU bottlenecks.
"""

import tracemalloc
import sys
import time
import cProfile
import pstats
from typing import Any, Callable, Dict, List, Optional, Tuple


class MemoryProfiler:
    """
    A utility for memory profiling using tracemalloc.
    """
    
    def __init__(self):
        self._snapshot1: Optional[tracemalloc.Snapshot] = None
        self._snapshot2: Optional[tracemalloc.Snapshot] = None

    def start(self) -> None:
        """
        Starts tracking memory allocations.
        """
        if tracemalloc.is_tracing():
            print("Tracemalloc is already tracing.")
            return
        tracemalloc.start()
        print("Memory profiling started.")

    def take_snapshot(self) -> None:
        """
        Takes a snapshot of current memory allocations.
        """
        if not tracemalloc.is_tracing():
            print("Tracemalloc is not tracing. Call start() first.")
            return
        
        if self._snapshot1 is None:
            self._snapshot1 = tracemalloc.take_snapshot()
            print("First memory snapshot taken.")
        else:
            self._snapshot2 = tracemalloc.take_snapshot()
            print("Second memory snapshot taken.")

    def stop(self) -> None:
        """
        Stops tracking memory allocations and clears snapshots.
        """
        if tracemalloc.is_tracing():
            tracemalloc.stop()
            self._snapshot1 = None
            self._snapshot2 = None
            print("Memory profiling stopped and snapshots cleared.")
        else:
            print("Tracemalloc is not tracing.")

    def print_top_diff(self, limit: int = 10) -> None:
        """
        Compares the two most recent snapshots and prints the top differences.
        """
        if self._snapshot1 is None or self._snapshot2 is None:
            print("Need at least two snapshots to compare. Call take_snapshot() twice.")
            return
        
        top_stats = self._snapshot2.compare_to(self._snapshot1, 'lineno')
        
        print(f"\n--- Top {limit} memory differences between snapshots ---")
        for index, stat in enumerate(top_stats[:limit]):
            print(f"#{index+1}: {stat.traceback.format_single().strip()}\n"\
                  f"         {stat.size / 1024:.1f} KiB ({stat.count} blocks)")
        print("--------------------------------------------------")

    def print_top_current(self, limit: int = 10) -> None:
        """
        Prints the top current memory allocations from the latest snapshot.
        """
        snapshot = self._snapshot2 if self._snapshot2 else self._snapshot1
        if snapshot is None:
            print("No snapshot available. Call take_snapshot() first.")
            return
        
        top_stats = snapshot.statistics('lineno')
        
        print(f"\n--- Top {limit} current memory allocations ---")
        for index, stat in enumerate(top_stats[:limit]):
            print(f"#{index+1}: {stat.traceback.format_single().strip()}\n"\
                  f"         {stat.size / 1024:.1f} KiB ({stat.count} blocks)")
        print("--------------------------------------------------")


class CPUProfiler:
    """
    A utility for CPU profiling using cProfile.
    """
    
    def __init__(self):
        self._profiler: Optional[cProfile.Profile] = None

    def start(self) -> None:
        """
        Starts CPU profiling.
        """
        if self._profiler is not None:
            print("CPU profiler is already running.")
            return
        self._profiler = cProfile.Profile()
        self._profiler.enable()
        print("CPU profiling started.")

    def stop(self, output_path: Optional[str] = None, sort_by: str = "cumulative", top_n: int = 10) -> None:
        """
        Stops CPU profiling and prints/saves the results.
        """
        if self._profiler is None:
            print("CPU profiler is not running.")
            return
        
        self._profiler.disable()
        
        if output_path:
            self._profiler.dump_stats(output_path)
            print(f"CPU profile data saved to: {output_path}")
        else:
            stats = pstats.Stats(self._profiler)
            print(f"\n--- Top {top_n} CPU usage stats (sorted by {sort_by}) ---")
            stats.sort_stats(sort_by).print_stats(top_n)
            print("--------------------------------------------------")
            
        self._profiler = None


# Global instances
_global_memory_profiler: Optional[MemoryProfiler] = None
_global_cpu_profiler: Optional[CPUProfiler] = None

def get_memory_profiler() -> MemoryProfiler:
    """
    Returns the global MemoryProfiler instance.
    """
    global _global_memory_profiler
    if _global_memory_profiler is None:
        _global_memory_profiler = MemoryProfiler()
    return _global_memory_profiler


def get_cpu_profiler() -> CPUProfiler:
    """
    Returns the global CPUProfiler instance.
    """
    global _global_cpu_profiler
    if _global_cpu_profiler is None:
        _global_cpu_profiler = CPUProfiler()
    return _global_cpu_profiler


