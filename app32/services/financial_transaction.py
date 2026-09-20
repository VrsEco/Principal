"""Session-local transaction ownership for composed financial operations.

Leaf services use financial_commit; outside an owned operation it preserves
their existing commit behavior. No process-global or cross-request state.
"""
from functools import wraps
import logging

from sqlalchemy import event
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)
_KEY = 'app32_financial_transaction_owner'


def abort_owned_financial_operation(session):
    """Mark a caught business failure for rollback by its transaction owner."""
    state = getattr(session, 'info', {}).get(_KEY)
    if state is None:
        return False
    state['aborted'] = True
    return True


def financial_commit(session):
    state = getattr(session, 'info', {}).get(_KEY)
    if state is None:
        session.commit()
    else:
        if state['aborted']:
            raise RuntimeError('A transação financeira já foi cancelada.')
        session.flush()


def atomic_financial_operation(session_provider):
    """Own commit/rollback for a service returning (result, error).

    Nested operations share ownership. A swallowed rollback or an unconverted
    raw commit fails closed instead of allowing partial financial persistence.
    """
    def decorate(callback):
        @wraps(callback)
        def wrapped(*args, **kwargs):
            proxy = session_provider()
            session = proxy() if callable(proxy) else proxy
            if _KEY in session.info:
                result, error = callback(*args, **kwargs)
                if error:
                    session.info[_KEY]['aborted'] = True
                return result, error
            state = {'aborted': False, 'allow_commit': False}
            session.info[_KEY] = state
            def forbid_inner_commit(current):
                if not state['allow_commit']:
                    state['aborted'] = True
                    raise RuntimeError('Commit intermediário proibido na operação financeira composta.')
            def mark_rollback(current):
                state['aborted'] = True
            event.listen(session, 'before_commit', forbid_inner_commit)
            event.listen(session, 'after_rollback', mark_rollback)
            try:
                result, error = callback(*args, **kwargs)
                if error or state['aborted']:
                    session.rollback()
                    return None, error or 'Operação financeira cancelada integralmente por falha interna.'
                state['allow_commit'] = True
                session.commit()
                return result, None
            except OperationalError as exc:
                session.rollback()
                if (getattr(exc.orig, 'pgcode', None) or getattr(exc.orig, 'sqlstate', None)) == '55P03':
                    return None, 'Operação financeira em processamento. Atualize os dados antes de tentar novamente.'
                logger.exception('Falha de banco em operação financeira composta')
                return None, 'Não foi possível concluir a operação financeira.'
            except Exception:
                session.rollback()
                logger.exception('Falha em operação financeira composta')
                return None, 'Não foi possível concluir a operação financeira.'
            finally:
                event.remove(session, 'before_commit', forbid_inner_commit)
                event.remove(session, 'after_rollback', mark_rollback)
                session.info.pop(_KEY, None)
        return wrapped
    return decorate
