"""
Scheduler module for recurring build flashing and testing tasks
Handles task scheduling, execution, and persistence
"""
import threading
import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional


class ScheduledTask:
    """Represents a scheduled automation task"""

    def __init__(self, task_id: str, name: str, task_type: str,
                 schedule_type: str, schedule_value: str,
                 config: Dict, enabled: bool = True):
        """
        Initialize a scheduled task

        Args:
            task_id: Unique identifier for the task
            name: Human-readable task name
            task_type: Type of task ('flash', 'test', 'flash_and_test')
            schedule_type: Type of schedule ('daily', 'weekly', 'interval')
            schedule_value: Schedule configuration (e.g., 'Wednesday', '14:30', '6h')
            config: Task configuration dict (build URL, test suite, devices, etc.)
            enabled: Whether task is currently enabled
        """
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.schedule_type = schedule_type
        self.schedule_value = schedule_value
        self.config = config
        self.enabled = enabled
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.last_status = None

        self._calculate_next_run()

    def _calculate_next_run(self):
        """Calculate the next run time based on schedule"""
        now = datetime.now()

        if self.schedule_type == 'daily':
            # schedule_value is time like "14:30"
            try:
                hour, minute = map(int, self.schedule_value.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                self.next_run = next_run
            except:
                self.next_run = None

        elif self.schedule_type == 'weekly':
            # schedule_value is "Monday 14:30", "Tuesday 09:00", etc.
            try:
                parts = self.schedule_value.split()
                day_name = parts[0]
                time_str = parts[1] if len(parts) > 1 else "00:00"
                hour, minute = map(int, time_str.split(':'))

                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                target_day = days.index(day_name)
                current_day = now.weekday()

                days_ahead = target_day - current_day
                if days_ahead < 0:
                    days_ahead += 7
                elif days_ahead == 0:
                    # Same day - check if time has passed
                    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target_time <= now:
                        days_ahead = 7

                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                self.next_run = next_run
            except:
                self.next_run = None

        elif self.schedule_type == 'interval':
            # schedule_value is like "6h", "30m", "2d"
            try:
                value = int(self.schedule_value[:-1])
                unit = self.schedule_value[-1]

                if unit == 'm':
                    delta = timedelta(minutes=value)
                elif unit == 'h':
                    delta = timedelta(hours=value)
                elif unit == 'd':
                    delta = timedelta(days=value)
                else:
                    delta = timedelta(hours=1)

                if self.last_run:
                    self.next_run = self.last_run + delta
                else:
                    self.next_run = now + delta
            except:
                self.next_run = None

    def should_run(self) -> bool:
        """Check if task should run now"""
        if not self.enabled or not self.next_run:
            return False
        return datetime.now() >= self.next_run

    def mark_executed(self, status: str):
        """Mark task as executed and calculate next run"""
        self.last_run = datetime.now()
        self.run_count += 1
        self.last_status = status
        self._calculate_next_run()

    def to_dict(self) -> Dict:
        """Convert task to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'task_type': self.task_type,
            'schedule_type': self.schedule_type,
            'schedule_value': self.schedule_value,
            'config': self.config,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'last_status': self.last_status
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduledTask':
        """Create task from dictionary"""
        task = cls(
            task_id=data['task_id'],
            name=data['name'],
            task_type=data['task_type'],
            schedule_type=data['schedule_type'],
            schedule_value=data['schedule_value'],
            config=data['config'],
            enabled=data.get('enabled', True)
        )

        if data.get('last_run'):
            task.last_run = datetime.fromisoformat(data['last_run'])
        if data.get('next_run'):
            task.next_run = datetime.fromisoformat(data['next_run'])
        task.run_count = data.get('run_count', 0)
        task.last_status = data.get('last_status')

        return task


class TaskScheduler:
    """Manages and executes scheduled tasks"""

    def __init__(self, persistence_file: str = 'scheduled_tasks.json'):
        """
        Initialize the task scheduler

        Args:
            persistence_file: Path to JSON file for task persistence
        """
        self.tasks: List[ScheduledTask] = []
        self.persistence_file = persistence_file
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.task_executor: Optional[Callable] = None
        self.logger = None

        # Load persisted tasks
        self.load_tasks()

    def set_task_executor(self, executor: Callable):
        """
        Set the function that will execute tasks

        Args:
            executor: Function that takes a ScheduledTask and executes it
        """
        self.task_executor = executor

    def set_logger(self, logger):
        """Set logger instance for task execution logging"""
        self.logger = logger

    def add_task(self, task: ScheduledTask) -> bool:
        """
        Add a new scheduled task

        Args:
            task: ScheduledTask instance to add

        Returns:
            True if task was added, False if task_id already exists
        """
        if any(t.task_id == task.task_id for t in self.tasks):
            return False

        self.tasks.append(task)
        self.save_tasks()

        if self.logger:
            self.logger.log(f"✅ Scheduled task added: {task.name}", level='success')

        return True

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task

        Args:
            task_id: ID of task to remove

        Returns:
            True if task was removed, False if not found
        """
        task = self.get_task(task_id)
        if task:
            self.tasks.remove(task)
            self.save_tasks()

            if self.logger:
                self.logger.log(f"🗑️ Scheduled task removed: {task.name}", level='info')

            return True
        return False

    def update_task(self, task: ScheduledTask) -> bool:
        """
        Update an existing task

        Args:
            task: Updated ScheduledTask instance

        Returns:
            True if task was updated, False if not found
        """
        for i, t in enumerate(self.tasks):
            if t.task_id == task.task_id:
                self.tasks[i] = task
                self.save_tasks()

                if self.logger:
                    self.logger.log(f"📝 Scheduled task updated: {task.name}", level='info')

                return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all tasks"""
        return self.tasks.copy()

    def enable_task(self, task_id: str):
        """Enable a task"""
        task = self.get_task(task_id)
        if task:
            task.enabled = True
            task._calculate_next_run()
            self.save_tasks()

    def disable_task(self, task_id: str):
        """Disable a task"""
        task = self.get_task(task_id)
        if task:
            task.enabled = False
            self.save_tasks()

    def start(self):
        """Start the scheduler background thread"""
        if self.running:
            return

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        if self.logger:
            self.logger.log("🕐 Task scheduler started", level='success')

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2)

        if self.logger:
            self.logger.log("⏸️ Task scheduler stopped", level='info')

    def _scheduler_loop(self):
        """Main scheduler loop running in background thread"""
        while self.running:
            try:
                # Check all tasks
                for task in self.tasks:
                    if task.should_run():
                        self._execute_task(task)

                # Sleep for 30 seconds between checks
                time.sleep(30)

            except Exception as e:
                if self.logger:
                    self.logger.log(f"Scheduler error: {e}", level='error')
                time.sleep(60)  # Wait longer on error

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        if self.logger:
            self.logger.log(f"🚀 Executing scheduled task: {task.name}", level='info')

        try:
            if self.task_executor:
                # Execute task in separate thread to not block scheduler
                exec_thread = threading.Thread(
                    target=self._run_task_executor,
                    args=(task,),
                    daemon=True
                )
                exec_thread.start()
            else:
                if self.logger:
                    self.logger.log("⚠️ No task executor configured", level='warning')
                task.mark_executed('error')
        except Exception as e:
            if self.logger:
                self.logger.log(f"Task execution error: {e}", level='error')
            task.mark_executed('error')

    def _run_task_executor(self, task: ScheduledTask):
        """Run task executor and mark completion"""
        try:
            result = self.task_executor(task)
            status = 'success' if result else 'failed'
        except Exception as e:
            if self.logger:
                self.logger.log(f"Task executor exception: {e}", level='error')
            status = 'error'

        task.mark_executed(status)
        self.save_tasks()

    def save_tasks(self):
        """Save tasks to JSON file"""
        try:
            data = {
                'tasks': [task.to_dict() for task in self.tasks],
                'last_saved': datetime.now().isoformat()
            }

            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error saving tasks: {e}", level='error')

    def load_tasks(self):
        """Load tasks from JSON file"""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)

                self.tasks = [
                    ScheduledTask.from_dict(task_data)
                    for task_data in data.get('tasks', [])
                ]

                if self.logger:
                    self.logger.log(f"📂 Loaded {len(self.tasks)} scheduled tasks", level='info')
        except Exception as e:
            if self.logger:
                self.logger.log(f"Error loading tasks: {e}", level='error')
            self.tasks = []

