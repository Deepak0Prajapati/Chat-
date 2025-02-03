import sys
import threading
import socket
import os
import argparse
import tkinter as tk
from tkinter import ttk
from translate import Translator
from textblob import TextBlob
from langdetect import detect

# Function to insert emojis into the message input field
def insert_emoji(textInput, emoji_char):
    textInput.insert(tk.END, emoji_char)

class Send(threading.Thread):
    def __init__(self, sock, name, preferred_language):
        super().__init__()
        self.sock = sock
        self.name = name
        self.preferred_language = preferred_language
        self.translator = Translator(from_lang=preferred_language, to_lang='en')

    def run(self):
        while True:
            print('{}: '.format(self.name), end='')
            sys.stdout.flush()
            message = sys.stdin.readline()[:-1]

            if message == "QUIT":
                self.sock.sendall('Server: {} has left the Chat.'.format(self.name).encode('utf-8'))
                break
            else:
                try:
                    translated_message = (
                        self.translator.translate(message) if self.preferred_language != 'en' else message
                    )
                    self.sock.sendall('{}: {}'.format(self.name, translated_message).encode('utf-8'))
                except Exception as e:
                    print(f"Translation error: {e}")
                    self.sock.sendall('{}: {}'.format(self.name, message).encode('utf-8'))

        print('\nQuitting...')
        self.sock.close()
        os._exit(0)

class Receive(threading.Thread):
    def __init__(self, sock, name, messages, preferred_language):
        super().__init__()
        self.sock = sock
        self.name = name
        self.messages = messages
        self.preferred_language = preferred_language
        self.translator = Translator(to_lang=preferred_language)

    def run(self):
        while True:
            message = self.sock.recv(1024).decode('utf-8')
            if message:
                try:
                    sender_name, original_message = message.split(': ', 1)
                    translated_message = (
                        self.translator.translate(original_message) if self.preferred_language != 'en' else original_message
                    )

                    sentiment = TextBlob(original_message).sentiment
                    sentiment_text = f"Sentiment: Polarity={sentiment.polarity}, Subjectivity={sentiment.subjectivity}"

                    if self.messages:
                        self.messages.insert(tk.END, f"{sender_name}: {translated_message}")
                        self.messages.insert(tk.END, sentiment_text)
                        print('\r{}\n{}: '.format(translated_message, self.name), end='')
                    else:
                        print('\r{}\n{}: '.format(translated_message, self.name), end='')

                except Exception as e:
                    print(f"Error processing message: {e}")
            else:
                print('\nConnection lost to the server! Exiting...')
                self.sock.close()
                os._exit(0)

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = None
        self.messages = None
        self.preferred_language = 'en'

    def start(self):
        print('Trying to connect to {}:{}...'.format(self.host, self.port))
        self.sock.connect((self.host, self.port))
        print('Connected to {}:{}'.format(self.host, self.port))

        self.name = input('Your Name: ')
        print('Welcome, {}! Ready to chat...'.format(self.name))

        send = Send(self.sock, self.name, self.preferred_language)
        receive = Receive(self.sock, self.name, self.messages, self.preferred_language)

        send.start()
        receive.start()

        self.sock.sendall('Server: {} has joined the chat.'.format(self.name).encode('utf-8'))
        print("\rReady! Type 'QUIT' to leave.\n")
        print('{}: '.format(self.name), end='')
        return receive

    def send(self, textInput):
        message = textInput.get()
        textInput.delete(0, tk.END)
        self.messages.insert(tk.END, '{}: {}'.format(self.name, message))

        if message == "QUIT":
            self.sock.sendall('Server: {} has left the chat.'.format(self.name).encode('utf-8'))
            print('\nQuitting...')
            self.sock.close()
            os._exit(0)

        else:
            send = Send(self.sock, self.name, self.preferred_language)
            send.translator = Translator(from_lang=self.preferred_language, to_lang='en')
            translated_message = send.translator.translate(message)
            self.sock.sendall('{}: {}'.format(self.name, translated_message).encode('utf-8'))

def main(host, port):
    client = Client(host, port)
    receive = client.start()

    # GUI Setup
    window = tk.Tk()
    window.title("Chat+")
    window.geometry("600x500")  # Restored larger window size

    languages = {'English': 'en', 'Spanish': 'es', 'French': 'fr', 'German': 'de', 'Hindi': 'hi', 'Japanese': 'ja'}
    selected_language = tk.StringVar(value='English')

    def set_language(*args):
        client.preferred_language = languages[selected_language.get()]
        receive.preferred_language = client.preferred_language
        receive.translator = Translator(to_lang=client.preferred_language)

    language_menu = ttk.Combobox(window, textvariable=selected_language, values=list(languages.keys()))
    language_menu.bind("<<ComboboxSelected>>", set_language)
    language_menu.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

    fromMessage = tk.Frame(master=window)
    scrollBar = tk.Scrollbar(master=fromMessage)
    messages = tk.Listbox(master=fromMessage, yscrollcommand=scrollBar.set, height=20, width=70)  # Enlarged message box
    scrollBar.pack(side=tk.RIGHT, fill=tk.Y)
    messages.pack(side=tk.LEFT, fill=tk.BOTH)

    client.messages = messages
    receive.messages = messages

    fromMessage.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

    fromEntry = tk.Frame(master=window)
    textInput = ttk.Entry(master=fromEntry, width=50)  # Increased text input width
    textInput.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    textInput.bind("<Return>", lambda x: client.send(textInput))
    textInput.insert(0, "Type your message...")

    btnSend = ttk.Button(master=window, text='Send', command=lambda: client.send(textInput))

    fromEntry.grid(row=2, column=0, padx=10, sticky="ew", pady=5)
    btnSend.grid(row=2, column=1, padx=10, sticky="ew", pady=5)

    emoji_frame = tk.Frame(master=window)
    emoji_frame.grid(row=2, column=2, padx=10, pady=5, sticky="ew")

    emoji_buttons = ["😀", "😍", "👍", "👋"]
    for i, emoji_char in enumerate(emoji_buttons):
        btn = tk.Button(master=emoji_frame, text=emoji_char, command=lambda e=emoji_char: insert_emoji(textInput, e))
        btn.grid(row=0, column=i, padx=2, pady=2)

    window.mainloop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Chatroom Client")
    parser.add_argument('host', help='Interface the server listens at')
    parser.add_argument('-p', metavar='PORT', type=int, default=1060, help='TCP port (default 1060)')

    args = parser.parse_args()
    main(args.host, args.p)
