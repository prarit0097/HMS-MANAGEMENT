"""Dormant rate schema only: no admission, grant, API or runtime quota claims."""
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import subprocess
import sys

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, migrations, models, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.writer import MigrationWriter
from django.db.models.deletion import ProtectedError
from django.db.models.fields import NOT_PROVIDED
from django.db.utils import NotSupportedError

MODEL = 'DocumentMetadataRateWindow'
MIGRATION = ('core', '0009_document_metadata_rate_window')
OLD = [('core', '0008_patient_document_foundation')]
MINUTE = datetime(2026, 10, 26, 3, 36, tzinfo=dt_timezone.utc)
GUARD_ERROR = 'Document metadata rate reversal requires an empty table; preserve limiter state.'


def rate_model():
    found = next((m for m in apps.get_app_config('core').get_models() if m.__name__ == MODEL), None)
    assert found is not None, f'{MODEL} must be registered by core model discovery'
    return found


def minute_expression():
    module = import_module('apps.core.document_models')
    found = getattr(module, 'DocumentMetadataMinuteAligned', None)
    assert found is not None, 'Permanent DocumentMetadataMinuteAligned expression is absent'
    return found


def actor_field_class():
    found = getattr(import_module('apps.core.document_models'), 'DocumentMetadataActorField', None)
    assert found is not None, 'Permanent DocumentMetadataActorField is absent'
    return found


def rate_migration():
    spec = import_module('importlib.util').find_spec('apps.core.migrations.' + MIGRATION[1])
    assert spec is not None, 'Additive document metadata rate migration0009 is absent'
    return import_module(spec.name)


@pytest.fixture
def actor(db):
    return get_user_model().objects.create(username='synthetic-rate-actor')


def create(rate_actor, **changes):
    values = dict(actor=rate_actor, window_started_at=MINUTE, admitted_count=1)
    values.update(changes)
    return rate_model().objects.create(**values)


def raw_insert(actor_id, timestamp=MINUTE, count=1):
    # Valid datetimes use the real backend adapter; malformed strings deliberately do not.
    if isinstance(timestamp, datetime):
        timestamp = connection.ops.adapt_datetimefield_value(timestamp)
    with connection.cursor() as cursor:
        cursor.execute(f'INSERT INTO {connection.ops.quote_name(rate_model()._meta.db_table)} '
                       '(actor_id, window_started_at, admitted_count) VALUES (%s, %s, %s)',
                       [actor_id, timestamp, count])


def raw_update(actor_id, timestamp):
    with connection.cursor() as cursor:
        cursor.execute(f'UPDATE {connection.ops.quote_name(rate_model()._meta.db_table)} '
                       'SET window_started_at = %s WHERE actor_id = %s', [timestamp, actor_id])


def rejects(write):
    # Force deferred FK constraints inside the bounded savepoint, not at teardown.
    with pytest.raises(DatabaseError), transaction.atomic():
        write()
        connection.check_constraints()


def test_rate_window_model_is_discovered_with_exact_fields():
    model = rate_model()
    assert apps.get_model('core', MODEL) is model
    assert model.__module__ == 'apps.core.document_models'
    fields = model._meta.local_fields
    assert [f.name for f in fields] == ['actor', 'window_started_at', 'admitted_count']
    actor_field, timestamp, count = fields
    assert type(actor_field) is actor_field_class()
    assert isinstance(actor_field, models.OneToOneField) and actor_field.primary_key
    assert actor_field.remote_field.model is get_user_model()
    assert actor_field.remote_field.on_delete is models.PROTECT
    assert actor_field.remote_field.related_name == '+'
    assert isinstance(timestamp, models.DateTimeField)
    assert not timestamp.auto_now and not timestamp.auto_now_add
    assert type(count) is models.PositiveSmallIntegerField
    for field in fields:
        assert not field.null and field.default is NOT_PROVIDED and field.db_default is NOT_PROVIDED
    assert [c.name for c in model._meta.constraints] == ['doc_metadata_rate_count', 'doc_metadata_rate_minute']
    assert model._meta.indexes == [] and model._meta.ordering == []
    assert model._meta.unique_together == ()


