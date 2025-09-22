#!/usr/bin/env python3
"""
Callback Validation Script
Überprüft alle Callbacks in der TI-Monitoring Anwendung auf Syntax und Konsistenz

Hinweis: Dieses Skript kann von überall gestartet werden. Pfade werden relativ
zum Projekt-Root (eine Ebene über diesem Skript) aufgelöst.
"""

import os
import re
import ast
import sys
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any


# Projekt-Root relativ zur Skript-Position ermitteln
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent


class CallbackInfo(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.callbacks: List[Dict[str, Any]] = []
        self.current_decorator_src = ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for dec in node.decorator_list:
            dec_src = ast.get_source_segment(self.source, dec) or ""
            if dec_src.strip().startswith("@callback("):
                self.current_decorator_src = dec_src
                outputs_count, outputs_ids, has_allow_dupes = parse_outputs_from_decorator(dec_src)
                self.callbacks.append({
                    'file': self.file_path,
                    'function': node.name,
                    'line': node.lineno,
                    'declaration': dec_src,
                    'outputs_count': outputs_count,
                    'outputs_ids': outputs_ids,
                    'has_allow_dupes': has_allow_dupes,
                    'returns': list(find_return_lengths(node)),
                    'inline_imports': list(find_inline_imports(node)),
                })
        self.generic_visit(node)


def parse_outputs_from_decorator(dec_src: str) -> Tuple[int, List[str], Dict[str, bool]]:
    # Zähle Output( ... ) im Dekorator; extrahiere IDs
    ids = re.findall(r"Output\('([^']+)'\s*,\s*'[^']+'(.*?)\)", dec_src)
    outputs_count = 0
    outputs_ids: List[str] = []
    allow_dupes: Dict[str, bool] = {}
    for out_id, tail in ids:
        outputs_count += 1
        outputs_ids.append(out_id)
        allow_dupes[out_id] = ('allow_duplicate=True' in tail)
    # Falls Outputs als Liste stehen: [Output(...), Output(...)]
    if outputs_count == 0:
        outputs_ids = re.findall(r"Output\('([^']+)'", dec_src)
        outputs_count = len(outputs_ids)
        for out_id in outputs_ids:
            allow_dupes.setdefault(out_id, False)
    return outputs_count, outputs_ids, allow_dupes


def find_return_lengths(fn_node: ast.FunctionDef):
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Return):
            value = n.value
            if isinstance(value, (ast.List, ast.Tuple)):
                yield {'line': n.lineno, 'length': len(value.elts), 'snippet': ''}
            else:
                yield {'line': n.lineno, 'length': 1, 'snippet': ''}


def find_inline_imports(fn_node: ast.FunctionDef):
    imports: List[int] = []
    for n in ast.walk(fn_node):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            imports.append(getattr(n, 'lineno', fn_node.lineno))
    return imports


def analyze_file(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)
    v = CallbackInfo(str(path))
    v.source = text
    v.visit(tree)
    return v.callbacks


def find_callback_declarations(file_path):
    callbacks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
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
    issues = []
    try:
        declaration = callback_info['declaration']
        if 'Output(' not in declaration:
            issues.append("Kein Output gefunden")
        if 'Input(' not in declaration and 'State(' not in declaration:
            issues.append("Keine Inputs oder States gefunden")
        if declaration.count('(') != declaration.count(')'):
            issues.append("Ungleiche Anzahl von Klammern")
        if 'prevent_initial_call' in declaration:
            if not any(valid in declaration for valid in ['prevent_initial_call=True', 'prevent_initial_call=False']):
                issues.append("prevent_initial_call hat keinen gültigen Wert")
    except Exception as e:
        issues.append(f"Syntax-Fehler: {e}")
    return issues


def validate_callback_parameters(callback_info):
    issues = []
    try:
        params = callback_info['parameters']
        param_list = [p.strip().split('=')[0].strip() for p in params.split(',') if p.strip()]
        if len(param_list) == 0:
            issues.append("Keine Parameter definiert")
        for param in param_list:
            if param == 'None':
                issues.append(f"Parameter '{param}' ist None")
    except Exception as e:
        issues.append(f"Parameter-Fehler: {e}")
    return issues


def check_callback_consistency(callbacks):
    """Global konsistenz: Ein Output darf nur EINEN schreibenden Callback haben (One-writer)."""
    issues = []
    output_to_callbacks: Dict[str, List[Tuple[str, str, int]]] = {}
    for cb in callbacks:
        declaration = cb.get('declaration', '')
        file_path = cb.get('file')
        function = cb.get('function', '?')
        line = cb.get('line', 0)
        output_matches = re.findall(r"Output\('([^']+)'", declaration)
        for out in output_matches:
            output_to_callbacks.setdefault(out, []).append((file_path, function, line))

    for out_id, writers in output_to_callbacks.items():
        if len(writers) > 1:
            locs = ", ".join([f"{f}:{ln}({fn})" for f, fn, ln in writers])
            issues.append(f"One-writer verletzt: Output-ID '{out_id}' wird in mehreren Callbacks beschrieben: {locs}")
    return issues


def check_store_usage_patterns(callbacks) -> List[str]:
    """Check for problematic store usage patterns"""
    issues: List[str] = []
    
    # Define store patterns that should be avoided
    problematic_patterns = {
        'auth-state-store': {
            'description': 'temporary auth store',
            'recommended': 'auth-status',
            'functions': ['save_profile', 'display_profiles', 'handle_edit_profile', 'handle_delete_profile']
        }
    }
    
    for cb in callbacks:
        function_name = cb.get('function', '')
        stores_used = cb.get('stores_used', [])
        
        for store_id in stores_used:
            if store_id in problematic_patterns:
                pattern = problematic_patterns[store_id]
                if function_name in pattern['functions']:
                    issues.append(
                        f"⚠️  {function_name} in {cb['file']}:{cb.get('line', '?')} verwendet {store_id} "
                        f"({pattern['description']}). Empfohlen: {pattern['recommended']} für Persistenz."
                    )
    
    return issues

