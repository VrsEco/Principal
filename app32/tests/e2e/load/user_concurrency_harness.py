from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.load.concurrency_profiles import UserConcurrencyProfile


@dataclass(frozen=True)
class UserConcurrencyResult:
    user_label: str
    success: bool
    iterations_completed: int
    details: dict[str, Any]


def execute_user_concurrency(
    *,
    settings: E2EEnvironmentSettings,
    profile: UserConcurrencyProfile,
    operation: Callable[[AuthenticatedHTTPSession, int], dict[str, Any]],
) -> list[UserConcurrencyResult]:
    results: list[UserConcurrencyResult] = []

    def _worker(user_index: int) -> UserConcurrencyResult:
        label = f"{settings.username}#worker{user_index+1}"
        http = AuthenticatedHTTPSession.create(settings)
        http.login()
        http.select_company()
        last_payload: dict[str, Any] = {}
        for iteration in range(profile.iterations_per_user):
            last_payload = operation(http, iteration)
        return UserConcurrencyResult(
            user_label=label,
            success=True,
            iterations_completed=profile.iterations_per_user,
            details=last_payload,
        )

    with ThreadPoolExecutor(max_workers=profile.concurrent_users) as executor:
        futures = [executor.submit(_worker, user_index) for user_index in range(profile.concurrent_users)]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    UserConcurrencyResult(
                        user_label="unknown",
                        success=False,
                        iterations_completed=0,
                        details={"error": str(exc)},
                    )
                )
    return results
