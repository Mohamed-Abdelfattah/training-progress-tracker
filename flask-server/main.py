from flask import Flask,send_from_directory,render_template, request, redirect, url_for,session,jsonify, make_response
import os
import json
from  hashlib import sha256
from random import randint
from flask_cors import CORS
from classes import Track


# Assuming `app` is your Flask application
app = Flask(__name__, static_folder="../client/dist")

app.secret_key = 'super_duper_secret_key_that_no_one_should_ever_know'

# app.config['SESSION_COOKIE_SAMESITE'] = 'None'
CORS(app, supports_credentials=True)


if __name__ == "__main__":
    app.run(debug=True)



# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Handle login logic 
        user_name = request.form['username']
        password = request.form['password']
        user = validate_credentials(user_name, password)
        # save the user id and role in the session if the user exists
        if user['exists']:
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            # redirect to the Dashboard page 
            # print('@signup ---- before redirect ---- session =',session)
            return redirect(url_for('dashboard'))
        else:
            error = 'Failed to login, wrong credentials.'
            # view function which is handles the route can return up to 3 values (tuple), first is the response body, second is the status code, third is the headers. Flask interprets the tuple without the need to create a Response object
            return render_template('login.html', error=error), 401
    
    # for GET requests
    if 'user_id' in session:
        # the user is already logged in so he should be redirected to teh dashboard
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

# Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Handle signup logic
        user_name = request.form['username']
        password = request.form['password']
        role = request.form['role']
        id = simple_generate_id()
        file = open('users.txt','a')
        hashed_pass = simple_sha_hash(password)
        file.write(f'{user_name} {hashed_pass} {id} {role}\n') 
        file.close()
        # save the user id and role in the session and redirect to the Dashboard page
        session['user_id'] = id
        session['user_role'] = role
        # print('@signup ---- before redirect ---- session =',session)
        return redirect(url_for('dashboard'))
    
    # for GET requests
    if 'user_id' in session:
        # the user is already logged in so he should be redirected to teh dashboard
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')



@app.route('/logout')
def logout():
    # remove all is and role from session 
    session.clear()
    # redirect to the login page
    return redirect(url_for('login'))


@app.route('/api/dashboard')
def api_dashboard():
    print('@api/dashboard ------ session =',session)
    for i in (request.headers.keys()):
        print(i)
        print(request.headers[i])
    print(request.headers.keys())
    if 'user_id' in session:
        # get data from db 
        return jsonify({'data': 'some data','another_data': 'another data'})
    # unauthorized
    return jsonify({'error': 'unauthorized'}), 401

@app.route('/dashboard')
def dashboard():
    print('@dashboard ------ session =',session)
    for i in (request.headers.keys()):
        print(i)
        print(request.headers[i])
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    return send_from_directory(app.static_folder, 'index.html')


# get all tracks
@app.route('/api/tracks', methods=['GET'])
def api_get_tracks():
    # no need for authorization as both trainers ad trainees can view all tracks
    if not ('user_id' in session):
        return jsonify({'error': 'unauthorized'}), 401
    # get data from db
    with open('./database.json','r') as file:
        data = json.load(file)
    return jsonify({'data': data['tracks']})

# get track by id
@app.route('/api/tracks/<id>', methods=['GET'])
def api_get_track(id):
    if not ('user_id' in session):
        return jsonify({'error': 'unauthorized'}), 401
    # get data from db
    with open('./database.json','r') as file:
        data = json.load(file)
    for track in data['tracks']:
        if track['id'] == id:
            return jsonify({'data': track}), 200
    return jsonify({'error': 'not found'}), 404


# add new track
@app.route('/api/tracks', methods=['POST'])
def api_add_track():
    if not ('user_id' in session and session['user_role'] == 'trainer'):
        return jsonify({'error': 'unauthorized'}), 401
    id = simple_generate_id()
    new_track = Track(id, request.form['title'], request.form['start_time'], request.form['duration'], request.form['description'], request.form['trainers'], request.form['trainees'], request.form['milestones'], request.form['resources'])
    # add new track to db, using 'with' keyword will assert that python closes the file after reading or writing to it
    with open('./database.json','r') as file:
        data = json.load(file)
    data['tracks'].append(new_track.to_dict())
    with open('./database.json','w') as file:
        json.dump(data, file, indent=4)
    # return success, should implement a way to check if the data was added correctly or not and return fail status if not
    return jsonify({'success': True}),201
    


