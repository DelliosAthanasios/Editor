"""
Provides tools for benchmarking various operations within the Cell Editor.
Measures execution time and resource usage for performance analysis.
"""

import time
import cProfile
import pstats
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import os


@dataclass
class BenchmarkResult:
    """
    Represents the result of a single benchmark run.
    """
    name: str
    duration_ms: float
    iterations: int
    average_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    profile_data: Optional[str] = None # Path to profile data file
    metadata: Dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """
    A utility for running and analyzing performance benchmarks.
    """
    
    def __init__(self):
        self._results: List[BenchmarkResult] = []

    def run_benchmark(self, 
                      name: str, 
                      func: Callable, 
                      iterations: int = 1, 
                      *args, 
                      profile: bool = False, 
                      profile_output_path: Optional[str] = None,
                      **kwargs) -> BenchmarkResult:
        """
        Runs a benchmark for a given function.
        
        Args:
            name (str): The name of the benchmark.
            func (Callable): The function to benchmark.
            iterations (int): The number of times to run the function.
            *args: Positional arguments to pass to the function.
            profile (bool): If True, runs cProfile on the function.
            profile_output_path (Optional[str]): Path to save cProfile data.
            **kwargs: Keyword arguments to pass to the function.
            
        Returns:
            BenchmarkResult: The results of the benchmark.
        """
        durations = []
        profile_data_path = None

        print(f"Running benchmark: {name} ({iterations} iterations)")

        if profile:
            pr = cProfile.Profile()
            pr.enable()

        for i in range(iterations):
            start_time = time.perf_counter()
            func(*args, **kwargs)
            end_time = time.perf_counter()
            durations.append((end_time - start_time) * 1000) # Convert to milliseconds

        if profile:
            pr.disable()
            if profile_output_path:
                profile_data_path = profile_output_path
                pr.dump_stats(profile_data_path)
                print(f"cProfile data saved to: {profile_data_path}")
            else:
                # Print stats to console if no path provided
                stats = pstats.Stats(pr)
                stats.sort_stats("cumulative").print_stats(10) # Print top 10 cumulative

        total_duration = sum(durations)
        result = BenchmarkResult(
            name=name,
            duration_ms=total_duration,
            iterations=iterations,
            average_duration_ms=total_duration / iterations,
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            profile_data=profile_data_path
        )
        self._results.append(result)
        print(f"  Completed: {name} - Avg: {result.average_duration_ms:.2f}ms, Total: {result.duration_ms:.2f}ms")
        return result

    def get_all_results(self) -> List[BenchmarkResult]:
        """
        Returns all collected benchmark results.
        """
        return self._results

    def clear_results(self) -> None:
        """
        Clears all stored benchmark results.
        """
        self._results.clear()

    @staticmethod
    def analyze_profile_data(profile_data_path: str, sort_by: str = "cumulative", top_n: int = 20) -> None:
        """
        Analyzes and prints cProfile data from a file.
        
        Args:
            profile_data_path (str): Path to the cProfile data file.
            sort_by (str): How to sort the stats (e.g., "cumulative", "time", "calls").
            top_n (int): Number of top entries to print.
        """
        if not os.path.exists(profile_data_path):
            print(f"Profile data file not found: {profile_data_path}")
            return
        
        print(f"\n--- Analyzing cProfile data from {profile_data_path} ---")
        stats = pstats.Stats(profile_data_path)
        stats.sort_stats(sort_by).print_stats(top_n)
        print("--------------------------------------------------")


# Global instance for BenchmarkRunner
_global_benchmark_runner: Optional[BenchmarkRunner] = None

def get_benchmark_runner() -> BenchmarkRunner:
    """
    Returns the global BenchmarkRunner instance.
    """
    global _global_benchmark_runner
    if _global_benchmark_runner is None:
        _global_benchmark_runner = BenchmarkRunner()
    return _global_benchmark_runner


