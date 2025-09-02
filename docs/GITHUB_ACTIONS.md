# GitHub Actions - Automatische Releases

Dieses Repository verwendet GitHub Actions für automatische portable Windows-Builds und Releases.

## 🚀 Workflows

### 1. Automatische Releases (`release.yml`)
**Trigger**: Git Tags (z.B. `v1.2.3`)

```bash
# Release erstellen
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

**Was passiert:**
1. ✅ Tests ausführen
2. ✅ Portable Build erstellen
3. ✅ GitHub Release mit ZIP-Asset erstellen
4. ✅ Automatische Release Notes generieren

### 2. Manuelle Releases (`manual-release.yml`)
**Trigger**: GitHub Actions UI → "Run workflow"

**Parameter:**
- `version`: Version (z.B. 1.2.3)
- `prerelease`: Als Pre-Release erstellen (Standard: true)
- `create_tag`: Git Tag erstellen (Standard: true)

### 3. Einfacher Build (`build-portable.yml`)
**Trigger**: Git Tags oder manuell

Nur Build ohne Tests - für schnelle Releases.

## 📋 Voraussetzungen

### Repository Secrets
Keine zusätzlichen Secrets erforderlich - verwendet `GITHUB_TOKEN`.

### GitHub CLI (optional)
Für lokale Tests:
```bash
# GitHub CLI installieren
winget install GitHub.cli

# Authentifizieren
gh auth login
```

## 🔧 Lokale Entwicklung

### Portable Build testen
```powershell
# Build wird automatisch in GitHub Actions erstellt
# Release publizieren (automatisch via GitHub Actions)
# Erstelle Git Tag: git tag -a v1.2.3 -m "Release v1.2.3"
# Push Tag: git push origin v1.2.3
```

### Workflow testen
```bash
# Workflow lokal testen (mit act)
act -j build-portable
```

## 📊 Release-Strategien

### 1. Semantische Versionierung
- `v1.2.3` → Final Release
- `v1.2.3-alpha.1` → Pre-Release
- `v1.2.3-beta.1` → Pre-Release
- `v1.2.3-rc.1` → Pre-Release

### 2. Branch-Strategie
- `main` → Stabile Releases
- `develop` → Pre-Releases
- `feature/*` → Feature-Entwicklung

### 3. Automatische Pre-Releases
Tags mit `alpha`, `beta`, `rc` werden automatisch als Pre-Release markiert.

## 🛠️ Workflow-Anpassungen

### Tests hinzufügen
```yaml
- name: Run Tests
  run: |
    python -m pytest tests/
    python -m flake8 .
    python -m mypy .
```

### Code-Qualität
```yaml
- name: Code Quality
  run: |
    python -m black --check .
    python -m isort --check-only .
```

### Sicherheit
```yaml
- name: Security Scan
  uses: github/super-linter@v4
  env:
    DEFAULT_BRANCH: main
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 📈 Monitoring

### Workflow-Status
- GitHub Actions Tab → Workflow-Status
- Release-Seite → Download-Statistiken
- Insights → Traffic → Releases

### Benachrichtigungen
- GitHub Notifications für Workflow-Fehler
- E-Mail-Benachrichtigungen für Releases
- Slack/Discord-Integration möglich

## 🔍 Troubleshooting

### Häufige Probleme

1. **Workflow schlägt fehl**
   ```bash
   # Logs prüfen
   GitHub Actions → Workflow → Job → Step
   ```

2. **Release wird nicht erstellt**
   ```bash
   # Tag prüfen
   git tag -l
   git push origin --tags
   ```

3. **ZIP-Datei fehlt**
   ```bash
   # Build wird automatisch in GitHub Actions erstellt
   # Lokaler Test nicht mehr nötig - alles läuft in der Cloud
   ```

### Debug-Modus
```yaml
- name: Debug Info
  run: |
    echo "Python Version: $(python --version)"
    echo "PowerShell Version: $(pwsh --version)"
    echo "Git Version: $(git --version)"
    echo "Working Directory: $(pwd)"
    echo "Files: $(ls -la)"
```

## 📚 Weitere Ressourcen

- [GitHub Actions Dokumentation](https://docs.github.com/en/actions)
- [PowerShell in GitHub Actions](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#using-powershell)
- [Release Management](https://docs.github.com/en/repositories/releasing-projects-on-github)
