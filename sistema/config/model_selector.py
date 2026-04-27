#!/usr/bin/env python3
"""
Model Selector Intel·ligent per a Biblioteca Universal Arion
Optimitza l'ús de DIEM segons pressupost i complexitat de la tasca
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# ==============================================================================
# CONFIGURACIÓ DE MODELS I COSTOS
# ==============================================================================

class ModelTier(Enum):
    ECONOMIC = "economic"      # < 0.5 DIEM per tasca
    BALANCED = "balanced"      # 0.5-2 DIEM per tasca
    SUPERIOR = "superior"      # > 2 DIEM per tasca

@dataclass
class ModelConfig:
    model_id: str
    tier: ModelTier
    estimated_cost: float  # DIEM per tasca típica
    best_for: List[str]
    avoid_for: List[str] = None
    
    def __post_init__(self):
        if self.avoid_for is None:
            self.avoid_for = []

# Models disponibles ordenats per cost
MODELS = {
    # Models econòmics (< 0.5 DIEM)
    "glm-5": ModelConfig(
        "zai-org-glm-5",
        ModelTier.ECONOMIC,
        0.15,
        ["rutinàries", "metadata", "web", "tests"],
        ["traduccions_complexes", "supervisió_qualitat"]
    ),
    "deepseek-v3": ModelConfig(
        "deepseek-v3.2",
        ModelTier.ECONOMIC,
        0.25,
        ["fetch", "parseig", "textos_curts"],
        ["literatura_complexa", "filosofia"]
    ),
    
    # Models equilibrats (0.5-2 DIEM)
    "claude-sonnet": ModelConfig(
        "claude-sonnet-4-6",
        ModelTier.BALANCED,
        0.8,
        ["traduccions_normals", "glossaris", "notes"],
        ["supervisió_final", "obres_complexes"]
    ),
    "qwen-27b": ModelConfig(
        "qwen3-6-27b",
        ModelTier.BALANCED,
        1.2,
        ["supervisió_bàsica", "revisions"],
        ["traduccions_literàries"]
    ),
    
    # Models superiors (> 2 DIEM)
    "claude-opus": ModelConfig(
        "claude-opus-4-7",
        ModelTier.SUPERIOR,
        3.5,
        ["traduccions_altes", "filosofia", "literatura"],
        ["rutinàries"]
    ),
    "gpt-55-pro": ModelConfig(
        "openai-gpt-55-pro",
        ModelTier.SUPERIOR,
        5.0,
        ["supervisió_final", "detecció_al·lucinacions"],
        ["rutinàries", "textos_senzills"]
    ),
}

# ==============================================================================
# TASQUES DEL PROJECTE
# ==============================================================================

TASK_TYPES = {
    "fetch": {
        "complexity": "low",
        "models": ["deepseek-v3", "glm-5"],
        "priority": 1
    },
    "metadata": {
        "complexity": "low",
        "models": ["glm-5"],
        "priority": 1
    },
    "translate_filosofia": {
        "complexity": "very_high",
        "models": ["claude-opus", "claude-sonnet"],
        "priority": 4
    },
    "translate_narrativa": {
        "complexity": "high",
        "models": ["claude-sonnet", "qwen-27b"],
        "priority": 3
    },
    "translate_poesia": {
        "complexity": "very_high",
        "models": ["claude-opus"],
        "priority": 4
    },
    "translate_oriental": {
        "complexity": "very_high",
        "models": ["claude-opus", "gpt-55-pro"],
        "priority": 4
    },
    "supervision_basic": {
        "complexity": "medium",
        "models": ["qwen-27b", "claude-sonnet"],
        "priority": 2
    },
    "supervision_final": {
        "complexity": "high",
        "models": ["gpt-55-pro", "claude-opus"],
        "priority": 3
    },
    "web_build": {
        "complexity": "low",
        "models": ["glm-5"],
        "priority": 1
    },
    "fix_quality": {
        "complexity": "medium",
        "models": ["claude-sonnet"],
        "priority": 2
    }
}

# ==============================================================================
# SELECTOR INTEL·LIGENT
# ==============================================================================

class ModelSelector:
    def __init__(self, min_diem_reserve: float = 2.0, config_file: str = None):
        self.min_diem_reserve = min_diem_reserve
        self.config_file = config_file or os.path.expanduser(
            "~/.hermes/venice_config.json"
        )
        self.current_balance = self._get_current_balance()
        
    def _get_current_balance(self) -> float:
        """Consulta el saldo DIEM actual."""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", os.path.expanduser(
                    "~/.openclaw/workspace/skills/venice-ai/scripts/venice.py"
                ), "balance"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                return 0.0
            
            # Parse DIEM from output
            for line in result.stdout.split('\n'):
                if 'DIEM:' in line:
                    return float(line.split('DIEM:')[1].strip())
            return 0.0
            
        except Exception as e:
            print(f"⚠️ Error consultant saldo: {e}")
            return 0.0
    
    def get_optimal_model(self, task_type: str, work_info: Dict = None) -> str:
        """
        Selecciona el model òptim segons:
        1. Tipus de tasca
        2. Saldo DIEM disponible
        3. Complexitat de l'obra
        4. Prioritat de la tasca
        """
        
        # Informació de la tasca
        task_info = TASK_TYPES.get(task_type, TASK_TYPES["metadata"])
        complexity = task_info["complexity"]
        priority = task_info["priority"]
        
        # Ajustar per informació de l'obra
        if work_info:
            # Obres especialment importants o complexes
            if work_info.get("importance") == "high":
                priority = min(priority + 1, 4)
            if work_info.get("pages", 0) > 100:
                complexity = "very_high"
        
        # Estratègia segons saldo disponible
        available = self.current_balance - self.min_diem_reserve
        
        # Saldo molt baix (< 3 DIEM): només econòmics
        if available < 3.0:
            return self._select_cheapest_model(task_info["models"])
        
        # Saldo baix (3-8 DIEM): models equilibrats
        elif available < 8.0:
            if complexity in ["very_high", "high"] and priority >= 3:
                # Tasca important: un model superior que no sigui el més car
                models = [m for m in task_info["models"] 
                         if MODELS[m].tier != ModelTier.SUPERIOR]
                if not models:
                    models = task_info["models"][:1]  # El primer disponible
                return models[0]
            else:
                # Tasca normal: model equilibrat o econòmic
                return self._select_balanced_model(task_info["models"])
        
        # Saldo alt (> 8 DIEM): llibertat total
        else:
            return task_info["models"][0]  # Millor model per la tasca
    
    def _select_cheapest_model(self, model_list: List[str]) -> str:
        """Selecciona el model més econòmic de la llista."""
        economic_models = [
            m for m in model_list 
            if MODELS[m].tier == ModelTier.ECONOMIC
        ]
        
        if economic_models:
            # Modelo més econòmic
            return min(economic_models, key=lambda m: MODELS[m].estimated_cost)
        
        # Si no n'hi ha econòmics, el més barat de la llista
        return min(model_list, key=lambda m: MODELS[m].estimated_cost)
    
    def _select_balanced_model(self, model_list: List[str]) -> str:
        """Selecciona un model equilibrat (cost/qualitat)."""
        balanced_models = [
            m for m in model_list 
            if MODELS[m].tier in [ModelTier.ECONOMIC, ModelTier.BALANCED]
        ]
        
        if balanced_models:
            # Model equilibrat preferit
            return balanced_models[0]
        
        # Si només hi ha superiors, el més barat
        return min(model_list, key=lambda m: MODELS[m].estimated_cost)
    
    def estimate_cost(self, task_type: str, work_info: Dict = None) -> float:
        """Estima el cost en DIEM d'una tasca."""
        model_id = self.get_optimal_model(task_type, work_info)
        return MODELS[model_id].estimated_cost
    
    def can_afford(self, task_type: str, work_info: Dict = None) -> bool:
        """Verifica si hi ha saldo suficient per a una tasca."""
        estimated_cost = self.estimate_cost(task_type, work_info)
        available = self.current_balance - self.min_diem_reserve
        return available >= estimated_cost
    
    def get_budget_status(self) -> Dict:
        """Retorna l'estat del pressupost."""
        available = self.current_balance - self.min_diem_reserve
        
        return {
            "total_balance": self.current_balance,
            "available_for_tasks": max(0, available),
            "reserve": self.min_diem_reserve,
            "recommended_actions": self._get_recommendations(available)
        }
    
    def _get_recommendations(self, available: float) -> List[str]:
        """Recomanacions segons saldo disponible."""
        recommendations = []
        
        if available < 2.0:
            recommendations.append("🚨 Saldo molt baix - només tasques rutinàries")
            recommendations.append("💡 Considera esperar al proper reset (00:00 UTC)")
        elif available < 5.0:
            recommendations.append("⚠️ Saldo baix - предпочte models econòmics")
            recommendations.append("📊 Prioritza supervisions bàsiques")
        elif available < 10.0:
            recommendations.append("✅ Saldo adequat - models equilibrats")
            recommendations.append("🎯 Prioritza traduccions importants")
        else:
            recommendations.append("💰 Saldo alt - llibertat total")
            recommendations.append("💎 Utilitza models superiors per a obres complexes")
        
        return recommendations
    
    def save_config(self):
        """Guarda la configuració actual."""
        config = {
            "current_balance": self.current_balance,
            "min_diem_reserve": self.min_diem_reserve,
            "timestamp": str(datetime.now())
        }
        
        Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

