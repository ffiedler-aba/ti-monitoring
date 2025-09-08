#!/usr/bin/env python3
"""
Callback Validation Script
Überprüft alle Callbacks in der TI-Monitoring Anwendung auf Syntax und Konsistenz
"""

import os
import re
import ast
import sys
from pathlib import Path

def find_callback_declarations(file_path):
    """Findet alle Callback-Deklarationen in einer Datei"""
    callbacks = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Suche nach @callback Deklarationen
        callback_pattern = r'@callback\s*\((.*?)\)\s*\n\s*def\s+(\w+)\s*\((.*?)\):'
        matches = re.finditer(callback_pattern, content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            callback_declaration = match.group(1)
            function_name = match.group(2)
            parameters = match.group(3)
            
            callbacks.append({
                'file': file_path,
                'function': function_name,
                'declaration': callback_declaration,
                'parameters': parameters,
                'line': content[:match.start()].count('\n') + 1
            })
            
    except Exception as e:
        print(f"❌ Fehler beim Lesen von {file_path}: {e}")
        
    return callbacks

def validate_callback_syntax(callback_info):
    """Validiert die Syntax eines Callbacks"""
    issues = []
    
    try:
        # Parse die Callback-Deklaration
        declaration = callback_info['declaration']
        
        # Prüfe auf Output/Input/State Struktur
        if 'Output(' not in declaration:
            issues.append("Kein Output gefunden")
            
        if 'Input(' not in declaration and 'State(' not in declaration:
            issues.append("Keine Inputs oder States gefunden")
            
        # Prüfe auf häufige Syntax-Fehler
        if declaration.count('(') != declaration.count(')'):
            issues.append("Ungleiche Anzahl von Klammern")
            
        if 'prevent_initial_call' in declaration:
            # Prüfe ob prevent_initial_call korrekt gesetzt ist
            if not any(valid in declaration for valid in ['prevent_initial_call=True', 'prevent_initial_call=False']):
                issues.append("prevent_initial_call hat keinen gültigen Wert")
                
    except Exception as e:
        issues.append(f"Syntax-Fehler: {e}")
        
    return issues

def validate_callback_parameters(callback_info):
    """Validiert die Parameter eines Callbacks"""
    issues = []
    
    try:
        # Parse Parameter
        params = callback_info['parameters']
        param_list = [p.strip().split('=')[0].strip() for p in params.split(',') if p.strip()]
        
        # Prüfe auf häufige Parameter-Probleme
        if len(param_list) == 0:
            issues.append("Keine Parameter definiert")
            
        # Prüfe auf None-Parameter
        for param in param_list:
            if param == 'None':
                issues.append(f"Parameter '{param}' ist None")
                
    except Exception as e:
        issues.append(f"Parameter-Fehler: {e}")
        
    return issues

def check_callback_consistency(callbacks):
    """Prüft die Konsistenz zwischen Callbacks"""
    issues = []
    
    # Gruppiere Callbacks nach Datei
    by_file = {}
    for cb in callbacks:
        file_path = cb['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(cb)
    
    # Prüfe jede Datei
    for file_path, file_callbacks in by_file.items():
        # Prüfe auf doppelte Output-IDs (ohne allow_duplicate)
        outputs = []
        for cb in file_callbacks:
            # Extrahiere Output-IDs
            declaration = cb['declaration']
            output_matches = re.findall(r"Output\('([^']+)'", declaration)
            
            # Prüfe ob allow_duplicate=True verwendet wird
            for match in output_matches:
                # Finde den vollständigen Output-Block für diese ID
                output_pattern = rf"Output\('{re.escape(match)}'[^)]*\)"
                output_blocks = re.findall(output_pattern, declaration)
                
                has_allow_duplicate = any('allow_duplicate=True' in block for block in output_blocks)
                if not has_allow_duplicate:
                    outputs.append(match)
            
        # Prüfe auf Duplikate (nur ohne allow_duplicate)
        seen_outputs = set()
        for output in outputs:
            if output in seen_outputs:
                issues.append(f"Duplikate Output-ID '{output}' in {file_path} (ohne allow_duplicate=True)")
            seen_outputs.add(output)
    
    return issues

def main():
    """Hauptfunktion für Callback-Validierung"""
    print("🔍 TI-Monitoring Callback Validierung")
    print("=" * 50)
    
    # Finde alle Python-Dateien in pages/
    pages_dir = Path("pages")
    if not pages_dir.exists():
        print("❌ pages/ Verzeichnis nicht gefunden")
        return
        
    python_files = list(pages_dir.glob("*.py"))
    
    all_callbacks = []
    total_issues = 0
    
    # Überprüfe jede Datei
    for file_path in python_files:
        print(f"\n📁 Überprüfe {file_path.name}...")
        
        callbacks = find_callback_declarations(file_path)
        all_callbacks.extend(callbacks)
        
        if not callbacks:
            print("  ℹ️  Keine Callbacks gefunden")
            continue
            
        print(f"  📊 {len(callbacks)} Callback(s) gefunden")
        
        # Validiere jeden Callback
        for i, callback_info in enumerate(callbacks, 1):
            print(f"    🔍 Callback {i}: {callback_info['function']}")
            
            # Syntax-Validierung
            syntax_issues = validate_callback_syntax(callback_info)
            if syntax_issues:
                print(f"      ❌ Syntax-Probleme: {', '.join(syntax_issues)}")
                total_issues += len(syntax_issues)
            else:
                print(f"      ✅ Syntax OK")
                
            # Parameter-Validierung
            param_issues = validate_callback_parameters(callback_info)
            if param_issues:
                print(f"      ❌ Parameter-Probleme: {', '.join(param_issues)}")
                total_issues += len(param_issues)
            else:
                print(f"      ✅ Parameter OK")
    
    # Konsistenz-Prüfung
    print(f"\n🔗 Konsistenz-Prüfung...")
    consistency_issues = check_callback_consistency(all_callbacks)
    if consistency_issues:
        for issue in consistency_issues:
            print(f"  ❌ {issue}")
        total_issues += len(consistency_issues)
    else:
        print("  ✅ Konsistenz OK")
    
    # Zusammenfassung
    print(f"\n📊 Zusammenfassung:")
    print(f"  📁 Dateien überprüft: {len(python_files)}")
    print(f"  🔄 Callbacks gefunden: {len(all_callbacks)}")
    print(f"  ❌ Probleme gefunden: {total_issues}")
    
    if total_issues == 0:
        print("  🎉 Alle Callbacks sind korrekt!")
        return 0
    else:
        print("  ⚠️  Es wurden Probleme gefunden, die behoben werden sollten.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
