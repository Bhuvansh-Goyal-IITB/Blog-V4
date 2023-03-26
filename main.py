import os
from datetime import date
from functools import wraps
from typing import List
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
ckeditor = CKEditor(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


def login_required(function):
    @wraps(function)
    def inner(*args, **kwargs):
        if current_user.is_authenticated:
            return function(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return inner


def needs_to_be_users_post(function):
    @wraps(function)
    def inner(*args, **kwargs):
        post = db.session.query(BlogPost).get(kwargs['post_id'])
        if post in current_user.posts:
            return function(*args, **kwargs)
        else:
            abort(403)
    return inner


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = Column(Integer, primary_key=True)
    author: Mapped["User"] = relationship(back_populates="posts")
    author_id = Column(Integer, ForeignKey('users.id'), unique=True)
    title = Column(String(250), unique=True, nullable=False)
    subtitle = Column(String(250), nullable=False)
    date = Column(String(250), nullable=False)
    body = Column(db.Text, nullable=False)
    img_url = Column(String(250), nullable=False)
    comments: Mapped[List["Comment"]] = relationship(back_populates="post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('users.id'), unique=True)
    author: Mapped["User"] = relationship(back_populates="comments")
    post_id = Column(Integer, ForeignKey("blog_posts.id"))
    post: Mapped["BlogPost"] = relationship(back_populates="comments")
    text = Column(db.Text, nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False, unique=True)
    password = Column(String(250), nullable=False)
    posts: Mapped[List["BlogPost"]] = relationship(back_populates="author")
    comments: Mapped[List["Comment"]] = relationship(back_populates="author")

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    if current_user.is_authenticated:
        print(current_user.posts)
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        query = db.session.query(User).filter_by(email=form.email.data).first()
        if query is not None:
            flash("You have already registered, try logging in")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        query = db.session.query(User).filter_by(email=form.email.data).first()
        if query is not None:
            if check_password_hash(query.password, form.password.data):
                login_user(query)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Wrong password, try again")
        else:
            flash("This email is not registered")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            text=form.body.data
        )
        requested_post.comments.append(comment)
        current_user.comments.append(comment)
        db.session.add(comment)
        db.session.commit()
    return render_template("post.html", form=form, post=requested_post)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        current_user.posts.append(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@needs_to_be_users_post
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@needs_to_be_users_post
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
