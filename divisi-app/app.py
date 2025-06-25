import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Model
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.mscz'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            score = Score(filename=file.filename)
            db.session.add(score)
            db.session.commit()
            return redirect(url_for('scores'))
    return render_template('index.html')

@app.route('/scores')
def scores():
    all_scores = Score.query.order_by(Score.timestamp.desc()).all()
    return render_template('scores.html', scores=all_scores)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Initialize DB
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
