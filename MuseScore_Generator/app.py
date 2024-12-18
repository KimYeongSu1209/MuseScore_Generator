import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from music21 import stream, note, metadata
from PIL import Image, ImageTk
import subprocess
import os

class MusicXMLExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("메인 화면")

        # --- 메인 화면 버튼 구성 ---
        tk.Label(root, text="악보 편집 프로그램", font=("Arial", 16)).pack(pady=10)
        tk.Button(root, text="악보 생성", command=self.prompt_score_title).pack(pady=10)
        tk.Button(root, text="종료", command=self.exit_program).pack(pady=10)

    def exit_program(self):
        """프로그램 종료"""
        self.root.destroy()

    def prompt_score_title(self):
        title = simpledialog.askstring("악보 제목 입력", "악보의 제목을 입력하세요:")
        if title:
            self.open_music_editor(title)
        else:
            messagebox.showwarning("입력 오류", "제목을 입력해주세요.")

    def open_music_editor(self, score_title):
        editor_window = tk.Toplevel(self.root)
        MusicEditor(editor_window, score_title)


class MusicEditor:
    def __init__(self, root, score_title):
        self.root = root
        self.root.title(f"악보 생성기 - {score_title}")

        self.score_title = score_title
        self.note_length = 1.0  # 기본 음표 길이
        self.score = stream.Score()
        self.part = stream.Part()
        self.score.metadata = metadata.Metadata()
        self.score.metadata.title = score_title
        self.note_images = {}
        self.current_note_index = None  # 선택된 음표의 인덱스
        self.canvas_notes = []  # Canvas에 그린 음표
        self.selected_note_button = None  # 선택된 음표 버튼

        self.load_images()

        # --- GUI 구성 ---
        tk.Label(root, text=f"악보 제목: {score_title}", font=("Arial", 14)).pack(pady=10)

        # 입력 필드
        tk.Label(root, text="음표 입력 (예: C4, D4, E4):").pack()
        self.note_input = tk.Entry(root, width=50)
        self.note_input.pack(pady=5)

        # 음표 길이 버튼 (이미지)
        self.length_frame = tk.Frame(root)
        self.length_frame.pack(pady=5)
        tk.Label(self.length_frame, text="음표 길이 선택:").pack(side="left")

        self.note_length_buttons = []
        for length, img in [
            ("whole", 4.0),
            ("dotted_half", 3.0),
            ("half", 2.0),
            ("dotted_quarter", 1.5),
            ("quarter", 1.0),
            ("eighth", 0.5)
        ]:
            btn = tk.Button(self.length_frame, image=self.note_images[length],
                            command=lambda l=img, b=len(self.note_length_buttons): self.set_note_length(l, b))
            btn.pack(side="left", padx=5)
            self.note_length_buttons.append(btn)

        # 버튼
        tk.Button(root, text="음표 추가", command=self.add_note).pack(pady=5)
        tk.Button(root, text="음표 수정", command=self.edit_note).pack(pady=5)
        tk.Button(root, text="악보 저장 및 열기", command=self.save_and_open_musescore).pack(pady=5)
        tk.Button(root, text="닫기", command=root.destroy).pack(pady=5)

        # Canvas
        self.canvas = tk.Canvas(root, width=800, height=200, bg="white")
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", self.select_note)

        # 상태 표시
        self.status_label = tk.Label(root, text="", fg="blue")
        self.status_label.pack(pady=5)

    def load_images(self):
        """이미지 로드"""
        try:
            self.note_images = {
                "whole": ImageTk.PhotoImage(Image.open("whole_note.png").resize((50, 50))),
                "dotted_half": ImageTk.PhotoImage(Image.open("dotted_half_note.png").resize((50, 50))),
                "half": ImageTk.PhotoImage(Image.open("half_note.png").resize((50, 50))),
                "dotted_quarter": ImageTk.PhotoImage(Image.open("dotted_quarter_note.png").resize((50, 50))),
                "quarter": ImageTk.PhotoImage(Image.open("quarter_note.png").resize((50, 50))),
                "eighth": ImageTk.PhotoImage(Image.open("eighth_note.png").resize((50, 50)))
            }
        except Exception as e:
            messagebox.showerror("이미지 오류", f"이미지 파일을 불러오지 못했습니다: {e}")
            self.root.destroy()

    def set_note_length(self, length, button_index):
        """음표 길이 설정 및 버튼 테두리 강조"""
        self.note_length = length
        length_name = {4.0: "온음표", 3.0: "점 2분음표", 2.0: "2분음표", 
                       1.5: "점 4분음표", 1.0: "4분음표", 0.5: "8분음표"}[length]
        self.status_label.config(text=f"선택된 음표 길이: {length_name}")

        # 기존 버튼 테두리 초기화
        if self.selected_note_button is not None:
            self.note_length_buttons[self.selected_note_button].config(relief="raised", highlightbackground="black")
        # 선택된 버튼 테두리 빨간색 강조
        self.note_length_buttons[button_index].config(relief="solid", highlightbackground="red", highlightthickness=2)
        self.selected_note_button = button_index

    def add_note(self):
        """새로운 음표 추가 (텍스트 유지)"""
        note_data = self.note_input.get().strip()
        if not note_data:
            messagebox.showwarning("입력 오류", "음표 데이터를 입력해주세요.")
            return

        try:
            n = note.Note(note_data, quarterLength=self.note_length)
            self.part.append(n)
            self.draw_note_on_canvas(note_data)
            self.status_label.config(text=f"음표 추가됨: {note_data} (길이: {self.note_length})")
        except Exception as e:
            messagebox.showerror("오류", f"유효하지 않은 음표입니다: {e}")

    def draw_note_on_canvas(self, note_data):
        """Canvas에 음표 추가"""
        x = len(self.canvas_notes) * 60 + 10
        y = 80
        note_id = self.canvas.create_text(x, y, text=note_data, font=("Arial", 14), fill="black")
        self.canvas_notes.append((note_id, note_data))

    def select_note(self, event):
        """Canvas에서 음표 선택"""
        for i, (note_id, note_data) in enumerate(self.canvas_notes):
            if self.canvas.bbox(note_id)[0] <= event.x <= self.canvas.bbox(note_id)[2]:
                self.current_note_index = i
                self.status_label.config(text=f"선택된 음표: {note_data}")
                self.canvas.itemconfig(note_id, fill="red")  # 선택된 음표 강조
            else:
                self.canvas.itemconfig(note_id, fill="black")

    def edit_note(self):
        """선택된 음표 수정"""
        if self.current_note_index is None:
            messagebox.showwarning("선택 오류", "수정할 음표를 선택해주세요.")
            return

        note_data = self.note_input.get().strip()
        if not note_data:
            messagebox.showwarning("입력 오류", "새로운 음표 데이터를 입력해주세요.")
            return

        try:
            n = note.Note(note_data, quarterLength=self.note_length)
            self.part[self.current_note_index] = n  # Music21의 Part에서 수정
            note_id, _ = self.canvas_notes[self.current_note_index]
            self.canvas.itemconfig(note_id, text=note_data)  # Canvas에서 수정
            self.status_label.config(text=f"음표 수정됨: {note_data} (길이: {self.note_length})")
        except Exception as e:
            messagebox.showerror("오류", f"음표 수정 실패: {e}")

    def save_and_open_musescore(self):
        """MusicXML 저장 및 MuseScore 열기"""
        if self.part not in self.score:
            self.score.append(self.part)

        # 저장 경로 명확하게 설정
        save_dir = r"C:\\Users\\duwls\\Sys"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        file_path = os.path.join(save_dir, f"{self.score_title}.musicxml")

        try:
            self.score.write("musicxml", file_path)
            messagebox.showinfo("저장 완료", f"악보가 저장되었습니다: {file_path}")
            
            # MuseScore 실행 경로 확인
            musescore_path = r"C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe"
            if not os.path.exists(musescore_path):
                raise FileNotFoundError(f"MuseScore 실행 파일이 없습니다: {musescore_path}")

            # MuseScore로 파일 열기
            subprocess.run([musescore_path, file_path], check=True)
        except FileNotFoundError as e:
            messagebox.showerror("오류", f"파일 또는 실행 파일 오류: {e}")
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장 또는 MuseScore 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicXMLExporterApp(root)
    root.mainloop()
