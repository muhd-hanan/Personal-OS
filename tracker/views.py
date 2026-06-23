import json
import time
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal
from collections import defaultdict

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .models import Tracker, Entry, Note, DiaryEntry, TodoTask, Reminder, HabitCategory, Habit, HabitProgress

def index(request):

    # Ensure default trackers exist if database is fresh
    if not Tracker.objects.exists():
        Tracker.objects.create(tracker_id='personal', name='Personal')
        Tracker.objects.create(tracker_id='business', name='Business')
        Tracker.objects.create(tracker_id='family', name='Family')

    # ── EXPENSE METRICS ────────────────────────────────────────────────────────
    today = date.today()
    # Default initial render to personal tracker
    personal_tracker = Tracker.objects.filter(tracker_id='personal').first()
    if personal_tracker:
        all_entries = Entry.objects.filter(tracker=personal_tracker)
    else:
        all_entries = Entry.objects.all()

    total_income = sum(e.amount for e in all_entries if e.type == 'income')
    total_expense = sum(e.amount for e in all_entries if e.type == 'expense')
    balance = total_income - total_expense

    # This-month metrics for the snapshot panel
    month_entries = [e for e in all_entries
                     if e.date.year == today.year and e.date.month == today.month]
    month_income  = sum(e.amount for e in month_entries if e.type == 'income')
    month_expense = sum(e.amount for e in month_entries if e.type == 'expense')
    month_balance = month_income - month_expense

    # Build monthly expense chart data: group by month for last 6 months
    monthly_expenses = defaultdict(float)
    monthly_incomes = defaultdict(float)
    for e in all_entries:
        month_key = e.date.strftime('%b %Y')
        if e.type == 'expense':
            monthly_expenses[month_key] += float(e.amount)
        else:
            monthly_incomes[month_key] += float(e.amount)

    # Produce last 6 month labels in order
    chart_months = []
    for i in range(5, -1, -1):
        d = today.replace(day=1) - timedelta(days=i * 28)
        chart_months.append(d.strftime('%b %Y'))

    chart_expense_data = [monthly_expenses.get(m, 0) for m in chart_months]
    chart_income_data  = [monthly_incomes.get(m, 0)  for m in chart_months]
    chart_labels       = [m.split()[0] for m in chart_months]  # Short month name

    # Package trackers and their entries for frontend filtering (optimized with prefetch_related)
    trackers_dict = {}
    for t in Tracker.objects.prefetch_related('entries'):
        entries_list = []
        for e in t.entries.all():
            entries_list.append({
                'id': e.entry_id,
                'date': str(e.date),
                'type': e.type,
                'description': e.description,
                'amount': float(e.amount),
                'remarks': e.remarks
            })
        trackers_dict[t.tracker_id] = {
            'name': t.name,
            'entries': entries_list
        }

    # ── RECENT NOTES ──────────────────────────────────────────────────────────
    notes_qs = Note.objects.all().order_by('-updated_at')[:4]
    now_ms = int(time.time() * 1000)
    recent_notes = []
    for n in notes_qs:
        delta_ms = now_ms - n.updated_at
        if delta_ms < 3600000:
            time_ago = f"{max(1, delta_ms // 60000)} min ago"
        elif delta_ms < 86400000:
            h = delta_ms // 3600000
            time_ago = f"{h} hr{'s' if h != 1 else ''} ago"
        elif delta_ms < 172800000:
            time_ago = "Yesterday"
            time_ago = "Yesterday"
        else:
            d = delta_ms // 86400000
            time_ago = f"{d} days ago"
        recent_notes.append({
            'title': n.title or 'Untitled Note',
            'content': n.content[:120] if n.content else '',
            'category': n.category or 'general',
            'time_ago': time_ago,
        })

    # ── RECENT DIARY ENTRIES ──────────────────────────────────────────────────
    diary_qs = DiaryEntry.objects.all().order_by('-date')[:2]
    recent_diary = []
    for entry in diary_qs:
        days_ago = (today - entry.date).days
        if days_ago == 0:
            date_label = "Today"
            date_color = "text-blue-400"
        elif days_ago == 1:
            date_label = "Yesterday"
            date_color = "text-blue-400"
        else:
            date_label = entry.date.strftime('%d %b, %Y').upper()
            date_color = "text-gray-500"
        recent_diary.append({
            'date_label': date_label,
            'date_color': date_color,
            'title': entry.title or 'Untitled Reflection',
            'content': (entry.content or '')[:100],
            'mood': entry.mood,
            'is_latest': days_ago == 0 or days_ago == 1,
        })

    # ── RECENT TODOS ──────────────────────────────────────────────────────────
    todos_qs = TodoTask.objects.all().order_by('-created_at')[:4]
    recent_todos = []
    for t in todos_qs:
        recent_todos.append({
            'title': t.title,
            'completed': t.completed,
            'category': t.category,
        })
    total_todos = TodoTask.objects.count()
    completed_todos = TodoTask.objects.filter(completed=True).count()

    # ── UPCOMING REMINDERS ──────────────────────────────────────────────────
    now_dt = datetime.now()
    reminders_qs = Reminder.objects.all()
    reminders_list = []
    for r in reminders_qs:
        target_dt = datetime.combine(r.date, r.time)
        has_passed = target_dt < now_dt
        if has_passed:
            while target_dt < now_dt:
                try:
                    target_dt = target_dt.replace(year=target_dt.year + 1)
                except ValueError:
                    target_dt = target_dt.replace(year=target_dt.year + 1, day=28)
        
        reminders_list.append({
            'title': r.title,
            'date': target_dt.date().strftime('%Y-%m-%d'),
            'time': r.time.strftime('%H:%M'),
            'target_dt': target_dt,
            'is_recurring': has_passed
        })
    
    reminders_list.sort(key=lambda x: x['target_dt'])
    first_3_reminders = reminders_list[:3]
    index_reminders_list = [{
        'title': r['title'],
        'date': r['date'],
        'time': r['time'],
        'is_recurring': r['is_recurring']
    } for r in first_3_reminders]

    context = {
        # Expense (all-time, used by chart)
        'total_income':   float(total_income),
        'total_expense':  float(total_expense),
        'balance':        float(balance),
        # This-month snapshot values
        'month_income':   float(month_income),
        'month_expense':  float(month_expense),
        'month_balance':  float(month_balance),
        'chart_labels':   json.dumps(chart_labels),
        'chart_expenses': json.dumps(chart_expense_data),
        'chart_incomes':  json.dumps(chart_income_data),
        # Trackers and full filtering context
        'trackers_json':  json.dumps(trackers_dict),
        'chart_month_keys': json.dumps(chart_months),
        'today_year':     today.year,
        'today_month':    today.month,
        # Notes
        'recent_notes':   recent_notes,
        'notes_count':    Note.objects.count(),
        # Diary
        'recent_diary':   recent_diary,
        'diary_count':    DiaryEntry.objects.count(),
        # Todos
        'recent_todos':   recent_todos,
        'total_todos':    total_todos,
        'completed_todos': completed_todos,
        # Reminders
        'index_reminders_json': json.dumps(index_reminders_list),
    }
    return render(request, 'index.html', context)

