import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import io
import hashlib

st.set_page_config(
    page_title="ShareStuff - Share Expensive Items",
    page_icon="🔄",
    layout="wide"
)

def init_db():
    conn = sqlite3.connect('sharestuff.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        location TEXT,
        bio TEXT,
        rating REAL DEFAULT 0,
        total_ratings INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        price REAL NOT NULL,
        category TEXT NOT NULL,
        condition TEXT NOT NULL,
        location TEXT,
        image BLOB,
        tags TEXT,
        available_for TEXT NOT NULL,
        status TEXT DEFAULT 'available',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        requested_by INTEGER NOT NULL,
        type TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        matched_item_id INTEGER,
        start_date DATE,
        end_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES items (id),
        FOREIGN KEY (requested_by) REFERENCES users (id),
        FOREIGN KEY (matched_item_id) REFERENCES items (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        transaction_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (reviewer_id) REFERENCES users (id),
        FOREIGN KEY (transaction_id) REFERENCES transactions (id)
    )''')
    
    conn.commit()
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication
def register_user(username, email, password, location, bio=""):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO users (username, email, password_hash, location, bio) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (username, email, hash_password(password), location, bio))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = init_db()
    c = conn.cursor()
    c.execute('''SELECT id, username, email, location, bio, rating, total_ratings 
                 FROM users WHERE email = ? AND password_hash = ?''',
              (email, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user

def get_current_user():
    return st.session_state.get('user')

def is_authenticated():
    return 'user' in st.session_state and st.session_state.user is not None

def add_item(user_id, title, description, price, category, condition, location, image, tags, available_for):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO items (user_id, title, description, price, category, 
                     condition, location, image, tags, available_for) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, title, description, price, category, condition, 
                   location, image, tags, available_for))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding item: {e}")
        return False
    finally:
        conn.close()

def get_user_items(user_id):
    conn = init_db()
    try:
        query = 'SELECT * FROM items WHERE user_id = ? ORDER BY created_at DESC'
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df
    except:
        return pd.DataFrame()
    finally:
        conn.close()

def get_all_items(exclude_user_id=None):
    conn = init_db()
    try:
        if exclude_user_id:
            query = '''SELECT items.*, users.username, users.rating as user_rating 
                       FROM items JOIN users ON items.user_id = users.id 
                       WHERE items.user_id != ? AND items.status = "available" 
                       ORDER BY items.created_at DESC'''
            df = pd.read_sql_query(query, conn, params=(exclude_user_id,))
        else:
            query = '''SELECT items.*, users.username, users.rating as user_rating 
                       FROM items JOIN users ON items.user_id = users.id 
                       WHERE items.status = "available" 
                       ORDER BY items.created_at DESC'''
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error getting items: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_item_by_id(item_id):
    conn = init_db()
    try:
        query = '''SELECT items.*, users.username, users.rating as user_rating 
                   FROM items JOIN users ON items.user_id = users.id 
                   WHERE items.id = ?'''
        df = pd.read_sql_query(query, conn, params=(item_id,))
        if not df.empty:
            return df.iloc[0].to_dict()  # Convert to dictionary
        return None
    except Exception as e:
        st.error(f"Error getting item: {e}")
        return None
    finally:
        conn.close()

def delete_item(item_id):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def update_item(item_id, **kwargs):
    conn = init_db()
    try:
        c = conn.cursor()
        if kwargs:
            set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [item_id]
            c.execute(f'UPDATE items SET {set_clause} WHERE id = ?', values)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating item: {e}")
        return False
    finally:
        conn.close()

# Smart matching algorithm
def find_matches(item_id, current_user_id):
    conn = init_db()
    try:
        # Get item details
        item_df = pd.read_sql_query('SELECT * FROM items WHERE id = ?', conn, params=(item_id,))
        if item_df.empty:
            return []
        
        item = item_df.iloc[0]
        
        # Find potential matches
        query = '''SELECT i.*, u.username, u.rating as user_rating 
                   FROM items i JOIN users u ON i.user_id = u.id 
                   WHERE i.user_id != ? AND i.status = "available" AND i.user_id != ?
                   ORDER BY i.created_at DESC'''
        
        potential_items = pd.read_sql_query(query, conn, 
                                          params=(int(item['user_id']), int(current_user_id)))
        
        matches = []
        for _, match_item in potential_items.iterrows():
            score = 0
            
            # Category match (40%)
            if str(item['category']) == str(match_item['category']):
                score += 40
            
            # Price match (30%)
            item_price = float(item['price'])
            match_price = float(match_item['price'])
            price_diff = abs(item_price - match_price) / max(item_price, match_price)
            if price_diff <= 0.2:
                score += 30
            elif price_diff <= 0.5:
                score += 15
            
            # Location match (20%)
            if item['location'] and match_item['location']:
                item_loc = str(item['location']).split(',')[0].strip().lower()
                match_loc = str(match_item['location']).split(',')[0].strip().lower()
                if item_loc == match_loc:
                    score += 20
            
            # Tags match (10%)
            if item['tags'] and match_item['tags']:
                item_tags = set(tag.strip().lower() for tag in str(item['tags']).split(','))
                match_tags = set(tag.strip().lower() for tag in str(match_item['tags']).split(','))
                common = item_tags.intersection(match_tags)
                if common:
                    score += min(len(common) * 5, 10)
            
            # Determine transaction type
            if str(item['available_for']) in ['rental', 'both'] and str(match_item['available_for']) in ['rental', 'both']:
                trans_type = 'rental'
            elif str(item['available_for']) in ['barter', 'both'] and str(match_item['available_for']) in ['barter', 'both']:
                trans_type = 'barter'
            else:
                trans_type = 'rental'  # Default
            
            if score >= 30:
                matches.append({
                    'id': int(match_item['id']),
                    'title': str(match_item['title']),
                    'price': float(match_item['price']),
                    'category': str(match_item['category']),
                    'condition': str(match_item['condition']),
                    'username': str(match_item['username']),
                    'user_rating': float(match_item['user_rating'] or 0),
                    'match_score': min(score, 100),
                    'type': trans_type,
                    'available_for': str(match_item['available_for'])
                })
        
        return sorted(matches, key=lambda x: x['match_score'], reverse=True)[:5]
    except Exception as e:
        st.error(f"Error finding matches: {e}")
        return []
    finally:
        conn.close()

# Get user rating - FIXED
def get_user_rating(user_id):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('SELECT rating FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0.0
    except:
        return 0.0
    finally:
        conn.close()

def create_transaction(item_id, requested_by, trans_type, matched_item_id=None, start_date=None, end_date=None):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO transactions (item_id, requested_by, type, matched_item_id, start_date, end_date, status) 
                     VALUES (?, ?, ?, ?, ?, ?, 'pending')''',
                  (int(item_id), int(requested_by), str(trans_type), matched_item_id, start_date, end_date))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating transaction: {e}")
        return False
    finally:
        conn.close()

