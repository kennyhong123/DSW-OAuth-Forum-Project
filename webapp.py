from flask import Flask, redirect, url_for, session, request, jsonify, Markup
from flask_oauthlib.client import OAuth
from flask import render_template
from flask_pymongo import PyMongo
from bson import ObjectId
from flask import flash

import pprint
import os
import json
import pymongo
import sys

app = Flask(__name__)

app.debug = True #Change this to False for production

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies

url = 'mongodb://{}:{}@{}:{}/{}'.format(
        os.environ["MONGO_USERNAME"],
        os.environ["MONGO_PASSWORD"],
        os.environ["MONGO_HOST"],
        os.environ["MONGO_PORT"],
        os.environ["MONGO_DBNAME"])
    
client = pymongo.MongoClient(url)
db = client[os.environ["MONGO_DBNAME"]]
collection = db['forum-posts'] #put the name of your collection in the quotes

oauth = OAuth(app)

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)

#use a JSON file to store the past posts.  A global list variable doesn't work when handling multiple requests coming in and being handled on different threads
#Create and set a global variable for the name of your JSON file here.  The file will be created on Heroku, so you don't need to make it in GitHub
file = 'posts.json'
os.system("echo '[]'>" + file)

@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/')
def home():
    return render_template('home.html', past_posts=posts_to_html())

@app.route('/posted', methods=['POST'])
def post():
    #This function should add the new post to the JSON file of posts and then render home.html and display the posts.  
    #Every post should include the username of the poster and text of the post.
    if request.form['message'] is '':
        flash("Type something bud.",'warning') #☭
    else:
        collection.insert_one({"post":[session['user_data']['login'], request.form['message'], session['user_data']['avatar_url']]})
    return render_template('home.html', past_posts=posts_to_html())

def posts_to_html():
    post = ""
    try:
        for document in collection.find():
            post += "<table id='postTable'><tr><td class='un'><b>Username</b></td><td class='post'><b>Post</b></td></tr>" + '<tr>' + '<td class="un">' + '<img src="'+ document['post'][2] + '" class="avatar"><a href=' + '"https://github.com/' + document['post'][0] + '">'+ '@' + document['post'][0] +'</a>' + '</td><td class="post">'
            swearwords = ['lorax','f-word','c-word','n-word','heckin']
            if '@' in document['post'][1]:
                username = ""
                massage = ""
                for character in document['post'][1]:
                    if " " in character:
                        username = stuff[1].split(" ",1)[0]
                        massage = stuff[1].split(" ",1)[1]
                        post+='<a href=' + '"https://github.com/' + username.split("@",1)[1] + '">' + username +'</a>' + '  ' + massage
            elif swearwords[0] in document['post'][1]:
                post += "Offensive language is not tolerated."
            elif swearwords[1] in document['post'][1]:
                post += "Offensive language is not tolerated."
            elif swearwords[2] in document['post'][1]:
                post += "Offensive language is not tolerated."
            elif swearwords[3] in document['post'][1]:
                post += "Offensive language is not tolerated."
            elif swearwords[4] in document['post'][1]:
                post += "Offensive language is not tolerated."
            else:
                post += document['post'][1]
            if 'github_token' in session:
                if session['user_data']['login'] == document['post'][0]:
                    post += '</td><td><form action="/deletePost" method="post"><button type="submit" name="delete" value="'+  str(document.get('_id')) +'" class="btn btn-danger">Delete</button></form></td></tr></table>'
            post += '</td></tr></table>'
    except Exception as e:
        print(e)
    formattedPost = Markup(post)
    return formattedPost

@app.route('/deletePost', methods=['POST']) #this does things
def deletePost():
    #delete post
    global collection
    collection.delete_one({"_id" : ObjectId(str(request.form['delete']))})
    return render_template('home.html', past_posts=posts_to_html())

#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='https')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    flash("You were Logged Out.",'info')
    return render_template('home.html',past_posts=posts_to_html())

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        flash('Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'],'warning')       
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            flash('You were successfully logged in as ' + session['user_data']['login'],'info')
        except Exception as inst:
            session.clear()
            print(inst)
            flash('Unable to login, please try again.','warning')
    return render_template('home.html',past_posts=posts_to_html())

#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')


if __name__ == '__main__':
    app.run()
