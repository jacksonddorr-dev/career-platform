-- Prints one "table md5" line per public table and one "seq:name last_value" line per sequence.
-- Run: psql "<connection>" -tA -F' ' -f scripts/db_fingerprint.sql
-- collate "C" makes the row order identical on servers with different default collations.
select format('select %L, md5(coalesce(string_agg(r::text, %L order by r::text collate "C"), %L)) from %I.%I r',
              table_name, E'\n', '', table_schema, table_name)
from information_schema.tables
where table_type = 'BASE TABLE' and table_schema = 'public'
order by table_name \gexec
select 'seq:' || sequencename, coalesce(last_value::text, 'null') from pg_sequences where schemaname = 'public' order by 1;