def get_user_transactions(user_id):
    conn = init_db()
    try:
        query = '''SELECT t.*, i.title as item_title, u.username as owner_name, 
                          u2.username as requester_name,
                          mi.title as matched_item_title
                   FROM transactions t
                   JOIN items i ON t.item_id = i.id
                   JOIN users u ON i.user_id = u.id
                   JOIN users u2 ON t.requested_by = u2.id
                   LEFT JOIN items mi ON t.matched_item_id = mi.id
                   WHERE t.requested_by = ? OR i.user_id = ?
                   ORDER BY t.created_at DESC'''
        df = pd.read_sql_query(query, conn, params=(int(user_id), int(user_id)))
        return df
    except Exception as e:
        st.error(f"Error getting transactions: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def update_transaction_status(transaction_id, status):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('UPDATE transactions SET status = ? WHERE id = ?', (str(status), int(transaction_id)))
        
        # If transaction is completed or cancelled and was a rental, free up the item
        if status in ['completed', 'cancelled']:
            # Get the item_id from transaction
            c.execute('SELECT item_id FROM transactions WHERE id = ?', (int(transaction_id),))
            result = c.fetchone()
            if result:
                item_id = result[0]
                c.execute('UPDATE items SET status = "available" WHERE id = ?', (int(item_id),))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating transaction: {e}")
        return False
    finally:
        conn.close()

# Review functions - FIXED
def add_review(user_id, reviewer_id, transaction_id, rating, comment=""):
    conn = init_db()
    try:
        c = conn.cursor()
        
        # Check if review already exists
        c.execute('SELECT id FROM reviews WHERE user_id = ? AND reviewer_id = ? AND transaction_id = ?',
                  (int(user_id), int(reviewer_id), int(transaction_id)))
        existing = c.fetchone()
        
        if existing:
            c.execute('UPDATE reviews SET rating = ?, comment = ? WHERE id = ?',
                      (int(rating), str(comment), existing[0]))
        else:
            c.execute('''INSERT INTO reviews (user_id, reviewer_id, transaction_id, rating, comment) 
                         VALUES (?, ?, ?, ?, ?)''',
                      (int(user_id), int(reviewer_id), int(transaction_id), int(rating), str(comment)))
        
        # Update user's average rating
        c.execute('SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM reviews WHERE user_id = ?', (int(user_id),))
        result = c.fetchone()
        if result:
            avg_rating = result[0] or 0.0
            count = result[1] or 0
            c.execute('UPDATE users SET rating = ?, total_ratings = ? WHERE id = ?',
                      (float(avg_rating), int(count), int(user_id)))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding review: {e}")
        return False
    finally:
        conn.close()

def get_user_reviews(user_id):
    conn = init_db()
    try:
        query = '''SELECT r.*, u.username as reviewer_name 
                   FROM reviews r 
                   JOIN users u ON r.reviewer_id = u.id 
                   WHERE r.user_id = ? 
                   ORDER BY r.created_at DESC'''
        df = pd.read_sql_query(query, conn, params=(user_id,))
        return df
    except Exception as e:
        st.error(f"Error getting reviews: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# Check if user has reviewed a transaction
def has_user_reviewed(transaction_id, reviewer_id):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('SELECT id FROM reviews WHERE transaction_id = ? AND reviewer_id = ?',
                  (int(transaction_id), int(reviewer_id)))
        result = c.fetchone()
        return result is not None
    except:
        return False
    finally:
        conn.close()

# Get user ID by username
def get_user_id_by_username(username):
    conn = init_db()
    try:
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        result = c.fetchone()
        if result:
            return result[0]
        return None
    except:
        return None
    finally:
        conn.close()

# Image processing
def process_image(uploaded_file):
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            # Resize image to reasonable dimensions
            image.thumbnail((400, 400))
            buf = io.BytesIO()
            image.save(buf, format='JPEG')
            return buf.getvalue()
        except Exception as e:
            st.error(f"Error processing image: {e}")
    return None

# UI Components
def login_page():
    st.title("ShareStuff - Login")
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
                    user = login_user(email, password)
                    if user:
                        st.session_state.user = {
                            'id': user[0],
                            'username': user[1],
                            'email': user[2],
                            'location': user[3],
                            'bio': user[4],
                            'rating': user[5],
                            'total_ratings': user[6]
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
                username = st.text_input("Username")
                email = st.text_input("Email")
            with col2:
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
            
            location = st.text_input("Location")
            bio = st.text_area("Bio (optional)")
            
            submit = st.form_submit_button("Register", type="primary")
            
            if submit:
                if not all([username, email, password, confirm_password, location]):
                    st.error("Please fill all required fields")
                elif password != confirm_password:
                    st.error("Passwords don't match")
                else:
                    if register_user(username, email, password, location, bio):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username or email already exists")

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
        items_count = len(get_user_items(user['id']))
        st.metric("Your Items", items_count)
    with col2:
        transactions = get_user_transactions(user['id'])
        if isinstance(transactions, pd.DataFrame) and not transactions.empty:
            pending = len(transactions[transactions['status'] == 'pending'])
        else:
            pending = 0
        st.metric("Pending Requests", pending)
    with col3:
        st.metric("Your Rating", f"{user['rating']:.1f}/5")
    with col4:
        st.metric("Total Reviews", user['total_ratings'])
    
    # Quick actions
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("List New Item", use_container_width=True, type="primary"):
            st.session_state.page = "list_item"
            st.rerun()
    with col2:
        if st.button("Browse Items", use_container_width=True):
            st.session_state.page = "browse"
            st.rerun()
    with col3:
        if st.button("View Transactions", use_container_width=True):
            st.session_state.page = "transactions"
            st.rerun()
    
    # Recent items
    st.subheader("Your Recent Items")
    items = get_user_items(user['id'])
    if isinstance(items, pd.DataFrame) and not items.empty:
        recent_items = items.head(3)
        cols = st.columns(3)
        for idx, (_, item) in enumerate(recent_items.iterrows()):
            with cols[idx]:
                with st.container():
                    st.write(f"**{item['title']}**")
                    st.write(f"${item['price']:.2f}")
                    st.write(f"Status: {item['status'].title()}")
                    
                    if item['image']:
                        try:
                            st.image(item['image'], use_container_width=True)
                        except:
                            st.info("Image not available")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Manage", key=f"dashboard_manage_{item['id']}_{idx}"):
                            st.session_state.edit_item_id = item['id']
                            st.rerun()
                    with col2:
                        if st.button("Matches", key=f"dashboard_matches_{item['id']}_{idx}"):
                            st.session_state.view_item = item['id']
                            st.rerun()
    else:
        st.info("You haven't listed any items yet. Click 'List New Item' to get started!")
    
    # Recent transactions
    st.subheader("Recent Transactions")
    transactions = get_user_transactions(user['id'])
    if isinstance(transactions, pd.DataFrame) and not transactions.empty:
        recent_trans = transactions.head(3)
        for _, trans in recent_trans.iterrows():
            status_text = str(trans['status']).title()
            st.write(f"**{trans['item_title']}** - {status_text}")
    else:
        st.info("No transactions yet")

def list_item():
    st.title("List New Item")
    
    with st.form("list_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Item Title*")
            price = st.number_input("Price ($)*", min_value=0.0, step=0.01, format="%.2f")
            category = st.selectbox("Category*", 
                ["Electronics", "Tools", "Sports Equipment", "Party Supplies", 
                 "Outdoor Gear", "Kitchen Appliances", "Furniture", "Clothing", "Books", "Other"])
            condition = st.selectbox("Condition*", 
                ["New", "Like New", "Good", "Fair", "Needs Repair"])
        
        with col2:
            description = st.text_area("Description*", height=100)
            user = get_current_user()
            location = st.text_input("Location*", value=user.get('location', '') if user else '')
            tags = st.text_input("Tags (comma separated)", 
                                placeholder="e.g., camping, portable, professional")
            available_for = st.selectbox("Available For*", 
                ["rental", "barter", "both"])
        
        image = st.file_uploader("Upload Image (optional)", type=['jpg', 'jpeg', 'png'])
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("List Item", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        if cancel:
            st.session_state.page = "dashboard"
            st.rerun()
        
        if submit:
            if not all([title, description, price, category, condition, location]):
                st.error("Please fill all required fields (*)")
            else:
                user = get_current_user()
                if user is None:
                    st.error("You must be logged in to list items")
                    return
                
                image_bytes = process_image(image)
                
                success = add_item(
                    user_id=user['id'],
                    title=title,
                    description=description,
                    price=float(price),
                    category=category,
                    condition=condition,
                    location=location,
                    image=image_bytes,
                    tags=tags,
                    available_for=available_for
                )
                
                if success:
                    st.success("Item listed successfully!")
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Failed to list item")

def browse_items():
    st.title("Browse Items")
    
    # Filters
    with st.expander("Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("Category", ["All"] + 
                ["Electronics", "Tools", "Sports Equipment", "Party Supplies", 
                 "Outdoor Gear", "Kitchen Appliances", "Furniture", "Clothing", "Books", "Other"])
        with col2:
            available = st.selectbox("Available For", ["All", "rental", "barter", "both"])
        with col3:
            condition = st.selectbox("Condition", ["All", "New", "Like New", "Good", "Fair", "Needs Repair"])
    
    search = st.text_input("Search items by title or description")
    
    # Get items
    user = get_current_user()
    items = get_all_items(exclude_user_id=user['id'] if user else None)
    
    # Apply filters
    if isinstance(items, pd.DataFrame) and not items.empty:
        if category != "All":
            items = items[items['category'] == category]
        if available != "All":
            items = items[items['available_for'] == available]
        if condition != "All":
            items = items[items['condition'] == condition]
        if search:
            search_lower = search.lower()
            mask = items['title'].str.lower().str.contains(search_lower, na=False) | \
                   items['description'].str.lower().str.contains(search_lower, na=False)
            items = items[mask]
    
    if isinstance(items, pd.DataFrame):
        st.write(f"**Found {len(items)} items**")
        
        if items.empty:
            st.info("No items found matching your criteria.")
        else:
            # Display items in a grid
            cols = st.columns(3)
            for idx, (_, item) in enumerate(items.iterrows()):
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"### {item['title']}")
                        st.markdown(f"**${item['price']:.2f}**")
                        
                        # Display image
                        if item['image']:
                            try:
                                st.image(item['image'], use_container_width=True)
                            except:
                                st.info("Image not available")
                        
                        # Basic info
                        st.markdown(f"**Category:** {item['category']}")
                        st.markdown(f"**Condition:** {item['condition']}")
                        st.markdown(f"**Available for:** {item['available_for'].title()}")
                        
                        # Get user rating properly
                        owner_rating = get_user_rating(item['user_id'])
                        st.markdown(f"**Owner:** {item['username']} (Rating: {owner_rating:.1f}/5)")
                        
                        st.markdown(f"**Location:** {item['location']}")
                        
                        # Action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Details", key=f"browse_details_{item['id']}_{idx}", use_container_width=True):
                                st.session_state.view_item = item['id']
                                st.rerun()
                        with col2:
                            if st.button("Request", key=f"browse_request_{item['id']}_{idx}", use_container_width=True):
                                st.session_state.request_item_id = item['id']
                                st.rerun()
                        
                        st.divider()
    else:
        st.info("No items available")

def view_item(item_id):
    item = get_item_by_id(item_id)
    if item is None:
        st.error("Item not found")
        if st.button("Back"):
            if 'view_item' in st.session_state:
                del st.session_state.view_item
            st.session_state.page = "browse"
            st.rerun()
        return
    
    st.title(f"{item['title']}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if item.get('image'):
            try:
                st.image(item['image'], use_container_width=True)
            except:
                st.info("Image not available")
        else:
            st.info("No image available")
        
        st.metric("Price", f"${item.get('price', 0):.2f}")
        
        # Get owner rating properly
        owner_rating = get_user_rating(item['user_id'])
        st.metric("Owner Rating", f"{owner_rating:.1f}/5")
    
    with col2:
        st.write(f"**Category:** {item.get('category', 'N/A')}")
        st.write(f"**Condition:** {item.get('condition', 'N/A')}")
        st.write(f"**Available for:** {item.get('available_for', 'N/A').title()}")
        st.write(f"**Location:** {item.get('location', 'N/A')}")
        st.write(f"**Owner:** {item.get('username', 'N/A')}")
        if item.get('tags'):
            st.write(f"**Tags:** {item['tags']}")
        
        st.divider()
        
        st.write("**Description:**")
        st.write(item.get('description', 'No description available'))
        
        st.divider()
        
        # Smart matches
        st.subheader("Smart Matches")
        user = get_current_user()
        if user:
            matches = find_matches(item_id, user['id'])
            
            if matches:
                st.write(f"Found {len(matches)} potential matches:")
                for idx, match in enumerate(matches[:3]):  # Show top 3 matches
                    # Use unique identifier for each expander
                    match_expander = st.expander(f"{match['title']} - {match['match_score']}% match")
                    with match_expander:
                        st.write(f"**Price:** ${match['price']:.2f}")
                        st.write(f"**Category:** {match['category']}")
                        st.write(f"**Condition:** {match['condition']}")
                        
                        # Get match owner rating properly
                        conn = init_db()
                        try:
                            c = conn.cursor()
                            c.execute('SELECT rating FROM users WHERE username = ?', (match['username'],))
                            result = c.fetchone()
                            match_owner_rating = float(result[0]) if result and result[0] else 0.0
                        except:
                            match_owner_rating = 0.0
                        finally:
                            conn.close()
                        
                        st.write(f"**Owner:** {match['username']} (Rating: {match_owner_rating:.1f}/5)")
                        st.write(f"**Type:** {match['type'].title()}")
                        
                        if match['type'] == 'rental':
                            if st.button("Request Rental", key=f"view_rent_{match['id']}_{idx}"):
                                st.session_state.request_item_id = match['id']
                                st.rerun()
                        else:
                            if st.button("Propose Barter", key=f"view_barter_{match['id']}_{idx}"):
                                st.session_state.barter_proposal = (item_id, match['id'])
                                st.rerun()
            else:
                st.info("No matches found yet. Try adjusting your item details!")
        else:
            st.info("Login to see matches")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Request This Item", use_container_width=True, type="primary"):
                st.session_state.request_item_id = item_id
                st.rerun()
        with col2:
            if st.button("More Matches", use_container_width=True):
                # Show more matches
                pass
        with col3:
            if st.button("Back", use_container_width=True):
                if 'view_item' in st.session_state:
                    del st.session_state.view_item
                st.session_state.page = "browse"
                st.rerun()

def manage_items():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    items = get_user_items(user['id'])
    
    st.title("Your Items")
    
    if isinstance(items, pd.DataFrame) and not items.empty:
        for idx, (_, item) in enumerate(items.iterrows()):
            # Create unique expander for each item
            item_expander = st.expander(f"{item['title']} - ${item['price']:.2f} - {item['status'].title()}")
            with item_expander:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if item['image']:
                        try:
                            st.image(item['image'], use_container_width=True)
                        except:
                            st.info("Image not available")
                    else:
                        st.info("No image")
                
                with col2:
                    st.write(f"**Category:** {item['category']}")
                    st.write(f"**Condition:** {item['condition']}")
                    st.write(f"**Available for:** {item['available_for'].title()}")
                    st.write(f"**Location:** {item['location']}")
                    st.write(f"**Description:** {item['description'][:200]}...")
                    if item['tags']:
                        st.write(f"**Tags:** {item['tags']}")
                    
                    col_edit, col_delete, col_matches = st.columns(3)
                    with col_edit:
                        if st.button("Edit", key=f"manage_edit_{item['id']}_{idx}", use_container_width=True):
                            st.session_state.edit_item_id = item['id']
                            st.rerun()
                    with col_delete:
                        if st.button("Delete", key=f"manage_delete_{item['id']}_{idx}", use_container_width=True):
                            if delete_item(item['id']):
                                st.success("Item deleted!")
                                st.rerun()
                    with col_matches:
                        if st.button("Matches", key=f"manage_matches_{item['id']}_{idx}", use_container_width=True):
                            st.session_state.view_item = item['id']
                            st.rerun()
    else:
        st.info("You haven't listed any items yet.")
    
    if st.button("List New Item", type="primary"):
        st.session_state.page = "list_item"
        st.rerun()

def edit_item(item_id):
    item = get_item_by_id(item_id)
    if item is None:
        st.error("Item not found")
        st.session_state.page = "manage_items"
        st.rerun()
        return
    
    st.title("Edit Item")
    
    with st.form("edit_item_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Item Title*", value=item.get('title', ''))
            price = st.number_input("Price ($)*", min_value=0.0, 
                                   value=float(item.get('price', 0)), step=0.01, format="%.2f")
            category = st.selectbox("Category*", 
                ["Electronics", "Tools", "Sports Equipment", "Party Supplies", 
                 "Outdoor Gear", "Kitchen Appliances", "Furniture", "Clothing", "Books", "Other"],
                index=["Electronics", "Tools", "Sports Equipment", "Party Supplies", 
                      "Outdoor Gear", "Kitchen Appliances", "Furniture", "Clothing", "Books", "Other"].index(
                          item.get('category', 'Other')) if item.get('category') in 
                          ["Electronics", "Tools", "Sports Equipment", "Party Supplies", 
                           "Outdoor Gear", "Kitchen Appliances", "Furniture", "Clothing", "Books", "Other"] else 9)
            condition = st.selectbox("Condition*", 
                ["New", "Like New", "Good", "Fair", "Needs Repair"],
                index=["New", "Like New", "Good", "Fair", "Needs Repair"].index(
                    item.get('condition', 'Good')) if item.get('condition') in 
                    ["New", "Like New", "Good", "Fair", "Needs Repair"] else 2)
        
        with col2:
            description = st.text_area("Description*", value=item.get('description', ''), height=100)
            location = st.text_input("Location*", value=item.get('location', ''))
            tags = st.text_input("Tags (comma separated)", value=item.get('tags', '') or '')
            available_for = st.selectbox("Available For*", 
                ["rental", "barter", "both"],
                index=["rental", "barter", "both"].index(
                    item.get('available_for', 'rental')) if item.get('available_for') in 
                    ["rental", "barter", "both"] else 0)
            status = st.selectbox("Status", 
                ["available", "pending", "rented"],
                index=["available", "pending", "rented"].index(
                    item.get('status', 'available')) if item.get('status') in 
                    ["available", "pending", "rented"] else 0)
        
        image = st.file_uploader("Upload New Image (optional)", type=['jpg', 'jpeg', 'png'])
        
        if item.get('image'):
            st.write("Current image:")
            try:
                st.image(item['image'], width=200)
            except:
                st.info("Image not available")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        if cancel:
            st.session_state.edit_item_id = None
            st.session_state.page = "manage_items"
            st.rerun()
        
        if submit:
            if not all([title, description, price, category, condition, location]):
                st.error("Please fill all required fields (*)")
            else:
                update_data = {
                    'title': title,
                    'description': description,
                    'price': float(price),
                    'category': category,
                    'condition': condition,
                    'location': location,
                    'tags': tags,
                    'available_for': available_for,
                    'status': status
                }
                
                if image:
                    image_bytes = process_image(image)
                    if image_bytes:
                        update_data['image'] = image_bytes
                
                if update_item(item_id, **update_data):
                    st.success("Item updated successfully!")
                    st.session_state.edit_item_id = None
                    st.session_state.page = "manage_items"
                    st.rerun()
                else:
                    st.error("Failed to update item")

def request_item(item_id):
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    item = get_item_by_id(item_id)
    
    if item is None:
        st.error("Item not found")
        st.session_state.page = "browse"
        st.rerun()
        return
    
    st.title("Request Item")
    st.write(f"**Item:** {item.get('title', 'Unknown')}")
    st.write(f"**Owner:** {item.get('username', 'Unknown')}")
    st.write(f"**Price:** ${item.get('price', 0):.2f}")
    
    # Determine available transaction types based on item availability
    available_for = item.get('available_for', 'rental')
    available_types = []
    if available_for in ['rental', 'both']:
        available_types.append('rental')
    if available_for in ['barter', 'both']:
        available_types.append('barter')
    
    if not available_types:
        st.error("This item is not available for any transaction type")
        if st.button("Back"):
            st.session_state.request_item_id = None
            st.rerun()
        return
    
    if len(available_types) == 1:
        trans_type = available_types[0]
    else:
        trans_type = st.radio("Transaction Type", available_types,
                            format_func=lambda x: "Rental" if x == 'rental' else "Barter Exchange")
    
    with st.form("request_form"):
        if trans_type == 'rental':
            st.write("### Rental Details")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", min_value=datetime.now().date())
            with col2:
                end_date = st.date_input("End Date", min_value=start_date + timedelta(days=1))
        
        elif trans_type == 'barter':
            st.write("### Barter Details")
            # Show user's available items for barter
            user_items = get_user_items(user['id'])
            if isinstance(user_items, pd.DataFrame) and not user_items.empty:
                available_items = user_items[user_items['status'] == 'available']
                
                if not available_items.empty:
                    item_options = {row['id']: f"{row['title']} (${row['price']:.2f})" 
                                   for _, row in available_items.iterrows()}
                    selected_item = st.selectbox("Select your item for exchange", 
                                               options=list(item_options.keys()),
                                               format_func=lambda x: item_options[x])
                    matched_item_id = selected_item
                else:
                    st.warning("You don't have any available items to barter. Please list an item first.")
                    matched_item_id = None
            else:
                st.warning("You don't have any items to barter. Please list an item first.")
                matched_item_id = None
        
        message = st.text_area("Additional Message (optional)", 
                              placeholder="Add any additional information...")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Send Request", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        if cancel:
            st.session_state.request_item_id = None
            st.rerun()
        
        if submit:
            if trans_type == 'rental' and start_date >= end_date:
                st.error("End date must be after start date")
            elif trans_type == 'barter' and matched_item_id is None:
                st.error("Please select an item for barter")
            else:
                success = create_transaction(
                    item_id=item_id,
                    requested_by=user['id'],
                    trans_type=trans_type,
                    matched_item_id=matched_item_id if trans_type == 'barter' else None,
                    start_date=start_date.strftime('%Y-%m-%d') if trans_type == 'rental' else None,
                    end_date=end_date.strftime('%Y-%m-%d') if trans_type == 'rental' else None
                )
                if success:
                    st.success("Request sent successfully!")
                    st.session_state.request_item_id = None
                    st.rerun()
                else:
                    st.error("Failed to send request")

def view_transactions():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    transactions = get_user_transactions(user['id'])
    
    st.title("Your Transactions")
    
    if isinstance(transactions, pd.DataFrame) and not transactions.empty:
        # Filter tabs
        tab1, tab2, tab3, tab4 = st.tabs(["All", "Pending", "Accepted", "Completed"])
        
        with tab1:
            display_transactions(transactions, user, "all")
        with tab2:
            pending = transactions[transactions['status'] == 'pending']
            display_transactions(pending, user, "pending")
        with tab3:
            accepted = transactions[transactions['status'] == 'accepted']
            display_transactions(accepted, user, "accepted")
        with tab4:
            completed = transactions[transactions['status'] == 'completed']
            display_transactions(completed, user, "completed")
    else:
        st.info("No transactions yet.")

def display_transactions(transactions_df, user, tab_type):
    if not isinstance(transactions_df, pd.DataFrame) or transactions_df.empty:
        st.info("No transactions in this category")
        return
    
    for idx, (_, trans) in enumerate(transactions_df.iterrows()):
        # Create expander without key parameter
        trans_expander = st.expander(f"{trans['item_title']} - {str(trans['status']).title()} - {str(trans['type']).title()}")
        with trans_expander:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Type:** {str(trans['type']).title()}")
                st.write(f"**Status:** {str(trans['status']).title()}")
                st.write(f"**Requested by:** {trans['requester_name']}")
                st.write(f"**Item Owner:** {trans['owner_name']}")
                if trans['matched_item_title']:
                    st.write(f"**Barter Item:** {trans['matched_item_title']}")
                if trans['start_date']:
                    st.write(f"**Start Date:** {trans['start_date']}")
                if trans['end_date']:
                    st.write(f"**End Date:** {trans['end_date']}")
                st.write(f"**Created:** {trans['created_at']}")
            
            with col2:
                # Action buttons based on status and user role
                if str(trans['status']) == 'pending':
                    if user['username'] == trans['owner_name']:
                        col_accept, col_reject = st.columns(2)
                        with col_accept:
                            if st.button("Accept", key=f"accept_{trans['id']}_{tab_type}_{idx}", use_container_width=True):
                                if update_transaction_status(trans['id'], 'accepted'):
                                    st.success("Transaction accepted!")
                                    st.rerun()
                        with col_reject:
                            if st.button("Reject", key=f"reject_{trans['id']}_{tab_type}_{idx}", use_container_width=True):
                                if update_transaction_status(trans['id'], 'cancelled'):
                                    st.success("Transaction rejected!")
                                    st.rerun()
                    else:
                        st.info("Waiting for owner's response")
                
                elif str(trans['status']) == 'accepted':
                    if st.button("Mark as Completed", key=f"complete_{trans['id']}_{tab_type}_{idx}", use_container_width=True, type="primary"):
                        if update_transaction_status(trans['id'], 'completed'):
                            st.success("Transaction marked as completed!")
                            st.rerun()
                
                elif str(trans['status']) == 'completed':
                    # Check if review already given
                    if not has_user_reviewed(trans['id'], user['id']):
                        # Determine who to review
                        if user['username'] == trans['owner_name']:
                            user_to_review_name = trans['requester_name']
                            # Get user_id of requester
                            user_to_review_id = get_user_id_by_username(user_to_review_name)
                        else:
                            user_to_review_name = trans['owner_name']
                            user_to_review_id = get_user_id_by_username(user_to_review_name)
                        
                        if user_to_review_id:
                            if st.button(f"Review {user_to_review_name}", key=f"review_{trans['id']}_{tab_type}_{idx}", use_container_width=True):
                                st.session_state.review_transaction = trans['id']
                                st.session_state.review_user_id = user_to_review_id
                                st.session_state.review_user_name = user_to_review_name
                                st.rerun()
                    else:
                        st.success("Review submitted")

def review_page():
    if 'review_transaction' not in st.session_state:
        st.session_state.page = "transactions"
        st.rerun()
        return
    
    transaction_id = st.session_state.review_transaction
    user_to_review_id = st.session_state.review_user_id
    user_to_review_name = st.session_state.review_user_name
    
    st.title("Leave a Review")
    st.write(f"Reviewing user: {user_to_review_name}")
    
    with st.form("review_form"):
        rating = st.slider("Rating", 1, 5, 5, 
                          help="1 = Poor, 5 = Excellent")
        
        comment = st.text_area("Comment (optional)", 
                              placeholder="Share your experience...",
                              height=100)
        
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            if st.form_submit_button("Submit Review", type="primary", use_container_width=True):
                user = get_current_user()
                if user:
                    success = add_review(
                        user_id=user_to_review_id,
                        reviewer_id=user['id'],
                        transaction_id=transaction_id,
                        rating=rating,
                        comment=comment
                    )
                    if success:
                        st.success("Review submitted successfully!")
                        # Clear review state
                        del st.session_state.review_transaction
                        del st.session_state.review_user_id
                        del st.session_state.review_user_name
                        st.session_state.page = "transactions"
                        st.rerun()
                    else:
                        st.error("Failed to submit review")
        
        with col_cancel:
            if st.form_submit_button("Cancel", use_container_width=True):
                # Clear review state
                if 'review_transaction' in st.session_state:
                    del st.session_state.review_transaction
                if 'review_user_id' in st.session_state:
                    del st.session_state.review_user_id
                if 'review_user_name' in st.session_state:
                    del st.session_state.review_user_name
                st.session_state.page = "transactions"
                st.rerun()

def view_reviews():
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    reviews = get_user_reviews(user['id'])
    
    st.title("Your Reviews")
    
    if isinstance(reviews, pd.DataFrame) and not reviews.empty:
        for idx, (_, review) in enumerate(reviews.iterrows()):
            with st.container():
                st.write(f"**From:** {review['reviewer_name']}")
                st.write(f"**Rating:** {review['rating']}/5")
                st.write(f"**Date:** {review['created_at']}")
                if review['comment']:
                    st.write(f"**Comment:** {review['comment']}")
                st.divider()
    else:
        st.info("No reviews received yet.")

def barter_proposal(item1_id, item2_id):
    user = get_current_user()
    if user is None:
        st.session_state.page = "login"
        st.rerun()
        return
    
    item1 = get_item_by_id(item1_id)  # Your item
    item2 = get_item_by_id(item2_id)  # Their item
    
    if item1 is None or item2 is None:
        st.error("One or both items not found")
        st.session_state.barter_proposal = None
        st.rerun()
        return
    
    st.title("Barter Proposal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Your Item")
        st.write(f"**{item1.get('title', 'Unknown')}**")
        st.write(f"**Price:** ${item1.get('price', 0):.2f}")
        st.write(f"**Condition:** {item1.get('condition', 'Unknown')}")
        if item1.get('image'):
            try:
                st.image(item1['image'], width=200)
            except:
                st.info("Image not available")
        st.write(f"**Description:** {item1.get('description', '')[:150]}...")
    
    with col2:
        st.subheader("Their Item")
        st.write(f"**{item2.get('title', 'Unknown')}**")
        st.write(f"**Price:** ${item2.get('price', 0):.2f}")
        st.write(f"**Condition:** {item2.get('condition', 'Unknown')}")
        
        # Get owner rating properly
        owner_rating = get_user_rating(item2['user_id'])
        st.write(f"**Owner:** {item2.get('username', 'Unknown')} (Rating: {owner_rating:.1f}/5)")
        
        if item2.get('image'):
            try:
                st.image(item2['image'], width=200)
            except:
                st.info("Image not available")
        st.write(f"**Description:** {item2.get('description', '')[:150]}...")
    
    st.divider()
    
    st.write("**Proposed Exchange:**")
    st.write(f"Your **{item1.get('title', 'Item')}** for their **{item2.get('title', 'Item')}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Send Proposal", type="primary", use_container_width=True):
            success = create_transaction(
                item_id=item2_id,  # Their item
                requested_by=user['id'],
                trans_type='barter',
                matched_item_id=item1_id  # Your item
            )
            if success:
                st.success("Barter proposal sent!")
                st.session_state.barter_proposal = None
                st.rerun()
            else:
                st.error("Failed to send proposal")
    
    with col2:
        if st.button("Edit Proposal", use_container_width=True):
            # Go back to match selection
            st.session_state.barter_proposal = None
            st.session_state.view_item = item1_id
            st.rerun()
    
    with col3:
        if st.button("Cancel", use_container_width=True):
            st.session_state.barter_proposal = None
            st.rerun()

# Main app
def main():
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'view_item' not in st.session_state:
        st.session_state.view_item = None
    if 'request_item_id' not in st.session_state:
        st.session_state.request_item_id = None
    if 'edit_item_id' not in st.session_state:
        st.session_state.edit_item_id = None
    if 'barter_proposal' not in st.session_state:
        st.session_state.barter_proposal = None
    if 'review_transaction' not in st.session_state:
        st.session_state.review_transaction = None
    if 'review_user_id' not in st.session_state:
        st.session_state.review_user_id = None
    if 'review_user_name' not in st.session_state:
        st.session_state.review_user_name = None
    
    # Initialize database
    init_db()
    
    # Sidebar
    with st.sidebar:
        st.title("ShareStuff")
        st.markdown("---")
        
        if is_authenticated():
            user = get_current_user()
            st.success(f"Logged in as: **{user['username']}**")
            st.caption(f"Location: {user['location']}")
            st.caption(f"Rating: {user['rating']:.1f}/5")
            st.markdown("---")
            
            # Navigation
            if st.button("Dashboard", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
            
            if st.button("Browse Items", use_container_width=True):
                st.session_state.page = "browse"
                st.rerun()
            
            if st.button("My Items", use_container_width=True):
                st.session_state.page = "manage_items"
                st.rerun()
            
            if st.button("Transactions", use_container_width=True):
                st.session_state.page = "transactions"
                st.rerun()
            
            if st.button("My Reviews", use_container_width=True):
                st.session_state.page = "reviews"
                st.rerun()
            
            st.markdown("---")
            if st.button("Logout", type="secondary", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            st.info("Please login to access all features")
    
    # Main content
    if not is_authenticated():
        login_page()
    else:
        # Clear any residual states if needed
        if st.session_state.page == "login":
            st.session_state.page = "dashboard"
            st.rerun()
        
        # Route to appropriate page
        if st.session_state.review_transaction is not None:
            review_page()
        elif st.session_state.request_item_id is not None:
            request_item(st.session_state.request_item_id)
        elif st.session_state.edit_item_id is not None:
            edit_item(st.session_state.edit_item_id)
        elif st.session_state.view_item is not None:
            view_item(st.session_state.view_item)
        elif st.session_state.barter_proposal is not None:
            barter_proposal(*st.session_state.barter_proposal)
        elif st.session_state.page == "dashboard":
            dashboard()
        elif st.session_state.page == "list_item":
            list_item()
        elif st.session_state.page == "browse":
            browse_items()
        elif st.session_state.page == "manage_items":
            manage_items()
        elif st.session_state.page == "transactions":
            view_transactions()
        elif st.session_state.page == "reviews":
            view_reviews()

if __name__ == "__main__":
    main()