@pytest.mark.parametrize('vendor,parent,expected', [
    ('sqlite', 'integer', 'bigint'), ('sqlite', 'INTEGER', 'bigint'),
    ('sqlite', 'bigint', 'bigint'), ('sqlite', 'varchar(36)', 'varchar(36)'),
    ('sqlite', None, None), ('sqlite', 7, 7), ('postgresql', 'integer', 'integer'),
    ('postgresql', 'bigint', 'bigint'), ('postgresql', None, None),
])
def test_actor_field_narrow_type_rule_preserves_parent(vendor, parent, expected):
    field = actor_field_class()(get_user_model(), primary_key=True, on_delete=models.PROTECT, related_name='+')
    with patch.object(models.OneToOneField, 'db_type', return_value=parent):
        assert field.db_type(SimpleNamespace(vendor=vendor)) == expected
    name, path, args, kwargs = field.deconstruct()
    assert path == 'apps.core.document_models.DocumentMetadataActorField'
    assert kwargs['primary_key'] and kwargs['on_delete'] is models.PROTECT


@pytest.mark.django_db
def test_actor_field_generated_type_and_required_identity_even_with_actor_one():
    model = rate_model()
    actor_field = model._meta.get_field('actor')
    parent_type = models.OneToOneField.db_type(actor_field, connection)
    if connection.vendor == 'postgresql':
        assert actor_field.db_type(connection) == parent_type
    elif connection.vendor == 'sqlite':
        assert actor_field.db_type(connection) == 'bigint'
        with connection.cursor() as cursor:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=%s", [model._meta.db_table])
            assert '"actor_id" bigint NOT NULL PRIMARY KEY' in cursor.fetchone()[0]
    actor = get_user_model().objects.create(pk=1, username='synthetic-explicit-actor-one')
    rejects(lambda: raw_insert(None))
    def omitted_actor():
        with connection.cursor() as cursor:
            cursor.execute(f'INSERT INTO {connection.ops.quote_name(model._meta.db_table)} '
                           '(window_started_at, admitted_count) VALUES (%s, %s)',
                           [connection.ops.adapt_datetimefield_value(MINUTE), 1])
    rejects(omitted_actor)
    assert model.objects.count() == 0
    raw_insert(actor.pk)
    model.objects.filter(pk=actor.pk).update(admitted_count=60)
    assert model.objects.get(pk=actor.pk).admitted_count == 60


@pytest.mark.django_db
def test_rate_window_valid_counts_and_unique_actor(actor):
    model = rate_model()
    create(actor, admitted_count=1)
    other = get_user_model().objects.create(username='synthetic-rate-other')
    create(other, admitted_count=60)
    rejects(lambda: raw_insert(actor.pk))
    assert list(model.objects.order_by('actor_id').values_list('admitted_count', flat=True)) == [1, 60]


@pytest.mark.django_db
@pytest.mark.parametrize('count', [0, -1, 61, 32768])
@pytest.mark.parametrize('raw', [False, True])
def test_rate_window_database_rejects_invalid_count_or_null(actor, count, raw):
    model = rate_model()
    rejects(lambda: raw_insert(actor.pk, count=count) if raw else create(actor, admitted_count=count))
    assert model.objects.count() == 0
    row = create(actor)
    if raw:
        def update_count():
            with connection.cursor() as cursor:
                cursor.execute(f'UPDATE {connection.ops.quote_name(model._meta.db_table)} '
                               'SET admitted_count = %s WHERE actor_id = %s', [count, actor.pk])
        rejects(update_count)
    else:
        rejects(lambda: model.objects.filter(pk=row.pk).update(admitted_count=count))
    assert model.objects.get(pk=row.pk).admitted_count == 1


