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
    root.mainloop()