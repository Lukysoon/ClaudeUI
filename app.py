from flask import Flask, render_template, request, jsonify
import anthropic
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid

load_dotenv()

app = Flask(__name__)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Store chats in memory (in production, you'd want to use a database)
CHATS = {}

# Response style prompts
STYLE_PROMPTS = {
    'concise': "Please provide a concise and direct response, focusing only on the key points.",
    'explanatory': "Please provide a detailed explanation with examples and thorough reasoning.",
    'normal': ""  # Default style, no special instructions
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    chat_id = data.get('chat_id')
    message = data.get('message')
    style = data.get('style', 'normal')
    custom_prompt = data.get('custom_prompt', '')
    
    if not chat_id:
        # Generate a unique ID for the chat
        chat_id = str(uuid.uuid4())
        CHATS[chat_id] = {
            'messages': [],
            'display_name': message[:30] + ('...' if len(message) > 30 else '')
        }
    
    if chat_id not in CHATS:
        return jsonify({"error": "Chat not found"}), 404
    
    chat = CHATS[chat_id]
    
    # Add user message to chat history
    chat['messages'].append({"role": "user", "content": message})
    
    try:
        # Create messages for Claude
        messages = [{"role": m["role"], "content": m["content"]} for m in chat['messages']]
        
        # Add style instruction if provided
        if custom_prompt:
            messages.append({"role": "user", "content": custom_prompt})
        elif style != 'normal':
            style_prompt = STYLE_PROMPTS[style]
            messages.append({"role": "user", "content": style_prompt})
        
        # Get response from Claude
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=messages
        )
        
        # Add Claude's response to chat history
        assistant_message = response.content[0].text
        chat['messages'].append({"role": "assistant", "content": assistant_message})
        
        return jsonify({
            "chat_id": chat_id,
            "response": assistant_message,
            "history": chat['messages']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chats', methods=['GET'])
def get_chats():
    # Return chat IDs along with display names
    chat_list = []
    for chat_id, chat_data in CHATS.items():
        chat_list.append({
            'id': chat_id,
            'name': chat_data['display_name']
        })
    return jsonify(chat_list)

@app.route('/api/chat/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    if chat_id not in CHATS:
        return jsonify({"error": "Chat not found"}), 404
    return jsonify(CHATS[chat_id]['messages'])

@app.route('/api/chat/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    if chat_id not in CHATS:
        return jsonify({"error": "Chat not found"}), 404
    del CHATS[chat_id]
    return jsonify({"message": "Chat deleted successfully"})

if __name__ == '__main__':
    app.run(debug=True)
