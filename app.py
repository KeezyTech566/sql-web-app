import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Load configuration
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 1. Toggle View between Login and Registration
auth_selection = st.sidebar.radio("Authentication", ["Login", "Create Account"])

if auth_selection == "Login":
    authenticator.login(location='main', key='login_widget')
    
    if st.session_state.get("authentication_status"):
        st.success(f"Welcome back, {st.session_state.get('name')}!")
        # Render main application here
    elif st.session_state.get("authentication_status") == False:
        st.error("Invalid username or password.")
    elif st.session_state.get("authentication_status") == None:
        st.info("Please enter your login credentials.")

elif auth_selection == "Create Account":
    st.subheader("Register a New User Account")
    
    with st.form("registration_form"):
        new_email = st.text_input("Email Address")
        new_name = st.text_input("Full Name")
        new_username = st.text_input("Choose Username")
        new_password = st.text_input("Secure Password", type="password")
        new_confirm_password = st.text_input("Confirm Password", type="password")
        submit_registration = st.form_submit_button("Create Account")
        
        if submit_registration:
            if not new_username or not new_password or not new_email or not new_confirm_password:
                st.error("Please fill in all required fields.")
            elif new_password != new_confirm_password:
                st.error("Passwords do not match.")
            elif new_username in config['credentials']['usernames']:
                st.error("Username already exists. Please choose a different one.")
            else:
                # 2. Hash the user-submitted password securely using the correct class method
                hashed_password = stauth.Hasher.hash(new_password)
                
                # 3. Add the user to the config structure
                config['credentials']['usernames'][new_username] = {
                    'email': new_email,
                    'name': new_name,
                    'password': hashed_password,
                    'role': 'viewer' # Default role assignment
                }
                
                # 4. Save changes back to config.yaml to persist the account
                with open('config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                
                st.success("Account successfully created! Switch to the 'Login' view to sign in.")
