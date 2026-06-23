from django.db import models

# Create your models here.

class Tracker(models.Model):
    tracker_id = models.CharField(max_length=100, unique=True, primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Entry(models.Model):
    entry_id = models.CharField(max_length=100, unique=True, primary_key=True)
    tracker = models.ForeignKey(Tracker, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    type = models.CharField(max_length=10, choices=[('income', 'Income'), ('expense', 'Expense')])
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remarks = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.description} - {self.type} - {self.amount}"

class Note(models.Model):
    note_id = models.CharField(max_length=100, unique=True, primary_key=True)
    title = models.CharField(max_length=255, blank=True, default='')
    content = models.TextField(blank=True, default='')
    category = models.CharField(max_length=50, blank=True, default='')
    pinned = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    checklist = models.TextField(blank=True, default='[]')
    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()

    def __str__(self):
        return self.title or "Untitled Note"


class DiaryEntry(models.Model):
    entry_id = models.CharField(max_length=100, unique=True, primary_key=True)
    date = models.DateField(unique=True)
    title = models.CharField(max_length=255, blank=True, default='')
    content = models.TextField(blank=True, default='')
    mood = models.CharField(max_length=50, blank=True, default='')
    tags = models.TextField(blank=True, default='[]')  # JSON list of strings

    def __str__(self):
        return f"{self.date} - {self.title or 'Untitled reflection'}"


class TodoTask(models.Model):
    task_id = models.CharField(max_length=100, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    category = models.CharField(max_length=50, blank=True, default='Inbox')
    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()

    def __str__(self):
        return self.title


class Reminder(models.Model):
    reminder_id = models.CharField(max_length=100, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()

    def __str__(self):
        return self.title


class HabitCategory(models.Model):
    category_id = models.CharField(max_length=100, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=50, default='blue')

    def __str__(self):
        return self.name


class Habit(models.Model):
    habit_id = models.CharField(max_length=100, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    created_at = models.CharField(max_length=10)  # format YYYY-MM-DD

    def __str__(self):
        return self.title


class HabitProgress(models.Model):
    habit_id = models.CharField(max_length=100)
    date = models.CharField(max_length=10)  # format YYYY-MM-DD

    class Meta:
        unique_together = ('habit_id', 'date')

    def __str__(self):
        return f"{self.habit_id} - {self.date}"
