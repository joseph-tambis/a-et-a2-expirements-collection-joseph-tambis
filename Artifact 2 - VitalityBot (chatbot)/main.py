import gradio as gr               # Web framework for creating the interactive UI
import random                     # Handles randomization for the motivational quotes
import re                         # Regular expressions for parsing numbers from text
from word2number import w2n       # Converts written words (e.g., "one") to integers
from datetime import datetime     # Manages system time for the dashboard date display

# ]onfiguration & State Initialization]
# DEFAULT_DATA stores the initial tracking metrics, targets, and a 'waiting_for' flag
# to handle follow-up questions from the bot.
DEFAULT_DATA = {
    "stats": {"water": 0, "exercise": 0, "calories": 0},
    "goals": {"water": 8, "exercise": 60, "calories": 2000},
    "waiting_for": None 
}

# Static list of motivational strings for the random quote feature
QUOTES = [
    "The only bad workout is the one that didn't happen.",
    "Hydration is the key to energy!",
    "Success is the sum of small efforts.",
    "Health is wealth.",
    "Your body hears everything your mind says. Keep it positive!"
]

def get_current_date():
    """Returns the current system date in a readable long-form format."""
    return datetime.now().strftime("%A, %B %d, %Y")

def extract_value(msg):
    """
    Attempts to pull a number from the user's message.
    It first tries Regex for digits, then tries word-to-number conversion (e.g., 'five').
    """
    digits = re.findall(r'\d+', msg)
    if digits:
        return int(digits[0])
    try:
        return w2n.word_to_num(msg)
    except ValueError:
        return None

def habit_bot_logic(message, current_data):
    """
    The central brain of the bot. Processes text, updates metrics, 
    and determines the assistant's response.
    """
    msg = message.lower()
    stats = current_data["stats"]
    goals = current_data["goals"]
    val = extract_value(msg)

    # CONTEXT CHECK (State Machine)
    # This section checks if the bot asked a follow-up question in the previous turn.
    if current_data["waiting_for"] == "water_amount":
        if val is not None:
            stats["water"] += val
            current_data["waiting_for"] = None
            response = f"✅ Got it! Added {val} glass(es). Total: {stats['water']}/{goals['water']}."
        else: return "I didn't catch a number. How many glasses was it?", current_data
    elif current_data["waiting_for"] == "exercise_mins":
        if val is not None:
            stats["exercise"] += val
            current_data["waiting_for"] = None
            response = f"✅ Added {val} minutes. Total: {stats['exercise']}/{goals['exercise']} mins."
        else: return "How many minutes was that workout?", current_data
    elif current_data["waiting_for"] == "calories_amount":
        if val is not None:
            stats["calories"] += val
            current_data["waiting_for"] = None
            response = f"🍽️ Logged {val} calories. Total: {stats['calories']}/{goals['calories']} kcal."
        else: return "How many calories were in that?", current_data

    # INTENT CLASSIFICATION
    # Goal Setting Logic
    elif "goal" in msg:
        if "water" in msg and val:
            goals["water"] = val
            response = f"🎯 Water goal set to **{val}**."
        elif "exercise" in msg and val:
            goals["exercise"] = val
            response = f"🎯 Exercise goal set to **{val}**."
        elif "calorie" in msg and val:
            goals["calories"] = val
            response = f"🎯 Calorie limit set to **{val}**."
        else: response = "Try: 'Set water goal to twelve'."
    
    # Water Logging
    elif "water" in msg or "drank" in msg:
        if val:
            stats["water"] += val
            response = f"🥤 Logged {val} glass(es). Total: {stats['water']}/{goals['water']}."
        else:
            current_data["waiting_for"] = "water_amount"
            response = "Stay hydrated! **How many glasses** did you drink?"
    
    # Exercise Logging
    elif any(word in msg for word in ["exercise", "workout"]):
        if val:
            stats["exercise"] += val
            response = f"💪 Logged {val} minutes. Total: {stats['exercise']}/{goals['exercise']} mins."
        else:
            current_data["waiting_for"] = "exercise_mins"
            response = "Nice! **How many minutes** was that?"
    
    # Calorie Logging
    elif any(word in msg for word in ["eat", "ate", "food", "calorie"]):
        if val:
            stats["calories"] += val
            response = f"🍽️ Added {val} calories. Total: {stats['calories']}/{goals['calories']} kcal."
        else:
            current_data["waiting_for"] = "calories_amount"
            response = "Tasty! **How many calories** were in that?"
    
    # Motivation Engine
    elif any(word in msg for word in ["quote", "motivation", "inspire"]):
        response = f"✨ *\"{random.choice(QUOTES)}\"*"
    
    # Reset Logic
    elif "reset" in msg:
        stats.update({"water": 0, "exercise": 0, "calories": 0})
        response = "🔄 All stats reset!"
    
    # Fallback response for unrecognized input
    else:
        response = "Try: 'I drank five glasses' or 'Give me some motivation'."

    # SCORE CALCULATION
    # Calculates a weighted health score out of 100% based on goal completion.
    w_p = (min(stats["water"], goals["water"]) / goals["water"]) * 33.33
    e_p = (min(stats["exercise"], goals["exercise"]) / goals["exercise"]) * 33.33
    c_p = (min(stats["calories"], goals["calories"]) / goals["calories"]) * 33.33
    score = f"{round(w_p + e_p + c_p)}%"
    
    # Return everything needed to update the Gradio UI components
    return response, current_data, stats["water"], stats["exercise"], stats["calories"], goals["water"], goals["exercise"], goals["calories"], score

