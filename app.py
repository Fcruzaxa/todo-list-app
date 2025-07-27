from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "secret"
tasks = []

@app.route('/')
def index():
    return render_template('index.html', tasks=tasks)

@app.route('/add', methods=['POST'])
def add():
    repeat = request.form.get('repeat') == 'on'
    repeat_days = request.form.getlist('repeat_days') if repeat else []

    task = {
        'id': str(uuid.uuid4()),
        'title': request.form['title'],
        'date': request.form['date'],
        'note': request.form.get('note'),
        'repeat': repeat,
        'repeat_days': repeat_days,
        'folder': request.form['folder'],
        'alarm': request.form.get('alarm'),
        'shared': False,
    }
    tasks.append(task)
    flash('Task added!')
    return redirect(url_for('index'))


@app.route('/delete/<task_id>')
def delete(task_id):
    global tasks
    tasks = [t for t in tasks if t['id'] != task_id]
    flash('Task deleted!')
    return redirect(url_for('index'))

@app.route('/share/<task_id>')
def share(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)
    return render_template('shared_task.html', task=task)

@app.route('/accept/<task_id>')
def accept(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task:
        task['shared'] = True
        flash("Task accepted!")
    return redirect(url_for('index'))

@app.route('/decline/<task_id>')
def decline(task_id):
    flash("Task declined!")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
