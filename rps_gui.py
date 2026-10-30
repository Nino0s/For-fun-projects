import random
import tkinter as tk
import winsound
from PIL import Image, ImageTk  # Requires: pip install Pillow

class RockPaperScissorsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rock-Paper-Scissors Arcade")
        self.root.geometry("500x550")
        self.root.resizable(False, False)

        self.player_score = 0
        self.computer_score = 0
        self.winning_rules = {
            "rock": "scissors",
            "paper": "rock",
            "scissors": "paper"
        }
        self.emojis = {
            "rock": "🪨 Rock",
            "paper": "📄 Paper",
            "scissors": "✂️ Scissors"
        }

        # --- Canvas for Graphics & Text ---
        self.canvas = tk.Canvas(root, width=500, height=550, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # --- Load Background Image ---
        try:
            self.bg_image = Image.open("images (1).jpg")
            self.bg_image = self.bg_image.resize((500, 550), Image.Resampling.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(self.bg_image)
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)
        except Exception as e:
            print(f"Could not load background image: {e}")
            self.canvas.config(bg="#1e1e2f")

        # --- Canvas Text Elements (Optimized Colors & Positions) ---
        
        # Title (Bright Cyan)
        self.canvas.create_text(250, 30, text="ROCK • PAPER • SCISSORS", font=("Helvetica", 16, "bold"), fill="#00ffcc")

        # Scoreboard (Bright White)
        self.score_text_id = self.canvas.create_text(250, 65, text="Score — You: 0 | Computer: 0", font=("Helvetica", 11, "bold"), fill="#ffffff")

        # Choice Display Texts (Placed cleanly inside the white box area)
        self.player_text_id = self.canvas.create_text(130, 130, text="Your Choice: —", font=("Helvetica", 11, "bold"), fill="#002b36", anchor="w")
        self.computer_text_id = self.canvas.create_text(130, 170, text="Computer Choice: —", font=("Helvetica", 11, "bold"), fill="#002b36", anchor="w")

        # Status / Feedback Text (Moved below choices so no overlapping)
        self.status_text_id = self.canvas.create_text(250, 225, text="Make your move!", font=("Helvetica", 13, "bold"), fill="#b58900")

        # --- Action Buttons ---
        self.btn_frame = tk.Frame(root, bg="#113333")
        
        btn_rock = tk.Button(self.btn_frame, text="🪨 Rock", font=("Helvetica", 10, "bold"), bg="#3b3b58", fg="white", activebackground="#4f4f78", activeforeground="white", relief="flat", width=10, height=2, command=lambda: self.play("rock"))
        btn_rock.grid(row=0, column=0, padx=5)

        btn_paper = tk.Button(self.btn_frame, text="📄 Paper", font=("Helvetica", 10, "bold"), bg="#3b3b58", fg="white", activebackground="#4f4f78", activeforeground="white", relief="flat", width=10, height=2, command=lambda: self.play("paper"))
        btn_paper.grid(row=0, column=1, padx=5)

        btn_scissors = tk.Button(self.btn_frame, text="✂️ Scissors", font=("Helvetica", 10, "bold"), bg="#3b3b58", fg="white", activebackground="#4f4f78", activeforeground="white", relief="flat", width=10, height=2, command=lambda: self.play("scissors"))
        btn_scissors.grid(row=0, column=2, padx=5)

        self.canvas.create_window(250, 310, window=self.btn_frame)

        # Reset Button (Placed down in the spell card description box text area)
        self.reset_btn = tk.Button(root, text="Reset Scores", font=("Helvetica", 9), bg="#2a2a40", fg="#aaaaaa", activebackground="#3a3a5a", activeforeground="white", relief="flat", width=15, command=self.reset_game)
        self.canvas.create_window(250, 395, window=self.reset_btn)

    def play(self, player_choice):
        try:
            winsound.Beep(800, 60)
        except RuntimeError:
            pass

        choices = ["rock", "paper", "scissors"]
        computer_choice = random.choice(choices)

        self.canvas.itemconfig(self.player_text_id, text=f"Your Choice: {self.emojis[player_choice]}")
        self.canvas.itemconfig(self.computer_text_id, text=f"Computer Choice: {self.emojis[computer_choice]}")

        if player_choice == computer_choice:
            self.canvas.itemconfig(self.status_text_id, text="It's a tie this round!", fill="#586e75")
            try:
                winsound.Beep(450, 120)
            except RuntimeError:
                pass
        elif self.winning_rules[player_choice] == computer_choice:
            self.canvas.itemconfig(self.status_text_id, text="You win this round! 🎉", fill="#2aa198")
            self.player_score += 1
            try:
                winsound.Beep(900, 90)
                winsound.Beep(1200, 140)
            except RuntimeError:
                pass
        else:
            self.canvas.itemconfig(self.status_text_id, text="Computer wins this round! 🤖", fill="#dc322f")
            self.computer_score += 1
            try:
                winsound.Beep(300, 200)
            except RuntimeError:
                pass

        self.canvas.itemconfig(self.score_text_id, text=f"Score — You: {self.player_score} | Computer: {self.computer_score}")

    def reset_game(self):
        try:
            winsound.Beep(600, 80)
        except RuntimeError:
            pass
        self.player_score = 0
        self.computer_score = 0
        self.canvas.itemconfig(self.score_text_id, text="Score — You: 0 | Computer: 0")
        self.canvas.itemconfig(self.player_text_id, text="Your Choice: —")
        self.canvas.itemconfig(self.computer_text_id, text="Computer Choice: —")
        self.canvas.itemconfig(self.status_text_id, text="Make your move!", fill="#b58900")

if __name__ == "__main__":
    root = tk.Tk()
    app = RockPaperScissorsApp(root)
import random
import tkinter as tk

class RockPaperScissorsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rock-Paper-Scissors")
        self.root.geometry("400x450")
        self.root.config(bg="#f0f0f0")

        # Scores and rules
        self.player_score = 0
        self.computer_score = 0
        self.winning_rules = {
            "rock": "scissors",
            "paper": "rock",
            "scissors": "paper"
        }
        self.emojis = {
            "rock": "🪨 Rock",
            "paper": "📄 Paper",
            "scissors": "✂️ Scissors"
        }

        # --- UI Components ---
        
        # Title Label
        self.title_label = tk.Label(root, text="Rock • Paper • Scissors", font=("Helvetica", 16, "bold"), bg="#f0f0f0")
        self.title_label.pack(pady=15)

        # Scoreboard Label
        self.score_label = tk.Label(root, text="Score — You: 0 | Computer: 0", font=("Helvetica", 12), bg="#f0f0f0", fg="#333333")
        self.score_label.pack(pady=5)

        # Choice Display Frame
        self.result_frame = tk.Frame(root, bg="#ffffff", bd=2, relief="groove")
        self.result_frame.pack(pady=15, padx=20, fill="x")

        self.player_choice_label = tk.Label(self.result_frame, text="Your Choice: —", font=("Helvetica", 11), bg="#ffffff")
        self.player_choice_label.pack(anchor="w", padx=15, pady=5)

        self.computer_choice_label = tk.Label(self.result_frame, text="Computer Choice: —", font=("Helvetica", 11), bg="#ffffff")
        self.computer_choice_label.pack(anchor="w", padx=15, pady=5)

        # Status / Outcome Label
        self.status_label = tk.Label(root, text="Make your move below!", font=("Helvetica", 12, "bold"), bg="#f0f0f0", fg="#0056b3")
        self.status_label.pack(pady=15)

        # Buttons Frame
        self.btn_frame = tk.Frame(root, bg="#f0f0f0")
        self.btn_frame.pack(pady=10)

        # Action Buttons
        btn_rock = tk.Button(self.btn_frame, text="🪨 Rock", font=("Helvetica", 11), width=10, command=lambda: self.play("rock"))
        btn_rock.grid(row=0, column=0, padx=5)

        btn_paper = tk.Button(self.btn_frame, text="📄 Paper", font=("Helvetica", 11), width=10, command=lambda: self.play("paper"))
        btn_paper.grid(row=0, column=1, padx=5)

        btn_scissors = tk.Button(self.btn_frame, text="✂️ Scissors", font=("Helvetica", 11), width=10, command=lambda: self.play("scissors"))
        btn_scissors.grid(row=0, column=2, padx=5)

        # Reset Match Button
        self.reset_btn = tk.Button(root, text="Reset Scores", font=("Helvetica", 10), bg="#e0e0e0", command=self.reset_game)
        self.reset_btn.pack(pady=20)

    def play(self, player_choice):
        choices = ["rock", "paper", "scissors"]
        computer_choice = random.choice(choices)

        # Update display labels
        self.player_choice_label.config(text=f"Your Choice: {self.emojis[player_choice]}")
        self.computer_choice_label.config(text=f"Computer Choice: {self.emojis[computer_choice]}")

        # Determine winner
        if player_choice == computer_choice:
            self.status_label.config(text="It's a tie this round!", fg="#555555")
        elif self.winning_rules[player_choice] == computer_choice:
            self.status_label.config(text="You win this round! 🎉", fg="#28a745")
            self.player_score += 1
        else:
            self.status_label.config(text="Computer wins this round! 🤖", fg="#dc3545")
            self.computer_score += 1

        # Update score tracker
        self.score_label.config(text=f"Score — You: {self.player_score} | Computer: {self.computer_score}")

    def reset_game(self):
        self.player_score = 0
        self.computer_score = 0
        self.score_label.config(text="Score — You: 0 | Computer: 0")
        self.player_choice_label.config(text="Your Choice: —")
        self.computer_choice_label.config(text="Computer Choice: —")
        self.status_label.config(text="Make your move below!", fg="#0056b3")

if __name__ == "__main__":
    root = tk.Tk()
    app = RockPaperScissorsApp(root)