# UI LAYOUT (Gradio Blocks)
with gr.Blocks(title="VitalityBot") as demo:
    # gr.State persists data for the specific user session
    session_data = gr.State(dict(DEFAULT_DATA))
    gr.HTML("<h1 style='text-align: center; font-family: sans-serif;'>🌱 VitalityBot: Your Personal Health Dashboard</h1>")
    
    with gr.Row():
        # Sidebar: Displays Date and Visual Tracking Bars
        with gr.Column(scale=1, variant="panel"):
            gr.Markdown(f"### 📅 {get_current_date()}")
            gr.Markdown("---")
            gr.Markdown("### 📊 Live Progress")
            water_bar = gr.Slider(0, 8, label="Water (Glasses)", interactive=False)
            exercise_bar = gr.Slider(0, 60, label="Exercise (Mins)", interactive=False)
            calorie_bar = gr.Slider(0, 2000, label="Calories (kcal)", interactive=False)
            health_score = gr.Label(value="0%", label="Health Score")

        # Main Column: Chat Interface and Quick-Action Buttons
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Chat History")
            user_input = gr.Textbox(placeholder="Talk to me! Try 'I drank three glasses'...", label="Input")
            with gr.Row():
                btn_water = gr.Button("🥤 Water", size="sm")
                btn_exercise = gr.Button("💪 Exercise", size="sm")
                btn_food = gr.Button("🍽️ Food", size="sm")
                btn_quote = gr.Button("✨ Motivation", size="sm") 
            clear_btn = gr.Button("Reset Everything", variant="stop")

    def engine(msg, history, data):
        """
        Wrapper function that links the UI to the habit_bot_logic.
        Updates the chat history and resets the input box.
        """
        res, upd_data, w_v, e_v, c_v, w_g, e_g, c_g, score = habit_bot_logic(msg, data)
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": res})
        # gr.update is used to dynamically change the maximum value of sliders if goals change
        return "", history, upd_data, gr.update(value=w_v, maximum=w_g), gr.update(value=e_v, maximum=e_g), gr.update(value=c_v, maximum=c_g), score

    # Map the UI components to the data processing function
    outputs = [user_input, chatbot, session_data, water_bar, exercise_bar, calorie_bar, health_score]
    user_input.submit(engine, [user_input, chatbot, session_data], outputs)
    
    # Preset Button Events: Clicking a button triggers the engine as if the user typed text
    btn_water.click(engine, [gr.State("I drank water"), chatbot, session_data], outputs)
    btn_exercise.click(engine, [gr.State("I exercised"), chatbot, session_data], outputs)
    btn_food.click(engine, [gr.State("I ate food"), chatbot, session_data], outputs)
    btn_quote.click(engine, [gr.State("Give me some motivation"), chatbot, session_data], outputs)
    
    # Global Reset: Returns UI and state variables to their starting points
    clear_btn.click(lambda: ("", [], dict(DEFAULT_DATA), gr.update(value=0, maximum=8), gr.update(value=0, maximum=60), gr.update(value=0, maximum=2000), "0%"), 
                    None, outputs)

if __name__ == "__main__":
    demo.launch()
