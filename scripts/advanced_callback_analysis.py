#!/usr/bin/env python3
"""
Erweiterte Callback-Analyse für TI-Monitoring
Sucht nach Duplikaten, Konflikten und Problemen in der Callback-Architektur
"""

import os
import re
import ast
import sys
from collections import defaultdict, Counter
from pathlib import Path

def find_callback_files():
    """Finde alle Python-Dateien mit Callbacks"""
    pages_dir = Path("pages")
    callback_files = []
    
    for py_file in pages_dir.glob("*.py"):
        if py_file.name != "__init__.py":
            callback_files.append(py_file)
    
    return callback_files

def extract_callbacks_from_file(file_path):
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
        print(f"Fehler beim Parsen von {file_path}: {e}")
    
    return callbacks

def extract_callback_details(callback):
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
        
        # Extrahiere Inputs
        if len(decorator.args) > 1:
            inputs_arg = decorator.args[1]
            if isinstance(inputs_arg, ast.List):
                for elt in inputs_arg.elts:
                    if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                        input_id = elt.elts[0].s if isinstance(elt.elts[0], ast.Constant) else str(elt.elts[0])
                        input_prop = elt.elts[1].s if isinstance(elt.elts[1], ast.Constant) else str(elt.elts[1])
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
        
        # Extrahiere Keyword-Argumente
        for keyword in decorator.keywords:
            if keyword.arg == 'prevent_initial_call':
                details['prevent_initial_call'] = keyword.value.value if isinstance(keyword.value, ast.Constant) else str(keyword.value)
            elif keyword.arg == 'allow_duplicate':
                details['allow_duplicate'] = keyword.value.value if isinstance(keyword.value, ast.Constant) else str(keyword.value)
    
    return details

def analyze_callback_conflicts(callbacks):
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
    
    return conflicts, duplicates

def analyze_layout_elements():
    """Analysiere Layout-Elemente auf fehlende IDs"""
    layout_elements = []
    missing_ids = []
    
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
            print(f"Fehler beim Analysieren von {py_file}: {e}")
    
    return layout_elements

def main():
    print("🔍 Erweiterte Callback-Analyse für TI-Monitoring")
    print("=" * 60)
    
    # Finde alle Callback-Dateien
    callback_files = find_callback_files()
    print(f"📁 Gefundene Dateien: {len(callback_files)}")
    
    # Extrahiere alle Callbacks
    all_callbacks = []
    for file_path in callback_files:
        callbacks = extract_callbacks_from_file(file_path)
        all_callbacks.extend(callbacks)
        print(f"📄 {file_path.name}: {len(callbacks)} Callback(s)")
    
    print(f"\n📊 Gesamt: {len(all_callbacks)} Callbacks")
    
    # Extrahiere Details
    detailed_callbacks = []
    for callback in all_callbacks:
        details = extract_callback_details(callback)
        detailed_callbacks.append(details)
    
    # Analysiere Konflikte
    conflicts, duplicates = analyze_callback_conflicts(detailed_callbacks)
    
    # Analysiere Layout-Elemente
    layout_elements = analyze_layout_elements()
    
    print(f"\n🔍 Analyse-Ergebnisse:")
    print(f"   Layout-Elemente: {len(layout_elements)}")
    print(f"   Konflikte: {len(conflicts)}")
    print(f"   Duplikate: {len(duplicates)}")
    
    # Zeige Duplikate
    if duplicates:
        print(f"\n❌ GEFUNDENE DUPLIKATE:")
        for dup in duplicates:
            print(f"   Output: {dup['output']}")
            for cb in dup['callbacks']:
                print(f"     - {cb['name']} in {cb['file']}:{cb['line']}")
    
    # Zeige Konflikte
    if conflicts:
        print(f"\n⚠️  GEFUNDENE KONFLIKTE:")
        for conflict in conflicts:
            cb = conflict['callback']
            print(f"   {conflict['type']}: {cb['name']} in {cb['file']}:{cb['line']}")
            print(f"     {conflict['message']}")
    
    # Zeige Callback-Übersicht
    print(f"\n📋 CALLBACK-ÜBERSICHT:")
    for cb in detailed_callbacks:
        print(f"   {cb['name']} ({cb['file']}:{cb['line']})")
        print(f"     Outputs: {len(cb['outputs'])} - {', '.join(cb['outputs'])}")
        print(f"     Inputs: {len(cb['inputs'])} - {', '.join(cb['inputs'])}")
        if cb['states']:
            print(f"     States: {len(cb['states'])} - {', '.join(cb['states'])}")
        if cb['allow_duplicate']:
            print(f"     ⚠️  allow_duplicate=True")
        if cb['prevent_initial_call'] is not None:
            print(f"     prevent_initial_call={cb['prevent_initial_call']}")
        print()
    
    # Empfehlungen
    print(f"\n💡 EMPFEHLUNGEN:")
    if duplicates:
        print("   1. Behebe alle Duplikate durch Umbenennung oder Konsolidierung")
    if conflicts:
        print("   2. Behebe alle Konflikte (allow_duplicate + prevent_initial_call)")
    if any(len(cb['outputs']) > 5 for cb in detailed_callbacks):
        print("   3. Teile komplexe Callbacks mit >5 Outputs auf")
    print("   4. Implementiere eine automatische Validierung in CI/CD")
    
    return len(conflicts) + len(duplicates)

if __name__ == "__main__":
    sys.exit(main())