@ensure_csrf_cookie
def expense(request):
    # Ensure default trackers exist if database is fresh
    if not Tracker.objects.exists():
        Tracker.objects.create(tracker_id='personal', name='Personal')
        Tracker.objects.create(tracker_id='business', name='Business')
        Tracker.objects.create(tracker_id='family', name='Family')
    
    # Package all trackers and their entries for the template (optimized with prefetch_related)
    trackers_dict = {}
    for t in Tracker.objects.prefetch_related('entries'):
        entries_list = []
        for e in t.entries.all():
            entries_list.append({
                'id': e.entry_id,
                'date': str(e.date),
                'type': e.type,
                'description': e.description,
                'amount': float(e.amount),
                'remarks': e.remarks
            })
        trackers_dict[t.tracker_id] = {
            'name': t.name,
            'entries': entries_list
        }
    
    context = {
        'trackers_json': json.dumps(trackers_dict)
    }
    return render(request, 'expense.html', context)

@require_POST
def save_data(request):
    try:
        data = json.loads(request.body)
        incoming_tracker_ids = list(data.keys())
        
        # 1. Delete trackers that are no longer in incoming data
        Tracker.objects.exclude(tracker_id__in=incoming_tracker_ids).delete()
        
        for t_id, t_data in data.items():
            # 2. Get or create tracker
            tracker, created = Tracker.objects.get_or_create(
                tracker_id=t_id,
                defaults={'name': t_data['name']}
            )
            if not created and tracker.name != t_data['name']:
                tracker.name = t_data['name']
                tracker.save()
            
            # 3. Synchronize entries
            incoming_entries = t_data.get('entries', [])
            incoming_entry_ids = [e['id'] for e in incoming_entries]
            
            # Delete entries not in incoming data for this tracker
            tracker.entries.exclude(entry_id__in=incoming_entry_ids).delete()
            
            for e_data in incoming_entries:
                Entry.objects.update_or_create(
                    entry_id=e_data['id'],
                    defaults={
                        'tracker': tracker,
                        'date': e_data['date'],
                        'type': e_data['type'],
                        'description': e_data['description'],
                        'amount': e_data['amount'],
                        'remarks': e_data.get('remarks', '')
                    }
                )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_POST
