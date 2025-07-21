"""
Advanced data processing and analytics engine for the Cell Editor.
Integrates with powerful libraries like pandas for large-scale data manipulation and analysis.
"""

from analytics.pandas_integration import PandasIntegration
from analytics.data_validation import DataValidator, ValidationRule, ValidationError
from analytics.data_transformation import DataTransformer, TransformationStep
from analytics.statistical_functions import StatisticalFunctions
from analytics.machine_learning_hooks import MachineLearningHooks
from analytics.streaming_data import StreamingDataManager

__all__ = [
    'PandasIntegration',
    'DataValidator', 'ValidationRule', 'ValidationError',
    'DataTransformer', 'TransformationStep',
    'StatisticalFunctions',
    'MachineLearningHooks',
    'StreamingDataManager'
]