@pytest.mark.django_db
@pytest.mark.parametrize('field', ['actor', 'window_started_at', 'admitted_count'])
@pytest.mark.parametrize('raw', [False, True])
def test_rate_window_database_rejects_invalid_count_or_null_required(actor, field, raw):
    model = rate_model()
    if raw:
        values = {'actor_id': actor.pk, 'timestamp': MINUTE, 'count': 1}
        values[{'actor': 'actor_id', 'window_started_at': 'timestamp', 'admitted_count': 'count'}[field]] = None
        rejects(lambda: raw_insert(**values))
        def missing_column():
            values = {'actor_id': actor.pk, 'window_started_at': connection.ops.adapt_datetimefield_value(MINUTE), 'admitted_count': 1}
            values.pop(model._meta.get_field(field).column)
            with connection.cursor() as cursor:
                cursor.execute(f'INSERT INTO {connection.ops.quote_name(model._meta.db_table)} '
                               f'({", ".join(values)}) VALUES (%s, %s)', list(values.values()))
        rejects(missing_column)
    else:
        rejects(lambda: create(actor, **{field: None}))
        values = dict(actor=actor, window_started_at=MINUTE, admitted_count=1)
        values.pop(field)
        rejects(lambda: model.objects.create(**values))
    assert model.objects.count() == 0
    row = create(actor)
    if raw:
        def update_null():
            column = connection.ops.quote_name(model._meta.get_field(field).column)
            with connection.cursor() as cursor:
                cursor.execute(f'UPDATE {connection.ops.quote_name(model._meta.db_table)} '
                               f'SET {column} = NULL WHERE actor_id = %s', [actor.pk])
        rejects(update_null)
    else:
        rejects(lambda: model.objects.filter(pk=row.pk).update(**{field: None}))
    assert model.objects.get(pk=row.pk).window_started_at == MINUTE
    assert model.objects.get(pk=row.pk).admitted_count == 1


@pytest.mark.django_db
def test_rate_window_actor_integrity_and_protection(actor):
    model = rate_model()
    row = create(actor)
    with pytest.raises(ProtectedError):
        actor.delete()
    rejects(lambda: raw_insert(actor.pk + 1000000))
    def delete_actor():
        with connection.cursor() as cursor:
            cursor.execute(f'DELETE FROM {connection.ops.quote_name(actor._meta.db_table)} WHERE id = %s', [actor.pk])
    rejects(delete_actor)
    assert get_user_model().objects.filter(pk=actor.pk).exists()
    assert model.objects.get(pk=row.pk).admitted_count == 1


@pytest.mark.django_db
@pytest.mark.parametrize('delta', [timedelta(seconds=1), timedelta(seconds=59), timedelta(microseconds=1),
                                  timedelta(microseconds=999999), timedelta(seconds=59, microseconds=999999)])
def test_rate_window_minute_constraint_rejects_precision(actor, delta):
    model = rate_model()
    rejects(lambda: create(actor, window_started_at=MINUTE + delta))
    row = create(actor, window_started_at=MINUTE.astimezone(dt_timezone(timedelta(hours=5, minutes=30))))
    model.objects.filter(pk=row.pk).update(window_started_at=MINUTE + timedelta(minutes=1))
    rejects(lambda: model.objects.filter(pk=row.pk).update(window_started_at=MINUTE + delta))
    assert model.objects.get(pk=row.pk).window_started_at == MINUTE + timedelta(minutes=1)


class CountingCompiler:
    """Count actual compilation of a parameter-bearing Django Value child."""
    def __init__(self):
        self.compiler = get_user_model().objects.all().query.get_compiler(connection=connection)
        self.calls = 0

    def compile(self, child):
        self.calls += 1
        return self.compiler.compile(child)


@pytest.mark.parametrize('vendor,copies', [('postgresql', 3), ('sqlite', 2)])
def test_minute_expression_compiles_with_repeated_params(vendor, copies):
    expression = minute_expression()(models.Value(MINUTE, output_field=models.DateTimeField()))
    compiler = CountingCompiler()
    sql, params = getattr(expression, 'as_' + vendor)(compiler, connection)
    assert compiler.calls == 1
    child_sql, child_params = compiler.compiler.compile(expression.get_source_expressions()[0])
    assert child_params and list(params) == list(child_params) * copies
    if vendor == 'postgresql':
        assert sql == f"((isfinite({child_sql}) AND {child_sql} = DATE_TRUNC('minute', {child_sql}, 'UTC')) IS TRUE)"
    else:
        assert sql == f"(({child_sql} = django_datetime_trunc('minute', {child_sql}, 'UTC', 'UTC')) IS TRUE)"
    assert '2026-10-26' not in sql and isinstance(expression.output_field, models.BooleanField)


def test_minute_expression_rejects_unsupported_vendor_and_wrong_arity():
    expression = minute_expression()
    with pytest.raises(NotSupportedError):
        expression(models.F('window_started_at')).as_sql(Mock(), SimpleNamespace(vendor='mysql'))
    for args in [(), (models.F('a'), models.F('b'))]:
        with pytest.raises(TypeError):
            expression(*args)


