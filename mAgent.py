import streamlit as st
import openai
import base64
import os
from io import BytesIO
from dotenv import load_dotenv
import hashlib
load_dotenv() 

try:
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        st.error("OpenAI API key not found. Please set the 'OPENAI_API_KEY' environment variable or use Streamlit secrets.")
        st.stop()
    client = openai.OpenAI(api_key=openai_api_key)
except Exception as e:
    st.error(f"Error initializing OpenAI client: {e}")
    st.stop()

GPT_MODEL = "gpt-4o-mini"

st.set_page_config(
    page_title="AI Math Tutor Agent",
    page_icon="📐",
    layout="centered"
)

st.title("📐 AI Math Tutor Agent")
st.markdown(":red[**Hello! I'm your AI Math Tutor**]. *I can help you solve complex math problems. You can type your problem or upload a screenshot.*")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_processed_image_hash" not in st.session_state:
    st.session_state.last_processed_image_hash = None

def encode_image_to_base64(image_file):

    if image_file is not None:
       
        bytes_data = image_file.getvalue()
        base64_encoded_data = base64.b64encode(bytes_data).decode("utf-8")
        image_hash = hashlib.md5(bytes_data).hexdigest()
        return base64_encoded_data, image_hash
    return None, None

def get_openai_response(messages_payload):

    try:
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages_payload,
                max_tokens=1000, # Adjust as needed for complex solutions
            )
            return response.choices[0].message.content
    except openai.OpenAIError as e:
        st.error(f"OpenAI API error: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None
def build_openai_messages_payload(current_messages):
   
    openai_messages = []
    openai_messages.append({
        "role": "system",
        "content": "You are a helpful AI Math Tutor. Provide a complete, step-by-step solution to the given math problems, including all intermediate calculations and the final answer. Format the steps using simple numbered lists (e.g., 1., 2., 3.). Use simple, plain text mathematical notation for expressions (e.g., '1/2' for fractions, 'x^2' for exponents, 'sqrt(x)' for square roots). Avoid using LaTeX commands like \\frac, \\boxed, or other complex formatting."
    })
    for msg in current_messages:
        content_for_openai = []
        if msg["role"] == "user":
            if any(item["type"] == "text" for item in msg["content"]):
                # If there's text, add the instruction as part of the text content
                original_text = next(item["text"] for item in msg["content"] if item["type"] == "text")
                content_for_openai.append({"type": "text", "text": f"Please provide a complete, step-by-step solution to the following math problem: {original_text}"})
            elif any(item["type"] == "image_url" for item in msg["content"]):
                # If it's an image, add an initial text instruction for the image
                content_for_openai.append({"type": "text", "text": "Please provide a complete, step-by-step solution to the math problem shown in this image:"})

            for item in msg["content"]:
                if item["type"] == "image_url": # Add image content
                    content_for_openai.append({"type": "image_url", "image_url": item["image_url"]})
        else: # For assistant messages, just add their content as is
            content_for_openai = msg["content"]

        openai_messages.append({"role": msg["role"], "content": content_for_openai})
    return openai_messages
    return openai_messages

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        for content_item in message["content"]:
            if content_item["type"] == "text":
                st.markdown(content_item["text"])
            elif content_item["type"] == "image_url":
                st.image(content_item["image_url"]["url"])



prompt = st.chat_input("Type your math problem here...")

uploaded_file = st.file_uploader("Or upload a screenshot of your problem", type=["png", "jpg", "jpeg"])

if prompt:
   
    st.session_state.messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    messages_payload_for_openai = [
        {"role": "user", "content": prompt} 
    ]

    for msg in st.session_state.messages:
        if msg["role"] == "user" and msg["content"][0]["type"] == "text":
            messages_payload_for_openai.append({"role": "user", "content": msg["content"][0]["text"]})
        elif msg["role"] == "assistant":
            messages_payload_for_openai.append({"role": "assistant", "content": msg["content"][0]["text"]})
        elif msg["role"] == "user" and msg["content"][0]["type"] == "image_url":
            messages_payload_for_openai.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Here is an image of a math problem:"},
                    {"type": "image_url", "image_url": msg["content"][0]["image_url"]}
                ]
            })
        ai_response = get_openai_response(messages_payload_for_openai)

        if ai_response:
            # Add AI response to session state
            st.session_state.messages.append({"role": "assistant", "content": [{"type": "text", "text": ai_response}]})
            st.rerun() # Rerun to update the chat display

if uploaded_file is not None:
    base64_image, current_image_hash = encode_image_to_base64(uploaded_file)

    if base64_image and current_image_hash != st.session_state.last_processed_image_hash:
       
        st.session_state.last_processed_image_hash = current_image_hash

        image_data_url = f"data:{uploaded_file.type};base64,{base64_image}"
        st.session_state.messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Here is an image of a math problem:"}, # Optional text to accompany image
                {"type": "image_url", "image_url": {"url": image_data_url}}
            ]
        })

        messages_payload_for_openai = build_openai_messages_payload(st.session_state.messages)
        ai_response = get_openai_response(messages_payload_for_openai)

        if ai_response:
           
            st.session_state.messages.append({"role": "assistant", "content": [{"type": "text", "text": ai_response}]})
            st.rerun() 
    elif uploaded_file is not None and current_image_hash == st.session_state.last_processed_image_hash:
        pass
        
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.last_processed_image_hash = None # Also clear the image hash
    st.rerun()

