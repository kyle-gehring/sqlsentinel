"""Scheduler module for automated alert execution.

This module provides scheduled execution of SQL Sentinel alerts using APScheduler.
It enables continuous background monitoring without manual intervention.
"""

from sqlsentinel.scheduler.scheduler import SchedulerService

__all__ = ["SchedulerService"]
