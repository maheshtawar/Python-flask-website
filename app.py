from asyncio.windows_events import NULL
from email import message
from fileinput import filename
import math
import os
from pydoc import pager
from flask import Flask, render_template, request ,session,redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import json
from flask_mail import Mail

with open('templates\\config.json','r') as c:
    parameter = json.load(c)["parameter"]

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = parameter['uploader location']

app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',  
    MAIL_USE_TLS = False,
    MAIL_USE_SSL = True,
    MAIL_USERNAME = parameter['gmail-user'],
    MAIL_PASSWORD = parameter['gmail-password']
)
mail = Mail(app)


if parameter['local_server']:
    app.config['SQLALCHEMY_DATABASE_URI'] = parameter['local_url']
else:    
    app.config['SQLALCHEMY_DATABASE_URI'] = parameter['production_url']
db = SQLAlchemy(app)


class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    sub_title = db.Column(db.String(40), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(20), nullable=True)
    

@app.route("/")
def home():
    # Page Previous and Next Logic
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(parameter['no_of_post']))
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page = last # to see last post i put page=last here else page = 1
    page = int(page)
    posts = posts[(page-1)*int(parameter['no_of_post']):(page-1)*int(parameter['no_of_post']) + int(parameter['no_of_post'])]
    # Pagination Logic
    # First
    if page==1:
        prev = "#"
        next = "/?page=" + str(page+1)
    # last
    elif page==last:
        prev = "/?page=" + str(page-1)
        next = "#"
    # middle
    else:
        prev = "/?page=" + str(page-1)
        next = "/?page=" + str(page+1)
    
    # posts = Posts.query.filter_by().all() [0:parameter['no_of_post']]
    return render_template('index.html',posts = posts,prev=prev,next=next,page=page,last=last,parameter=parameter)


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/admin')


@app.route("/uploader" , methods=['GET', 'POST'])
def uploader():
    if "user" in session and session['user']== parameter['admin_username']:        
        if request.method=="POST":
            f = request.files['file']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
            return "Uploaded Successfully"

@app.route("/delete/<string:sno>" , methods=['GET', 'POST'])
def delete(sno):
    if "user" in session and session['user']== parameter['admin_username']:        
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/admin')

@app.route("/edit/<string:sno>" , methods=['GET', 'POST'])
def edit(sno):
    if "user" in session and session['user']== parameter['admin_username']:        
        if request.method=="POST":
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()
        
        # New Post
            if sno=='0':
                post = Posts(title=box_title, slug=slug, content=content, sub_title=tline, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
        # Edit Post 
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.sub_title = tline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+sno)

        post = Posts.query.filter_by(sno=sno).first()
        # to solve new post error start
        if sno == '0':
            post=Posts(sno=sno,title='', slug='', content='', sub_title='', img_file='')
        # end solve
        return render_template('edit.html', post=post,parameter=parameter)

@app.route("/admin", methods = ['GET', 'POST'])
def adminLogin():
    # If already login in
    if('user' in session and session['user']== parameter['admin_username']):
        posts = Posts.query.all()
        return render_template('dashboard.html',posts = posts,parameter=parameter)

    if(request.method=='POST'):
        username = request.form.get('username')
        password = request.form.get('password')
        if(username== parameter['admin_username'] and password==parameter['admin_password']):
            # set session variable
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html',posts = posts,parameter=parameter)
        else:
            message = "Please Enter Valid Username And Password"
            return render_template('adminLogin.html',message=message,parameter=parameter)
    
    return render_template('adminLogin.html',parameter=parameter)


@app.route("/about")
def about():
    return render_template('about.html',parameter=parameter)


@app.route("/post/<string:post_slug>",methods=['GET'])
def fnpost(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    
    return render_template('post.html',post=post,parameter=parameter)


@app.route("/contact", methods = ['GET', 'POST'])
def contact():
    if(request.method=='POST'):
        '''Add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contact(name=name,email = email, phone = phone, msg = message, date= datetime.now() )
        db.session.add(entry)
        db.session.commit()
        mail.send_message('Contact Mail from '+ name,
                            sender=(f"{name} <{parameter['gmail-user']}>"),
                            recipients=['maheshtawar@pm.me'],
                            body = "Hello Sir,\n\n\t" + message + "\n\nThanks,\n" + name + "\n" + phone)
    return render_template('contact.html',parameter=parameter)


app.run(debug=True)
