import google.generativeai as genai
import os

key = "AIzaSyAV00ID44koVDc92FuUPj1JKoJ1lT-b-Ps"
genai.configure(api_key=key)

try:
    model = genai.GenerativeModel('gemini-3.5-flash')
    response = model.generate_content("Responde 'Hola mundo'")
    print("ÉXITO:", response.text)
except Exception as e:
    print("ERROR:", str(e))