# ==============================================================================
# FUNCIONS D'ÚS
# ==============================================================================

def select_model_for_task(task_type: str, work_info: Dict = None) -> str:
    """Funció principal per seleccionar model."""
    selector = ModelSelector()
    return selector.get_optimal_model(task_type, work_info)

def can_proceed_with_task(task_type: str, work_info: Dict = None) -> tuple:
    """Verifica si s pot procedir amb una tasca."""
    selector = ModelSelector()
    model = selector.get_optimal_model(task_type, work_info)
    can_afford = selector.can_afford(task_type, work_info)
    estimated_cost = selector.estimate_cost(task_type, work_info)
    
    return can_afford, model, estimated_cost

def get_budget_report() -> str:
    """Genera un informe del pressupost."""
    selector = ModelSelector()
    status = selector.get_budget_status()
    
    report = f"""
╔══════════════════════════════════════════╗
║     PRESSUPOST VENICE AI - DIEM          ║
╠══════════════════════════════════════════╣
║ Saldo total:        {status['total_balance']:>8.2f} DIEM       ║
║ Disponible:         {status['available_for_tasks']:>8.2f} DIEM       ║
║ Reserva mínima:     {status['reserve']:>8.2f} DIEM       ║
╠══════════════════════════════════════════╣
║ Recomanacions:                           ║
"""
    
    for rec in status['recommended_actions']:
        report += f"║ {rec:<40} ║\n"
    
    report += "╚══════════════════════════════════════════╝\n"
    
    return report

if __name__ == "__main__":
    # Exemple d'ús
    print(get_budget_report())
    
    # Exemples de selecció
    print("\n exemples de selecció de models:")
    for task in ["translate_filosofia", "translate_narrativa", "supervision_final", "fetch"]:
        model = select_model_for_task(task)
        cost = ModelSelector().estimate_cost(task)
        print(f"  {task:25} → {model:20} (~{cost:.2f} DIEM)")