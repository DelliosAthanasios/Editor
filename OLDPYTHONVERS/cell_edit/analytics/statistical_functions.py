"""
Provides a collection of built-in statistical functions for data analysis within the Cell Editor.
These functions can be exposed to the formula engine or used directly by other modules.
"""

import math
from typing import Any, List, Union


class StatisticalFunctions:
    """
    A collection of common statistical functions.
    """
    
    @staticmethod
    def _to_numeric_list(data: List[Any]) -> List[Union[int, float]]:
        """
        Converts a list of mixed types to a list of numeric values, ignoring non-numeric.
        """
        numeric_data = []
        for item in data:
            try:
                numeric_data.append(float(item))
            except (ValueError, TypeError):
                pass # Ignore non-numeric values
        return numeric_data

    @staticmethod
    def sum(data: List[Any]) -> Union[int, float]:
        """
        Calculates the sum of numeric values in a list.
        """
        numeric_data = StatisticalFunctions._to_numeric_list(data)
        return sum(numeric_data)

    @staticmethod
    def average(data: List[Any]) -> Union[float, None]:
        """
        Calculates the average (mean) of numeric values in a list.
        Returns None if the list is empty.
        """
        numeric_data = StatisticalFunctions._to_numeric_list(data)
        if not numeric_data:
            return None
        return sum(numeric_data) / len(numeric_data)

    @staticmethod
    def count(data: List[Any]) -> int:
        """
        Counts the number of non-empty values in a list.
        """
        return len([item for item in data if item is not None and str(item).strip() != ""])

    @staticmethod
    def count_numbers(data: List[Any]) -> int:
        """
        Counts the number of numeric values in a list.
        """
        return len(StatisticalFunctions._to_numeric_list(data))

    @staticmethod
    def min(data: List[Any]) -> Union[int, float, None]:
        """
        Finds the minimum numeric value in a list.
        Returns None if the list is empty.
        """
        numeric_data = StatisticalFunctions._to_numeric_list(data)
        if not numeric_data:
            return None
        return min(numeric_data)

    @staticmethod
    def max(data: List[Any]) -> Union[int, float, None]:
        """
        Finds the maximum numeric value in a list.
        Returns None if the list is empty.
        """
        numeric_data = StatisticalFunctions._to_numeric_list(data)
        if not numeric_data:
            return None
        return max(numeric_data)

    @staticmethod
    def median(data: List[Any]) -> Union[int, float, None]:
        """
        Calculates the median of numeric values in a list.
        Returns None if the list is empty.
        """
        numeric_data = sorted(StatisticalFunctions._to_numeric_list(data))
        n = len(numeric_data)
        if n == 0:
            return None
        
        if n % 2 == 1:
            return numeric_data[n // 2]
        else:
            mid1 = numeric_data[n // 2 - 1]
            mid2 = numeric_data[n // 2]
            return (mid1 + mid2) / 2

    @staticmethod
    def mode(data: List[Any]) -> List[Any]:
        """
        Calculates the mode(s) of values in a list.
        Returns a list of modes, as there can be multiple.
        """
        if not data:
            return []
        
        counts = {}
        for item in data:
            counts[item] = counts.get(item, 0) + 1
        
        max_count = 0
        for count in counts.values():
            if count > max_count:
                max_count = count
        
        modes = [item for item, count in counts.items() if count == max_count]
        return modes

    @staticmethod
    def stdev(data: List[Any], sample: bool = True) -> Union[float, None]:
        """
        Calculates the standard deviation of numeric values in a list.
        
        Args:
            data (List[Any]): The list of values.
            sample (bool): If True, calculates sample standard deviation (n-1 denominator).
                           If False, calculates population standard deviation (n denominator).
                           Defaults to True.
        Returns:
            Union[float, None]: The standard deviation, or None if not enough data.
        """
        numeric_data = StatisticalFunctions._to_numeric_list(data)
        n = len(numeric_data)
        
        if n < (2 if sample else 1):
            return None
        
        mean = sum(numeric_data) / n
        variance = sum([(x - mean) ** 2 for x in numeric_data])
        
        if sample:
            return math.sqrt(variance / (n - 1))
        else:
            return math.sqrt(variance / n)

    @staticmethod
    def variance(data: List[Any], sample: bool = True) -> Union[float, None]:
        """
        Calculates the variance of numeric values in a list.
        
        Args:
            data (List[Any]): The list of values.
            sample (bool): If True, calculates sample variance (n-1 denominator).
                           If False, calculates population variance (n denominator).
                           Defaults to True.
        Returns:
            Union[float, None]: The variance, or None if not enough data.
        """
        numeric_data = StatisticalFunctions._to_numeric_list(data)
        n = len(numeric_data)
        
        if n < (2 if sample else 1):
            return None
        
        mean = sum(numeric_data) / n
        variance = sum([(x - mean) ** 2 for x in numeric_data])
        
        if sample:
            return variance / (n - 1)
        else:
            return variance / n

    @staticmethod
    def percentile(data: List[Any], q: Union[int, float]) -> Union[int, float, None]:
        """
        Calculates the q-th percentile of numeric values in a list.
        
        Args:
            data (List[Any]): The list of values.
            q (Union[int, float]): The percentile to compute, must be between 0 and 100 inclusive.
            
        Returns:
            Union[float, None]: The q-th percentile, or None if the list is empty.
        """
        if not (0 <= q <= 100):
            raise ValueError("Percentile q must be between 0 and 100 inclusive.")
            
        numeric_data = sorted(StatisticalFunctions._to_numeric_list(data))
        n = len(numeric_data)
        
        if n == 0:
            return None
        
        if q == 0:
            return numeric_data[0]
        if q == 100:
            return numeric_data[-1]
            
        # Use linear interpolation between the two closest ranks
        k = (n - 1) * (q / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return numeric_data[int(k)]
        
        d0 = numeric_data[int(f)] * (c - k)
        d1 = numeric_data[int(c)] * (k - f)
        return d0 + d1

    @staticmethod
    def correlation(data1: List[Any], data2: List[Any]) -> Union[float, None]:
        """
        Calculates the Pearson correlation coefficient between two lists of numeric values.
        Returns None if there's not enough data or if standard deviation is zero.
        """
        num_data1 = StatisticalFunctions._to_numeric_list(data1)
        num_data2 = StatisticalFunctions._to_numeric_list(data2)
        
        n = len(num_data1)
        if n != len(num_data2) or n < 2:
            return None
            
        mean1 = sum(num_data1) / n
        mean2 = sum(num_data2) / n
        
        numerator = sum([(x - mean1) * (y - mean2) for x, y in zip(num_data1, num_data2)])
        
        stdev1 = StatisticalFunctions.stdev(num_data1, sample=False) # Population stdev
        stdev2 = StatisticalFunctions.stdev(num_data2, sample=False)
        
        if stdev1 is None or stdev2 is None or stdev1 == 0 or stdev2 == 0:
            return None
            
        denominator = n * stdev1 * stdev2
        
        if denominator == 0:
            return None
            
        return numerator / denominator

    @staticmethod
    def covariance(data1: List[Any], data2: List[Any], sample: bool = True) -> Union[float, None]:
        """
        Calculates the covariance between two lists of numeric values.
        
        Args:
            data1 (List[Any]): The first list of values.
            data2 (List[Any]): The second list of values.
            sample (bool): If True, calculates sample covariance (n-1 denominator).
                           If False, calculates population covariance (n denominator).
                           Defaults to True.
        Returns:
            Union[float, None]: The covariance, or None if not enough data.
        """
        num_data1 = StatisticalFunctions._to_numeric_list(data1)
        num_data2 = StatisticalFunctions._to_numeric_list(data2)
        
        n = len(num_data1)
        if n != len(num_data2) or n < (2 if sample else 1):
            return None
            
        mean1 = sum(num_data1) / n
        mean2 = sum(num_data2) / n
        
        covariance_sum = sum([(x - mean1) * (y - mean2) for x, y in zip(num_data1, num_data2)])
        
        if sample:
            return covariance_sum / (n - 1)
        else:
            return covariance_sum / n


