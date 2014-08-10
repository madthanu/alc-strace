BEGIN;
SET LOCAL synchronous_commit TO OFF;
insert into test1 values (300);
insert into test1 values (300);
COMMIT;