@pytest.mark.django_db
def test_minute_expression_is_true_rejects_unknown():
    expression = minute_expression()(models.Value(None, output_field=models.DateTimeField()))
    compiler = get_user_model().objects.all().query.get_compiler(connection=connection)
    # Typed NULL resolves PostgreSQL isfinite/date_trunc overloads independently of column NOT NULL.
    class TypedNullCompiler:
        def compile(self, child):
            assert isinstance(child, models.Value) and child.value is None
            return ('CAST(NULL AS timestamp with time zone)' if connection.vendor == 'postgresql' else 'NULL'), []
    sql, params = getattr(expression, 'as_' + connection.vendor)(TypedNullCompiler(), connection)
    with connection.cursor() as cursor:
        cursor.execute('SELECT ' + sql, params)
        result = cursor.fetchone()[0]
    assert result is False or result == 0
    assert result is not None
    constraint = rate_model()._meta.constraints[1]
    compiled, _ = compiler.compile(constraint.condition.resolve_expression(rate_model().objects.all().query))
    assert 'IS TRUE' in compiled


@pytest.mark.django_db
@pytest.mark.parametrize('value', ['not-a-date', '', 'infinity', '-infinity', '2026-02-30 00:00:00'])
def test_sqlite_minute_constraint_rejects_malformed_raw_values(actor, value):
    model = rate_model()
    if connection.vendor != 'sqlite':
        pytest.skip('SQLite registered-function malformed input gate')
    rejects(lambda: raw_insert(actor.pk, timestamp=value))
    row = create(actor)
    rejects(lambda: raw_update(actor.pk, value))
    assert model.objects.get(pk=row.pk).window_started_at == MINUTE


@pytest.mark.django_db
@pytest.mark.parametrize('session_zone', ['UTC', 'Asia/Kolkata'])
def test_postgresql_minute_constraint_is_finite_and_timezone_independent(actor, session_zone):
    model = rate_model()
    if connection.vendor != 'postgresql':
        pytest.skip('Requires actual PostgreSQL constraint execution')
    assert connection.pg_version >= 170000
    with connection.cursor() as cursor:
        cursor.execute('SHOW TIME ZONE')
        previous = cursor.fetchone()[0]
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('TimeZone', %s, false)", [session_zone])
            cursor.execute('SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = %s', ['doc_metadata_rate_minute'])
            ddl = cursor.fetchone()[0].lower()
        assert 'isfinite' in ddl and 'date_trunc' in ddl and "'utc'" in ddl and 'is true' in ddl
        for value in ['2026-10-26 03:36:00+00', '2026-10-26 09:06:00+05:30', '2026-10-26 03:37:00+00']:
            raw_insert(actor.pk, timestamp=value)
            raw_update(actor.pk, value)
            assert model.objects.count() == 1
            model.objects.all().delete()
        for value in ['infinity', '-infinity', '2026-10-26 03:36:01+00', '2026-10-26 03:36:59+00',
                      '2026-10-26 03:36:00.000001+00', '2026-10-26 03:36:00.999999+00', '2026-10-26 03:36:59.999999+00']:
            rejects(lambda: raw_insert(actor.pk, timestamp=value))
            create(actor)
            rejects(lambda: raw_update(actor.pk, value))
            # SET TimeZone changes the server session, not psycopg's configured
            # datetime loader. Compare the stored instant on the server directly.
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT EXTRACT(EPOCH FROM window_started_at) FROM '
                               f'{connection.ops.quote_name(model._meta.db_table)} WHERE actor_id = %s', [actor.pk])
                assert cursor.fetchone()[0] == Decimal(str(MINUTE.timestamp()))
            model.objects.all().delete()
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('TimeZone', %s, false)", [previous])


