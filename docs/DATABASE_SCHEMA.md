# Datenbank-Schema (TimescaleDB / PostgreSQL)

Dieses Dokument beschreibt die aktuelle Datenbankstruktur, wie sie durch die Anwendung beim Start bzw. durch Migrationsfunktionen erstellt und gepflegt wird.

## Übersicht
- Erweiterung: `timescaledb`
- Zeitreihen-Hypertable: `measurements` (partitioniert über `ts`)
- Metadaten: `ci_metadata`
- Benutzer und OTP: `users`, `otp_codes`
- Benachrichtigungen: `notification_profiles`, `notification_logs`
- Telemetrie/Statistiken: `page_views`

---

## timescaledb Erweiterung
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

## measurements
Zeitreihen-Tabelle für Verfügbarkeitsmessungen der CIs.
```sql
CREATE TABLE IF NOT EXISTS measurements (
  ci TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  status SMALLINT NOT NULL,
  PRIMARY KEY (ci, ts)
);
SELECT create_hypertable('measurements','ts', if_not_exists => TRUE);
```

- ci: ID des Configuration Items (Text)
- ts: Zeitstempel der Messung (TIMESTAMPTZ)
- status: 1 = verfügbar, 0 = nicht verfügbar (SMALLINT)

## ci_metadata
Metadaten zu den CIs.
```sql
CREATE TABLE IF NOT EXISTS ci_metadata (
  ci TEXT PRIMARY KEY,
  name TEXT,
  organization TEXT,
  product TEXT,
  bu TEXT,
  tid TEXT,
  pdt TEXT,
  comment TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

Felder werden idempotent per UPSERT aktualisiert.

## users
Benutzerverwaltung für OTP/Benachrichtigungen.
```sql
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  email_hash TEXT NOT NULL,
  email_salt TEXT NOT NULL,
  email_encrypted TEXT,
  email_enc_salt TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login TIMESTAMPTZ,
  failed_login_attempts INTEGER DEFAULT 0,
  locked_until TIMESTAMPTZ
);
```

Index:
```sql
CREATE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash);
```

## otp_codes
Einmalpasswörter für Benutzer-Login/Bestätigung.
```sql
CREATE TABLE IF NOT EXISTS otp_codes (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  otp_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  used BOOLEAN DEFAULT FALSE,
  ip_address TEXT
);
```

Indizes:
```sql
CREATE INDEX IF NOT EXISTS idx_otp_codes_user_id ON otp_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_otp_codes_expires_at ON otp_codes(expires_at);
```

## notification_profiles
Benachrichtigungs-Profile je Benutzer.
```sql
CREATE TABLE IF NOT EXISTS notification_profiles (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('whitelist', 'blacklist')),
  ci_list TEXT[] DEFAULT '{}',
  apprise_urls TEXT[] DEFAULT '{}',
  apprise_urls_hash TEXT[],
  apprise_urls_salt TEXT[],
  email_notifications BOOLEAN DEFAULT FALSE,
  email_address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_tested_at TIMESTAMPTZ,
  test_result TEXT,
  unsubscribe_token TEXT UNIQUE
);
```

Indizes:
```sql
CREATE INDEX IF NOT EXISTS idx_notification_profiles_user_id ON notification_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_profiles_unsubscribe_token ON notification_profiles(unsubscribe_token);
```

## notification_logs
Protokolle versendeter Benachrichtigungen.
```sql
CREATE TABLE IF NOT EXISTS notification_logs (
  id SERIAL PRIMARY KEY,
  profile_id INTEGER REFERENCES notification_profiles(id) ON DELETE CASCADE,
  ci TEXT NOT NULL,
  notification_type TEXT NOT NULL CHECK (notification_type IN ('incident', 'recovery')),
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  delivery_status TEXT DEFAULT 'sent' CHECK (delivery_status IN ('sent', 'failed', 'pending')),
  error_message TEXT,
  recipient_type TEXT CHECK (recipient_type IN ('email', 'apprise')),
  recipient_count INTEGER DEFAULT 1
);
```

Indizes:
```sql
CREATE INDEX IF NOT EXISTS idx_notification_logs_sent_at ON notification_logs(sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_logs_profile_ci ON notification_logs(profile_id, ci);
CREATE INDEX IF NOT EXISTS idx_notification_logs_type_status ON notification_logs(notification_type, delivery_status);
```

## page_views
Einfache Telemetrie zu Seitenaufrufen der App.
```sql
CREATE TABLE IF NOT EXISTS page_views (
  id SERIAL PRIMARY KEY,
  page TEXT NOT NULL,
  session_id TEXT NOT NULL,
  user_agent_hash TEXT,
  referrer TEXT,
  ts TIMESTAMPTZ DEFAULT NOW()
);
```

Indizes:
```sql
CREATE INDEX IF NOT EXISTS idx_page_views_ts ON page_views(ts);
CREATE INDEX IF NOT EXISTS idx_page_views_page ON page_views(page);
CREATE INDEX IF NOT EXISTS idx_page_views_session ON page_views(session_id);
```

---

## Hinweise zur Pflege
- Alle CREATE/ALTER Befehle sind idempotent umgesetzt.
- Retention (Beispiel): `SELECT add_retention_policy('measurements', INTERVAL '185 days', if_not_exists => TRUE);`
- Continuous Aggregates können bei Bedarf ergänzt werden.
- DB-Verbindungsparameter werden ausschließlich über Umgebungsvariablen geladen (`POSTGRES_*`).
