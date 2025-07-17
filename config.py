# app/config.py
class Config:
    SECRET_KEY = 'your_secret_key_here'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'JMS'

    # Settings for Cross-Origin API Authentication DOING THIS FOR STOPPING AUTO LOGIN
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True

   
    # SECURITY FIX FOR SESSION HANDLING 
   
    # By setting SESSION_PERMANENT to False, the session cookie will be
    # deleted when the user closes their web browser. This prevents
    # the auto-login issue you identified and is much more secure.
    SESSION_PERMANENT = False