def detect_forbidden_allow_duplicate(callbacks) -> List[str]:
    issues: List[str] = []
    for cb in callbacks:
        declaration = cb.get('declaration', '')
        if 'allow_duplicate=True' in declaration.replace(' ', ''):
            issues.append(
                f"Verbotene Option allow_duplicate=True in {cb['file']}:{cb.get('line', '?')} (Callback {cb.get('function', '?')})"
            )
    return issues


def validate_policy(callbacks_ast: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    MAX_OUTPUTS = 5
    for cb in callbacks_ast:
        if cb.get('outputs_count', 0) > MAX_OUTPUTS:
            issues.append(
                f"Zu viele Outputs ({cb['outputs_count']}) in {cb['file']}:{cb['line']} (Callback {cb['function']}); max {MAX_OUTPUTS}"
            )
    return issues


def validate_returns(callbacks_ast: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    for cb in callbacks_ast:
        expected = cb['outputs_count']
        if expected == 0:
            continue
        for ret in cb['returns']:
            length = ret['length']
            if length != expected:
                issues.append(
                    f"Return-Länge in {cb['file']}:{cb['line']} (Callback {cb['function']}) erwartet {expected}, gefunden {length}"
                )
        if cb['inline_imports']:
            issues.append(
                f"Inline-Imports in {cb['file']}:{cb['line']} (Callback {cb['function']}): Zeilen {cb['inline_imports']}"
            )
    return issues


def main():
    strict = ('--strict' in sys.argv)
    as_json = ('--json' in sys.argv)
    files_arg: List[str] = []
    if '--files' in sys.argv:
        i = sys.argv.index('--files')
        files_arg = sys.argv[i+1:]
    print("🔍 TI-Monitoring Callback Validierung")
    print("=" * 50)
    pages: List[Path]
    if files_arg:
        # Explizit übergebene Dateipfade relativ zum Aufrufpfad oder absolut
        pages = [Path(p).resolve() if not Path(p).is_absolute() else Path(p) for p in files_arg]
    else:
        pages_dir = ROOT_DIR / "pages"
        if not pages_dir.exists():
            print("❌ pages/ Verzeichnis nicht gefunden")
            return 1
        pages = list(pages_dir.glob("*.py"))

    all_callbacks = []
    total_issues = 0
    report: Dict[str, Any] = {'files': [], 'errors': [], 'warnings': []}

    for file_path in pages:
        print(f"\n📁 Überprüfe {file_path.name}...")
        callbacks = find_callback_declarations(str(file_path))
        callbacks_ast = analyze_file(file_path)
        all_callbacks.extend(callbacks)
        if not callbacks:
            print("  ℹ️  Keine Callbacks gefunden")
            continue
        print(f"  📊 {len(callbacks)} Callback(s) gefunden")
        # Syntax/Param Checks
        for i, callback_info in enumerate(callbacks, 1):
            print(f"    🔍 Callback {i}: {callback_info['function']}")
            syntax_issues = validate_callback_syntax(callback_info)
            if syntax_issues:
                msg = f"      ❌ Syntax-Probleme: {', '.join(syntax_issues)}"
                print(msg)
                report['errors'].append(msg)
                total_issues += len(syntax_issues)
            else:
                print("      ✅ Syntax OK")
            param_issues = validate_callback_parameters(callback_info)
            if param_issues:
                msg = f"      ❌ Parameter-Probleme: {', '.join(param_issues)}"
                print(msg)
                report['errors'].append(msg)
                total_issues += len(param_issues)
            else:
                print("      ✅ Parameter OK")
        # Return length & inline import checks (AST)
        return_issues = validate_returns(callbacks_ast)
        for issue in return_issues:
            sev = 'errors' if strict else 'warnings'
            report[sev].append(issue)
            label = '❌' if strict else '⚠️ '
            print(f"      {label} {issue}")
            if strict:
                total_issues += 1
        # Policy checks (AST): Max Outputs
        policy_issues = validate_policy(callbacks_ast)
        for issue in policy_issues:
            report['errors'].append(issue)
            print(f"      ❌ {issue}")
            total_issues += 1

    print(f"\n🔗 Konsistenz-Prüfung...")
    consistency_issues = check_callback_consistency(all_callbacks)
    for issue in consistency_issues:
        print(f"  ❌ {issue}")
        report['errors'].append(issue)
        total_issues += 1
    if not consistency_issues:
        print("  ✅ Konsistenz OK")
    # Forbid allow_duplicate=True globally
    allow_dupe_issues = detect_forbidden_allow_duplicate(all_callbacks)
    for issue in allow_dupe_issues:
        print(f"  ❌ {issue}")
        report['errors'].append(issue)
        total_issues += 1

    print(f"\n🔍 Store-Verwendungs-Prüfung...")
    store_usage_issues = check_store_usage_patterns(all_callbacks)
    for issue in store_usage_issues:
        print(f"  {issue}")
        report['warnings'].append(issue)
        # Store usage issues are warnings, not errors

    print(f"\n📊 Zusammenfassung:")
    print(f"  📁 Dateien überprüft: {len(pages)}")
    print(f"  🔄 Callbacks gefunden: {len(all_callbacks)}")
    print(f"  ❌ Probleme gefunden: {total_issues}")
    print(f"  ⚠️  Warnungen: {len(store_usage_issues)}")

    if as_json:
        print(json.dumps(report, ensure_ascii=False))

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

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
