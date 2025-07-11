#!/usr/bin/env python3
"""
Regenerate API keys for all apps in last_used order
This maintains the same order as client-side sorting
"""

import psycopg2
import secrets
import string
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="dify",
    user="postgres",
    password="difyai123456"
)

def generate_api_key():
    """Generate a secure API key in Dify format"""
    # Dify format: app-{32 random chars}
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(32))
    return f"app-{random_part}"

try:
    cur = conn.cursor()
    
    # Get all apps with API tokens, ordered by last_used_at
    cur.execute("""
        SELECT DISTINCT ON (a.id) 
            a.id, 
            a.name, 
            t.id as token_id,
            t.token as old_token,
            COALESCE(t.last_used_at, t.created_at) as sort_date
        FROM apps a 
        JOIN api_tokens t ON a.id = t.app_id 
        WHERE t.type = 'app' 
        ORDER BY a.id, COALESCE(t.last_used_at, t.created_at) DESC
    """)
    
    apps = cur.fetchall()
    
    # Sort by last used date
    apps.sort(key=lambda x: x[3], reverse=True)
    
    print("Regenerating API keys in last_used order:")
    print("-" * 80)
    
    new_keys = []
    for app_id, app_name, old_token_id, old_token, sort_date in apps:
        # Generate new token
        new_token = generate_api_key()
        
        # Update the token
        cur.execute("""
            UPDATE api_tokens 
            SET token = %s 
            WHERE id = %s
        """, (new_token, old_token_id))
        
        new_keys.append({
            'app_id': app_id,
            'app_name': app_name,
            'old_token': old_token,
            'new_token': new_token,
            'last_used': sort_date
        })
        
        print(f"App: {app_name[:40]:<40} | Old: {old_token} | New: {new_token}")
    
    # Commit changes
    conn.commit()
    
    print("-" * 120)
    print(f"Successfully regenerated {len(new_keys)} API keys")
    print("\nMapping table (old -> new):")
    print("-" * 120)
    
    for key_info in new_keys:
        print(f"{key_info['old_token']} -> {key_info['new_token']}")
    
    print("\nNew keys in order (for client-side replacement):")
    print("-" * 120)
    
    for key_info in new_keys:
        print(key_info['new_token'])
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()