from flask import Flask,send_from_directory,render_template, request, redirect, url_for,session,jsonify
import os
import json
from  hashlib import sha256
from random import randint
from flask_cors import CORS
from dotenv import load_dotenv
from classes import Track,User,Trainee
from progress_calculator import calculate_progress


load_dotenv()

app = Flask(__name__, static_folder="../client/dist")

app.secret_key = os.environ.get('SECRET_KEY')

CORS(app, supports_credentials=True)


if __name__ == "__main__":
    app.run(debug=True)



# As the app is simple, i'll depend on flask session for the authentication and authorization: 
# 1. save a secure session cookie in the browser upon login or signup, which will contain the values for user_id (for authentication) and role (for authorization) 
# 2. send that cookie every time a request is made to the server to use the info within it for authorization and authentication 
# 3. I won't cover all the possible cases and outputs of the apis for the sake of simplicity as all the routes will eb using 401 status code.

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
            user_data = get_user(session['user_role'], session['user_id'])
            if user_data['name'] == "":
                return redirect(url_for('profile'))
            return redirect(url_for('dashboard'))
        else:
            error = 'Failed to login, wrong credentials.'
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
        # Handle signup logic, should have a logic that checks if the user already exists but for simplicity I'll just create a new user
        user_name = request.form['username']
        password = request.form['password']
        role = request.form['role']
        id = simple_generate_id()
        file = open('users.txt','a')
        hashed_pass = simple_sha_hash(password)
        file.write(f'{user_name} {hashed_pass} {id} {role} \n') 
        file.close()
        # create an entry in database.json for the new user (a place holder that will be updated later)
        with open('database.json', 'r') as f:
            data = json.load(f)
            if role == 'trainer':  
                data['trainers'].append({'id': id,"name": "","photo_path": "","role": "trainer","tracks": []})
            else:
                data['trainees'].append({'id': id, "name": "","photo_path": "", "role": "trainee", "progress": []})
        with open('database.json', 'w') as f:
            json.dump(data, f)
        # save the user id and role in the session and redirect to the Dashboard page
        session['user_id'] = id
        session['user_role'] = role
        return redirect(url_for('serve',path='profile'))
        # return redirect(url_for('dashboard'))
    
    # for GET requests
    if 'user_id' in session:
        # the user is already logged in so he should be redirected to the dashboard
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')



@app.route('/logout')
def logout():
    # remove id and role from session 
    session.clear()
    # redirect to the login page
    return redirect(url_for('login'))



@app.route('/dashboard')
def dashboard():
    if "user_id" not in session:
        return redirect(url_for('login'))
    user = get_user(session['user_role'], session['user_id'])
    if user['name'] == "":
        return redirect(url_for('profile'))
    return send_from_directory(app.static_folder, 'index.html')

# profile will be accessed only once
@app.route('/profile')
def profile():
    if "user_id" not in session:
        return redirect(url_for('login'))
    user = get_user(session['user_role'], session['user_id'])
    if user['name'] != "":
        return redirect(url_for('dashboard'))
    return send_from_directory(app.static_folder, 'index.html')

# update trainer or trainee data in database
@app.route('/api/profile', methods=['POST'])
def update_profile():
    if not ('user_id' in session) :
        return jsonify({'error': 'unauthorized'}), 401
    user_data = get_user(session['user_role'], session['user_id'])
    if user_data is None:
        # most probably this status code is wrong 
        return jsonify({'error': 'user not found'}), 404
    user_data['name'] = request.form['first_name'] + ' ' + request.form['last_name']
    user_data['photo_path'] = request.form['photo_path']
    update_ok = update_user_data(user_data)
    if update_ok:
        return redirect(url_for('dashboard'))
    return jsonify({'error': 'failed to update profile'}), 500
        
    


@app.route('/api/dashboard')
def api_dashboard():
    if 'user_id' in session: 
        user_data = get_user(session['user_role'], session['user_id'])
        if user_data is None:
            return jsonify({'error': 'user not found'}), 404
        user = User(user_data['id'], user_data['name'], user_data['photo_path'], user_data['role'])
        return jsonify({'data':user.get_profile_info()}), 200
   
    return jsonify({'error': 'unauthorized'}), 401


