"""Dashboard web per monitoritzar traduccions."""

from dashboard.server import (
    TranslationDashboard,
    dashboard,
    start_dashboard,
    stop_dashboard,
    LogLevel,
)

__all__ = [
    "TranslationDashboard",
    "dashboard",
    "start_dashboard",
    "stop_dashboard",
    "LogLevel",
]
