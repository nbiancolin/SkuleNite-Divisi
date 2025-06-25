import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template, send_from_directory, abort
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
    title = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    version = db.Column(db.String(6), nullable=False) #eg. v1.0.0
    timestamp = db.Column(db.DateTime, default=datetime.now)

def increment_version(version: str, version_type: str) -> str:
    """ Helper Fn to process version number strings and increment them"""
    if version_type not in ["major", "minor", "release"]:
        #TODO: Do something
        print('oops')
    
    major = int(version[1])
    minor = int(version[3])
    patch = int(version[5])
    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    return f"v{major}.{minor}.{patch}"


# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):

            # check if score with this name exists already
            score = Score.query.filter_by(title=request.form["title"]).first()
            if score:
                score.filename = file.filename
                updated_version = increment_version(score.version, request.form["type"])
                score.version = updated_version
                score.timestamp = datetime.now()
            else:
                score = Score(title=request.form["title"], filename=file.filename, version="v1.0.0")
                db.session.add(score)

            folder_path = os.path.join(app.config["UPLOAD_FOLDER"], request.form["title"], score.version)
            os.makedirs(folder_path, exist_ok=True)

            filepath = os.path.join(folder_path, file.filename)
            file.save(filepath)

            #only update DB if file was successfully saved
            db.session.commit()

            return redirect(url_for('scores'))
    return render_template('index.html')

@app.route('/scores')
def scores():
    all_scores = Score.query.order_by(Score.timestamp.desc()).all()
    return render_template('scores.html', scores=all_scores)

@app.route('/uploads/<path:filepath>')
def uploaded_file(filepath):
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
    if not os.path.isfile(full_path):
        abort(404)
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename)

# Initialize DB
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