# get list of trainers who are not assigned to a track, the api intended to be called while assigning trainers to a track by another trainer and using the track_id in the track card from within the frontend app
@app.route('/api/trainers', methods=['GET'])
def api_get_trainers():
    if not ('user_id' in session and session['user_role'] == 'trainer'):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    track_id = request.args.get('track_id')
    # should respond to the case where track_id is not valid, but as the api should be called from within the frontend app, i will assume that it is valid, but only to prevent runtime errors
    if track_id is None or track_id not in data['tracks']:
        return jsonify({'error': 'Invalid track ID'}), 400
    return jsonify({'data': [trainer for trainer in data['trainers'] if trainer['id'] not in data['tracks'][track_id]['trainers']]}), 200



# get list of trainees who aren't enrolled into a track or all the trainees in the database
@app.route('/api/trainees', methods=['GET'])
def api_get_trainees():
    if not ('user_id' in session):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    # return a list of trainees who aren't enrolled into a track, for trainers to add them 
    track_id = request.args.get('track_id')
    if track_id is not None:
        return jsonify({'data': [trainee for trainee in data['trainees'] if trainee['id'] not in data['tracks'][track_id]['trainees']]}), 200
    # return all the trainees otherwise
    return jsonify({'data': data['trainees']}), 200


# get trainee by id
@app.route('/api/trainees/<id>', methods=['GET'])
def api_get_trainee(id):
    if not ('user_id' in session):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    for trainee in data['trainees']:
        if trainee['id'] == id:
            return jsonify({'data': trainee}), 200 
    return jsonify({'error': 'not found'}), 404


# update trainee progress
@app.route('/api/trainees/<id>/progress', methods=['POST'])
def api_update_trainee_progress(id):
    if not ('user_id' in session and session['user_id'] == id and session['user_role'] == 'trainee'):
        return jsonify({'error': 'unauthorized'}), 401
    updated_progress = request.form['progress']
    track_to_update = request.form['track_id']
    with open('./database.json','r') as file:
        data = json.load(file)
    for trainee in data['trainees']:
        if trainee['id'] == id:
            for prog in trainee['progress']:
                if prog['track_id'] == track_to_update:
                    prog['percentage'] = updated_progress
                    with open('./database.json','w') as file:
                        json.dump(data, file, indent=4)
                    return jsonify({'success': True}), 200
    return jsonify({'error': 'not found'}), 404


# add trainee to track
@app.route('/api/trainees/<id>/track', methods=['POST'])
def api_add_trainee_to_track(id):
    # the authorized people to add trainee to track are (any trainer) and (trainees themselves)
    if not ('user_id' in session and (( session['user_role'] == 'trainee' and session['user_id'] == id) or session['user_role'] == 'trainer')):
        return jsonify({'error': 'unauthorized'}), 401
    track_id = request.form['track_id']
    with open('./database.json','r') as file:
        data = json.load(file)
    for track in data['tracks']:
        if track['id'] == track_id:
            track['trainees'].append(id)
            with open('./database.json','w') as file:
                json.dump(data, file, indent=4)
            return jsonify({'success': True}), 200
    return jsonify({'error': 'not found'}), 404



# handle all other routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')




def validate_credentials(name,password):
    file = open('users.txt')
    hashed_pass = simple_sha_hash(password)
    for line in file:
        [stored_username,stored_password,stored_id,stored_role] = line.split(' ')
        if name == stored_username and hashed_pass == stored_password: 
            return{ 'exists': True,'id':stored_id, 'role': stored_role}
    return {'exists': False, 'role': None,'id':None}



def simple_hash(word):
    '''this is a very simple hashing function, will be used simulate the auth flow'''
    hash = 0
    for char in word:
        hash += ord(char)
    return hash

def simple_sha_hash(word):
    '''this is simple hashing function, uses SHA256 function, will be used to simulate the auth flow'''
    return sha256(word.encode('utf-8')).hexdigest()

def simple_generate_id():
    return str(randint(100000000,999999999))