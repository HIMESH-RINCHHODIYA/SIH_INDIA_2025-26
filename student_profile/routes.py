from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os

profile_bp = Blueprint('profile', __name__, template_folder='../templates', static_folder='../static')

UPLOAD_FOLDER = 'static/uploads'

user_data = {
    'name': 'HIMESH RINCHHODIYA',
    'dob': '2005-08-30',
    'contact': '9685527886',
    'program': 'BTECH',
    'year': '2',
    'branch': 'CSBS',
    'roll_no': '25',
    'admission_date': '2023-07-01',
    'photo': '',
    'id_card': '',
    'certificate': '',
    'transcript': ''
}

@profile_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    global user_data

    if request.method == 'POST':
        user_data['name'] = request.form.get('name')
        user_data['dob'] = request.form.get('dob')
        user_data['contact'] = request.form.get('contact')
        user_data['program'] = request.form.get('program')
        user_data['year'] = request.form.get('year')
        user_data['branch'] = request.form.get('branch')
        user_data['roll_no'] = request.form.get('roll_no')
        user_data['admission_date'] = request.form.get('admission_date')

        for field in ['photo', 'id_card', 'certificate', 'transcript']:
            file = request.files.get(field)
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                user_data[field] = filepath

        return redirect(url_for('profile.profile'))

    return render_template('profile.html', user=user_data)
