#!/usr/bin/env python3
"""
Callback Registry System für TI-Monitoring

Dieses System hilft bei der Organisation und Validierung von Callbacks.
Es verhindert Duplikate und stellt Konsistenz sicher.
"""

import json
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class CallbackInfo:
    """Informationen über einen Callback"""
    name: str
    file: str
    line: int
    outputs: List[str]
    inputs: List[str]
    has_allow_duplicate: bool
    has_prevent_initial_call: bool
    complexity_score: int  # Anzahl Outputs + Inputs

class CallbackRegistry:
    """Registry für alle Callbacks im Projekt"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.callbacks: Dict[str, CallbackInfo] = {}
        self.output_registry: Dict[str, List[str]] = {}  # output_id -> [callback_names]
        self.input_registry: Dict[str, List[str]] = {}   # input_id -> [callback_names]
    
    def register_callback(self, callback_info: CallbackInfo) -> bool:
        """Registriert einen neuen Callback"""
        # Validiere Callback-Regeln
        if not self._validate_callback(callback_info):
            return False
        
        # Prüfe auf Duplikate
        if callback_info.name in self.callbacks:
            print(f"⚠️  Warnung: Callback '{callback_info.name}' bereits registriert")
            return False
        
        # Registriere Callback
        self.callbacks[callback_info.name] = callback_info
        
        # Aktualisiere Output-Registry
        for output in callback_info.outputs:
            if output not in self.output_registry:
                self.output_registry[output] = []
            self.output_registry[output].append(callback_info.name)
        
        # Aktualisiere Input-Registry
        for input_id in callback_info.inputs:
            if input_id not in self.input_registry:
                self.input_registry[input_id] = []
            self.input_registry[input_id].append(callback_info.name)
        
        return True
    
    def _validate_callback(self, callback_info: CallbackInfo) -> bool:
        """Validiert Callback-Regeln"""
        errors = []
        
        # Regel 1: allow_duplicate erfordert prevent_initial_call=True
        if callback_info.has_allow_duplicate and not callback_info.has_prevent_initial_call:
            errors.append(f"allow_duplicate=True erfordert prevent_initial_call=True")
        
        # Regel 2: Komplexität prüfen
        if callback_info.complexity_score > 10:
            errors.append(f"Callback zu komplex (Score: {callback_info.complexity_score})")
        
        # Regel 3: Doppelte Outputs prüfen
        for output in callback_info.outputs:
            if output in self.output_registry:
                existing_callbacks = self.output_registry[output]
                if not callback_info.has_allow_duplicate:
                    errors.append(f"Output '{output}' bereits in Callbacks: {existing_callbacks}")
        
        if errors:
            print(f"❌ Callback '{callback_info.name}' ungültig:")
            for error in errors:
                print(f"   - {error}")
            return False
        
        return True
    
    def get_callback_by_output(self, output_id: str) -> List[CallbackInfo]:
        """Gibt alle Callbacks zurück, die ein bestimmtes Output verwenden"""
        callback_names = self.output_registry.get(output_id, [])
        return [self.callbacks[name] for name in callback_names if name in self.callbacks]
    
    def get_callback_by_input(self, input_id: str) -> List[CallbackInfo]:
        """Gibt alle Callbacks zurück, die ein bestimmtes Input verwenden"""
        callback_names = self.input_registry.get(input_id, [])
        return [self.callbacks[name] for name in callback_names if name in self.callbacks]
    
    def get_complex_callbacks(self, threshold: int = 5) -> List[CallbackInfo]:
        """Gibt komplexe Callbacks zurück"""
        return [cb for cb in self.callbacks.values() if len(cb.outputs) > threshold]
    
    def generate_report(self) -> str:
        """Generiert einen Bericht über alle Callbacks"""
        report = []
        report.append("📊 Callback Registry Report")
        report.append("=" * 50)
        report.append(f"Gesamt Callbacks: {len(self.callbacks)}")
        report.append(f"Eindeutige Outputs: {len(self.output_registry)}")
        report.append(f"Eindeutige Inputs: {len(self.input_registry)}")
        
        # Komplexe Callbacks
        complex_callbacks = self.get_complex_callbacks()
        if complex_callbacks:
            report.append(f"\n⚠️  Komplexe Callbacks ({len(complex_callbacks)}):")
            for cb in complex_callbacks:
                report.append(f"   - {cb.name} ({cb.file}:{cb.line}) - {len(cb.outputs)} Outputs")
        
        # Callbacks mit allow_duplicate
        duplicate_callbacks = [cb for cb in self.callbacks.values() if cb.has_allow_duplicate]
        if duplicate_callbacks:
            report.append(f"\n🔄 Callbacks mit allow_duplicate ({len(duplicate_callbacks)}):")
            for cb in duplicate_callbacks:
                report.append(f"   - {cb.name} ({cb.file}:{cb.line})")
        
        return "\n".join(report)
    
    def save_to_file(self, file_path: str):
        """Speichert Registry in JSON-Datei"""
        data = {
            'callbacks': {name: asdict(cb) for name, cb in self.callbacks.items()},
            'output_registry': self.output_registry,
            'input_registry': self.input_registry
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, file_path: str):
        """Lädt Registry aus JSON-Datei"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Lade Callbacks
        self.callbacks = {}
        for name, cb_data in data['callbacks'].items():
            self.callbacks[name] = CallbackInfo(**cb_data)
        
        # Lade Registrys
        self.output_registry = data['output_registry']
        self.input_registry = data['input_registry']

def main():
    """Beispiel-Verwendung des Callback Registry Systems"""
    registry = CallbackRegistry(".")
    
    # Beispiel-Callback
    example_callback = CallbackInfo(
        name="example_callback",
        file="example.py",
        line=10,
        outputs=["output-1", "output-2"],
        inputs=["input-1"],
        has_allow_duplicate=False,
        has_prevent_initial_call=True,
        complexity_score=3
    )
    
    # Registriere Callback
    success = registry.register_callback(example_callback)
    print(f"Callback registriert: {success}")
    
    # Generiere Bericht
    report = registry.generate_report()
    print(report)

if __name__ == "__main__":
    main()