def create_tracker(request):
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Tracker name is required'}, status=400)
        
        # Generate ID similar to frontend format tracker_<timestamp>
        tracker_id = f"tracker_{int(time.time() * 1000)}"
        
        tracker = Tracker.objects.create(
            tracker_id=tracker_id,
            name=name
        )
        return JsonResponse({'status': 'success', 'tracker_id': tracker.tracker_id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
def delete_tracker(request):
    try:
        data = json.loads(request.body)
        tracker_id = data.get('tracker_id')
        if not tracker_id:
            return JsonResponse({'status': 'error', 'message': 'Tracker ID is required'}, status=400)
        
        Tracker.objects.filter(tracker_id=tracker_id).delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
def save_entry(request):
    try:
        data = json.loads(request.body)
        entry_id = data.get('id')
        tracker_id = data.get('tracker_id')
        date = data.get('date')
        entry_type = data.get('type')
        description = data.get('description', '').strip()
        amount = data.get('amount')
        remarks = data.get('remarks', '').strip()
        
        if not all([tracker_id, date, entry_type, description, amount]):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
        
        tracker = Tracker.objects.get(tracker_id=tracker_id)
        
        # If entry_id is not provided, generate one
        if not entry_id:
            entry_id = f"entry_{int(time.time() * 1000)}"
            
        entry, created = Entry.objects.update_or_create(
            entry_id=entry_id,
            defaults={
                'tracker': tracker,
                'date': date,
                'type': entry_type,
                'description': description,
                'amount': amount,
                'remarks': remarks
            }
        )
        return JsonResponse({'status': 'success', 'entry_id': entry.entry_id})
    except Tracker.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Tracker does not exist'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
def delete_entry(request):
    try:
        data = json.loads(request.body)
        entry_id = data.get('entry_id')
        if not entry_id:
            return JsonResponse({'status': 'error', 'message': 'Entry ID is required'}, status=400)
        
        Entry.objects.filter(entry_id=entry_id).delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@ensure_csrf_cookie
def notes(request):
    # Ensure default notes exist if database is fresh
    if not Note.objects.exists():
        now_ms = int(time.time() * 1000)
        Note.objects.create(
            note_id=str(now_ms),
            title="Premium Cyber Interface Specifications",
            content="We have fully implemented a futuristic, high-contrast dark space gradient matching cyber aesthetics: \n\n- Linear reflective borders: rgba(255, 255, 255, 0.15)\n- Backing ambient glowing meshes (electric blue, deep purple)\n- Neon gradient accents (#00f2fe to #a855f7)\n- Translucent glassmorphism with 3D bevel box-shadows\n\nDouble clicking format buttons injects clean wrappers immediately.",
            category="work",
            pinned=True,
            locked=False,
            checklist=json.dumps([
                {"text": "Style active toggles with cyan glows", "done": True},
                {"text": "Verify local database draft auto-saves", "done": True},
                {"text": "Integrate standard copy tooltips", "done": False}
            ]),
            created_at=now_ms - 3600000,
            updated_at=now_ms - 3600000
        )
        Note.objects.create(
            note_id=str(now_ms - 1000),
            title="Creative brainstorming session notes",
            content="Spend time detailing notes with secure locking folders. Encrypted vaults can mask content details until passcode codes check out.",
            category="idea",
            pinned=False,
            locked=False,
            checklist="[]",
            created_at=now_ms - 86400000,
            updated_at=now_ms - 86400000
        )

    # Package all notes for the template
    notes_list = []
    for n in Note.objects.all():
        notes_list.append({
            'id': int(n.note_id),
            'title': n.title,
            'content': n.content,
            'category': n.category,
            'pinned': n.pinned,
            'locked': n.locked,
            'checklist': json.loads(n.checklist) if n.checklist else [],
            'createdAt': n.created_at,
            'updatedAt': n.updated_at
        })

    context = {
        'notes_json': json.dumps(notes_list)
     }
    return render(request, 'notes.html', context)

@require_POST
def save_notes(request):
    try:
        data = json.loads(request.body)
        incoming_note_ids = [str(n['id']) for n in data]

        # 1. Delete notes that are no longer in incoming data
        Note.objects.exclude(note_id__in=incoming_note_ids).delete()

        # 2. Update or create incoming notes
        for n_data in data:
            Note.objects.update_or_create(
                note_id=str(n_data['id']),
                defaults={
                    'title': n_data.get('title', ''),
                    'content': n_data.get('content', ''),
                    'category': n_data.get('category', ''),
                    'pinned': n_data.get('pinned', False),
                    'locked': n_data.get('locked', False),
                    'checklist': json.dumps(n_data.get('checklist', [])),
                    'created_at': n_data.get('createdAt', n_data.get('id')),
                    'updated_at': n_data.get('updatedAt', n_data.get('id'))
                }
            )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@ensure_csrf_cookie
def diary(request):
    # Ensure default entries exist if database is fresh
    if not DiaryEntry.objects.exists():
        today_date = date.today()
        yesterday_date = today_date - timedelta(days=1)
        
        DiaryEntry.objects.create(
            entry_id=str(today_date),
            date=today_date,
            title="Starting ZenDiary Reflection",
            content="Today marks the first entry into this beautiful reflection journal. The interface feels completely premium, allowing me to organize my thoughts cleanly with category tags, custom moods, and system backups. \n\nI want to focus on high impact deliverables, maintain positive habits, and capture all milestones securely.",
            mood="inspired",
            tags=json.dumps(["Sprint", "Milestone", "Vision"])
        )
        
        DiaryEntry.objects.create(
            entry_id=str(yesterday_date),
            date=yesterday_date,
            title="Creative brainstorming session",
            content="Spent the afternoon mapping out clean gradient tokens, CSS radial meshes, and custom interactive numpads. Excited to integrate secure local lock boxes so entries can remain completely private.",
            mood="creative",
            tags=json.dumps(["Design", "Ideas"])
        )

    # Package all diary entries for the template
    diary_dict = {}
    for entry in DiaryEntry.objects.all():
        diary_dict[str(entry.date)] = {
            'date': str(entry.date),
            'title': entry.title,
            'content': entry.content,
            'mood': entry.mood,
            'tags': json.loads(entry.tags) if entry.tags else []
        }

    context = {
        'diary_json': json.dumps(diary_dict)
    }
    return render(request, 'diary.html', context)

@require_POST
def save_diary(request):
    try:
        data = json.loads(request.body)
        incoming_dates = list(data.keys())

        # 1. Delete entries that are no longer in incoming data
        DiaryEntry.objects.exclude(entry_id__in=incoming_dates).delete()

        # 2. Update or create incoming entries
        for date_str, entry_data in data.items():
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            DiaryEntry.objects.update_or_create(
                entry_id=date_str,
                defaults={
                    'date': parsed_date,
                    'title': entry_data.get('title', ''),
                    'content': entry_data.get('content', ''),
                    'mood': entry_data.get('mood', ''),
                    'tags': json.dumps(entry_data.get('tags', []))
                }
            )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@ensure_csrf_cookie
def todo(request):
    # Ensure default entries exist if database is fresh
    if not TodoTask.objects.exists():
        now_ms = int(time.time() * 1000)
        TodoTask.objects.create(
            task_id=str(now_ms),
            title="Design premium dashboard layout",
            description="Create a glassmorphic 3-column dashboard layout with glowing meshes and custom styling.",
            completed=False,
            due_date=None,
            priority="high",
            category="Work",
            created_at=now_ms,
            updated_at=now_ms
        )
        TodoTask.objects.create(
            task_id=str(now_ms - 1000),
            title="Configure cloud databases",
            description="Set up Postgres backups, replication, and connection pooling for production scale.",
            completed=True,
            due_date=None,
            priority="medium",
            category="Database",
            created_at=now_ms - 86400000,
            updated_at=now_ms - 86400000
        )
        TodoTask.objects.create(
            task_id=str(now_ms - 2000),
            title="Draft next sprint plan",
            description="Detail user stories, point estimates, and assign tickets for upcoming sprint.",
            completed=False,
            due_date=None,
            priority="low",
            category="Planning",
            created_at=now_ms - 172800000,
            updated_at=now_ms - 172800000
        )

    # Package all todos
    todo_list = []
    for t in TodoTask.objects.all():
        todo_list.append({
            'id': t.task_id,
            'title': t.title,
            'description': t.description,
            'completed': t.completed,
            'dueDate': str(t.due_date) if t.due_date else '',
            'priority': t.priority,
            'category': t.category,
            'createdAt': t.created_at,
            'updatedAt': t.updated_at
        })

    context = {
        'todos_json': json.dumps(todo_list)
    }
    return render(request, 'todo.html', context)


@require_POST
def save_todos(request):
    try:
        data = json.loads(request.body)
        incoming_task_ids = [str(t['id']) for t in data]
        
        # Delete tasks that are no longer in incoming data
        TodoTask.objects.exclude(task_id__in=incoming_task_ids).delete()
        
        # Update or create incoming tasks
        for t_data in data:
            due_date_str = t_data.get('dueDate')
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except Exception:
                    due_date = None
                
            TodoTask.objects.update_or_create(
                task_id=str(t_data['id']),
                defaults={
                    'title': t_data['title'],
                    'description': t_data.get('description', ''),
                    'completed': t_data.get('completed', False),
                    'due_date': due_date,
                    'priority': t_data.get('priority', 'medium'),
                    'category': t_data.get('category', 'Inbox'),
                    'created_at': t_data.get('createdAt', t_data['id']),
                    'updated_at': t_data.get('updatedAt', t_data['id'])
                }
            )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def login_view(request):
    if request.session.get('is_logged_in'):
        return redirect('/')
    
    error = None
    if request.method == 'POST':
        password = request.POST.get('password')
        if password == '62426':
            request.session['is_logged_in'] = True
            return redirect('/')
        else:
            error = 'Incorrect passcode. Access denied.'
            
    return render(request, 'login.html', {'error': error})

def logout_view(request):
    request.session['is_logged_in'] = False
    return redirect('/login/')

@ensure_csrf_cookie
def reminder(request):
    # Pre-populate some reminders if database is empty
    if not Reminder.objects.exists():
        now_ms = int(time.time() * 1000)
        Reminder.objects.create(
            reminder_id=str(now_ms),
            title="Review Workspace Design",
            date=date.today(),
            time=dt_time(18, 0),
            created_at=now_ms,
            updated_at=now_ms
        )

    reminders_list = []
    for r in Reminder.objects.all():
        reminders_list.append({
            'id': r.reminder_id,
            'title': r.title,
            'date': str(r.date),
            'time': r.time.strftime('%H:%M'),
            'createdAt': r.created_at,
            'updatedAt': r.updated_at
        })

    context = {
        'reminders_json': json.dumps(reminders_list)
    }
    return render(request, 'reminder.html', context)

@require_POST
def save_reminders(request):
    try:
        data = json.loads(request.body)
        incoming_ids = [str(r['id']) for r in data]
        
        # Delete reminders not in incoming list
        Reminder.objects.exclude(reminder_id__in=incoming_ids).delete()
        
        # Update or create incoming reminders
        for r_data in data:
            date_val = datetime.strptime(r_data['date'], "%Y-%m-%d").date()
            time_str = r_data['time']
            try:
                time_val = datetime.strptime(time_str, "%H:%M").time()
            except Exception:
                time_val = datetime.strptime(time_str, "%H:%M:%S").time()
                
            Reminder.objects.update_or_create(
                reminder_id=str(r_data['id']),
                defaults={
                    'title': r_data['title'],
                    'date': date_val,
                    'time': time_val,
                    'created_at': r_data.get('createdAt', r_data['id']),
                    'updated_at': r_data.get('updatedAt', r_data['id'])
                }
            )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@ensure_csrf_cookie
def task(request):
    # 1. Pre-populate categories if database is fresh
    if not HabitCategory.objects.exists():
        HabitCategory.objects.create(category_id='cat_health', name='Health', color='emerald')
        HabitCategory.objects.create(category_id='cat_work', name='Work', color='blue')
        HabitCategory.objects.create(category_id='cat_learning', name='Learning', color='purple')
        HabitCategory.objects.create(category_id='cat_mind', name='Mind', color='cyan')
        HabitCategory.objects.create(category_id='cat_personal', name='Personal', color='pink')
        HabitCategory.objects.create(category_id='cat_other', name='Other', color='gray')

    # 2. Pre-populate default habits if database is fresh
    if not Habit.objects.exists():
        today_str = date.today().strftime('%Y-%m-%d')
        now_ms = int(time.time() * 1000)
        Habit.objects.create(habit_id=f"habit_{now_ms}", title="30-Minute Workout", category="Health", created_at=today_str)
        Habit.objects.create(habit_id=f"habit_{now_ms+1}", title="Read 10 Pages of a Book", category="Learning", created_at=today_str)
        Habit.objects.create(habit_id=f"habit_{now_ms+2}", title="Morning Reflection & Breathing", category="Mind", created_at=today_str)
        Habit.objects.create(habit_id=f"habit_{now_ms+3}", title="Review Tasks & Log Expenses", category="Work", created_at=today_str)

    # 3. Load categories from DB
    categories_list = []
    for c in HabitCategory.objects.all():
        categories_list.append({
            'id': c.category_id,
            'name': c.name,
            'color': c.color
        })

    # 4. Load habits from DB
    tasks_list = []
    for h in Habit.objects.all():
        tasks_list.append({
            'id': h.habit_id,
            'title': h.title,
            'category': h.category,
            'createdAt': h.created_at
        })

    # 5. Load progress history from DB
    history_dict = defaultdict(list)
    for p in HabitProgress.objects.all():
        history_dict[p.date].append(p.habit_id)

    context = {
        'categories_json': json.dumps(categories_list),
        'tasks_json': json.dumps(tasks_list),
        'history_json': json.dumps(dict(history_dict))
    }
    return render(request, 'task.html', context)


@require_POST
def save_task_state(request):
    try:
        data = json.loads(request.body)
        
        # 1. Update/Save categories
        incoming_categories = data.get('categories', [])
        incoming_cat_ids = [str(c['id']) for c in incoming_categories]
        HabitCategory.objects.exclude(category_id__in=incoming_cat_ids).delete()
        for cat in incoming_categories:
            HabitCategory.objects.update_or_create(
                category_id=str(cat['id']),
                defaults={
                    'name': cat['name'],
                    'color': cat.get('color', 'blue')
                }
            )

        # 2. Update/Save habits (tasks)
        incoming_tasks = data.get('tasks', [])
        incoming_task_ids = [str(t['id']) for t in incoming_tasks]
        Habit.objects.exclude(habit_id__in=incoming_task_ids).delete()
        for t in incoming_tasks:
            Habit.objects.update_or_create(
                habit_id=str(t['id']),
                defaults={
                    'title': t['title'],
                    'category': t['category'],
                    'created_at': t.get('createdAt', '')
                }
            )

        # 3. Update/Save progress history logs
        incoming_history = data.get('history', {})
        HabitProgress.objects.all().delete()
        for date_str, habit_ids in incoming_history.items():
            for h_id in habit_ids:
                if h_id in incoming_task_ids:
                    HabitProgress.objects.create(
                        habit_id=h_id,
                        date=date_str
                    )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)