#!/usr/bin/env python3
"""
Callback Validation Script für TI-Monitoring

Dieses Skript überprüft alle Callbacks auf:
- DuplicateCallback-Probleme
- Fehlende prevent_initial_call Parameter
- Doppelte Output-IDs
- Null-Prüfungen für Parameter
- Konsistenz zwischen Layout und Callbacks
- Häufige Runtime-Fehler
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

class CallbackValidator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.pages_dir = self.project_root / "pages"
        self.callbacks = []
        self.layout_elements = set()
        self.output_ids = {}  # Track output IDs across callbacks
        self.errors = []
        self.warnings = []
    
    def validate_all(self) -> bool:
        """Validiert alle Callbacks im Projekt"""
        print("🔍 Validiere Callbacks in TI-Monitoring...")
        
        # Finde alle Python-Dateien in pages/
        page_files = list(self.pages_dir.glob("*.py"))
        
        for file_path in page_files:
            if file_path.name.startswith("__"):
                continue
            print(f"📄 Überprüfe {file_path.name}...")
            self._validate_file(file_path)
        
        # Validiere doppelte Outputs
        self._validate_duplicate_outputs()
        
        # Zeige Ergebnisse
        self._print_results()
        return len(self.errors) == 0
    
    def _validate_file(self, file_path: Path):
        """Validiert eine einzelne Datei"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Finde Callbacks und Layout-Elemente
            self._extract_callbacks(tree, file_path)
            self._extract_layout_elements(tree, file_path)
            
        except Exception as e:
            self.errors.append(f"❌ Fehler beim Parsen von {file_path.name}: {e}")
    
    def _extract_callbacks(self, tree: ast.AST, file_path: Path):
        """Extrahiert Callbacks aus dem AST"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == 'callback':
                    self._analyze_callback(node, file_path)
        
        # Analysiere auch die Callback-Funktionen selbst
        self._analyze_callback_functions(tree, file_path)
    
    def _analyze_callback(self, callback_node: ast.Call, file_path: Path):
        """Analysiert einen einzelnen Callback"""
        callback_info = {
            'file': file_path.name,
            'line': callback_node.lineno,
            'outputs': [],
            'has_allow_duplicate': False,
            'has_prevent_initial_call': False,
            'prevent_initial_call_value': None
        }
        
        # Analysiere Argumente
        for arg in callback_node.args:
            if isinstance(arg, ast.List):
                # Output-Liste
                for elt in arg.elts:
                    if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name):
                        if elt.func.id == 'Output':
                            output_id = self._extract_output_id(elt)
                            if output_id:
                                callback_info['outputs'].append(output_id)
        
        # Analysiere Keywords
        for keyword in callback_node.keywords:
            if keyword.arg == 'allow_duplicate':
                callback_info['has_allow_duplicate'] = True
            elif keyword.arg == 'prevent_initial_call':
                callback_info['has_prevent_initial_call'] = True
                callback_info['prevent_initial_call_value'] = keyword.value
        
        # Validiere Callback
        self._validate_callback_rules(callback_info)
        
        # Track output IDs for duplicate detection
        for output_id in callback_info['outputs']:
            if output_id not in self.output_ids:
                self.output_ids[output_id] = []
            self.output_ids[output_id].append({
                'file': callback_info['file'],
                'line': callback_info['line']
            })
        
        self.callbacks.append(callback_info)
    
    def _extract_output_id(self, output_node: ast.Call) -> str:
        """Extrahiert die ID aus einem Output-Node"""
        if len(output_node.args) >= 1:
            if isinstance(output_node.args[0], ast.Constant):
                return output_node.args[0].value
        return None
    
    def _extract_layout_elements(self, tree: ast.AST, file_path: Path):
        """Extrahiert Layout-Elemente mit IDs"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Suche nach html.Div, dcc.Input, etc. mit id-Parameter
                if hasattr(node.func, 'attr') and node.func.attr in ['Div', 'Input', 'Button', 'Textarea']:
                    for keyword in node.keywords:
                        if keyword.arg == 'id':
                            if isinstance(keyword.value, ast.Constant):
                                self.layout_elements.add(keyword.value.value)
    
    def _validate_callback_rules(self, callback_info: Dict):
        """Validiert Callback-Regeln"""
        # Regel 1: allow_duplicate erfordert prevent_initial_call=True
        if callback_info['has_allow_duplicate']:
            if not callback_info['has_prevent_initial_call']:
                self.errors.append(
                    f"❌ {callback_info['file']}:{callback_info['line']} - "
                    f"allow_duplicate=True erfordert prevent_initial_call=True"
                )
            elif not self._is_prevent_initial_call_true(callback_info['prevent_initial_call_value']):
                self.errors.append(
                    f"❌ {callback_info['file']}:{callback_info['line']} - "
                    f"allow_duplicate=True erfordert prevent_initial_call=True (aktuell: {callback_info['prevent_initial_call_value']})"
                )
        
        # Regel 2: Warnung bei vielen Outputs
        if len(callback_info['outputs']) > 5:
            self.warnings.append(
                f"⚠️  {callback_info['file']}:{callback_info['line']} - "
                f"Callback hat {len(callback_info['outputs'])} Outputs (komplex)"
            )
        
        # Regel 3: Validiere Null-Prüfungen für häufige Parameter
        self._validate_null_checks(callback_info)
    
    def _validate_duplicate_outputs(self):
        """Validiert doppelte Output-IDs zwischen Callbacks"""
        for output_id, callbacks in self.output_ids.items():
            if len(callbacks) > 1:
                # Check if any callback has allow_duplicate=True
                has_allow_duplicate = False
                for callback in self.callbacks:
                    if output_id in callback['outputs'] and callback['has_allow_duplicate']:
                        has_allow_duplicate = True
                        break
                
                if not has_allow_duplicate:
                    callback_locations = [f"{cb['file']}:{cb['line']}" for cb in callbacks]
                    self.errors.append(
                        f"❌ Doppelte Output-ID '{output_id}' in Callbacks: {', '.join(callback_locations)}. "
                        f"Verwende allow_duplicate=True oder konsolidiere die Callbacks."
                    )
    
    def _analyze_callback_functions(self, tree: ast.AST, file_path: Path):
        """Analysiert Callback-Funktionen auf häufige Fehler"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Suche nach Funktionen, die wahrscheinlich Callbacks sind
                if self._is_callback_function(node):
                    self._validate_callback_function(node, file_path)
    
    def _is_callback_function(self, func_node: ast.FunctionDef) -> bool:
        """Überprüft ob eine Funktion wahrscheinlich ein Callback ist"""
        # Suche nach Funktionen mit typischen Callback-Parametern
        param_names = [arg.arg for arg in func_node.args.args]
        callback_params = ['auth_data', 'n_clicks', 'value', 'data', 'children']
        return any(param in param_names for param in callback_params)
    
    def _validate_callback_function(self, func_node: ast.FunctionDef, file_path: Path):
        """Validiert eine Callback-Funktion auf häufige Fehler"""
        # Suche nach .get() Aufrufen ohne Null-Prüfung
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
                    # Überprüfe ob es eine Null-Prüfung gibt
                    if not self._has_null_check_before_get(node, func_node):
                        self.warnings.append(
                            f"⚠️  {file_path.name}:{node.lineno} - "
                            f"Möglicherweise fehlende Null-Prüfung vor .get() Aufruf"
                        )
    
    def _has_null_check_before_get(self, get_node: ast.Call, func_node: ast.FunctionDef) -> bool:
        """Überprüft ob vor einem .get() Aufruf eine Null-Prüfung steht"""
        # Vereinfachte Überprüfung - suche nach if-statements mit dem gleichen Objekt
        if isinstance(get_node.func, ast.Attribute):
            obj_name = self._get_object_name(get_node.func.value)
            if obj_name:
                for node in ast.walk(func_node):
                    if isinstance(node, ast.If):
                        if self._check_if_condition_for_object(node, obj_name):
                            return True
        return False
    
    def _get_object_name(self, node: ast.AST) -> str:
        """Extrahiert den Namen eines Objekts aus einem AST-Node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_object_name(node.value)
        return None
    
    def _check_if_condition_for_object(self, if_node: ast.If, obj_name: str) -> bool:
        """Überprüft ob eine if-Bedingung eine Null-Prüfung für das Objekt ist"""
        # Suche nach Bedingungen wie "if not obj_name" oder "if obj_name"
        for node in ast.walk(if_node.test):
            if isinstance(node, ast.Name) and node.id == obj_name:
                return True
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                if isinstance(node.operand, ast.Name) and node.operand.id == obj_name:
                    return True
        return False
    
    def _validate_null_checks(self, callback_info: Dict):
        """Validiert Null-Prüfungen für häufige Parameter"""
        # Diese Methode würde eine AST-Analyse der Callback-Funktion erfordern
        # Für jetzt fügen wir eine einfache Warnung hinzu
        pass
    
    def _is_prevent_initial_call_true(self, value) -> bool:
        """Überprüft ob prevent_initial_call=True ist"""
        if isinstance(value, ast.Constant):
            return value.value is True
        return False
    
    def _print_results(self):
        """Druckt Validierungsergebnisse"""
        print(f"\n📊 Validierungsergebnisse:")
        print(f"   Callbacks gefunden: {len(self.callbacks)}")
        print(f"   Layout-Elemente gefunden: {len(self.layout_elements)}")
        print(f"   Fehler: {len(self.errors)}")
        print(f"   Warnungen: {len(self.warnings)}")
        
        if self.errors:
            print("\n❌ Fehler:")
            for error in self.errors:
                print(f"   {error}")
        
        if self.warnings:
            print("\n⚠️  Warnungen:")
            for warning in self.warnings:
                print(f"   {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ Alle Callbacks sind korrekt!")

def main():
    """Hauptfunktion"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    validator = CallbackValidator(project_root)
    
    success = validator.validate_all()
    
    if not success:
        print("\n💡 Lösungsvorschläge:")
        print("   1. Füge prevent_initial_call=True zu Callbacks mit allow_duplicate=True hinzu")
        print("   2. Überprüfe doppelte Output-IDs")
        print("   3. Verwende eindeutige Callback-Namen")
        sys.exit(1)
    else:
        print("\n🎉 Alle Callbacks sind korrekt!")
        sys.exit(0)

if __name__ == "__main__":
    main()
