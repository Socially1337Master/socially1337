from flask import Flask, render_template_string, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'BoomBangSocially1337@@'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social_platform.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ============ MODELS ============
class User(db.Model, UserMixin):
    id          = db.Column(db.Integer, primary_key=True)
    username    = db.Column(db.String(150), unique=True, nullable=False)
    email       = db.Column(db.String(150), unique=True, nullable=False)
    password    = db.Column(db.String(150), nullable=False)
    profile_pic = db.Column(db.String(150), default='default.jpg')

class FriendRequest(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status      = db.Column(db.String(20), default="pending")  # "pending", "accepted", "denied"

class Message(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content     = db.Column(db.String(500), nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content        = db.Column(db.String(500), nullable=False)
    timestamp      = db.Column(db.DateTime, default=datetime.utcnow)
    image_filename = db.Column(db.String(150), nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ============ CREATE TABLES / SEED DATA ============
@app.before_first_request
def create_tables():
    db.create_all()
    # 1) Ensure "John_Doe" exists
    if not User.query.filter_by(username="John_Doe").first():
        hashed_pw = bcrypt.generate_password_hash("changeme123").decode('utf-8')
        john = User(username="John_Doe", email="john_doe@example.com", password=hashed_pw)
        db.session.add(john)
        db.session.commit()

    # 2) If user count < 20, auto-generate more dummy users (with fake names) + posts
    user_count = User.query.count()
    if user_count < 20:
        fake_names = [
            "Jane_Smith", "Bob_Miller", "Alice_Jones", "Michael_Carter", "Sara_Parker",
            "James_Brown", "Emily_Davis", "David_Evans", "Linda_Miller", "Josh_Taylor",
            "Olivia_Hill", "Ethan_Clark", "Sophia_Wilson", "Mason_Roberts", "Ava_Richards",
            "William_Wright", "Mia_Turner", "Benjamin_Reed", "Amelia_Cooper"
        ]
        needed = 20 - user_count
        to_create = min(needed, len(fake_names))
        for i in range(to_create):
            name = fake_names[i]
            if User.query.filter_by(username=name).first():
                continue

            pw_hash = bcrypt.generate_password_hash("test123").decode('utf-8')
            dummy_user = User(
                username=name,
                email=f"{name.lower().replace(' ','_')}@example.com",
                password=pw_hash
            )
            db.session.add(dummy_user)
            db.session.commit()

            # Create some sample posts
            sample_texts = [
                f"Hello from {name}!",
                f"Enjoying the day, {name} here!",
                f"Another post from {name}."
            ]
            for text in sample_texts:
                new_post = Post(user_id=dummy_user.id, content=text)
                db.session.add(new_post)
            db.session.commit()


# ============ HELPER FUNCTIONS ============
def get_friends(user):
    """Return a list of users that have an accepted friend request with 'user'."""
    accepted = FriendRequest.query.filter(
        or_(
            FriendRequest.sender_id == user.id,
            FriendRequest.receiver_id == user.id
        ),
        FriendRequest.status == "accepted"
    ).all()
    friends = []
    for fr in accepted:
        if fr.sender_id == user.id:
            friend = User.query.get(fr.receiver_id)
        else:
            friend = User.query.get(fr.sender_id)
        friends.append(friend)
    return friends

def is_friend(u1, u2):
    """Check if two users have an accepted friend relationship."""
    if not u1 or not u2:
        return False
    fr = FriendRequest.query.filter(
        or_(
            (FriendRequest.sender_id == u1.id) & (FriendRequest.receiver_id == u2.id),
            (FriendRequest.sender_id == u2.id) & (FriendRequest.receiver_id == u1.id)
        ),
        FriendRequest.status == "accepted"
    ).first()
    return fr is not None

def get_conversation(u1, u2, limit=50):
    """Return up to 'limit' messages in ascending order between u1 and u2."""
    msgs = Message.query.filter(
        or_(
            (Message.sender_id == u1.id) & (Message.receiver_id == u2.id),
            (Message.sender_id == u2.id) & (Message.receiver_id == u1.id)
        )
    ).order_by(Message.timestamp.desc()).limit(limit).all()
    return list(reversed(msgs))


# ============ ROYAL DARK BLUE + YELLOW COLOR SCHEME ============

CSS_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

    /* Body & Basic Layout */
    body {
        font-family: 'Poppins', sans-serif;
        background-color: #001a4f; /* Royal dark blue background */
        color: #ffff00;           /* Bright yellow text */
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
    }

    .container {
        background: rgba(255, 255, 0, 0.1); /* translucent yellow overlay */
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
        width: 90%;
        max-width: 400px;
        backdrop-filter: blur(8px);
        text-align: center;
    }
    h1 {
        font-size: 24px;
        margin-bottom: 20px;
        font-weight: 600;
        color: #ffff00; /* headings also bright yellow */
    }
    /* Inputs & Buttons */
    input, button {
        width: 100%;
        padding: 12px;
        margin: 10px 0;
        border-radius: 6px;
        font-size: 16px;
        border: none;
    }
    input {
        background-color: rgba(255,255,0,0.2); /* slightly darker translucent yellow */
        color: #ffff00;
        outline: none;
    }
    input::placeholder {
        color: #cccc66; /* a dimmer yellow placeholder */
    }
    button {
        background-color: #001a4f; /* solid royal dark blue */
        color: #ffff00;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    button:hover {
        background-color: #000e3a; /* darker on hover */
    }
    /* Links */
    a {
        display: block;
        margin-top: 15px;
        color: #ffff00;
        text-decoration: none;
        font-size: 14px;
    }
    a:hover {
        text-decoration: underline;
    }
    .profile-img {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        border: 3px solid #ffff00;
        margin: 20px auto;
        display: block;
    }
</style>
"""


# ============ LOGIN, SIGNUP, LOGOUT, HOME ============
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_password = bcrypt.generate_password_hash(
            request.form['password']
        ).decode('utf-8')
        new_user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    
    return render_template_string(CSS_STYLE + """
    <div class="container">
        <h1>Sign Up</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign Up</button>
        </form>
        <a href="{{ url_for('login') }}">Already have an account? Login</a>
    </div>
    """)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('profile', username=user.username))
        else:
            flash("Invalid login credentials.", "error")
    
    return render_template_string(CSS_STYLE + """
    <div class="container">
        <h1>Login</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <a href="{{ url_for('signup') }}">Sign up</a>
    </div>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ============ SEARCH USERS ============
@app.route('/search_users')
@login_required
def search_users():
    query = request.args.get('search_query', '')
    users = User.query.filter(User.username.contains(query)).all()
    return render_template_string(CSS_STYLE + """
    <div class="container">
        <h1>Search Results</h1>
        {% for user in users %}
            <p><a href="{{ url_for('profile', username=user.username) }}">{{ user.username }}</a></p>
        {% endfor %}
        <a href="{{ url_for('home') }}">Back</a>
    </div>
    """, users=users)


# ============ FRIENDS ============
@app.route('/add_friend/<username>', methods=['GET','POST'])
@login_required
def add_friend(username):
    user_to_add = User.query.filter_by(username=username).first_or_404()
    if user_to_add.id == current_user.id:
        flash("You can't add yourself!", "error")
        return redirect(url_for('profile', username=current_user.username))

    existing = FriendRequest.query.filter(
        or_(
            (FriendRequest.sender_id == current_user.id) & (FriendRequest.receiver_id == user_to_add.id),
            (FriendRequest.sender_id == user_to_add.id) & (FriendRequest.receiver_id == current_user.id)
        )
    ).first()

    if existing and existing.status == "accepted":
        flash("You're already friends!", "info")
    else:
        # For simplicity, mark as "accepted" right away
        if existing:
            existing.status = "accepted"
        else:
            new_req = FriendRequest(
                sender_id   = current_user.id,
                receiver_id = user_to_add.id,
                status      = "accepted"
            )
            db.session.add(new_req)
        db.session.commit()
        flash("Friend added!", "success")

    return redirect(url_for('profile', username=user_to_add.username))


# ============ PROFILE PAGE (LAYOUT, FEED, MESSAGING) ============

PROFILE_CSS = """
<style>
/* MAIN BODY */
body {
    background-color: #001a4f;
    color: #ffff00;
    margin: 0;
    padding: 0;
    font-family: 'Poppins', sans-serif;
    overflow-y: auto;
}

/* WRAPPER */
.profile-wrapper {
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
}

/* TOP BAR */
.top-bar {
    background-color: rgba(255,255,0,0.1);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.top-bar h2 {
    margin: 0;
    color: #ffff00;
}
.profile-pic-dropdown {
    position: relative;
    cursor: pointer;
}
.profile-pic-dropdown img {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 2px solid #ffff00;
}
.profile-pic-dropdown:hover .dropdown-menu {
    display: block;
}
.dropdown-menu {
    display: none;
    position: absolute;
    right: 0;
    top: 45px;
    background-color: rgba(255,255,0,0.1);
    color: #ffff00;
    min-width: 140px;
    border-radius: 6px;
    overflow: hidden;
    z-index: 999;
    padding: 0;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
}
.dropdown-menu form,
.dropdown-menu a {
    display: block;
    padding: 10px;
    text-decoration: none;
    color: #ffff00;
    font-size: 14px;
}
.dropdown-menu form:hover,
.dropdown-menu a:hover {
    background-color: rgba(255,255,0,0.2);
}
.hidden-file-input {
    display: none;
}

/* CONTENT AREA */
.content-area {
    display: flex;
    flex: 1;
    overflow-y: auto;
}

/* LEFT SIDE */
.left-side {
    width: 300px;
    background-color: rgba(255,255,0,0.1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 10px;
}
.left-side h3 {
    margin-top: 0;
    color: #ffff00;
}
.friends-section {
    margin-bottom: 20px;
    max-height: 250px;
    overflow-y: auto;
}
.friend-item a {
    color: #ffff00;
    text-decoration: none;
}
.friend-item a:hover {
    text-decoration: underline;
}

/* MESSAGING SECTION */
.messaging-section {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
}
.chat-box {
    background-color: rgba(255,255,0,0.2);
    border-radius: 6px;
    padding: 10px;
    max-height: 200px;
    overflow-y: auto;
    margin-bottom: 10px;
    color: #ffff00;
}
.chat-msg {
    margin: 5px 0;
}
.chat-msg .sender {
    font-weight: bold;
    color: #ffff00;
}
.messaging-section textarea,
.messaging-section select {
    width: 100%;
    margin: 5px 0;
    border-radius: 6px;
    border: none;
    outline: none;
    padding: 8px;
    background-color: rgba(255,255,0,0.2);
    color: #ffff00;
}
.messaging-section button {
    background-color: #001a4f;
    color: #ffff00;
    cursor: pointer;
    transition: background-color 0.3s;
    border: none;
    padding: 10px 16px;
    margin-top: 5px;
    border-radius: 6px;
}
.messaging-section button:hover {
    background-color: #000e3a;
}

/* CENTER FEED */
.center-feed {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
}
.create-post {
    background-color: rgba(255,255,0,0.1);
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 20px;
}
.create-post textarea {
    width: 100%;
    background-color: rgba(255,255,0,0.2);
    color: #ffff00;
    border: none;
    border-radius: 6px;
    padding: 10px;
    resize: vertical;
    margin-bottom: 10px;
}
.create-post button {
    background-color: #001a4f;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    color: #ffff00;
    cursor: pointer;
}
.create-post button:hover {
    background-color: #000e3a;
}
.feed-posts .post {
    background-color: rgba(255,255,0,0.1);
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 15px;
}
.post-header {
    font-weight: 600;
    margin-bottom: 5px;
    color: #ffff00;
}
.time {
    font-size: 12px;
    margin-left: 8px;
    color: #ffff00;
}
.post-content {
    margin-bottom: 10px;
}
.post-image {
    max-width: 100%;
    border: 2px solid #ffff00;
    border-radius: 6px;
}

/* BOTTOM SEARCH SECTION */
.search-section {
    text-align: center;
    background-color: rgba(255,255,0,0.1);
    padding: 10px;
}
.search-section form input {
    background-color: rgba(255,255,0,0.2);
    color: #ffff00;
    border: none;
    border-radius: 6px;
    padding: 8px;
    margin: 5px 0;
}
.search-section button {
    background-color: #001a4f;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    color: #ffff00;
    cursor: pointer;
}
.search-section button:hover {
    background-color: #000e3a;
}
</style>
"""

PROFILE_JS = """
<script>
document.addEventListener('DOMContentLoaded', function() {
  const chatBox = document.querySelector('.chat-box');
  const messageInput = document.querySelector('#messageInput');
  const activeChatSelect = document.querySelector('#active_chat');
  const sendBtn = document.querySelector('#sendBtn');

  if (messageInput) {
    messageInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  if (sendBtn) {
    sendBtn.addEventListener('click', function(e) {
      e.preventDefault();
      sendMessage();
    });
  }

  function sendMessage() {
    const friendId = activeChatSelect.value;
    const content = messageInput.value.trim();
    if (!friendId || !content) {
      alert("Choose a friend and type a message.");
      return;
    }

    fetch('/send_message_ajax', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ receiver_id: friendId, content: content })
    })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert(data.error);
        return;
      }
      messageInput.value = '';
      fetchMessages();
    })
    .catch(err => console.error(err));
  }

  function fetchMessages() {
    if (!activeChatSelect) return;
    const friendId = activeChatSelect.value;
    if (!friendId) return;
    fetch(`/conversation/${friendId}/json`)
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          console.log("Chat error: ", data.error);
          return;
        }
        if (chatBox) {
          chatBox.innerHTML = '';
          data.messages.forEach(msg => {
            const div = document.createElement('div');
            div.classList.add('chat-msg');
            let senderName = (msg.sender_id === parseInt(data.current_user_id)) ? "You" : data.friend_username;
            div.innerHTML = `<span class="sender">${senderName}:</span> ${msg.content} <small>(${msg.timestamp})</small>`;
            chatBox.appendChild(div);
          });
          chatBox.scrollTop = chatBox.scrollHeight;
        }
      })
      .catch(err => console.error(err));
  }

  setInterval(fetchMessages, 3000);
});
</script>
"""

PROFILE_HTML = """
{{ layout_css|safe }}
<div class="profile-wrapper">
    <!-- Top bar -->
    <div class="top-bar">
        <div>
            <h2>{{ user.username }}'s Profile</h2>
        </div>
        {% if current_user.id == user.id %}
            <div class="profile-pic-dropdown">
                <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}" alt="profile_pic">
                <div class="dropdown-menu">
                    <form method="POST" enctype="multipart/form-data">
                        <input type="hidden" name="action" value="change_pic">
                        <label>Change Image
                            <input type="file" name="profile_pic" accept="image/*" class="hidden-file-input" onchange="this.form.submit()">
                        </label>
                    </form>
                    <a href="{{ url_for('logout') }}">Logout</a>
                </div>
            </div>
        {% else %}
            <img src="{{ url_for('static', filename='uploads/' + current_user.profile_pic) }}"
                 style="width:40px; height:40px; border-radius:50%; border:2px solid #ffff00;">
        {% endif %}
    </div>

    <!-- Content area -->
    <div class="content-area">
        <!-- Left side: friend list & chat -->
        <div class="left-side">
            <div class="friends-section">
                <h3>{{ user.username }}'s Friends</h3>
                {% if friends_list %}
                    {% for f in friends_list %}
                        <div class="friend-item">
                            <a href="{{ url_for('profile', username=f.username) }}">{{ f.username }}</a>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>No friends yet</p>
                {% endif %}
            </div>

            {% if current_user.id == user.id %}
                <div class="messaging-section">
                    <h3>Chat</h3>
                    <div class="chat-box">
                        {% for msg in conversation %}
                            <div class="chat-msg">
                                {% if msg.sender_id == current_user.id %}
                                    <span class="sender">You:</span> {{ msg.content }}
                                    <small>({{ msg.timestamp }})</small>
                                {% else %}
                                    <span class="sender">{{ active_chat_user.username }}:</span> {{ msg.content }}
                                    <small>({{ msg.timestamp }})</small>
                                {% endif %}
                            </div>
                        {% endfor %}
                    </div>
                    <form method="GET">
                        <label for="active_chat">Select Friend:</label>
                        <select name="active_chat" id="active_chat" onchange="this.form.submit()">
                            <option value="">--Chat With--</option>
                            {% for friend in friends_list %}
                                <option value="{{ friend.id }}"
                                    {% if active_chat_user and friend.id == active_chat_user.id %}selected{% endif %}
                                >{{ friend.username }}</option>
                            {% endfor %}
                        </select>
                    </form>
                    {% if active_chat_user %}
                        <textarea rows="2" placeholder="Type your message..." id="messageInput"></textarea>
                        <button id="sendBtn">Send</button>
                    {% endif %}
                </div>
            {% else %}
                {% if not is_friend(current_user, user) %}
                    <div style="margin-top:10px;">
                        <a href="{{ url_for('add_friend', username=user.username) }}"
                           style="color:#ffff00; text-decoration:none;">
                            Add Friend
                        </a>
                    </div>
                {% else %}
                    <p style="margin-top:10px;">You are friends.</p>
                {% endif %}
            {% endif %}
        </div>

        <!-- Center feed -->
        <div class="center-feed">
            {% if current_user.id == user.id %}
                <div class="create-post">
                    <form method="POST" enctype="multipart/form-data">
                        <input type="hidden" name="action" value="create_post">
                        <textarea name="post_content" rows="3" placeholder="What's on your mind?"></textarea>
                        <input type="file" name="post_image" accept=".jpg, .jpeg, .png">
                        <button type="submit">Post</button>
                    </form>
                </div>
            {% endif %}
            <div class="feed-posts">
                {% for p in posts %}
                    <div class="post">
                        <div class="post-header">
                            <strong>{{ user.username }}</strong>
                            <span class="time">- {{ p.timestamp }}</span>
                        </div>
                        <div class="post-content">
                            {{ p.content }}
                        </div>
                        {% if p.image_filename %}
                            <img src="{{ url_for('static', filename='uploads/' + p.image_filename) }}"
                                 alt="Post Image"
                                 class="post-image">
                        {% endif %}
                    </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- Search form at bottom -->
    <div class="search-section">
        <h2>Find Friends</h2>
        <form action="{{ url_for('search_users') }}" method="GET">
            <input type="text" name="search_query" placeholder="Enter username">
            <button type="submit">Search</button>
        </form>
    </div>
</div>
{{ chat_script|safe }}
"""

@app.route('/profile/<username>', methods=['GET','POST'])
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    if request.method == 'POST':
        action = request.form.get('action')

        # 1) Change profile picture
        if action == "change_pic":
            if current_user.id != user.id:
                flash("You cannot change someone else's picture!", "error")
                return redirect(url_for('profile', username=user.username))
            pic_file = request.files.get('profile_pic')
            if pic_file and pic_file.filename.strip():
                filename = secure_filename(pic_file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pic_file.save(path)
                user.profile_pic = filename
                db.session.commit()
                flash("Profile picture updated!", "success")
            return redirect(url_for('profile', username=user.username))

        # 2) Create a post
        elif action == "create_post":
            if current_user.id != user.id:
                flash("You can't post on someone else's feed!", "error")
                return redirect(url_for('profile', username=user.username))

            content = request.form.get('post_content', '').strip()
            image_filename = None

            post_image = request.files.get('post_image')
            if post_image and post_image.filename.strip():
                ext = os.path.splitext(post_image.filename)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png']:
                    flash("Only JPG or PNG files are allowed!", "error")
                    return redirect(url_for('profile', username=user.username))

                secure_name = secure_filename(post_image.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
                post_image.save(save_path)
                image_filename = secure_name

            if content or image_filename:
                new_post = Post(
                    user_id=user.id,
                    content=content if content else "",
                    image_filename=image_filename
                )
                db.session.add(new_post)
                db.session.commit()
                flash("Post created!", "success")
            else:
                flash("Cannot create an empty post without text or image!", "error")

            return redirect(url_for('profile', username=user.username))

    friends_list = get_friends(user)
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()

    active_chat_user = None
    conversation = []
    if current_user.id == user.id:
        friend_id = request.args.get('active_chat')
        if friend_id:
            try:
                friend_id = int(friend_id)
            except ValueError:
                friend_id = None

        if friend_id:
            friend_obj = User.query.get(friend_id)
            if friend_obj and is_friend(current_user, friend_obj):
                active_chat_user = friend_obj
                conversation = get_conversation(current_user, friend_obj, limit=50)

    return render_template_string(
        PROFILE_HTML,
        layout_css=PROFILE_CSS,
        chat_script=PROFILE_JS,
        user=user,
        friends_list=friends_list,
        posts=posts,
        active_chat_user=active_chat_user,
        conversation=conversation,
        is_friend=is_friend
    )


# ============ AJAX MESSAGING ENDPOINT ============
@app.route('/send_message_ajax', methods=['POST'])
@login_required
def send_message_ajax():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    receiver_id = data.get('receiver_id')
    content = data.get('content', '').strip()

    if not receiver_id or not content:
        return jsonify({"error": "Receiver ID and message content are required"}), 400

    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({"error": "That user doesn't exist!"}), 404

    if not is_friend(current_user, receiver):
        return jsonify({"error": "You can only message your friends!"}), 403

    new_msg = Message(sender_id=current_user.id, receiver_id=receiver.id, content=content)
    db.session.add(new_msg)
    db.session.commit()

    return jsonify({"message": "Message sent successfully"})


# ============ AJAX ENDPOINT FOR MESSAGES IN JSON ============
@app.route('/conversation/<int:friend_id>/json')
@login_required
def conversation_json(friend_id):
    friend = User.query.get(friend_id)
    if not friend:
        return jsonify({"error": "Invalid friend"}), 400

    if not is_friend(current_user, friend):
        return jsonify({"error": "Not your friend"}), 403

    msgs = get_conversation(current_user, friend, limit=50)
    output = []
    for m in msgs:
        output.append({
            "id": m.id,
            "sender_id": m.sender_id,
            "receiver_id": m.receiver_id,
            "content": m.content,
            "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify({
        "current_user_id": str(current_user.id),
        "friend_id": str(friend.id),
        "friend_username": friend.username,
        "messages_count": len(output),
        "messages": output,
    })


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=1337)