# get all tracks
@app.route('/api/tracks', methods=['GET'])
def api_get_tracks():
    # no need for authorization as both trainers ad trainees can view all tracks
    if not ('user_id' in session):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    return jsonify({'data': data['tracks']})



# get overview
@app.route('/api/overview', methods=['GET'])
def api_get_overview():
    if not ('user_id' in session):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    overview = []
    for track in data['tracks']:
        # calculate track progress
        progress_percentage = calculate_progress(track['start_time'], track['duration_value'], track['duration_unit'])
        if progress_percentage < 0:
            progress_percentage = 0
        # calculate trainees progress
        trainees_progress = []
        for trainee in data['trainees']:
            if trainee['id'] not in track['trainees']:
                continue
            # loop over progress for each trainee cause he might be in multiple tracks
            for item in trainee['progress']:
                if item['track_id'] == track['id']:
                    trainees_progress.append({'name':trainee['name'], 'id':trainee['id'],"photo_path":trainee['photo_path'], 'progress':item['percentage']})
        # populate overview
        overview.append({'info':{ "id": track['id'], 'progress_percentage':progress_percentage, 'title':track['title']}, 'trainees_progress':trainees_progress}) 
    # should add error handling 
    return jsonify({'data': overview}), 200        
    

    

# add new track
@app.route('/api/tracks', methods=['POST'])
def api_add_track():
    if not ('user_id' in session and session['user_role'] == 'trainer'):
        return jsonify({'error': 'unauthorized'}), 401
    data = request.json
    # Validate that all required fields are present
    required_fields = ['title', 'start_time', 'duration_unit', 'duration_value', 'description', 'trainers', 'trainees']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    id = simple_generate_id()
    new_track = Track(id, data['title'], data['start_time'], data['duration_unit'], data['duration_value'], data['description'], data['trainers'], data['trainees'])
    with open('./database.json','r') as file:
        database = json.load(file)
    database['tracks'].append(new_track.to_dict())
    # add new track to trainers
    new_trainers_list,update_status = add_track_to_trainer(database['trainers'], id, data['trainers'])
    database['trainers'] = new_trainers_list
    # add new track to trainees 
    new_trainees_list,update_status = add_track_to_trainee(database['trainees'], id, data['trainees'])
    database['trainees'] = new_trainees_list
    with open('./database.json','w') as file:
        json.dump(database, file, indent=4)
    # return success, should implement a way to check if the data was added correctly or not and return fail status if not
    return jsonify({'success': True}),201



# for a trainer or trainee to add himself to a track
@app.route('/api/<track_id>/<role>/<user_id>', methods=['POST'])
def api_add_user_to_track(track_id, role, user_id):
    if not ('user_id' in session and session['user_role'] == role):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    # add user to a track
    new_tracks_list,is_track_updated = add_user_to_track(data['tracks'], track_id, user_id,role)
    data['tracks'] = new_tracks_list
    if not is_track_updated:
        return jsonify({'error': 'invalid track'}), 400
    # add track to a user
    if role == 'trainer':
        new_trainers_list,update_status = add_track_to_trainer(data['trainers'], track_id, [user_id])
        data['trainers'] = new_trainers_list
    elif role == 'trainee':
        new_trainees_list,update_status = add_track_to_trainee(data['trainees'], track_id, [user_id])
        data['trainees'] = new_trainees_list
    else:
        return jsonify({'error': 'invalid user'}), 400
    # write changes to db
    with open('./database.json','w') as file:
        json.dump(data, file, indent=4)
    return jsonify({'success': True}),201
    

# for a trainer or trainee to remove himself from a track
@app.route('/api/<track_id>/<role>/<user_id>', methods=['DELETE'])
def api_remove_user_from_track(track_id, role, user_id):
    if not ('user_id' in session and session['user_role'] == role):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    # remove user from a track
    is_track_updated = False
    for track in data['tracks']:
        if track['id'] == track_id:                
            track[role+'s'].remove(user_id)
            is_track_updated = True
            break
    if not is_track_updated:
        return jsonify({'error': 'invalid track'}), 400
    # remove track from a user
    if role == 'trainer':
        for trainer in data['trainers']:
            if trainer['id'] == user_id:
                trainer['tracks'].remove(track_id)
    elif role == 'trainee':
        for trainee in data['trainees']:
            if trainee['id'] != user_id: 
                continue 
            for track in trainee['progress']:
                if track['track_id'] == track_id:
                    trainee['progress'].remove(track)
                    break
    else:
        return jsonify({'error': 'invalid user'}), 400
    # write changes to db
    with open('./database.json','w') as file:
        json.dump(data, file, indent=4)
    return jsonify({'success': True}),201
    
        


