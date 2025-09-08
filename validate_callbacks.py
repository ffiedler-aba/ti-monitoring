#!/usr/bin/env python3
"""
Callback Validation Script
Überprüft alle Callbacks in der TI-Monitoring Anwendung auf Syntax und Konsistenz
"""

import os
import re
import ast
import sys
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any


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
    issues = []
    by_file = {}
    for cb in callbacks:
        file_path = cb['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(cb)
    for file_path, file_callbacks in by_file.items():
        outputs = []
        dupe_map: Dict[str, List[Dict[str, Any]]]= {}
        for cb in file_callbacks:
            declaration = cb.get('declaration', '')
            output_matches = re.findall(r"Output\('([^']+)'", declaration)
            for out in output_matches:
                dupe_map.setdefault(out, []).append(cb)
            for match in output_matches:
                output_pattern = rf"Output\('{re.escape(match)}'[^)]*\)"
                output_blocks = re.findall(output_pattern, declaration)
                has_allow_duplicate = any('allow_duplicate=True' in block for block in output_blocks)
                if not has_allow_duplicate:
                    outputs.append(match)
        seen_outputs = set()
        for output in outputs:
            if output in seen_outputs:
                issues.append(f"Duplikate Output-ID '{output}' in {file_path} (ohne allow_duplicate=True)")
            seen_outputs.add(output)
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
        pages = [Path(p) for p in files_arg]
    else:
        pages_dir = Path("pages")
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

    print(f"\n🔗 Konsistenz-Prüfung...")
    consistency_issues = check_callback_consistency(all_callbacks)
    for issue in consistency_issues:
        print(f"  ❌ {issue}")
        report['errors'].append(issue)
        total_issues += 1
    if not consistency_issues:
        print("  ✅ Konsistenz OK")

    print(f"\n📊 Zusammenfassung:")
    print(f"  📁 Dateien überprüft: {len(pages)}")
    print(f"  🔄 Callbacks gefunden: {len(all_callbacks)}")
    print(f"  ❌ Probleme gefunden: {total_issues}")

    if as_json:
        print(json.dumps(report, ensure_ascii=False))

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
