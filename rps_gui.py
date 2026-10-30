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
    root.mainloop()