# student_gigs.py - Student Skills Marketplace
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import io
import hashlib
import re
import time

# Page configuration
st.set_page_config(
    page_title="SkillSwap - Student Gig Marketplace",
    page_icon="🎓",
    layout="wide"
)

# Initialize database
def init_db():
    conn = sqlite3.connect('skillswap.db', check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        university TEXT,
        major TEXT,
        skills TEXT,
        bio TEXT,
        rating REAL DEFAULT 0,
        completed_tasks INTEGER DEFAULT 0,
        total_earnings REAL DEFAULT 0,
        is_verified INTEGER DEFAULT 0
    )''')
    
    # Gigs table
    c.execute('''CREATE TABLE IF NOT EXISTS gigs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        budget_type TEXT NOT NULL,
        budget_amount REAL,
        time_estimate TEXT,
        urgency TEXT,
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deadline DATE,
        location TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Bids table
    c.execute('''CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gig_id INTEGER NOT NULL,
        bidder_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        estimated_time TEXT,
        proposal TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (gig_id) REFERENCES gigs (id),
        FOREIGN KEY (bidder_id) REFERENCES users (id)
    )''')
    
    # Tasks/Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gig_id INTEGER NOT NULL,
        bid_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        freelancer_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'in_progress',
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        client_rating INTEGER,
        freelancer_rating INTEGER,
        client_review TEXT,
        freelancer_review TEXT,
        FOREIGN KEY (gig_id) REFERENCES gigs (id),
        FOREIGN KEY (bid_id) REFERENCES bids (id),
        FOREIGN KEY (client_id) REFERENCES users (id),
        FOREIGN KEY (freelancer_id) REFERENCES users (id)
    )''')
    
    # Portfolio items table
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        skills_used TEXT,
        completion_date DATE,
        client_feedback TEXT,
        rating INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )''')
    
    # Messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        task_id INTEGER,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )''')
    
    conn.commit()
    return conn

# Password hashing with validation
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, ""

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Authentication functions with error handling
def register_user(username, email, password, university, major, skills, bio=""):
    conn = init_db()
    try:
        # Validate email
        if not validate_email(email):
            return False, "Invalid email format"
        
        # Validate password
        is_valid, msg = validate_password(password)
        if not is_valid:
            return False, msg
        
        # Check if username or email already exists
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if c.fetchone():
            return False, "Username or email already exists"
        
        # Insert new user
        c.execute('''INSERT INTO users (username, email, password_hash, university, major, skills, bio) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (username, email, hash_password(password), university, major, skills, bio))
        conn.commit()
        return True, "Registration successful!"
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Registration error: {str(e)}"
    finally:
        conn.close()

def login_user(email, password):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('''SELECT id, username, email, university, major, skills, bio, 
                     rating, completed_tasks, total_earnings, is_verified 
                     FROM users WHERE email = ? AND password_hash = ?''',
                  (email, hash_password(password)))
        user = c.fetchone()
        return user
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return None
    finally:
        conn.close()

def get_current_user():
    return st.session_state.get('user')

def is_authenticated():
    return 'user' in st.session_state and st.session_state.user is not None

# Gig management functions
def create_gig(user_id, title, description, category, budget_type, budget_amount, 
               time_estimate, urgency, deadline, location):
    conn = init_db()
    try:
        # Validate inputs
        if not all([title, description, category, budget_type, urgency]):
            return False, "Please fill all required fields"
        
        if budget_type == 'fixed' and (budget_amount is None or budget_amount <= 0):
            return False, "Please enter a valid budget amount"
        
        c = conn.cursor()
        c.execute('''INSERT INTO gigs (user_id, title, description, category, budget_type, 
                     budget_amount, time_estimate, urgency, deadline, location, status) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')''',
                  (user_id, title, description, category, budget_type, 
                   budget_amount, time_estimate, urgency, deadline, location))
        conn.commit()
        return True, "Gig created successfully!"
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error creating gig: {str(e)}"
    finally:
        conn.close()

