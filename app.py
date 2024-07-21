import time
import os
import joblib
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

MODEL_ROLE = 'ai'
AI_AVATAR_ICON = '✨'

# Create a data/ folder if it doesn't already exist
os.makedirs('data/', exist_ok=True)

# Load past chats (if available)
try:
    past_chats: dict = joblib.load('data/past_chats_list')
except FileNotFoundError:
    past_chats = {}

# Initialize session state variables
if 'chat_id' not in st.session_state:
    st.session_state.chat_id = None
if 'chat_title' not in st.session_state:
    st.session_state.chat_title = None

# Sidebar for past chats and new chat option
with st.sidebar:
    st.write('# Past Chats')
    if st.button('New Chat'):
        st.session_state.chat_id = str(time.time())
        st.session_state.chat_title = 'New Chat'
        st.session_state.messages = []
        st.session_state.gemini_history = []

    for chat_id, chat_title in past_chats.items():
        if st.button(chat_title):
            st.session_state.chat_id = chat_id
            st.session_state.chat_title = chat_title
            try:
                st.session_state.messages = joblib.load(f'data/{chat_id}-st_messages')
                st.session_state.gemini_history = joblib.load(f'data/{chat_id}-gemini_messages')
            except FileNotFoundError:
                st.session_state.messages = []
                st.session_state.gemini_history = []

# If no chat is selected, start a new chat
if st.session_state.chat_id is None:
    st.session_state.chat_id = str(time.time())
    st.session_state.chat_title = 'New Chat'
    st.session_state.messages = []
    st.session_state.gemini_history = []

st.write(f'# Chat with Gemini: {st.session_state.chat_title}')

# Initialize the generative model and chat
st.session_state.model = genai.GenerativeModel('gemini-pro')
st.session_state.chat = st.session_state.model.start_chat(history=st.session_state.gemini_history)

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(name=message['role'], avatar=message.get('avatar')):
        st.markdown(message['content'])

# React to user input
if prompt := st.chat_input('Your message here...'):
    # Save this as a new chat if it's the first message
    if st.session_state.chat_id not in past_chats:
        st.session_state.chat_title = ' '.join(prompt.split(' ')[:5])  # Use the first few words of the first question as the title
        past_chats[st.session_state.chat_id] = st.session_state.chat_title
        joblib.dump(past_chats, 'data/past_chats_list')
    
    # Display user message in chat message container
    with st.chat_message('user'):
        st.markdown(prompt)
    
    # Add user message to chat history
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    
    # Send message to AI
    response = st.session_state.chat.send_message(prompt, stream=True)
    
    # Display assistant response in chat message container
    with st.chat_message(name=MODEL_ROLE, avatar=AI_AVATAR_ICON):
        message_placeholder = st.empty()
        full_response = ''
        
        # Streams in a chunk at a time
        for chunk in response:
            for ch in chunk.text.split(' '):
                full_response += ch + ' '
                time.sleep(0.05)
                message_placeholder.write(full_response + '▌')
        message_placeholder.write(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({
        'role': MODEL_ROLE,
        'content': full_response,
        'avatar': AI_AVATAR_ICON,
    })
    
    st.session_state.gemini_history = st.session_state.chat.history
    
    # Save chat history to file
    joblib.dump(st.session_state.messages, f'data/{st.session_state.chat_id}-st_messages')
    joblib.dump(st.session_state.gemini_history, f'data/{st.session_state.chat_id}-gemini_messages')
