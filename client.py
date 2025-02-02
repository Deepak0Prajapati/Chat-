import sys
import threading
import socket
import os
import argparse
import tkinter as tk
from tkinter import ttk
from translate import Translator  # Using the translate library

class Send(threading.Thread):
    def __init__(self, sock, name):
        super().__init__()
        self.sock = sock
        self.name = name

    def run(self):
        while True:
            print('{}: '.format(self.name), end='')
            sys.stdout.flush()
            message = sys.stdin.readline()[:-1]

            if message == "QUIT":
                self.sock.sendall('Server: {} has left the Chat.'.format(self.name).encode('ascii'))
                break
            else:
                self.sock.sendall('{}: {}'.format(self.name, message).encode('ascii'))

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
        self.translator = Translator(to_lang=preferred_language)  # Initialize translator

    def run(self):
        while True:
            message = self.sock.recv(1024).decode('ascii')
            if message:
                # Translate the message to the preferred language
                if self.preferred_language != 'en':  # Skip translation if English
                    try:
                        translated_message = self.translator.translate(message)
                    except Exception as e:
                        print(f"Translation error: {e}")
                        translated_message = message  # Fallback to original message
                else:
                    translated_message = message

                # Display the translated message
                if self.messages:
                    self.messages.insert(tk.END, translated_message)
                    print("hi")
                    print('\r{}\n{}: '.format(translated_message, self.name), end='')
                else:
                    print('\r{}\n{}: '.format(translated_message, self.name), end='')
            else:
                print('\n No. We have lost connection to the server!')
                print('\n Quitting...')
                self.sock.close()
                os._exit(0)


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = None
        self.messages = None
        self.preferred_language = 'en'  # Default language is English

    def start(self):
        print('trying to connect to {}:{}...'.format(self.host, self.port))

        self.sock.connect((self.host, self.port))

        print('succesffully connected to {}:{}'.format(self.host, self.port))

        print()

        self.name = input('your Name: ')

        print()

        print('Welcome, {}! Getting ready to send and receive messages... '.format(self.name))

        # Create send and receive threads
        send = Send(self.sock, self.name)
        receive = Receive(self.sock, self.name, self.messages, self.preferred_language)

        # Start send and receive thread
        send.start()
        receive.start()

        self.sock.sendall('Server: {} has joined the chat. Say whatsup!'.format(self.name).encode('ascii'))

        print("\rReady! Leave the chat room anytime by typing 'QUIT'\n")
        print('{}: '.format(self.name), end='')
        return receive

    def send(self, textInput):
        # Send textInput data from GUI
        message = textInput.get()
        textInput.delete(0, tk.END)
        self.messages.insert(tk.END, '{}: {}'.format(self.name, message))

        # Type 'QUIT' to leave chatroom
        if message == "QUIT":
            self.sock.sendall('Server: {} has left the chat.'.format(self.name).encode('ascii'))
            print('\n Quitting...')
            self.sock.close()
            os._exit(0)

        # Send message to the server for broadcasting
        else:
            self.sock.sendall('{}: {}'.format(self.name, message).encode('ascii'))


def main(host, port):
    # Initialize and run GUI application
    client = Client(host, port)
    receive = client.start()

    window = tk.Tk()
    window.title("Chat+")

    # Language selection dropdown
    languages = {
        'English': 'en',
        'Spanish': 'es',
        'French': 'fr',
        'German': 'de',
        'Chinese (Simplified)': 'zh',
        'Hindi': 'hi',
        'Japanese': 'ja',
    }

    selected_language = tk.StringVar(value='English')  # Default language

    def set_language(*args):
        client.preferred_language = languages[selected_language.get()]
        receive.preferred_language = client.preferred_language
        receive.translator = Translator(to_lang=client.preferred_language)  # Update translator
        print(f"Preferred language set to: {selected_language.get()}")

    language_menu = ttk.Combobox(window, textvariable=selected_language, values=list(languages.keys()))
    language_menu.bind("<<ComboboxSelected>>", set_language)
    language_menu.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

    fromMessage = tk.Frame(master=window)
    scrollBar = tk.Scrollbar(master=fromMessage)
    messages = tk.Listbox(master=fromMessage, yscrollcommand=scrollBar.set)
    scrollBar.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
    messages.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    client.messages = messages
    receive.messages = messages

    fromMessage.grid(row=1, column=0, columnspan=3, sticky="nsew")
    fromEntry = tk.Frame(master=window)
    textInput = tk.Entry(master=fromEntry)
    textInput.pack(fill=tk.BOTH, expand=True)
    textInput.bind("<Return>", lambda x: client.send(textInput))
    textInput.insert(0, "Write your message here.")

    btnSend = tk.Button(
        master=window,
        text='send',
        command=lambda: client.send(textInput)
    )

    fromEntry.grid(row=2, column=0, padx=10, sticky="ew")
    btnSend.grid(row=2, column=1, padx=10, sticky="ew")

    window.rowconfigure(1, minsize=500, weight=1)
    window.rowconfigure(2, minsize=50, weight=0)
    window.columnconfigure(0, minsize=500, weight=1)
    window.columnconfigure(1, minsize=200, weight=0)

    window.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="chatroom server")
    parser.add_argument('host', help='Interface the server listens at')
    parser.add_argument('-p', metavar='PORT', type=int, default=1060, help='TCP port (default 1060)')

    args = parser.parse_args()
    main(args.host, args.p)