#!/usr/bin/env python3
"""
Projektübergreifende Callback-Validierung für TI-Monitoring
Dieses Skript sollte in CI/CD integriert werden, um Callback-Probleme frühzeitig zu erkennen.
"""

import os
import re
import ast
import sys
import json
from collections import defaultdict, Counter
from pathlib import Path

class CallbackValidator:
    def __init__(self):
        self.callbacks = []
        self.layout_elements = []
        self.conflicts = []
        self.duplicates = []
        self.warnings = []
        
    def find_callback_files(self):
        """Finde alle Python-Dateien mit Callbacks"""
        pages_dir = Path("pages")
        callback_files = []
        
        for py_file in pages_dir.glob("*.py"):
            if py_file.name != "__init__.py":
                callback_files.append(py_file)
        
        return callback_files
    
    def extract_callbacks_from_file(self, file_path):
        """Extrahiere alle Callbacks aus einer Datei"""
        callbacks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Prüfe ob es ein Callback ist (hat @callback decorator)
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == 'callback':
                            callbacks.append({
                                'name': node.name,
                                'file': str(file_path),
                                'line': node.lineno,
                                'function': node
                            })
                        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == 'callback':
                            callbacks.append({
                                'name': node.name,
                                'file': str(file_path),
                                'line': node.lineno,
                                'function': node,
                                'decorator': decorator
                            })
        
        except Exception as e:
            self.warnings.append(f"Fehler beim Parsen von {file_path}: {e}")
        
        return callbacks
    
    def extract_callback_details(self, callback):
        """Extrahiere Details aus einem Callback"""
        details = {
            'name': callback['name'],
            'file': callback['file'],
            'line': callback['line'],
            'outputs': [],
            'inputs': [],
            'states': [],
            'prevent_initial_call': None,
            'allow_duplicate': False
        }
        
        if 'decorator' in callback:
            decorator = callback['decorator']
            
            # Extrahiere Outputs
            if len(decorator.args) > 0:
                outputs_arg = decorator.args[0]
                if isinstance(outputs_arg, ast.List):
                    for elt in outputs_arg.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                            output_id = elt.elts[0].s if isinstance(elt.elts[0], ast.Constant) else str(elt.elts[0])
                            output_prop = elt.elts[1].s if isinstance(elt.elts[1], ast.Constant) else str(elt.elts[1])
                            details['outputs'].append(f"{output_id}.{output_prop}")
                elif isinstance(outputs_arg, ast.Tuple) and len(outputs_arg.elts) >= 2:
                    output_id = outputs_arg.elts[0].s if isinstance(outputs_arg.elts[0], ast.Constant) else str(outputs_arg.elts[0])
                    output_prop = outputs_arg.elts[1].s if isinstance(outputs_arg.elts[1], ast.Constant) else str(outputs_arg.elts[1])
                    details['outputs'].append(f"{output_id}.{output_prop}")
            
            # Extrahiere Inputs
            if len(decorator.args) > 1:
                inputs_arg = decorator.args[1]
                if isinstance(inputs_arg, ast.List):
                    for elt in inputs_arg.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                            input_id = elt.elts[0].s if isinstance(elt.elts[0], ast.Constant) else str(elt.elts[0])
                            input_prop = elt.elts[1].s if isinstance(elt.elts[1], ast.Constant) else str(elt.elts[1])
                            details['inputs'].append(f"{input_id}.{input_prop}")
                elif isinstance(inputs_arg, ast.Tuple) and len(inputs_arg.elts) >= 2:
                    input_id = inputs_arg.elts[0].s if isinstance(inputs_arg.elts[0], ast.Constant) else str(inputs_arg.elts[0])
                    input_prop = inputs_arg.elts[1].s if isinstance(inputs_arg.elts[1], ast.Constant) else str(inputs_arg.elts[1])
                    details['inputs'].append(f"{input_id}.{input_prop}")
            
            # Extrahiere States
            if len(decorator.args) > 2:
                states_arg = decorator.args[2]
                if isinstance(states_arg, ast.List):
                    for elt in states_arg.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                            state_id = elt.elts[0].s if isinstance(elt.elts[0], ast.Constant) else str(elt.elts[0])
                            state_prop = elt.elts[1].s if isinstance(elt.elts[1], ast.Constant) else str(elt.elts[1])
                            details['states'].append(f"{state_id}.{state_prop}")
                elif isinstance(states_arg, ast.Tuple) and len(states_arg.elts) >= 2:
                    state_id = states_arg.elts[0].s if isinstance(states_arg.elts[0], ast.Constant) else str(states_arg.elts[0])
                    state_prop = states_arg.elts[1].s if isinstance(states_arg.elts[1], ast.Constant) else str(states_arg.elts[1])
                    details['states'].append(f"{state_id}.{state_prop}")
            
            # Extrahiere Keyword-Argumente
            for keyword in decorator.keywords:
                if keyword.arg == 'prevent_initial_call':
                    details['prevent_initial_call'] = keyword.value.value if isinstance(keyword.value, ast.Constant) else str(keyword.value)
                elif keyword.arg == 'allow_duplicate':
                    details['allow_duplicate'] = keyword.value.value if isinstance(keyword.value, ast.Constant) else str(keyword.value)
        
        return details
    
    def analyze_callback_conflicts(self, callbacks):
        """Analysiere Callback-Konflikte und Duplikate"""
        conflicts = []
        duplicates = []
        
        # Gruppiere nach Outputs
        output_groups = defaultdict(list)
        for callback in callbacks:
            for output in callback['outputs']:
                output_groups[output].append(callback)
        
        # Finde Duplikate
        for output, callback_list in output_groups.items():
            if len(callback_list) > 1:
                duplicates.append({
                    'output': output,
                    'callbacks': callback_list
                })
        
        # Finde Konflikte
        for callback in callbacks:
            # Prüfe allow_duplicate ohne prevent_initial_call
            if callback['allow_duplicate'] and callback['prevent_initial_call'] is not True:
                conflicts.append({
                    'type': 'allow_duplicate_without_prevent_initial_call',
                    'callback': callback,
                    'message': 'allow_duplicate=True erfordert prevent_initial_call=True'
                })
            
            # Prüfe zu viele Outputs
            if len(callback['outputs']) > 5:
                conflicts.append({
                    'type': 'too_many_outputs',
                    'callback': callback,
                    'message': f'Callback hat {len(callback["outputs"])} Outputs (maximal 5 empfohlen)'
                })
            
            # Prüfe fehlende Outputs
            if len(callback['outputs']) == 0:
                conflicts.append({
                    'type': 'no_outputs',
                    'callback': callback,
                    'message': 'Callback hat keine Outputs definiert'
                })
        
        return conflicts, duplicates
    
    def analyze_layout_elements(self):
        """Analysiere Layout-Elemente auf fehlende IDs"""
        layout_elements = []
        
        pages_dir = Path("pages")
        for py_file in pages_dir.glob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Suche nach HTML-Elementen mit IDs
                id_pattern = r"id=['\"]([^'\"]+)['\"]"
                ids = re.findall(id_pattern, content)
                
                for id_match in ids:
                    layout_elements.append({
                        'id': id_match,
                        'file': str(py_file)
                    })
            
            except Exception as e:
                self.warnings.append(f"Fehler beim Analysieren von {py_file}: {e}")
        
        return layout_elements
    
    def validate_all(self):
        """Führe alle Validierungen durch"""
        # Finde alle Callback-Dateien
        callback_files = self.find_callback_files()
        
        # Extrahiere alle Callbacks
        all_callbacks = []
        for file_path in callback_files:
            callbacks = self.extract_callbacks_from_file(file_path)
            all_callbacks.extend(callbacks)
        
        # Extrahiere Details
        detailed_callbacks = []
        for callback in all_callbacks:
            details = self.extract_callback_details(callback)
            detailed_callbacks.append(details)
        
        # Analysiere Konflikte
        self.conflicts, self.duplicates = self.analyze_callback_conflicts(detailed_callbacks)
        
        # Analysiere Layout-Elemente
        self.layout_elements = self.analyze_layout_elements()
        
        self.callbacks = detailed_callbacks
        
        return len(self.conflicts) + len(self.duplicates)
    
    def generate_report(self, format='text'):
        """Generiere einen Validierungsbericht"""
        if format == 'json':
            return json.dumps({
                'callbacks': self.callbacks,
                'conflicts': self.conflicts,
                'duplicates': self.duplicates,
                'warnings': self.warnings,
                'layout_elements': self.layout_elements,
                'summary': {
                    'total_callbacks': len(self.callbacks),
                    'total_conflicts': len(self.conflicts),
                    'total_duplicates': len(self.duplicates),
                    'total_warnings': len(self.warnings),
                    'total_layout_elements': len(self.layout_elements)
                }
            }, indent=2)
        
        # Text-Format
        report = []
        report.append("🔍 Projektübergreifende Callback-Validierung")
        report.append("=" * 60)
        report.append(f"📊 Gesamt: {len(self.callbacks)} Callbacks")
        report.append(f"   Layout-Elemente: {len(self.layout_elements)}")
        report.append(f"   Konflikte: {len(self.conflicts)}")
        report.append(f"   Duplikate: {len(self.duplicates)}")
        report.append(f"   Warnungen: {len(self.warnings)}")
        
        # Zeige Duplikate
        if self.duplicates:
            report.append(f"\n❌ GEFUNDENE DUPLIKATE:")
            for dup in self.duplicates:
                report.append(f"   Output: {dup['output']}")
                for cb in dup['callbacks']:
                    report.append(f"     - {cb['name']} in {cb['file']}:{cb['line']}")
        
        # Zeige Konflikte
        if self.conflicts:
            report.append(f"\n⚠️  GEFUNDENE KONFLIKTE:")
            for conflict in self.conflicts:
                cb = conflict['callback']
                report.append(f"   {conflict['type']}: {cb['name']} in {cb['file']}:{cb['line']}")
                report.append(f"     {conflict['message']}")
        
        # Zeige Warnungen
        if self.warnings:
            report.append(f"\n⚠️  WARNUNGEN:")
            for warning in self.warnings:
                report.append(f"   {warning}")
        
        # Empfehlungen
        report.append(f"\n💡 EMPFEHLUNGEN:")
        if self.duplicates:
            report.append("   1. Behebe alle Duplikate durch Umbenennung oder Konsolidierung")
        if self.conflicts:
            report.append("   2. Behebe alle Konflikte (allow_duplicate + prevent_initial_call)")
        if any(len(cb['outputs']) > 5 for cb in self.callbacks):
            report.append("   3. Teile komplexe Callbacks mit >5 Outputs auf")
        report.append("   4. Integriere diese Validierung in CI/CD")
        
        return "\n".join(report)

def main():
    validator = CallbackValidator()
    error_count = validator.validate_all()
    
    # Generiere Bericht
    report = validator.generate_report()
    print(report)
    
    # Speichere JSON-Bericht für CI/CD
    json_report = validator.generate_report('json')
    with open('callback_validation_report.json', 'w') as f:
        f.write(json_report)
    
    # Exit-Code für CI/CD
    return error_count

if __name__ == "__main__":
    sys.exit(main())
