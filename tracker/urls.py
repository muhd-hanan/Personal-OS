from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('expense/', views.expense, name='expense'),
    path('notes/', views.notes, name='notes'),
    path('diary/', views.diary, name='diary'),
    path('todo/', views.todo, name='todo'),
    path('task/', views.task, name='task'),
    path('reminder/', views.reminder, name='reminder'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/save_data/', views.save_data, name='save_data'),
    path('api/save_notes/', views.save_notes, name='save_notes'),
    path('api/save_diary/', views.save_diary, name='save_diary'),
    path('api/save_todos/', views.save_todos, name='save_todos'),
    path('api/save_reminders/', views.save_reminders, name='save_reminders'),
    path('api/tracker/create/', views.create_tracker, name='create_tracker'),
    path('api/tracker/delete/', views.delete_tracker, name='delete_tracker'),
    path('api/entry/save/', views.save_entry, name='save_entry'),
    path('api/entry/delete/', views.delete_entry, name='delete_entry'),
    path('api/save_task_state/', views.save_task_state, name='save_task_state'),
]