def test_minute_expression_migration_serialization_replays_stable_path():
    expression = minute_expression()(models.F('window_started_at'))
    path, args, kwargs = expression.deconstruct()
    assert path == 'apps.core.document_models.DocumentMetadataMinuteAligned'
    assert len(args) == 1 and args[0].name == 'window_started_at' and kwargs == {}
    migration = rate_migration().Migration(MIGRATION[1], 'core')
    # Django explicitly requires manual porting of numeric-migration functions.
    # The real full migration is exercised by executor/reverse tests below.
    full_writer = MigrationWriter(migration, include_header=False)
    full_writer.as_string()
    assert full_writer.needs_manual_porting
    schema = migrations.Migration(MIGRATION[1], 'core')
    schema.dependencies = migration.dependencies
    schema.operations = [op for op in migration.operations if isinstance(op, migrations.CreateModel)]
    assert len(schema.operations) == 1
    source = MigrationWriter(schema, include_header=False).as_string()
    assert 'apps.core.document_models.DocumentMetadataMinuteAligned' in source and '__main__' not in source
    namespace = {}
    exec(compile(source, '<rate migration roundtrip>', 'exec'), namespace)
    rebuilt = namespace['Migration'](MIGRATION[1], 'core')
    assert MigrationWriter(rebuilt, include_header=False).as_string() == source
    # A fresh interpreter imports the real production path and executes the full writer reconstruction.
    code = """
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
import django
django.setup()
from django.db import connection
from django.db import migrations
from django.db.migrations.writer import MigrationWriter
from importlib import import_module
m = import_module('apps.core.migrations.0009_document_metadata_rate_window').Migration('0009_document_metadata_rate_window', 'core')
full_writer = MigrationWriter(m, include_header=False)
full_writer.as_string()
assert full_writer.needs_manual_porting
schema = migrations.Migration('0009_document_metadata_rate_window', 'core')
schema.dependencies = m.dependencies
schema.operations = [op for op in m.operations if isinstance(op, migrations.CreateModel)]
assert len(schema.operations) == 1
source = MigrationWriter(schema, include_header=False).as_string()
namespace = {}
exec(compile(source, '<fresh rate migration>', 'exec'), namespace)
rebuilt = namespace['Migration']('0009_document_metadata_rate_window', 'core')
from apps.core.document_models import DocumentMetadataMinuteAligned
from django.db.models import F
class Compiler:
    def compile(self, child):
        assert child.name == 'window_started_at'
        return '"window_started_at"', []
for op in rebuilt.operations:
    constraints = getattr(op, 'options', {}).get('constraints', [])
    if hasattr(op, 'constraint'):
        constraints.append(op.constraint)
    for constraint in constraints:
        if constraint.name == 'doc_metadata_rate_minute':
            expression = constraint.condition
            assert isinstance(expression, DocumentMetadataMinuteAligned)
            for dialect in ['postgresql', 'sqlite']:
                sql, params = getattr(expression, 'as_' + dialect)(Compiler(), connection)
                assert 'IS TRUE' in sql and params == []
            print('PERMANENT_PATH_REPLAY_OK')
    for name, field in getattr(op, 'fields', []):
        if name == 'actor':
            from apps.core.document_models import DocumentMetadataActorField
            assert isinstance(field, DocumentMetadataActorField)
            assert field.deconstruct()[1] == 'apps.core.document_models.DocumentMetadataActorField'
            print('PERMANENT_FIELD_REPLAY_OK')
"""
    result = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert sorted(result.stdout.splitlines()) == ['PERMANENT_FIELD_REPLAY_OK', 'PERMANENT_PATH_REPLAY_OK']


def existing_rows():
    """Non-vacuous old state: clinical references plus network and identity."""
    apps.get_model('core', 'NetworkPolicyState').objects.get_or_create(pk=1, defaults={
        'revision': 7, 'confirmed_policy': {'allowlist_only': False, 'allowlist': [], 'blocklist': []},
        'confirmed_policy_digest': 'a'*64,
    })
    user = get_user_model().objects.create(username='synthetic-rate-migration')
    org = apps.get_model('core', 'Organisation').objects.create(name='Synthetic rate organisation')
    branch = apps.get_model('core', 'Branch').objects.create(organisation=org, name='Synthetic rate', code='RATE')
    patient = apps.get_model('core', 'Patient').objects.create(branch=branch, full_name='Synthetic rate patient')
    appointment = apps.get_model('core', 'Appointment').objects.create(patient=patient, branch=branch, doctor_name='Synthetic', scheduled_at=MINUTE)
    apps.get_model('core', 'Encounter').objects.create(appointment=appointment)
    apps.get_model('core', 'IdentitySecurity').objects.create(user=user, auth_epoch=7)
    apps.get_model('core', 'PatientDocumentIntent').objects.create(patient=patient, created_by=user,
        category='registration', declared_filename='synthetic.png', declared_media_type='image/png', declared_size_bytes=1,
        declared_sha256='a'*64, created_at=MINUTE, expires_at=MINUTE+timedelta(minutes=30))
    return user


