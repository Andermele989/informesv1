import google.generativeai as genai
import os

key = "AQ.Ab8RN6KyJVfe6ZLc7y_0ZWkT7YFmoUFMLmY6aZg542kyDZOUGg"
genai.configure(api_key=key)

try:
    model = genai.GenerativeModel('gemini-3.5-flash')
    response = model.generate_content("Responde 'Hola mundo'")
    print("ÉXITO:", response.text)
except Exception as e:
    print("ERROR:", str(e))
