"""Transaction ownership guards without a database or Flask application."""
import os
import sys

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.financial_transaction import atomic_financial_operation, financial_commit


@pytest.mark.parametrize('failure', ['raw_commit', 'rollback', 'nested_error'])
def test_nested_failure_cannot_be_swallowed(failure):
    with Session() as session:
        commits = []
        event.listen(session, 'after_commit', lambda current: commits.append(True))

        @atomic_financial_operation(lambda: session)
        def child():
            return None, 'child rejected'

        @atomic_financial_operation(lambda: session)
        def operation():
            session.begin()
            if failure == 'raw_commit':
                try:
                    session.commit()
                except RuntimeError:
                    pass
            elif failure == 'rollback':
                session.rollback()
            else:
                child()
            return {'pretended_success': True}, None

        result, error = operation()
        assert result is None and error
        assert commits == []
        assert session.info == {}
        # No leaked listener may block the next independent operation.
        session.commit()
        assert commits == [True]


def test_nested_success_has_one_owner_commit():
    with Session() as session:
        commits = []
        event.listen(session, 'after_commit', lambda current: commits.append(True))

        @atomic_financial_operation(lambda: session)
        def child():
            financial_commit(session)
            return {'ok': True}, None

        @atomic_financial_operation(lambda: session)
        def operation():
            financial_commit(session)
            return child()

        assert operation() == ({'ok': True}, None)
        assert commits == [True]
        assert session.info == {}
