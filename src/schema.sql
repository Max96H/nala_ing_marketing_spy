PRAGMA foreign_keys = ON;

-- 1. Main Pages Table
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank TEXT NOT NULL,
    page_url TEXT NOT NULL UNIQUE,
    page_type TEXT,
    language TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')), -- Fixed initial insert date
    scrape_date TIMESTAMP DEFAULT (datetime('now', 'localtime')), -- Updated on every change
    headline TEXT,
    subtitle TEXT,
    tone TEXT,
    value_proposition TEXT,
    has_numeric_offer INTEGER CHECK (has_numeric_offer IN (0, 1)),
    cta_text TEXT,
    cta_count INTEGER,
    image_count INTEGER,
    raw_text TEXT,
    screenshot_path TEXT,
    source_type TEXT
);

-- 2. Topics Table (Junction)
CREATE TABLE IF NOT EXISTS page_topics (
    page_id INTEGER,
    topic TEXT NOT NULL,
    PRIMARY KEY (page_id, topic),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);

-- 3. Colors Table (Junction)
CREATE TABLE IF NOT EXISTS page_colors (
    page_id INTEGER,
    color_hex TEXT NOT NULL,
    PRIMARY KEY (page_id, color_hex),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);

-- 4. Trigger to automatically update scrape_date whenever a row is modified
CREATE TRIGGER IF NOT EXISTS update_pages_scrape_date
AFTER UPDATE ON pages
FOR EACH ROW
BEGIN
    UPDATE pages 
    SET scrape_date = (datetime('now', 'localtime')) 
    WHERE id = OLD.id;
END;