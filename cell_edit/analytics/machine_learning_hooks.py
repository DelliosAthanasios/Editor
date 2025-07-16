"""
Provides hooks and interfaces for integrating machine learning models and workflows.
Enables users to train, evaluate, and deploy ML models directly within the Cell Editor.
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from enum import Enum

from core.interfaces import ISheet, IWorkbook
from core.coordinates import CellRange, CellCoordinate
from plugins.extension_points import register_extension, get_extensions, create_extension_point


class MLModelType(Enum):
    """Types of machine learning models."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    FORECASTING = "forecasting"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    CUSTOM = "custom"


# Define an extension point for custom ML models/algorithms
CUSTOM_ML_EXTENSION_POINT = create_extension_point(
    "custom_ml_models",
    "Allows plugins to register custom machine learning models or algorithms."
)


@dataclass
class MLModelInfo:
    """
    Represents information about a custom ML model provided by a plugin.
    """
    model_id: str
    display_name: str
    model_type: MLModelType
    # Callable to train the model
    train_function: Callable[[Any, Any, Optional[Dict[str, Any]]], Any]
    # Callable to make predictions with the model
    predict_function: Callable[[Any, Optional[Dict[str, Any]]], Any]
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not callable(self.train_function):
            raise ValueError("ML model train function must be a callable.")
        if not callable(self.predict_function):
            raise ValueError("ML model predict function must be a callable.")


@dataclass
class MLWorkflowInfo:
    """
    Represents information about a predefined ML workflow provided by a plugin.
    """
    workflow_id: str
    display_name: str
    description: str
    # Callable to execute the entire workflow (e.g., data prep, train, predict, visualize)
    execute_function: Callable[[ISheet, Optional[Dict[str, Any]]], Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not callable(self.execute_function):
            raise ValueError("ML workflow execute function must be a callable.")


class MachineLearningHooks:
    """
    Manages the registration and execution of machine learning models and workflows.
    """
    
    def __init__(self):
        self._registered_models: Dict[str, MLModelInfo] = {}
        self._registered_workflows: Dict[str, MLWorkflowInfo] = {}

    def register_ml_model(self, plugin_name: str, model_info: MLModelInfo) -> None:
        """
        Registers a custom ML model from a plugin.
        """
        if not isinstance(model_info, MLModelInfo):
            raise TypeError("model_info must be an instance of MLModelInfo")
            
        if model_info.model_id in self._registered_models:
            raise ValueError(f"ML model with ID \'{model_info.model_id}\' already registered.")
            
        self._registered_models[model_info.model_id] = model_info
        
        # Register with the extension point for discovery
        register_extension(
            CUSTOM_ML_EXTENSION_POINT.name,
            plugin_name,
            model_info.model_id,
            model_info
        )
        print(f"Custom ML model \'{model_info.model_id}\' registered by plugin \'{plugin_name}\'")

    def unregister_ml_model(self, model_id: str) -> None:
        """
        Unregisters a custom ML model.
        """
        if model_id not in self._registered_models:
            print(f"ML model \'{model_id}\' not found.")
            return
            
        CUSTOM_ML_EXTENSION_POINT.unregister(model_id)
        del self._registered_models[model_id]
        print(f"ML model \'{model_id}\' unregistered.")

    def get_ml_model(self, model_id: str) -> Optional[MLModelInfo]:
        """
        Retrieves a registered ML model by its ID.
        """
        return self._registered_models.get(model_id)

    def get_all_ml_models(self) -> List[MLModelInfo]:
        """
        Returns a list of all registered ML models.
        """
        return list(self._registered_models.values())

    def register_ml_workflow(self, plugin_name: str, workflow_info: MLWorkflowInfo) -> None:
        """
        Registers a custom ML workflow from a plugin.
        """
        if not isinstance(workflow_info, MLWorkflowInfo):
            raise TypeError("workflow_info must be an instance of MLWorkflowInfo")
            
        if workflow_info.workflow_id in self._registered_workflows:
            raise ValueError(f"ML workflow with ID \'{workflow_info.workflow_id}\' already registered.")
            
        self._registered_workflows[workflow_info.workflow_id] = workflow_info
        
        # Register with the extension point for discovery (can use the same EP or a new one)
        register_extension(
            CUSTOM_ML_EXTENSION_POINT.name, # Reusing for simplicity, could be a new EP
            plugin_name,
            workflow_info.workflow_id,
            workflow_info
        )
        print(f"Custom ML workflow \'{workflow_info.workflow_id}\' registered by plugin \'{plugin_name}\'")

    def unregister_ml_workflow(self, workflow_id: str) -> None:
        """
        Unregisters a custom ML workflow.
        """
        if workflow_id not in self._registered_workflows:
            print(f"ML workflow \'{workflow_id}\' not found.")
            return
            
        CUSTOM_ML_EXTENSION_POINT.unregister(workflow_id)
        del self._registered_workflows[workflow_id]
        print(f"ML workflow \'{workflow_id}\' unregistered.")

    def get_ml_workflow(self, workflow_id: str) -> Optional[MLWorkflowInfo]:
        """
        Retrieves a registered ML workflow by its ID.
        """
        return self._registered_workflows.get(workflow_id)

    def get_all_ml_workflows(self) -> List[MLWorkflowInfo]:
        """
        Returns a list of all registered ML workflows.
        """
        return list(self._registered_workflows.values())

    def execute_ml_workflow(self, workflow_id: str, sheet: ISheet, 
                            options: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes a registered ML workflow.
        """
        workflow_info = self.get_ml_workflow(workflow_id)
        if not workflow_info:
            raise ValueError(f"ML workflow \'{workflow_id}\' not found.")
        
        print(f"Executing ML workflow: {workflow_info.display_name}")
        return workflow_info.execute_function(sheet, options)


# Global instance for MachineLearningHooks
_global_ml_hooks: Optional[MachineLearningHooks] = None

def get_machine_learning_hooks() -> MachineLearningHooks:
    """
    Returns the global MachineLearningHooks instance.
    """
    global _global_ml_hooks
    if _global_ml_hooks is None:
        _global_ml_hooks = MachineLearningHooks()
    return _global_ml_hooks


