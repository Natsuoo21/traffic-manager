-- Traffic Manager — SQLite Schema v1.0

-- Platform accounts (Meta, Google, LinkedIn)
CREATE TABLE IF NOT EXISTS platform_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    account_name    TEXT,
    is_active       INTEGER DEFAULT 1,
    last_synced_at  TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(platform, account_id)
);

-- Campaigns (normalized across all platforms)
CREATE TABLE IF NOT EXISTS campaigns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,
    platform_id     TEXT NOT NULL,
    account_id      INTEGER NOT NULL REFERENCES platform_accounts(id),
    name            TEXT NOT NULL,
    objective       TEXT,
    status          TEXT NOT NULL DEFAULT 'PAUSED',
    budget_type     TEXT,
    budget_amount   REAL,
    currency        TEXT DEFAULT 'BRL',
    start_date      TEXT,
    end_date        TEXT,
    platform_data   TEXT,
    last_synced_at  TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(platform, platform_id)
);

-- Ad Sets / Ad Groups
CREATE TABLE IF NOT EXISTS ad_sets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,
    platform_id     TEXT NOT NULL,
    campaign_id     INTEGER NOT NULL REFERENCES campaigns(id),
    name            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PAUSED',
    targeting       TEXT,
    bid_strategy    TEXT,
    budget_amount   REAL,
    budget_type     TEXT,
    platform_data   TEXT,
    last_synced_at  TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(platform, platform_id)
);

-- Individual ads
CREATE TABLE IF NOT EXISTS ads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,
    platform_id     TEXT NOT NULL,
    ad_set_id       INTEGER NOT NULL REFERENCES ad_sets(id),
    name            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PAUSED',
    creative_data   TEXT,
    preview_url     TEXT,
    platform_data   TEXT,
    last_synced_at  TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(platform, platform_id)
);

-- Daily metrics per entity
CREATE TABLE IF NOT EXISTS metrics_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    entity_id       INTEGER NOT NULL,
    date            TEXT NOT NULL,
    impressions     INTEGER DEFAULT 0,
    clicks          INTEGER DEFAULT 0,
    spend           REAL DEFAULT 0.0,
    conversions     INTEGER DEFAULT 0,
    conversion_value REAL DEFAULT 0.0,
    reach           INTEGER DEFAULT 0,
    ctr             REAL DEFAULT 0.0,
    cpc             REAL DEFAULT 0.0,
    cpm             REAL DEFAULT 0.0,
    cpa             REAL DEFAULT 0.0,
    roas            REAL DEFAULT 0.0,
    platform_metrics TEXT,
    currency        TEXT DEFAULT 'BRL',
    synced_at       TEXT DEFAULT (datetime('now')),
    UNIQUE(platform, entity_type, entity_id, date)
);

-- Alert rules
CREATE TABLE IF NOT EXISTS alert_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    platform        TEXT,
    entity_type     TEXT,
    entity_id       INTEGER,
    metric          TEXT NOT NULL,
    operator        TEXT NOT NULL,
    threshold       REAL NOT NULL,
    window_days     INTEGER DEFAULT 1,
    notify_channels TEXT DEFAULT '[]',
    is_enabled      INTEGER DEFAULT 1,
    cooldown_hours  INTEGER DEFAULT 24,
    last_triggered_at TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Triggered alerts log
CREATE TABLE IF NOT EXISTS alert_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id         INTEGER NOT NULL REFERENCES alert_rules(id),
    entity_type     TEXT NOT NULL,
    entity_id       INTEGER NOT NULL,
    metric_value    REAL NOT NULL,
    threshold       REAL NOT NULL,
    message         TEXT NOT NULL,
    notified        INTEGER DEFAULT 0,
    acknowledged    INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Sync operation log
CREATE TABLE IF NOT EXISTS sync_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,
    sync_type       TEXT NOT NULL,
    status          TEXT NOT NULL,
    entities_synced INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TEXT DEFAULT (datetime('now')),
    finished_at     TEXT,
    duration_ms     INTEGER
);

-- Generated reports
CREATE TABLE IF NOT EXISTS reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    report_type     TEXT NOT NULL,
    platforms       TEXT DEFAULT '[]',
    date_from       TEXT NOT NULL,
    date_to         TEXT NOT NULL,
    filters         TEXT,
    html_content    TEXT,
    json_data       TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_campaigns_platform ON campaigns(platform);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_account ON campaigns(account_id);
CREATE INDEX IF NOT EXISTS idx_ad_sets_campaign ON ad_sets(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ads_ad_set ON ads(ad_set_id);
CREATE INDEX IF NOT EXISTS idx_metrics_entity ON metrics_snapshots(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics_snapshots(date);
CREATE INDEX IF NOT EXISTS idx_metrics_platform_date ON metrics_snapshots(platform, date);
CREATE INDEX IF NOT EXISTS idx_metrics_lookup ON metrics_snapshots(platform, entity_type, entity_id, date);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(is_enabled);
CREATE INDEX IF NOT EXISTS idx_alert_history_rule ON alert_history(rule_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_created ON alert_history(created_at);
CREATE INDEX IF NOT EXISTS idx_sync_log_platform ON sync_log(platform, sync_type);
