STATEMENTS = (
    """
    create table countries (
        pk integer not null primary key autoincrement,
        name text,
        country_key text,
        id integer,
        selected boolean
    )
    """,
    """
    create table cities (
        pk integer not null primary key autoincrement,
        name text,
        city_key text,
        id integer,
        selected boolean
    )
    """,
    """
    create table times (
        pk integer not null primary key autoincrement,
        time_name text,
        from_time text,
        to_time text,
        date text,
        city_id integer,
        FOREIGN KEY(city_id) REFERENCES cities(pk)
    )
    """,
    """
    create table praying_status (
        pk integer not null primary key autoincrement,
        time_name text,
        is_prayed boolean default false,
        date text
    )
    """,
    """
    create table languages (
        pk integer not null primary key autoincrement,
        lang text,
        lang_text text,
        selected boolean default false
    )
    """,
    """
    create table rewards (
        pk integer not null primary key autoincrement,
        name text,
        count integer
    )
    """,
    "CREATE UNIQUE INDEX idx_rewards_name ON rewards (name)",
    "CREATE UNIQUE INDEX idx_languages_lang ON languages (lang)",
    "insert into rewards (name, count) select 'daily', 0 where not exists(select 1 from rewards where name='daily')",
    "insert into rewards (name, count) select 'weekly', 0 where not exists(select 1 from rewards where name='weekly')",
    "insert into rewards (name, count) select 'monthly', 0 where not exists(select 1 from rewards where name='monthly')",
    "insert into rewards (name, count) select 'yearly', 0 where not exists(select 1 from rewards where name='yearly')",
    "insert into languages (lang, lang_text) select 'tr', 'Türkçe' where not exists(select 1 from languages where lang='tr')",
    "insert into languages (lang, lang_text) select 'en', 'English' where not exists(select 1 from languages where lang='en')",
    "CREATE INDEX idx_praying_status_date_prayed ON praying_status (is_prayed, date)",
    "CREATE INDEX idx_praying_status_isprayed ON praying_status (is_prayed)",
    "CREATE INDEX idx_praying_status_date ON praying_status (date)",
    "CREATE INDEX idx_times_date ON times (date)",
    "alter table cities add column country_id int"
)
