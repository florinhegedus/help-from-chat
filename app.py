import os
import streamlit as st
from openai import OpenAI
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
import google.auth.transport.requests

st.set_page_config(page_title="Improve your conversation",
                   page_icon=":beers:")
st.title("Improve your conversation:")

# Check if running inside a container
in_container = os.getenv('IN_CONTAINER', 'False')  # Default to 'False' if not found

# Access the secret from environment variables
if in_container:
    api_key = os.getenv("OPENAI_API_KEY")
else:
    api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o-mini"

# Authentication
if 'credentials' not in st.session_state:
    st.session_state.credentials = None

if not st.session_state.credentials:
    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]  # e.g., "http://localhost:8501"
    SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent')

    # Provide a link to the user
    st.write(f"[Sign in with Google]({auth_url})")

    # Check if the authorization code is in the query parameters
    code = st.query_params.get_all('code')
    if code:
        code = code[0]  # Get the code from the list
        flow.fetch_token(code=code)
        credentials = flow.credentials
        st.session_state.credentials = credentials

if st.session_state.credentials:
    # User is authenticated
    credentials = st.session_state.credentials
    request = google.auth.transport.requests.Request()
    id_info = id_token.verify_oauth2_token(
        credentials._id_token, request, st.secrets["GOOGLE_CLIENT_ID"])

    # Now we have the user's email and other info
    user_email = id_info.get('email')
    st.write(f"Hello, {user_email}!")

    # Proceed with the rest of the app
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