def get_all_gigs(exclude_user_id=None, category=None, status='open'):
    conn = init_db()
    try:
        query = '''SELECT g.*, u.username as client_name, u.rating as client_rating 
                   FROM gigs g 
                   JOIN users u ON g.user_id = u.id 
                   WHERE g.status = ?'''
        params = [status]
        
        if exclude_user_id:
            query += ' AND g.user_id != ?'
            params.append(exclude_user_id)
        
        if category and category != 'All':
            query += ' AND g.category = ?'
            params.append(category)
        
        query += ' ORDER BY g.created_at DESC'
        
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Error getting gigs: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_user_gigs(user_id):
    conn = init_db()
    try:
        query = '''SELECT g.*, 
                   (SELECT COUNT(*) FROM bids WHERE gig_id = g.id) as bid_count 
                   FROM gigs g 
                   WHERE g.user_id = ? 
                   ORDER BY g.created_at DESC'''
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df
    except Exception as e:
        st.error(f"Error getting user gigs: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_gig_by_id(gig_id):
    conn = init_db()
    try:
        query = '''SELECT g.*, u.username as client_name, u.rating as client_rating, 
                   u.completed_tasks as client_completed
                   FROM gigs g 
                   JOIN users u ON g.user_id = u.id 
                   WHERE g.id = ?'''
        df = pd.read_sql_query(query, conn, params=(gig_id,))
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
    except Exception as e:
        st.error(f"Error getting gig: {str(e)}")
        return None
    finally:
        conn.close()

def update_gig_status(gig_id, status):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('UPDATE gigs SET status = ? WHERE id = ?', (status, gig_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating gig: {str(e)}")
        return False
    finally:
        conn.close()

# Bid management functions
def place_bid(gig_id, bidder_id, amount, estimated_time, proposal):
    conn = init_db()
    try:
        # Validate inputs
        if amount <= 0:
            return False, "Please enter a valid bid amount"
        
        # Check if user has already bid on this gig
        c = conn.cursor()
        c.execute('SELECT id FROM bids WHERE gig_id = ? AND bidder_id = ?', 
                  (gig_id, bidder_id))
        if c.fetchone():
            return False, "You have already placed a bid on this gig"
        
        # Get gig details to validate budget
        c.execute('SELECT budget_type, budget_amount FROM gigs WHERE id = ?', (gig_id,))
        gig = c.fetchone()
        if gig:
            budget_type, budget_amount = gig
            if budget_type == 'fixed' and amount > budget_amount * 1.5:
                return False, "Your bid exceeds the maximum allowed amount (150% of budget)"
        
        # Place bid
        c.execute('''INSERT INTO bids (gig_id, bidder_id, amount, estimated_time, proposal, status) 
                     VALUES (?, ?, ?, ?, ?, 'pending')''',
                  (gig_id, bidder_id, amount, estimated_time, proposal))
        conn.commit()
        return True, "Bid placed successfully!"
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error placing bid: {str(e)}"
    finally:
        conn.close()

def get_gig_bids(gig_id):
    conn = init_db()
    try:
        query = '''SELECT b.*, u.username as bidder_name, u.rating as bidder_rating, 
                   u.completed_tasks as bidder_completed
                   FROM bids b 
                   JOIN users u ON b.bidder_id = u.id 
                   WHERE b.gig_id = ? 
                   ORDER BY b.amount ASC, b.created_at ASC'''
        df = pd.read_sql_query(query, conn, params=(gig_id,))
        return df
    except Exception as e:
        st.error(f"Error getting bids: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_user_bids(user_id):
    conn = init_db()
    try:
        query = '''SELECT b.*, g.title as gig_title, g.status as gig_status, 
                   u.username as client_name
                   FROM bids b 
                   JOIN gigs g ON b.gig_id = g.id 
                   JOIN users u ON g.user_id = u.id 
                   WHERE b.bidder_id = ? 
                   ORDER BY b.created_at DESC'''
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df
    except Exception as e:
        st.error(f"Error getting user bids: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def accept_bid(bid_id):
    conn = init_db()
    try:
        c = conn.cursor()
        
        # Get bid details
        c.execute('SELECT gig_id, bidder_id, amount FROM bids WHERE id = ?', (bid_id,))
        bid = c.fetchone()
        if not bid:
            return False, "Bid not found"
        
        gig_id, bidder_id, amount = bid
        
        # Get gig owner
        c.execute('SELECT user_id FROM gigs WHERE id = ?', (gig_id,))
        gig = c.fetchone()
        if not gig:
            return False, "Gig not found"
        
        client_id = gig[0]
        
        # Create task
        c.execute('''INSERT INTO tasks (gig_id, bid_id, client_id, freelancer_id, amount, status) 
                     VALUES (?, ?, ?, ?, ?, 'in_progress')''',
                  (gig_id, bid_id, client_id, bidder_id, amount))
        
        # Update bid status
        c.execute('UPDATE bids SET status = "accepted" WHERE id = ?', (bid_id,))
        
        # Update other bids status
        c.execute('UPDATE bids SET status = "rejected" WHERE gig_id = ? AND id != ?', 
                  (gig_id, bid_id))
        
        # Update gig status
        c.execute('UPDATE gigs SET status = "in_progress" WHERE id = ?', (gig_id,))
        
        conn.commit()
        return True, "Bid accepted! Task has started."
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error accepting bid: {str(e)}"
    finally:
        conn.close()

# Task management functions
def get_user_tasks(user_id, role=None):
    conn = init_db()
    try:
        if role == 'client':
            query = '''SELECT t.*, g.title as gig_title, u.username as freelancer_name 
                       FROM tasks t 
                       JOIN gigs g ON t.gig_id = g.id 
                       JOIN users u ON t.freelancer_id = u.id 
                       WHERE t.client_id = ? 
                       ORDER BY t.started_at DESC'''
        elif role == 'freelancer':
            query = '''SELECT t.*, g.title as gig_title, u.username as client_name 
                       FROM tasks t 
                       JOIN gigs g ON t.gig_id = g.id 
                       JOIN users u ON t.client_id = u.id 
                       WHERE t.freelancer_id = ? 
                       ORDER BY t.started_at DESC'''
        else:
            query = '''SELECT t.*, g.title as gig_title, 
                       u1.username as client_name, u2.username as freelancer_name 
                       FROM tasks t 
                       JOIN gigs g ON t.gig_id = g.id 
                       JOIN users u1 ON t.client_id = u1.id 
                       JOIN users u2 ON t.freelancer_id = u2.id 
                       WHERE t.client_id = ? OR t.freelancer_id = ? 
                       ORDER BY t.started_at DESC'''
            return pd.read_sql_query(query, conn, params=(user_id, user_id))
        
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df
    except Exception as e:
        st.error(f"Error getting tasks: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def complete_task(task_id, user_id, rating=None, review=None):
    conn = init_db()
    try:
        c = conn.cursor()
        
        # Get task details
        c.execute('SELECT client_id, freelancer_id, status, amount FROM tasks WHERE id = ?', 
                  (task_id,))
        task = c.fetchone()
        if not task:
            return False, "Task not found"
        
        client_id, freelancer_id, status, amount = task
        
        # Check if user is authorized
        if user_id not in [client_id, freelancer_id]:
            return False, "Unauthorized access"
        
        # Update task based on user role
        if user_id == client_id:
            if rating is not None:
                if rating < 1 or rating > 5:
                    return False, "Rating must be between 1 and 5"
                c.execute('UPDATE tasks SET client_rating = ?, client_review = ? WHERE id = ?',
                          (rating, review, task_id))
            else:
                c.execute('UPDATE tasks SET status = "completed", completed_at = CURRENT_TIMESTAMP WHERE id = ?',
                          (task_id,))
        elif user_id == freelancer_id:
            c.execute('UPDATE tasks SET status = "pending_review" WHERE id = ?', (task_id,))
        
        # If both parties have completed their parts, update portfolio and user stats
        if status == 'pending_review' and user_id == client_id:
            # Update freelancer stats
            c.execute('''UPDATE users SET 
                         completed_tasks = completed_tasks + 1,
                         total_earnings = total_earnings + ?,
                         rating = (rating * completed_tasks + ?) / (completed_tasks + 1)
                         WHERE id = ?''',
                      (amount, rating or 5, freelancer_id))
            
            # Add to portfolio
            c.execute('''INSERT INTO portfolio (user_id, task_id, title, description, 
                         skills_used, completion_date, client_feedback, rating) 
                         SELECT ?, t.id, g.title, g.description, 
                         (SELECT skills FROM users WHERE id = ?),
                         DATE(t.completed_at), t.client_review, t.client_rating
                         FROM tasks t 
                         JOIN gigs g ON t.gig_id = g.id 
                         WHERE t.id = ?''',
                      (freelancer_id, freelancer_id, task_id))
            
            # Update gig status
            c.execute('UPDATE gigs SET status = "completed" WHERE id = (SELECT gig_id FROM tasks WHERE id = ?)',
                      (task_id,))
        
        conn.commit()
        return True, "Task updated successfully!"
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error updating task: {str(e)}"
    finally:
        conn.close()

# Portfolio functions
def get_user_portfolio(user_id):
    conn = init_db()
    try:
        query = '''SELECT p.*, t.amount as earnings, u.username as client_name 
                   FROM portfolio p 
                   JOIN tasks t ON p.task_id = t.id 
                   JOIN users u ON t.client_id = u.id 
                   WHERE p.user_id = ? 
                   ORDER BY p.completion_date DESC'''
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df
    except Exception as e:
        st.error(f"Error getting portfolio: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

# Messaging functions
def send_message(sender_id, receiver_id, task_id, message):
    conn = init_db()
    try:
        if not message.strip():
            return False, "Message cannot be empty"
        
        c = conn.cursor()
        c.execute('''INSERT INTO messages (sender_id, receiver_id, task_id, message) 
                     VALUES (?, ?, ?, ?)''',
                  (sender_id, receiver_id, task_id, message))
        conn.commit()
        return True, "Message sent!"
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error sending message: {str(e)}"
    finally:
        conn.close()

def get_user_messages(user_id, other_user_id=None, task_id=None):
    conn = init_db()
    try:
        query = '''SELECT m.*, 
                   s.username as sender_name, 
                   r.username as receiver_name,
                   g.title as task_title
                   FROM messages m 
                   JOIN users s ON m.sender_id = s.id 
                   JOIN users r ON m.receiver_id = r.id 
                   LEFT JOIN tasks t ON m.task_id = t.id 
                   LEFT JOIN gigs g ON t.gig_id = g.id 
                   WHERE (m.sender_id = ? OR m.receiver_id = ?)'''
        params = [user_id, user_id]
        
        if other_user_id:
            query += ' AND (m.sender_id = ? OR m.receiver_id = ?)'
            params.extend([other_user_id, other_user_id])
        
        if task_id:
            query += ' AND m.task_id = ?'
            params.append(task_id)
        
        query += ' ORDER BY m.created_at ASC'
        
        df = pd.read_sql_query(query, conn, params=params)
        
        # Mark messages as read
        if not df.empty:
            c = conn.cursor()
            c.execute('''UPDATE messages SET is_read = 1 
                         WHERE receiver_id = ? AND is_read = 0''',
                      (user_id,))
            conn.commit()
        
        return df
    except Exception as e:
        st.error(f"Error getting messages: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_unread_message_count(user_id):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0', 
                  (user_id,))
        count = c.fetchone()[0]
        return count
    except:
        return 0
    finally:
        conn.close()

# UI Components
def login_page():
    st.title("SkillSwap - Student Gig Marketplace")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", type="primary")
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    with st.spinner("Logging in..."):
                        user = login_user(email, password)
                        if user:
                            st.session_state.user = {
                                'id': user[0],
                                'username': user[1],
                                'email': user[2],
                                'university': user[3],
                                'major': user[4],
                                'skills': user[5],
                                'bio': user[6],
                                'rating': user[7],
                                'completed_tasks': user[8],
                                'total_earnings': user[9],
                                'is_verified': user[10]
                            }
                            st.session_state.page = "dashboard"
                            st.success(f"Welcome {user[1]}!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password")
    
    with tab2:
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Username*")
                email = st.text_input("Email*")
                password = st.text_input("Password*", type="password")
                confirm_password = st.text_input("Confirm Password*", type="password")
            
            with col2:
                university = st.text_input("University*")
                major = st.text_input("Major*")
                skills = st.text_input("Skills (comma separated)*", 
                                      placeholder="e.g., Python, Web Design, Tutoring")
                bio = st.text_area("Bio (optional)", height=100)
            
            submit = st.form_submit_button("Register", type="primary")
            
            if submit:
                if not all([username, email, password, confirm_password, university, major, skills]):
                    st.error("Please fill all required fields (*)")
                elif password != confirm_password:
                    st.error("Passwords don't match")
                else:
                    with st.spinner("Creating account..."):
                        success, message = register_user(username, email, password, 
                                                        university, major, skills, bio)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

def dashboard():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.title(f"Welcome, {user['username']}!")
    
    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Your Rating", f"{user['rating']:.1f}/5")
    with col2:
        st.metric("Completed Tasks", user['completed_tasks'])
    with col3:
        st.metric("Total Earnings", f"${user['total_earnings']:.2f}")
    with col4:
        unread_count = get_unread_message_count(user['id'])
        st.metric("Unread Messages", unread_count)
    
    # Quick actions
    st.subheader("Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Post a Gig", use_container_width=True, type="primary"):
            st.session_state.page = "post_gig"
            st.rerun()
    with col2:
        if st.button("Browse Gigs", use_container_width=True):
            st.session_state.page = "browse_gigs"
            st.rerun()
    with col3:
        if st.button("My Tasks", use_container_width=True):
            st.session_state.page = "my_tasks"
            st.rerun()
    with col4:
        if st.button("Messages", use_container_width=True):
            st.session_state.page = "messages"
            st.rerun()
    
    # Recent activity
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Your Active Gigs")
        gigs = get_user_gigs(user['id'])
        if isinstance(gigs, pd.DataFrame) and not gigs.empty:
            active_gigs = gigs[gigs['status'] == 'open'].head(3)
            if not active_gigs.empty:
                for _, gig in active_gigs.iterrows():
                    st.write(f"**{gig['title']}**")
                    st.write(f"Bids: {gig['bid_count']} | Status: {gig['status']}")
                    if st.button("View", key=f"view_gig_{gig['id']}"):
                        st.session_state.view_gig = gig['id']
                        st.rerun()
                    st.divider()
            else:
                st.info("No active gigs. Post one now!")
        else:
            st.info("No gigs yet. Post your first gig!")
    
    with col2:
        st.subheader("Your Active Bids")
        bids = get_user_bids(user['id'])
        if isinstance(bids, pd.DataFrame) and not bids.empty:
            active_bids = bids[bids['status'] == 'pending'].head(3)
            if not active_bids.empty:
                for _, bid in active_bids.iterrows():
                    st.write(f"**{bid['gig_title']}**")
                    st.write(f"Your Bid: ${bid['amount']:.2f} | Status: {bid['status']}")
                    st.divider()
            else:
                st.info("No active bids. Browse gigs to bid!")
        else:
            st.info("No bids placed yet.")

def post_gig():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.title("Post a New Gig")
    
    with st.form("post_gig_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Gig Title*")
            category = st.selectbox("Category*", 
                ["Academic Help", "Design & Creative", "Programming & Tech", 
                 "Writing & Translation", "Marketing", "Tutoring", "Other"])
            budget_type = st.radio("Budget Type*", ["fixed", "hourly"])
            
            if budget_type == 'fixed':
                budget_amount = st.number_input("Budget Amount ($)*", min_value=1.0, step=1.0, format="%.2f")
            else:
                budget_amount = st.number_input("Hourly Rate ($)*", min_value=5.0, step=1.0, format="%.2f")
            
            time_estimate = st.selectbox("Time Estimate", 
                ["Less than 1 hour", "1-3 hours", "3-8 hours", 
                 "1-3 days", "3-7 days", "1-2 weeks", "More than 2 weeks"])
        
        with col2:
            description = st.text_area("Description*", height=150,
                                      placeholder="Describe what you need help with...")
            urgency = st.selectbox("Urgency*", 
                ["Low", "Medium", "High", "Urgent"])
            deadline = st.date_input("Deadline", min_value=datetime.now().date())
            location = st.selectbox("Location", 
                ["On-campus", "Remote", "Hybrid", "Any"])
        
        submit = st.form_submit_button("Post Gig", type="primary", use_container_width=True)
        
        if submit:
            if not all([title, description, category, budget_type, urgency]):
                st.error("Please fill all required fields (*)")
            else:
                with st.spinner("Posting gig..."):
                    success, message = create_gig(
                        user_id=user['id'],
                        title=title,
                        description=description,
                        category=category,
                        budget_type=budget_type,
                        budget_amount=budget_amount,
                        time_estimate=time_estimate,
                        urgency=urgency,
                        deadline=deadline.strftime('%Y-%m-%d'),
                        location=location
                    )
                    if success:
                        st.success(message)
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else:
                        st.error(message)
    
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def browse_gigs():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.title("Browse Gigs")
    
    # Filters
    with st.expander("Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("Category", ["All"] + 
                ["Academic Help", "Design & Creative", "Programming & Tech", 
                 "Writing & Translation", "Marketing", "Tutoring", "Other"])
        with col2:
            budget_type = st.selectbox("Budget Type", ["All", "fixed", "hourly"])
        with col3:
            urgency = st.selectbox("Urgency", ["All", "Low", "Medium", "High", "Urgent"])
    
    search = st.text_input("Search gigs by title or description")
    
    # Get gigs
    gigs = get_all_gigs(exclude_user_id=user['id'])
    
    # Apply filters
    if isinstance(gigs, pd.DataFrame) and not gigs.empty:
        if category != "All":
            gigs = gigs[gigs['category'] == category]
        if budget_type != "All":
            gigs = gigs[gigs['budget_type'] == budget_type]
        if urgency != "All":
            gigs = gigs[gigs['urgency'] == urgency]
        if search:
            search_lower = search.lower()
            mask = gigs['title'].str.lower().str.contains(search_lower, na=False) | \
                   gigs['description'].str.lower().str.contains(search_lower, na=False)
            gigs = gigs[mask]
    
    if isinstance(gigs, pd.DataFrame):
        st.write(f"**Found {len(gigs)} gigs**")
        
        if gigs.empty:
            st.info("No gigs found matching your criteria.")
        else:
            # Display gigs
            for idx, (_, gig) in enumerate(gigs.iterrows()):
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"### {gig['title']}")
                        st.markdown(f"**Category:** {gig['category']}")
                        st.markdown(f"**Budget:** {gig['budget_type'].title()} - ${gig['budget_amount']:.2f}")
                        st.markdown(f"**Time Estimate:** {gig['time_estimate']}")
                        st.markdown(f"**Urgency:** {gig['urgency']}")
                        st.markdown(f"**Posted by:** {gig['client_name']} (Rating: {gig['client_rating']:.1f}/5)")
                        st.markdown(f"**Location:** {gig['location']}")
                    
                    with col2:
                        st.markdown(f"**Deadline:** {gig['deadline']}")
                        st.markdown(f"**Status:** {gig['status'].replace('_', ' ').title()}")
                        
                        col_view, col_bid = st.columns(2)
                        with col_view:
                            if st.button("View", key=f"view_{gig['id']}_{idx}"):
                                st.session_state.view_gig = gig['id']
                                st.rerun()
                        with col_bid:
                            if st.button("Bid", key=f"bid_{gig['id']}_{idx}"):
                                st.session_state.bid_gig = gig['id']
                                st.rerun()
                    
                    st.divider()
    else:
        st.info("No gigs available")
    
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def view_gig(gig_id):
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    gig = get_gig_by_id(gig_id)
    if gig is None:
        st.error("Gig not found")
        st.session_state.page = "browse_gigs"
        st.rerun()
        return
    
    st.title(gig['title'])
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**Category:** {gig['category']}")
        st.write(f"**Budget Type:** {gig['budget_type'].title()}")
        st.write(f"**Budget Amount:** ${gig['budget_amount']:.2f}")
        st.write(f"**Time Estimate:** {gig['time_estimate']}")
        st.write(f"**Urgency:** {gig['urgency']}")
        st.write(f"**Location:** {gig['location']}")
        st.write(f"**Deadline:** {gig['deadline']}")
        st.write(f"**Status:** {gig['status'].replace('_', ' ').title()}")
        
        st.divider()
        
        st.write("**Description:**")
        st.write(gig['description'])
        
        st.divider()
        
        # Show bids if user is the gig owner
        if gig['user_id'] == user['id'] and gig['status'] == 'open':
            st.subheader("Bids Received")
            bids = get_gig_bids(gig_id)
            if isinstance(bids, pd.DataFrame) and not bids.empty:
                for _, bid in bids.iterrows():
                    bid_expander = st.expander(f"Bid by {bid['bidder_name']} - ${bid['amount']:.2f}")
                    with bid_expander:
                        st.write(f"**Bidder Rating:** {bid['bidder_rating']:.1f}/5")
                        st.write(f"**Completed Tasks:** {bid['bidder_completed']}")
                        st.write(f"**Estimated Time:** {bid['estimated_time']}")
                        st.write(f"**Proposal:** {bid['proposal']}")
                        st.write(f"**Submitted:** {bid['created_at']}")
                        
                        if st.button("Accept Bid", key=f"accept_bid_{bid['id']}"):
                            with st.spinner("Accepting bid..."):
                                success, message = accept_bid(bid['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
            else:
                st.info("No bids received yet.")
    
    with col2:
        st.write(f"**Posted by:** {gig['client_name']}")
        st.write(f"**Client Rating:** {gig['client_rating']:.1f}/5")
        st.write(f"**Client Tasks Completed:** {gig['client_completed']}")
        
        # Place bid button (only if not the gig owner and gig is open)
        if gig['user_id'] != user['id'] and gig['status'] == 'open':
            st.divider()
            if st.button("Place a Bid", type="primary", use_container_width=True):
                st.session_state.place_bid_gig = gig_id
                st.rerun()
        
        # Show existing bid if user has already bid
        if gig['user_id'] != user['id']:
            user_bids = get_user_bids(user['id'])
            user_bid = user_bids[user_bids['gig_id'] == gig_id]
            if not user_bid.empty:
                st.divider()
                st.write("**Your Bid:**")
                st.write(f"Amount: ${user_bid.iloc[0]['amount']:.2f}")
                st.write(f"Status: {user_bid.iloc[0]['status']}")
    
    if st.button("Back"):
        if 'view_gig' in st.session_state:
            del st.session_state.view_gig
        st.session_state.page = "browse_gigs"
        st.rerun()

def place_bid_page(gig_id):
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    gig = get_gig_by_id(gig_id)
    if gig is None:
        st.error("Gig not found")
        st.session_state.page = "browse_gigs"
        st.rerun()
        return
    
    st.title(f"Place Bid: {gig['title']}")
    
    with st.form("place_bid_form"):
        st.write(f"**Budget Type:** {gig['budget_type'].title()}")
        st.write(f"**Original Budget:** ${gig['budget_amount']:.2f}")
        
        amount = st.number_input("Your Bid Amount ($)*", min_value=0.01, step=0.01, format="%.2f")
        
        estimated_time = st.selectbox("Your Time Estimate*", 
            ["Less than 1 hour", "1-3 hours", "3-8 hours", 
             "1-3 days", "3-7 days", "1-2 weeks", "More than 2 weeks"])
        
        proposal = st.text_area("Your Proposal*", height=150,
                               placeholder="Explain why you're the best fit for this gig...")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Submit Bid", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        if cancel:
            if 'place_bid_gig' in st.session_state:
                del st.session_state.place_bid_gig
            st.session_state.page = "browse_gigs"
            st.rerun()
        
        if submit:
            if not all([amount, estimated_time, proposal]):
                st.error("Please fill all required fields (*)")
            else:
                with st.spinner("Submitting bid..."):
                    success, message = place_bid(gig_id, user['id'], amount, estimated_time, proposal)
                    if success:
                        st.success(message)
                        if 'place_bid_gig' in st.session_state:
                            del st.session_state.place_bid_gig
                        st.session_state.page = "browse_gigs"
                        st.rerun()
                    else:
                        st.error(message)

def my_tasks():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.title("My Tasks")
    
    tab1, tab2, tab3 = st.tabs(["As Client", "As Freelancer", "All Tasks"])
    
    with tab1:
        tasks = get_user_tasks(user['id'], role='client')
        display_tasks(tasks, user, 'client')
    
    with tab2:
        tasks = get_user_tasks(user['id'], role='freelancer')
        display_tasks(tasks, user, 'freelancer')
    
    with tab3:
        tasks = get_user_tasks(user['id'])
        display_tasks(tasks, user, 'all')

def display_tasks(tasks_df, user, role):
    if not isinstance(tasks_df, pd.DataFrame) or tasks_df.empty:
        st.info("No tasks found")
        return
    
    for idx, (_, task) in enumerate(tasks_df.iterrows()):
        task_expander = st.expander(f"{task['gig_title']} - {task['status'].replace('_', ' ').title()}")
        with task_expander:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Task ID:** {task['id']}")
                st.write(f"**Amount:** ${task['amount']:.2f}")
                st.write(f"**Status:** {task['status'].replace('_', ' ').title()}")
                st.write(f"**Started:** {task['started_at']}")
                if task['completed_at']:
                    st.write(f"**Completed:** {task['completed_at']}")
                
                if role == 'client' or role == 'all':
                    st.write(f"**Freelancer:** {task.get('freelancer_name', 'N/A')}")
                if role == 'freelancer' or role == 'all':
                    st.write(f"**Client:** {task.get('client_name', 'N/A')}")
            
            with col2:
                # Action buttons based on status and role
                if task['status'] == 'in_progress':
                    if role == 'freelancer' or (role == 'all' and task['freelancer_id'] == user['id']):
                        if st.button("Mark as Complete", key=f"complete_{task['id']}_{idx}"):
                            with st.spinner("Updating task..."):
                                success, message = complete_task(task['id'], user['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                
                elif task['status'] == 'pending_review':
                    if role == 'client' or (role == 'all' and task['client_id'] == user['id']):
                        col_rate, col_complete = st.columns(2)
                        with col_rate:
                            rating = st.slider("Rate Freelancer", 1, 5, 5, 
                                             key=f"rating_{task['id']}_{idx}")
                            review = st.text_area("Leave Review", 
                                                key=f"review_{task['id']}_{idx}",
                                                placeholder="Optional feedback...")
                        with col_complete:
                            if st.button("Submit Review", key=f"submit_review_{task['id']}_{idx}"):
                                with st.spinner("Submitting review..."):
                                    success, message = complete_task(task['id'], user['id'], 
                                                                   rating, review)
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                
                elif task['status'] == 'completed':
                    st.success("Task Completed!")
                    if task.get('client_rating'):
                        st.write(f"**Client Rating:** {task['client_rating']}/5")
                    if task.get('client_review'):
                        st.write(f"**Client Review:** {task['client_review']}")
                    
                    # Message button
                    other_user_id = task['client_id'] if task['freelancer_id'] == user['id'] else task['freelancer_id']
                    other_user_name = task['client_name'] if task['freelancer_id'] == user['id'] else task['freelancer_name']
                    
                    if st.button(f"Message {other_user_name}", key=f"message_{task['id']}_{idx}"):
                        st.session_state.message_user = other_user_id
                        st.session_state.message_user_name = other_user_name
                        st.session_state.message_task = task['id']
                        st.session_state.page = "messages"
                        st.rerun()

def messages_page():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.title("Messages")
    
    # Get conversation partners
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('''SELECT DISTINCT 
                     CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as other_user_id,
                     u.username as other_user_name
                     FROM messages m
                     JOIN users u ON (CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END) = u.id
                     WHERE sender_id = ? OR receiver_id = ?
                     ORDER BY (SELECT MAX(created_at) FROM messages 
                              WHERE (sender_id = ? AND receiver_id = other_user_id) 
                                 OR (receiver_id = ? AND sender_id = other_user_id)) DESC''',
                  (user['id'], user['id'], user['id'], user['id'], user['id'], user['id']))
        conversations = c.fetchall()
    finally:
        conn.close()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Conversations")
        
        # Start new conversation
        if st.button("New Message", type="primary", use_container_width=True):
            st.session_state.new_message = True
        
        if st.session_state.get('new_message'):
            with st.form("new_message_form"):
                receiver_username = st.text_input("Recipient Username")
                message = st.text_area("Message")
                
                col_send, col_cancel = st.columns(2)
                with col_send:
                    if st.form_submit_button("Send"):
                        # Get receiver ID
                        conn = init_db()
                        try:
                            c = conn.cursor()
                            c.execute('SELECT id FROM users WHERE username = ?', (receiver_username,))
                            receiver = c.fetchone()
                            if receiver:
                                success, msg = send_message(user['id'], receiver[0], None, message)
                                if success:
                                    st.success(msg)
                                    del st.session_state.new_message
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.error("User not found")
                        finally:
                            conn.close()
                
                with col_cancel:
                    if st.form_submit_button("Cancel"):
                        del st.session_state.new_message
                        st.rerun()
        
        # List conversations
        for other_user_id, other_user_name in conversations:
            if st.button(f"{other_user_name}", key=f"conv_{other_user_id}", 
                        use_container_width=True):
                st.session_state.message_user = other_user_id
                st.session_state.message_user_name = other_user_name
                st.rerun()
    
    with col2:
        if st.session_state.get('message_user'):
            st.subheader(f"Chat with {st.session_state.message_user_name}")
            
            # Display messages
            messages = get_user_messages(user['id'], st.session_state.message_user)
            
            for _, msg in messages.iterrows():
                is_sender = msg['sender_id'] == user['id']
                align = "right" if is_sender else "left"
                color = "blue" if is_sender else "gray"
                
                st.markdown(f"""
                <div style='text-align: {align}; margin: 5px;'>
                    <div style='background-color: {color}; color: white; 
                                padding: 8px; border-radius: 10px; 
                                display: inline-block; max-width: 70%;'>
                        {msg['message']}
                    </div>
                    <div style='font-size: 0.8em; color: gray;'>
                        {msg['sender_name']} • {msg['created_at']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Send message form
            with st.form("send_message_form"):
                new_message = st.text_area("Type your message...", key="new_msg")
                
                col_send, col_task = st.columns([3, 1])
                with col_send:
                    if st.form_submit_button("Send", type="primary"):
                        if new_message.strip():
                            success, msg = send_message(user['id'], 
                                                       st.session_state.message_user,
                                                       st.session_state.get('message_task'),
                                                       new_message)
                            if success:
                                st.rerun()
                            else:
                                st.error(msg)
                
                with col_task:
                    # Option to attach to task
                    user_tasks = get_user_tasks(user['id'])
                    if not user_tasks.empty:
                        task_options = {row['id']: row['gig_title'] 
                                       for _, row in user_tasks.iterrows()}
                        selected_task = st.selectbox("Attach to task", 
                                                   options=["None"] + list(task_options.keys()),
                                                   format_func=lambda x: task_options.get(x, "None"))
                        if selected_task != "None":
                            st.session_state.message_task = selected_task
        else:
            st.info("Select a conversation or start a new one")

def portfolio_page():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.title("Your Portfolio")
    
    portfolio = get_user_portfolio(user['id'])
    
    if isinstance(portfolio, pd.DataFrame) and not portfolio.empty:
        st.write(f"**Total Portfolio Items:** {len(portfolio)}")
        
        for _, item in portfolio.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {item['title']}")
                    st.markdown(f"**Client:** {item['client_name']}")
                    st.markdown(f"**Skills Used:** {item['skills_used']}")
                    st.markdown(f"**Completion Date:** {item['completion_date']}")
                    st.markdown(f"**Rating:** {item['rating']}/5")
                    st.markdown(f"**Earnings:** ${item['earnings']:.2f}")
                    
                    if item['description']:
                        st.markdown("**Description:**")
                        st.write(item['description'])
                    
                    if item['client_feedback']:
                        st.markdown("**Client Feedback:**")
                        st.write(item['client_feedback'])
                
                with col2:
                    # Portfolio item actions
                    pass
                
                st.divider()
    else:
        st.info("No portfolio items yet. Complete tasks to build your portfolio!")
    
    # Show statistics
    st.subheader("Portfolio Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        if isinstance(portfolio, pd.DataFrame) and not portfolio.empty:
            avg_rating = portfolio['rating'].mean()
            st.metric("Average Rating", f"{avg_rating:.1f}/5")
        else:
            st.metric("Average Rating", "0.0/5")
    
    with col2:
        if isinstance(portfolio, pd.DataFrame) and not portfolio.empty:
            total_earnings = portfolio['earnings'].sum()
            st.metric("Portfolio Earnings", f"${total_earnings:.2f}")
        else:
            st.metric("Portfolio Earnings", "$0.00")
    
    with col3:
        st.metric("Total Tasks", user['completed_tasks'])
    
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def profile_page():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.title("Your Profile")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Profile Info")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**University:** {user['university']}")
        st.write(f"**Major:** {user['major']}")
        st.write(f"**Skills:** {user['skills']}")
        st.write(f"**Rating:** {user['rating']:.1f}/5")
        st.write(f"**Completed Tasks:** {user['completed_tasks']}")
        st.write(f"**Total Earnings:** ${user['total_earnings']:.2f}")
        
        if user['is_verified']:
            st.success("✓ Verified Student")
        else:
            st.info("Unverified - Contact admin for verification")
    
    with col2:
        st.subheader("Bio")
        if user['bio']:
            st.write(user['bio'])
        else:
            st.info("No bio yet. Add one to improve your profile!")
        
        # Edit profile form
        with st.expander("Edit Profile"):
            with st.form("edit_profile_form"):
                new_bio = st.text_area("Bio", value=user.get('bio', ''), height=100)
                new_skills = st.text_input("Skills", value=user.get('skills', ''))
                
                if st.form_submit_button("Update Profile"):
                    conn = init_db()
                    try:
                        c = conn.cursor()
                        c.execute('UPDATE users SET bio = ?, skills = ? WHERE id = ?',
                                  (new_bio, new_skills, user['id']))
                        conn.commit()
                        
                        # Update session state
                        user['bio'] = new_bio
                        user['skills'] = new_skills
                        st.session_state.user = user
                        
                        st.success("Profile updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating profile: {str(e)}")
                    finally:
                        conn.close()
        
        # Portfolio preview
        st.subheader("Recent Portfolio Items")
        portfolio = get_user_portfolio(user['id'])
        if isinstance(portfolio, pd.DataFrame) and not portfolio.empty:
            recent_items = portfolio.head(3)
            for _, item in recent_items.iterrows():
                st.write(f"**{item['title']}** - {item['rating']}/5")
                st.write(f"Earned: ${item['earnings']:.2f}")
                st.divider()
        else:
            st.info("No portfolio items yet")

# Main app
def main():
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'view_gig' not in st.session_state:
        st.session_state.view_gig = None
    if 'place_bid_gig' not in st.session_state:
        st.session_state.place_bid_gig = None
    if 'bid_gig' not in st.session_state:
        st.session_state.bid_gig = None
    if 'message_user' not in st.session_state:
        st.session_state.message_user = None
    if 'message_user_name' not in st.session_state:
        st.session_state.message_user_name = None
    if 'message_task' not in st.session_state:
        st.session_state.message_task = None
    if 'new_message' not in st.session_state:
        st.session_state.new_message = False
    
    # Initialize database
    init_db()
    
    # Sidebar
    with st.sidebar:
        st.title("SkillSwap")
        st.markdown("🎓 Student Gig Marketplace")
        st.markdown("---")
        
        if is_authenticated():
            user = get_current_user()
            st.success(f"Logged in as: **{user['username']}**")
            st.caption(f"{user['university']} • {user['major']}")
            st.caption(f"Rating: {user['rating']:.1f}/5 • Earnings: ${user['total_earnings']:.2f}")
            st.markdown("---")
            
            # Navigation
            if st.button("Dashboard", use_container_width=True, icon="🏠"):
                st.session_state.page = "dashboard"
                st.rerun()
            
            if st.button("Browse Gigs", use_container_width=True, icon="🔍"):
                st.session_state.page = "browse_gigs"
                st.rerun()
            
            if st.button("Post a Gig", use_container_width=True, icon="➕"):
                st.session_state.page = "post_gig"
                st.rerun()
            
            if st.button("My Tasks", use_container_width=True, icon="📋"):
                st.session_state.page = "my_tasks"
                st.rerun()
            
            if st.button("Messages", use_container_width=True, icon="💬"):
                st.session_state.page = "messages"
                st.rerun()
            
            if st.button("Portfolio", use_container_width=True, icon="📊"):
                st.session_state.page = "portfolio"
                st.rerun()
            
            if st.button("Profile", use_container_width=True, icon="👤"):
                st.session_state.page = "profile"
                st.rerun()
            
            st.markdown("---")
            if st.button("Logout", type="secondary", use_container_width=True, icon="🚪"):
                st.session_state.clear()
                st.rerun()
        else:
            st.info("Login to access the marketplace")
            if st.button("Login / Register", type="primary", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
    
    # Main content with error handling
    try:
        if not is_authenticated():
            login_page()
        else:
            # Clear any residual states if needed
            if st.session_state.page == "login":
                st.session_state.page = "dashboard"
                st.rerun()
            
            # Route to appropriate page
            if st.session_state.view_gig is not None:
                view_gig(st.session_state.view_gig)
            elif st.session_state.place_bid_gig is not None:
                place_bid_page(st.session_state.place_bid_gig)
            elif st.session_state.bid_gig is not None:
                st.session_state.view_gig = st.session_state.bid_gig
                del st.session_state.bid_gig
                st.rerun()
            elif st.session_state.page == "dashboard":
                dashboard()
            elif st.session_state.page == "post_gig":
                post_gig()
            elif st.session_state.page == "browse_gigs":
                browse_gigs()
            elif st.session_state.page == "my_tasks":
                my_tasks()
            elif st.session_state.page == "messages":
                messages_page()
            elif st.session_state.page == "portfolio":
                portfolio_page()
            elif st.session_state.page == "profile":
                profile_page()
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Please try refreshing the page or contact support if the issue persists.")
        
        if st.button("Return to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

if __name__ == "__main__":
    main()