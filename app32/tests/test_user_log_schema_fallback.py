from models.user_log import UserLog, _allocate_user_log_id


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeConnection:
    def __init__(self, sequence_name=None, next_id=None, max_id=None, column_default=None):
        self.sequence_name = sequence_name
        self.next_id = next_id
        self.max_id = max_id
        self.column_default = column_default
        self.commands = []

    def exec_driver_sql(self, sql):
        self.commands.append(sql)
        if "pg_get_serial_sequence" in sql:
            return _FakeResult(self.sequence_name)
        if "SELECT column_default" in sql:
            return _FakeResult(self.column_default)
        if "nextval" in sql:
            return _FakeResult(self.next_id)
        if "COALESCE(MAX(id), 0) + 1" in sql:
            return _FakeResult(self.max_id)
        return _FakeResult(None)


def test_user_log_model_accepts_plan_id():
    log = UserLog(
        user_email="admin@versus.com.br",
        user_name="Administrador",
        action="LOGIN",
        entity_type="user",
        plan_id="42",
    )

    assert log.plan_id == "42"


def test_allocate_user_log_id_uses_sequence_when_available():
    connection = _FakeConnection(
        sequence_name="public.user_logs_id_seq",
        next_id=18,
    )

    next_id = _allocate_user_log_id(connection)

    assert next_id == 18
    assert any("pg_get_serial_sequence" in command for command in connection.commands)
    assert any("nextval('public.user_logs_id_seq')" in command for command in connection.commands)


def test_allocate_user_log_id_falls_back_to_locked_max_plus_one():
    connection = _FakeConnection(
        sequence_name=None,
        max_id=27,
    )

    next_id = _allocate_user_log_id(connection)

    assert next_id == 27
    assert "LOCK TABLE public.user_logs IN EXCLUSIVE MODE" in connection.commands


def test_allocate_user_log_id_uses_column_default_sequence_when_not_owned():
    connection = _FakeConnection(
        sequence_name=None,
        column_default="nextval('user_logs_id_seq'::regclass)",
        next_id=31,
    )

    next_id = _allocate_user_log_id(connection)

    assert next_id == 31
    assert any("SELECT column_default" in command for command in connection.commands)
    assert any("nextval('user_logs_id_seq')" in command for command in connection.commands)