# get list of trainers who are not assigned to a track, the api intended to be called while assigning trainers to a track by another trainer and using the track_id in the track card from within the frontend app
@app.route('/api/trainers', methods=['GET'])
def api_get_trainers():
    if not ('user_id' in session and session['user_role'] == 'trainer'):
        return jsonify({'error': 'unauthorized'}), 401
    with open('./database.json','r') as file:
        data = json.load(file)
    track_id = request.args.get('track_id')
    if track_id is None or track_id not in data['tracks']:
        return jsonify({'data': data['trainers']}), 200
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




# update trainee progress, only trainee himself can update his progress (only for now)
@app.route('/api/trainees/<id>/progress', methods=['POST'])
def api_update_trainee_progress(id):
    if not ('user_id' in session and session['user_role'] == 'trainee'):
        return jsonify({'error': 'unauthorized'}), 401
    trainee_data = get_user(session['user_role'], id)
    track_to_update = request.form['track_id']
    # validate input and get the number
    new_progress = get_int_progress(request.form['progress'],trainee_data['progress'],track_to_update)
    trainee_instance = Trainee(trainee_data['id'], trainee_data['name'], trainee_data['photo_path'], trainee_data['role'], trainee_data['progress'])
    update_status = trainee_instance.update_track_progress(track_to_update,new_progress)
    # update database
    with open('./database.json','r') as file:
        data = json.load(file)
    for trainee in data['trainees']:
        if trainee['id'] == id:
            data['trainees'].remove(trainee)
            data['trainees'].append(trainee_instance.get_profile_info())
            break 
    with open('./database.json','w') as file:
        json.dump(data, file, indent=4)
    return jsonify({'success': True}), 200


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




def add_track_to_trainer(list_to_be_modified, track_id, trainers_id_list):
    updated = False        
    for trainer in list_to_be_modified:
        if trainer['id'] in trainers_id_list:
            trainer['tracks'].append(track_id)
            updated = True
    return list_to_be_modified, updated

def add_track_to_trainee(list_to_be_modified, track_id, trainees_id_list):
    updated = False
    for trainee in list_to_be_modified:
        if trainee['id'] in trainees_id_list:  
            trainee['progress'].append({'track_id':track_id,'percentage':0})
            updated = True
    return list_to_be_modified, updated
        

def update_user_data(new_data):
    try:
        with open ('./database.json','r') as file:
            data = json.load(file)
        new_users_list = [user for user in data[new_data['role']+'s'] if user['id'] != new_data['id']]
        new_users_list.append(new_data)
        data[new_data['role']+'s'] = new_users_list
        with open ('./database.json','w') as file:
            json.dump(data, file, indent=4)
        return True
    except:
        False



def add_user_to_track(list_to_be_modified, track_id,user_id,role):
    updated = False
    for track in list_to_be_modified:
        if track['id'] == track_id:                
            track[role+'s'].append(user_id)
            updated = True
            break
    return list_to_be_modified, updated


def get_int_progress(input_string, progress_list, track_id):
    try:
        return int(input_string)
    except (TypeError, ValueError):
        for prog in progress_list:
            if prog['track_id'] == track_id:
                return int(prog['percentage'])
        return 0
    


def validate_credentials(name,password):
    hashed_pass = simple_sha_hash(password)
    with open('users.txt') as file:
        for line in file:
            [stored_username,stored_password,stored_id,stored_role, _] = line.split(' ')
            if name == stored_username and hashed_pass == stored_password: 
                return{ 'exists': True,'id':stored_id, 'role': stored_role}
    return {'exists': False, 'role': None,'id':None}


def get_user(role, id):
    with open('./database.json','r') as file:
        data = json.load(file)
    # won't handle the case where the role is neither trainer nor trainee as session asserts that role won't be tampered
    for record in data[role+'s']:
        if record['id'] == id:
            return record
    # not found
    return None



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