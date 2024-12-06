from flask import Flask, render_template, request, jsonify
import anthropic
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import base64
import uuid

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
        
        # Add style instruction if not normal
        if style != 'normal':
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

@app.route('/api/analyze-file', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    style = request.form.get('style', 'normal')
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        # Save the file
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        
        # Read file content
        with open(filename, 'rb') as f:
            file_content = f.read()
            
        # Convert binary content to base64 for text files
        try:
            file_content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            file_content = base64.b64encode(file_content).decode('utf-8')
        
        # Create analysis request
        analysis_prompt = f"Please analyze this file named '{file.filename}'. Here's its content:\n\n{file_content}"
        
        messages = [{"role": "user", "content": analysis_prompt}]
        
        # Add style instruction if not normal
        if style != 'normal':
            style_prompt = STYLE_PROMPTS[style]
            messages.append({"role": "user", "content": style_prompt})
        
        # Get Claude's analysis
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=messages
        )
        
        analysis = response.content[0].text
        
        return jsonify({
            "analysis": analysis,
            "filename": file.filename
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up uploaded file
        if os.path.exists(filename):
            os.remove(filename)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    chat_id = request.form.get('chat_id')
    style = request.form.get('style', 'normal')
    analysis = request.form.get('analysis')  # Pre-computed analysis
    
    if not analysis:
        return jsonify({"error": "No analysis provided"}), 400
    
    if not chat_id:
        # Generate a unique ID for the chat
        chat_id = str(uuid.uuid4())
        display_name = f"File: {file.filename[:25]}" + ('...' if len(file.filename) > 25 else '')
        CHATS[chat_id] = {
            'messages': [],
            'display_name': display_name
        }
    
    chat = CHATS[chat_id]
    
    # Add file analysis to chat history
    user_message = f"I've uploaded a file named '{file.filename}'. Please analyze it."
    chat['messages'].append({"role": "user", "content": user_message})
    chat['messages'].append({"role": "assistant", "content": analysis})
    
    return jsonify({
        "chat_id": chat_id,
        "response": analysis,
        "history": chat['messages']
    })

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