def old_snapshot():
    names = ['Organisation', 'Branch', 'Patient', 'Appointment', 'Encounter', 'PatientDocumentIntent', 'NetworkPolicyState', 'IdentitySecurity']
    return {name: list(apps.get_model('core', name).objects.order_by('pk').values()) for name in names}


def applied():
    return set(MigrationRecorder(connection).applied_migrations())


@pytest.mark.django_db(transaction=True)
def test_rate_migration_forward_preserves_existing_rows():
    model = rate_model()
    rate_migration()
    leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        MigrationExecutor(connection).migrate(OLD)
        existing_rows()
        before = old_snapshot()
        tables = set(connection.introspection.table_names())
        executor = MigrationExecutor(connection)
        executor.migrate([MIGRATION])
        assert set(connection.introspection.table_names()) - tables == {model._meta.db_table}
        assert old_snapshot() == before and model.objects.count() == 0
        state_model = executor.loader.project_state([MIGRATION]).apps.get_model('core', MODEL)
        assert [field.deconstruct()[1:] for field in state_model._meta.local_fields] == [field.deconstruct()[1:] for field in model._meta.local_fields]
        assert [c.deconstruct() for c in state_model._meta.constraints] == [c.deconstruct() for c in model._meta.constraints]
    finally:
        MigrationExecutor(connection).migrate(leaves)


@pytest.mark.django_db(transaction=True)
def test_rate_migration_empty_reverse_forward_round_trip():
    model = rate_model()
    rate_migration()
    leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        assert model.objects.count() == 0
        MigrationExecutor(connection).migrate(OLD)
        assert model._meta.db_table not in connection.introspection.table_names() and MIGRATION not in applied()
        MigrationExecutor(connection).migrate([MIGRATION])
        assert model._meta.db_table in connection.introspection.table_names() and MIGRATION in applied()
        actor = get_user_model().objects.create(username='synthetic-rate-replay')
        rejects(lambda: raw_insert(actor.pk, count=0))
        rejects(lambda: raw_insert(actor.pk, timestamp=MINUTE+timedelta(microseconds=1)))
        create(actor).delete()
    finally:
        MigrationExecutor(connection).migrate(leaves)


@pytest.mark.django_db(transaction=True)
def test_rate_migration_nonempty_reverse_refuses_before_ddl():
    model = rate_model()
    rate_migration()
    leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
    actor = existing_rows()
    row = create(actor)
    before, recorder = old_snapshot(), applied()
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, model._meta.db_table)
    ddl = []
    def observe(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith(('DROP ', 'ALTER ')):
            ddl.append(sql)
        return execute(sql, params, many, context)
    try:
        with connection.execute_wrapper(observe), pytest.raises(RuntimeError) as error:
            MigrationExecutor(connection).migrate(OLD)
        assert str(error.value) == GUARD_ERROR and ddl == []
        assert model._meta.db_table in connection.introspection.table_names()
        assert model.objects.get(pk=row.pk).admitted_count == 1
        assert old_snapshot() == before and applied() == recorder
        with connection.cursor() as cursor:
            assert connection.introspection.get_constraints(cursor, model._meta.db_table) == constraints
    finally:
        model.objects.filter(pk=row.pk).delete()
        MigrationExecutor(connection).migrate(leaves)


@pytest.mark.parametrize('nonempty', [False, True])
def test_rate_reverse_guard_uses_historical_registry_and_alias(nonempty):
    module = rate_migration()
    manager = Mock()
    manager.using.return_value.exists.return_value = nonempty
    historical = Mock()
    historical.get_model.return_value = SimpleNamespace(objects=manager)
    editor = SimpleNamespace(connection=SimpleNamespace(alias='synthetic_nondefault'))
    if nonempty:
        with pytest.raises(RuntimeError) as error:
            module.reverse_empty_only(historical, editor)
        assert str(error.value) == GUARD_ERROR
    else:
        assert module.reverse_empty_only(historical, editor) is None
    historical.get_model.assert_called_once_with('core', MODEL)
    manager.using.assert_called_once_with('synthetic_nondefault')
    assert manager.using.return_value.method_calls == [('exists', (), {})]
    final = module.Migration.operations[-1]
    assert isinstance(final, migrations.RunPython)
    assert final.code is migrations.RunPython.noop and final.reverse_code is module.reverse_empty_only
