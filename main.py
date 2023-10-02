from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
import os
from database import DataBaseManager 

from werkzeug.security import generate_password_hash, check_password_hash
from flask_gravatar import Gravatar
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

db_manager = DataBaseManager()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ["SECRET_KEY"]
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(
    app,
    size=100,
    rating='g',
    default='retro',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    user_document = db_manager.get_user_by_id(user_id)
    if (user_document == None): 
        return None

    user_object = User(user_document["name"], user_document["email"], user_document["password"], user_document["posts"])
    user_object.set_id(user_document["_id"])
    return user_object

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
        print(kwargs)
        print(current_user.posts)
        if kwargs["post_id"] in current_user.posts:
            return function(*args, **kwargs)
        else:
            abort(403)
    return inner

class User(UserMixin):
    def __init__(self, name, email, password, posts):
        self.id = None
        self.posts = posts
        self.name = name
        self.email = email
        self.password = password

    def set_id(self, _id):
        self.id = _id

@app.route('/')
def get_all_posts():
    posts = list(db_manager.get_all_posts())
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        query = db_manager.get_user_by_email(form.email.data)
        if query is not None:
            flash("You have already registered, try logging in")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            posts=[]
        )
        db_manager.add_user(new_user)
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        query = db_manager.get_user_by_email(form.email.data)
        if query is not None:
            if check_password_hash(query["password"], form.password.data):
                user = User(query["name"], query["email"], query["password"], query["posts"])
                user.set_id(query["_id"])
                login_user(user)
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


@app.route("/post/<post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = dict(db_manager.get_post_by_id(post_id))
    
    print(str(requested_post["_id"]) in current_user.posts)
    
    form = CommentForm()
    if form.validate_on_submit():
        comment ={
            "text": form.body.data,
            "author_name": current_user.name,
            "author_email": current_user.email
        }
        requested_post["comments"].append(comment)
        db_manager.update_post(post_id, requested_post)
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
        new_post_id = db_manager.add_post(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
        )
        current_user.posts.append(str(new_post_id.inserted_id))
        db_manager.update_user(current_user.id, current_user)
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@needs_to_be_users_post
def edit_post(post_id):
    post = db_manager.get_post_by_id(post_id)
    edit_form = CreatePostForm(
        title=post["title"],
        subtitle=post["subtitle"],
        img_url=post["img_url"],
        body=post["body"]
    )
    if edit_form.validate_on_submit():
        new_post = {
            "title": edit_form.title.data,
            "subtitle": edit_form.subtitle.data,
            "body": edit_form.body.data,
            "img_url": edit_form.img_url.data,
            "author_id": current_user.id,
            "author_name": current_user.name,
            "date": post["date"],
            "comments": post["comments"]
        }

        db_manager.update_post(post["_id"], new_post)
        return redirect(url_for("show_post", post_id=post["_id"]))

    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<post_id>")
@needs_to_be_users_post
def delete_post(post_id):
    db_manager.delete_post(post_id)
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

