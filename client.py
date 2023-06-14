import socket
from PIL import Image, ImageGrab, ImageTk
import pygetwindow
import os
import win32gui
import lz4.frame
from io import BytesIO
from threading import Thread
from multiprocessing import freeze_support, Process, Queue as Multiprocess_queue
from pynput.keyboard import Listener as Key_listener
from pynput.mouse import Button, Listener as Mouse_listener
import tkinter as tk
from tkinter.font import Font
from tkinter import ttk, messagebox, filedialog
import win32api
import datetime
import pygame
from tkinter import filedialog , StringVar,scrolledtext
from tkinter import ttk
import os
from tkinterdnd2 import *
import time
import shutil
from tkinterdnd2 import TkinterDnD, DND_FILES
import tkinter.dnd as dnd
import sys
import webbrowser
import re
from PIL import Image
from datetime import datetime
from os.path import exists
import sqlite3

# Receive data as chunks and rebuild message.
def data_recive(socket, size_of_header, chunk_prev_message, buffer_size=65536):
    # print(socket,"--socket")
    prev_buffer_size = len(chunk_prev_message)
    headerMsg = bytes()
    # print(f'headerMsg {headerMsg}')
    if prev_buffer_size < size_of_header:
            headerMsg = socket.recv(size_of_header - prev_buffer_size)

            if len(headerMsg) != size_of_header:
                headerMsg = chunk_prev_message + headerMsg
                chunk_prev_message = bytes()

    elif prev_buffer_size >= size_of_header:
        headerMsg = chunk_prev_message[:size_of_header]
        chunk_prev_message = chunk_prev_message[size_of_header:]
    
    global msgSize,newMsg
    try:   
        msgSize = int(headerMsg.decode())
        # print(f'msgSize {msgSize}')
        newMsg = chunk_prev_message
        # print(f'newMsg {newMsg}')
        chunk_prev_message = bytes()
    except (ValueError):
        pass    

    if msgSize:
        while True:
            if len(newMsg) < msgSize:
                newMsg += socket.recv(buffer_size)
            elif len(newMsg) > msgSize:
                chunk_prev_message = newMsg[msgSize:]
                newMsg = newMsg[:msgSize]
            if len(newMsg) == msgSize:
                break
        return newMsg, chunk_prev_message
    else:
        return None

#Send data 
def send_data(socket, size_of_header, msg_data):
    msg_len = len(msg_data)
    if msg_len:
        header = f"{msg_len:<{size_of_header}}"
        # time.sleep(5)
        socket.send(bytes(header, "utf-8") + msg_data)  


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def show_frame(frame):
    frame.tkraise()

    
def send_event(sock,message):
    send_data(sock, 2, message)
    
    
def mouse_controlling(sock, event_queue, resize, cli_width, cli_height, disp_width, disp_height):
    while True:
        event_code = event_queue.get()
        x = event_queue.get()
        y = event_queue.get()
        x, y, inside_the_display = check_in_display(x, y, resize, cli_width, cli_height, disp_width, disp_height)
        if event_code == 0 or event_code == 7:
            if inside_the_display: 
                if event_code == 7:
                    x = event_queue.get()
                    y = event_queue.get()
                message = bytes(f"{event_code:<2}" + str(x) + "," + str(y), "utf-8")
                send_event(sock,message)
        elif event_code in range(1, 10):
            if inside_the_display:
                message = bytes(f"{event_code:<2}", "utf-8")
                send_event(sock,message)


def XY_scale(x, y, cli_width, cli_height, disp_width, disp_height):
    X_scale = cli_width / disp_width
    Y_scale = cli_height / disp_height
    x *= X_scale
    y *= Y_scale
    return round(x, 1), round(y, 1)


def check_in_display(x, y, resize, cli_width, cli_height, disp_width, disp_height):
    active_window = pygetwindow.getWindowsWithTitle(f"Remote Desktop")
    if active_window and (len(active_window) == 1):
        x, y = win32gui.ScreenToClient(active_window[0]._hWnd, (x, y))
        if (0 <= x <= disp_width) and (0 <= y <= disp_height):
            if resize:
                x, y = XY_scale(x, y, cli_width, cli_height, disp_width, disp_height)
            return x, y, True
    return x, y, False


def on_move(x, y):
    mouse_event.put(0)  
    mouse_event.put(x)
    mouse_event.put(y)


def on_click(x, y, button, pressed):
    if pressed:                                             # mouse down
        mouse_event.put(button_code.get(button)[0])
        mouse_event.put(x)
        mouse_event.put(y)
    else:                                                   # mouse up
        mouse_event.put(button_code.get(button)[1]) 
        mouse_event.put(x)
        mouse_event.put(y)


def on_scroll(x, y, dx, dy):
    mouse_event.put(7) 
    mouse_event.put(x)
    mouse_event.put(y)
    mouse_event.put(dx)
    mouse_event.put(dy)


def keyboard_controlling(key, event_code):
    active_window = pygetwindow.getActiveWindow()
    if active_window and active_window.title == "Remote Desktop":
        if hasattr(key, "char"):
            msg = bytes(event_code + key.char, "utf-8")
        else:
            msg = bytes(event_code + key.name, "utf-8")
        send_event(remote_server_socket,msg)


def on_press(key):
    keyboard_controlling(key, "-1")  # -1 indicate a key press event


def on_release(key):
    keyboard_controlling(key, "-2")   # -2 indicate a key release event.


def receive_and_put_in_list(client_socket, jpeg_list):
    chunk_prev_message = bytes()
    size_of_header = 10
    print('inside recive and put in list function')
    try:
        while True:
            message = data_recive(client_socket, size_of_header, chunk_prev_message)
            if message:
                jpeg_list.put(lz4.frame.decompress(message[0])) 
                chunk_prev_message = message[1]
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        print("Thread automatically closed")


def display_data(jpeg_list, status_list, disp_width, disp_height, resize):
    # Hide the Pygame support prompt
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

    pygame.init()   # Initialize Pygame
    
    display_surface = pygame.display.set_mode((disp_width, disp_height))
    pygame.display.set_caption(f"Remote Desktop") # Set the window caption
    clock = pygame.time.Clock()   # Create a clock object to control the frame rate

    display = True     # Set the initial display flag

    print("inside display data function")
    # Main loop for updating the display
    while display:
        
        for event in pygame.event.get():   # Check for Pygame events
            # If the QUIT event is triggered (user closes the window)
            if event.type == pygame.QUIT:
                # Put "stop" into the status_list to signal the termination of the function
                status_list.put("stop")
                pygame.quit()  # Clean up Pygame resources
                return

        # Retrieve JPEG data from the jpeg_list
        jpeg_buffer = BytesIO(jpeg_list.get())

        # Open the JPEG image using PIL
        img = Image.open(jpeg_buffer)

        # Convert the PIL image to a Pygame surface
        py_image = pygame.image.frombuffer(img.tobytes(), img.size, img.mode)

        # If resize flag is True, resize the py_image to fit the display surface
        if resize:
            py_image = pygame.transform.scale(py_image, (disp_width, disp_height))

        jpeg_buffer.close()  # Close the JPEG buffer

        # Draw the py_image onto the display surface at coordinates (0, 0)
        display_surface.blit(py_image, (0, 0))
        
       # Update the display
        pygame.display.flip()
        clock.tick(60) # Control the frame rate (targeting 60 FPS)
        
        
def capture_screen(queue,disp_width,disp_height):
    print("inside capture screen function")
    while True:
        frame = ImageGrab.grab()  # Capture the screen frame
        frame = frame.resize((disp_width, disp_height))  # Resize the frame
        
        # Add border to the frame
        border_width = 10  # Width of the border in pixels
        border_color = (255, 0, 0)  # Red color for the border (change as desired)
        frame_with_border = Image.new('RGB', (disp_width + 2*border_width, disp_height + 2*border_width), border_color)
        frame_with_border.paste(frame, (border_width, border_width))
        # print("inside capture screen while loop function")
        image_bytes = BytesIO()
        frame_with_border.save(image_bytes, format='PNG')  # Convert the frame to PNG format
        compressed_bytes = lz4.frame.compress(image_bytes.getvalue())  # Compress the frame
        queue.put(compressed_bytes) 


def cleanup_process():
    process_list = [process1, process2]
    for process in process_list:
        if process:
            if process.is_alive():
                process.kill()
            process.join()
    mouse_listner.stop()
    mouse_listner.join()
    keyboard_listner.stop()
    keyboard_listner.join()
    print("cleanup finished")


def cleanup_display_process(status_list):
    if status_list.get() == "stop":
        send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("stop_capture", "utf-8"))
        print("inside cleaup display process")
        cleanup_process()


def computer_resolution(cli_width, cli_height, ser_width, ser_height):
    resolution_tuple = ((7680, 4320), (3840, 2160), (2560, 1440), (1920, 1080), (1600, 900), (1366, 768), (1280, 720),(1024, 768), (960, 720), (800, 600), (640, 480))
    if cli_width >= ser_width or cli_height >= ser_height:
        for resolution in resolution_tuple:
            if (resolution[0] <= ser_width and resolution[1] <= ser_height) and (resolution != (ser_width, ser_height)):
                return resolution
        else:
            return ser_width, ser_height

    else:
        return cli_width, cli_height


def remote_display():
    global thread2, mouse_listner,keyboard_listner, process1, process2, remote_server_socket, mouse_event  
    print("Send start message")
    send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("start_capture", "utf-8"))
    print("Start message sent")
    disable_choice = messagebox.askyesno("Remote Box", "Disable remote device wallpaper?(yes,Turn black)")

    remote_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # remote display sockets
    remote_server_socket.connect((server_ip, 1234))
    
    send_data(remote_server_socket, HEADER_COMMAND_SIZE, bytes(str(disable_choice), "utf-8"))
    print("\n")
    print(f">>Now you can CONTROL remote desktop")
    resize_option = False
    server_width, server_height = ImageGrab.grab().size
    client_resolution = data_recive(remote_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
    print("Received client_resolution :", client_resolution)
    client_width, client_height = client_resolution.split(",")

    display_width, display_height = computer_resolution(int(client_width), int(client_height), server_width,  server_height)
   
    if (client_width, client_height) != (display_width, display_height):
        resize_option = True

    jpeg_sync_queue = Multiprocess_queue()  

    thread2 = Thread(target=receive_and_put_in_list, name="recv_stream", args=(remote_server_socket, jpeg_sync_queue), daemon=True)
    thread2.start()
    
    keyboard_listner = Key_listener(on_press=on_press, on_release=on_release)
    keyboard_listner.start()
    
    mouse_event = Multiprocess_queue()

    process1 = Process(target=mouse_controlling, args=(remote_server_socket, mouse_event, resize_option, int(client_width), int(client_height), display_width, display_height), daemon=True)
    process1.start()

    mouse_listner = Mouse_listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    mouse_listner.start()
    
    execution_status_list = Multiprocess_queue()
    
    process2 = Process(target=display_data, args=(jpeg_sync_queue, execution_status_list, display_width, display_height , resize_option), daemon=True)
    process2.start()
    
    thread3 = Thread(target=cleanup_display_process, args=(execution_status_list,), daemon=True)
    thread3.start()
    
    screen_queue = Multiprocess_queue()
    screen_capture_process = Process(target=capture_screen, args=(screen_queue, display_width, display_height,), daemon=True)
    screen_capture_process.start()


# Function to reset UI elements and clear entered password
def reset_ui():
    name_entry.configure(state="normal")
    password_entry.configure(state="normal")
    connect_button.configure(state="normal")
    password_entry.delete(0, "end")

def client_con_data():
     # Connect to the SQLite database
    conn = sqlite3.connect('client_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS client_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_date TEXT NOT NULL,
            log_message TEXT NOT NULL
        )
    ''')
    connection_date = datetime.now().strftime("%Y-%m-%d")
    connection_time = datetime.now().strftime("%H:%M:%S")
    log_message = f"Connection from {server_ip} established at {connection_time}\n"
    cursor.execute('INSERT INTO client_connections (connection_date , log_message) VALUES (?,?)',
                   (connection_date,log_message))
    conn.commit()
    cursor.close()


def login_to_connect():
    global command_server_socket, remote_server_socket, thread1, server_ip, file_server_socket, f_thread, chat_server_socket
    if messagebox.askquestion("Connection Request", "Do you want to connect?") == 'yes':
        server_ip = name_entry.get()
        server_password = password_entry.get()

        if len(server_password) == 6 and server_password.strip() != "":
            try:
                command_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                command_server_socket.connect((server_ip, 1234))
                server_password = bytes(server_password, "utf-8")

                send_data(command_server_socket, 2, server_password)
                connect_response = data_recive(command_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
                print(connect_response, "connect_response")

                if connect_response != "1":
                    print("Wrong Password Entered...!")
                else:
                    password_entered_time = time.time()
                    thread1 = Thread(target=listen_for_commands, daemon=True)
                    thread1.start()
                  
                    client_con_data()

                    
                    print("\n")
                    print("Connected to the remote desktop...!")
         
                    name_entry.configure(state="disabled")
                    password_entry.configure(state="disabled")
                    connect_button.configure(state="disabled")
                    
                    file_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    file_server_socket.connect((server_ip, 1234))

                    f_thread = Thread(target=send_files, name='send_file',daemon=True)
                    f_thread.start()
                    print(f'file server socket start {file_server_socket}')
                    
                    # chat socket
                    chat_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    chat_server_socket.connect((server_ip, 1234))
                    
                    # thread for chat
                    recv_chat_msg_thread = Thread(target=receive_message, name="recv_chat_msg_thread", daemon=True)
                    recv_chat_msg_thread.start()
                    
                    
                    show_frame(frame2)
                    expiration_thread = Thread(target=check_password_expiration, daemon=True)
                    expiration_thread.start()
                    # disconnect_button.configure(state="normal")  # Enable

            except OSError as e:
                print(e.strerror)
        else:
            print("Password is not 6 characters")


def is_password_expired():
    global command_server_socket,remote_server_socket,thread1,server_ip,file_server_socket,f_thread,chat_server_socket,password_entered_time
    if password_entered_time is not None:
        elapsed_time = time.time() - password_entered_time
        if elapsed_time >= 30 * 60: # 30min elapsed_time >= 30 * 60: # 30min
            print("Password expired")
            messagebox.showinfo("Password Expired", "Your password has expired. Please login again.")
            root.destroy()
            # Reset the global variables
            command_server_socket = None
            remote_server_socket = None
            thread1 = None
            server_ip = None
            file_server_socket = None
            f_thread = None
            chat_server_socket = None
            password_entered_time = None


def check_password_expiration():
    while True:
        is_password_expired()
        time.sleep(60)


def close_sockets():
    # service_socket_list = [command_server_socket, remote_server_socket,file_server_socket]
    service_socket_list = [command_server_socket, remote_server_socket,file_server_socket,chat_server_socket]
    for sock in service_socket_list:
        if sock:
            sock.close()
    print("All Sockets are closed now")


def disconnect(btn_caller):
    if btn_caller == "button":
        result = messagebox.askquestion("Disconnect", "Are you sure you want to disconnect?")
        if result == 'yes':
            send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("disconnect", "utf-8"))
        else:
            return
    
    close_sockets()

    # Enable
    name_entry.configure(state="normal")
    password_entry.configure(state="normal")
    connect_button.configure(state="normal")

    # Disable
    # disconnect_button.configure(state="disabled")
    messagebox.showinfo("Disconnected", "You have been disconnected successfully.")
    
    
def listen_for_commands():
    # global connection_timestamp
    listen = True
    try:
        while listen:
            message = data_recive(command_server_socket, HEADER_COMMAND_SIZE, bytes(), 1024)[0].decode("utf-8")
            if message == "disconnect":
                listen = False
               
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        disconnect("message")
        print("Thread automatically exit")


def file_path_listbox(event):
    listbox.insert(tk.END, event.data)
    


def save_file_send_log(filename, data):
    # Connect to the SQLite database
    conn = sqlite3.connect('client_data.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_send_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            send_time TEXT NOT NULL,
            server_ip TEXT NOT NULL,
            file_data BLOB
        )
    ''')

    send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT INTO file_send_logs (server_ip, filename, send_time, file_data) VALUES (?,?,?,?)',
                   (server_ip, filename, send_time, data))
    conn.commit()
    cursor.close()

forbidden_extensions = [".exe", ".dll"]

def send_files():
    selected_indices = listbox.curselection()
    if selected_indices:
        files = [listbox.get(index) for index in selected_indices]
        print(f"Sending files: {files}")

        for file in files:
            filename = os.path.basename(file)
            extension = os.path.splitext(filename)[1].lower()

            if extension in forbidden_extensions:
                # Ask for confirmation to send forbidden file types
                result = messagebox.askquestion("Send File", f"Are you sure you want to send the file: {filename}?\nSending forbidden file types (.exe, .dll) can be risky.")
                if result != "yes":
                    print(f"Skipping file: {filename}")
                    continue

            # Send the filename to the server
            file_server_socket.send(filename.encode())
              
              # Read the file data
            with open(file, "rb") as f:
                data = f.read()

            # Save the file send log with time, server IP, filename, and file data
            save_file_send_log(filename, data)

            # Send the file data
            while data:
                file_server_socket.send(data)
                data = f.read(1024)
            
            print(f"File sent: {file}")

        print("All files sent.")
    else:
        print("No files selected.")
        messagebox.showwarning("No File Selected", "Please select at least one file to send.")



        
def browse_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        listbox.insert(tk.END, file_path)
        # file_server_socket.send(file_path)
        
        
def ui_file():
    global window_file,listbox
    window_file = TkinterDnD.Tk()
    window_file.title('file Tranfer (Client)')
    window_file.geometry('400x350')
    window_file.resizable(0, 0)
    window_file.config(bg='#2E2E2E')
    # window.iconbitmap('icon.ico')

    frame = tk.Frame(window_file,width=700,height=700,bg='#2E2E2E')
    frame.pack(fill=tk.BOTH, expand=True)

    heading_file = tk.Label(frame,text='Drag and Drop file here',font=("Helvetica", 14 ,"italic"),fg='white',bg='#2E2E2E')
    # heading_file.place(x=0,y=0)
    heading_file.pack()

    listbox = tk.Listbox(
        frame,
        width=63,
        height=15,
        selectmode=tk.EXTENDED,
        background='light blue',
        highlightbackground="dodger blue",
        highlightthickness=2
        
    )
    listbox.pack(fill=tk.X, side=tk.LEFT)
    # listbox.place(x=200,y=300)
    listbox.drop_target_register(DND_FILES)
    listbox.dnd_bind('<<Drop>>', file_path_listbox)

    scrollbar = tk.Scrollbar(
        frame,
        orient=tk.VERTICAL
    )
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.configure(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)

    button_frame = tk.Frame(window_file,bg="#8A8A8A")
    button_frame.pack(pady=10)
    
    send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("start_file_explorer", "utf-8"))
    # select_file_process = Process(target=browse_file,  name="select_file_process", daemon=True)
    # select_file_process.start()
    
    # send_file_process = Thread(target=send_files, name="send_file_process", daemon=True)
    # send_file_process.start()
    send_button = tk.Button(button_frame, text="Send Files", command=send_files ,compound=tk.TOP, bg="#8A8A8A", activebackground='#808080',activeforeground="white")
    send_button.pack(side=tk.LEFT, padx=0)
    

    browse_button = tk.Button(button_frame, text="Browse File", command=browse_file,compound=tk.TOP,bg="#8A8A8A", activebackground='#808080',activeforeground="white")
    browse_button.pack(side=tk.LEFT, padx=0)

    window_file.mainloop()
    
    
def remote_display_screen():
    global thread2, process1, process2, remote_server_socket 
    print("Send start message")
    send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("screen_sharing", "utf-8"))
    print("Start message sent")
    remote_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # remote display sockets
    remote_server_socket.connect((server_ip, 1234))
    print("\n")
    print(f">>Now you can SHARE SCREEN to remote desktop")
    resize_option = False
    server_width, server_height = ImageGrab.grab().size
    client_resolution = data_recive(remote_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
    print("Received client_resolution :", client_resolution)
    client_width, client_height = client_resolution.split(",")

    display_width, display_height = computer_resolution(int(client_width), int(client_height), server_width, server_height)

    if (client_width, client_height) != (display_width, display_height):
        resize_option = True

    jpeg_sync_queue = Multiprocess_queue()  
    thread2 = Thread(target=receive_and_put_in_list, name="recv_stream", args=(remote_server_socket, jpeg_sync_queue), daemon=True)
    thread2.start()
    
    execution_status_list = Multiprocess_queue()
    process2 = Process(target=display_data, args=(jpeg_sync_queue, execution_status_list, display_width, display_height , resize_option), daemon=True)
    process2.start()
    
    thread3 = Thread(target=cleanup_display_process, args=(execution_status_list,), daemon=True)
    thread3.start()
    
    screen_queue = Multiprocess_queue()
    screen_capture_process = Process(target=capture_screen, args=(screen_queue, display_width, display_height,), daemon=True)
    screen_capture_process.start()


def animate_text(label, text, delay, index=0):
    label.config(text=text[:index])
    index += 1
    if index <= len(text):
        label.after(delay, animate_text, label, text, delay, index)

def on_enter(event):
    sign_in_btn['background'] = '#1f8cff'
    # connect_button['background'] = '#1f8cff'

def on_leave(event):
    sign_in_btn['background'] = '#28adff'
    # connect_button['background'] = '#28adff'
    

def open_facebook():
    webbrowser.open_new(r"https://www.facebook.com/multispanindia")
    print('hello facebook')

def open_instagram():
    webbrowser.open_new(r"https://www.instagram.com/multispanindia")
    print('hello instagram')
    
def open_tweeter():
    webbrowser.open_new(r"https://twitter.com/multispanindia")
    print('hello facebook')
    
def open_linkedin():
    webbrowser.open_new(r"https://www.linkedin.com/company/multispancontrolinstruments")
    print('hello linkedin')
    
def create_connection_table():
    conn = sqlite3.connect('client_data.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS client_connections
                      (connection_date TEXT, log_message TEXT)''')

    conn.commit()
    cursor.close()
    conn.close()  

def create_file_table():
    conn = sqlite3.connect('client_data.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS file_send_logs
                      (filename TEXT, send_time TEXT, server_ip TEXT,file_data BLOB)''')

    conn.commit()
    cursor.close()
    conn.close()  
def display_text_file():
    
    create_connection_table()
    create_file_table()
    
    conn = sqlite3.connect('client_data.db')
    cursor = conn.cursor()

    cursor.execute('SELECT connection_date, log_message FROM client_connections')
    connection_rows = cursor.fetchall()

    cursor.execute('SELECT filename, send_time, server_ip FROM file_send_logs')
    file_send_rows = cursor.fetchall()

    cursor.close()
    conn.close()

    tree.delete(*tree.get_children())

    for i, (time, message) in enumerate(connection_rows):
        if i % 2 == 0:
            color = 'lightblue'
        else:
            color = 'white'
        tree.insert('', tk.END, values=(time, message, "-", "-"), tags=(color,))

    for i, (filename, send_time, server_ip) in enumerate(file_send_rows):
        if i % 2 == 0:
            color = 'lightblue'
        else:
            color = 'white'
        tree.insert('', tk.END, values=(send_time, f"File '{filename}' sent from {server_ip}", filename, server_ip), tags=(color,))

    tree.tag_configure('lightblue', background='lightblue')
    tree.tag_configure('white', background='white')


# def apply_filter():
#     filter_text = search_entry.get().lower()

#     # Clear previous filter results
#     filter_text.tag_remove('highlight', '1.0', tk.END)

#     # Apply the filter to file data
#     file_content = filter_text.get('1.0', tk.END)
#     filtered_indices = [(m.start(), m.end()) for m in re.finditer(re.escape(filter_text), file_content, re.IGNORECASE)]
#     for start, end in filtered_indices:
#         filter_text.tag_add('highlight', f'1.0+{start}c', f'1.0+{end}c')


def apply_filter():
    filter_text = search_entry.get().lower()

    # Clear previous filter results
    tree.tag_remove('highlight', '1.0', tk.END)

    # Apply the filter to file data
    file_content = tree.item(tree.focus())['values'][1]
    filtered_indices = [(m.start(), m.end()) for m in re.finditer(re.escape(filter_text), file_content, re.IGNORECASE)]
    for start, end in filtered_indices:
        tree.tag_add('highlight', f'1.0+{start}c', f'1.0+{end}c')


     # Apply the tag configuration to highlight the text
    tree.tag_configure('highlight', background='yellow')
  


def add_chat_display(msg, name,current_time):
    formatted_message = f"{msg} \n {current_time}"
    text_chat_tab.configure(state=tk.NORMAL,fg="white",padx=5,pady=10)
    text_chat_tab.insert(tk.END, "\n")
    text_chat_tab.insert(tk.END, name + ": " + formatted_message)
    text_chat_tab.configure(state="disabled")

def send_message():
    try:
        msg = input_text_widget.get()
        print('send_message', msg)

        if msg and msg.strip() != "":
            input_text_widget.delete(0, "end")
            send_data(chat_server_socket, CHAT_HEADER_SIZE, bytes(msg, "utf-8"))

            current_time = datetime.now().strftime("%H:%M:%S")
            add_chat_display(msg, LOCAL_NAME, current_time)

            # Save the message to the chat log file
            save_chat_message(msg, LOCAL_NAME + ":", current_time)

    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)


def receive_message():
    try:
        while True:
            msg = data_recive(chat_server_socket, CHAT_HEADER_SIZE, bytes())[0].decode("utf-8")

            current_time = datetime.now().strftime("%H:%M:%S")
            add_chat_display(msg, REMOTE_NAME, current_time)

            # Save the message to the chat log file
            save_chat_message(msg, REMOTE_NAME + ":", current_time)

            if not is_chat_window_open():
                messagebox.showinfo("New Message", "You have a new message!")

    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass

def is_chat_window_open():
    return chat_frame.winfo_exists() and chat_frame.winfo_viewable()

# Function to save chat message in the database
def save_chat_message(sender, message,timestamp):
    conn = sqlite3.connect('client_data.db')
    cursor = conn.cursor()
    
    # Create the table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            sender TEXT ,
            message TEXT  
        )
    ''')
    
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insert the chat message with the timestamp into the table
    cursor.execute('INSERT INTO chat_messages (timestamp,sender, message) VALUES (?, ?, ?)', (timestamp,sender,message))
    
    conn.commit()
    conn.close()
        
     
if __name__ == "__main__":
    
    freeze_support()
    command_server_socket = None
    remote_server_socket = None
    file_server_socket = None
    chat_server_socket = None
    password_entered_time = None
    thread1 = None
    thread2 = None
    f_thread = None
    mouse_listner = None
    keyboard_listner = None
    process1 = None
    process2 = None
    server_ip = str()
    # server_port = int()
    status_event_log = 1
    HEADER_COMMAND_SIZE = 10
    FILE_HEADER_SIZE = 2
    CHAT_HEADER_SIZE = 10
    LOCAL_NAME = "Me"
    REMOTE_NAME = "Remote"
    button_code = {Button.left: (1, 4), Button.right: (2, 5), Button.middle: (3, 6)}

    root = tk.Tk()
    root.title("Remote Access Desktop Application")
    # root.iconphoto(True,tk.PhotoImage(file='assets/images/img/m_logo'))
    root.iconbitmap("m_logo.ico")
    root.state('zoomed')
    # root.resizable(False, False)

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    frame1 = tk.Frame(root)
    frame2 = tk.Frame(root)
    frame3 = tk.Frame(root)
    frame4 = tk.Frame(root)


    for frame in (frame1, frame2, frame3,frame4):
        frame.grid(row=0,column=0,sticky='nsew')
        
    #==================Frame 1 code=======================
    # Set the background image
    img = Image.open('assets/leone-venter-VieM9BdZKFo-unsplash.png')
    #
    resized_image = img.resize((1920, 1020), Image.LANCZOS)

    # Convert the resized image to PhotoImage
    new_image = ImageTk.PhotoImage(resized_image)
    label = tk.Label(frame1, image=new_image, background='#f2f2f2')
    label.place(x=0, y=0, relwidth=1, relheight=1)

    # logo_image = tk.PhotoImage(file='assets/images/img/multispan-logo.png')\
    logo_image = tk.PhotoImage(file='assets/img/multispan-logo.png')
        
    logo_label = tk.Label(frame1, image=logo_image)
    logo_label.place(x=60, y=40)
    # logo_label.pack(expand=True)


    # left side 
    # Create a card frame
    card_frame0 = tk.Frame(frame1, bg='#f2f2f2', padx=20, pady=20)
    card_frame0.place(x=223, y=320)

    heading1_label = tk.Label(card_frame0, text='Provide help', font=('Rubik', 23, 'bold'), fg='black', bg='#f2f2f2', padx=25)
    heading1_label.pack(anchor='w')

    # separator = ttk.Separator(card_frame0, orient='horizontal', style='info.Horizontal.TSeparator')
    # separator.pack(fill='x', pady=5,padx=20)

    heading2_label = tk.Label(card_frame0, text='Remotely access and control.', font=('Rubik', 18, 'bold'), fg='black', bg='#f2f2f2', justify='left')
    heading2_label.pack()

    text_to_animate_1 = heading1_label.cget('text')
    text_to_animate_2 = heading2_label.cget('text')
    animation_delay = 100  # milliseconds

    # animate_text(heading1_label, text_to_animate_1, animation_delay)
    animate_text(heading2_label, text_to_animate_2, animation_delay)


    paragraph_label = tk.Label(card_frame0, text='''
    Sign in to TeamViewer Remote to view, control and
    access any device.
    ''', font=('Rubik', 13), fg='gray', bg='#f2f2f2', justify='left',padx=0,pady=0)
    paragraph_label.pack(anchor='w')
    # paragraph_label.place(x=2,y=100)

    sign_in_btn = tk.Button(card_frame0,text='SIGN IN',width=13,height=2,bg='#28adff',fg='white', font=('Rubik', 12, 'bold'))
    sign_in_btn.pack()
    # sign_in_btn.place(x=25,y=150)
    

    style = ttk.Style()
    style.configure('Custom.TButton', background='#28adff', foreground='white', font=('Rubik', 12, 'bold'))

    sign_in_btn.bind("<Enter>", on_enter)
    sign_in_btn.bind("<Leave>", on_leave)

    dont_have_account_text =  tk.Label(card_frame0, text="Don't have an account? ", font=('Rubik', 11), fg='gray', bg='#f2f2f2',padx=25)
    dont_have_account_text.pack(anchor='w')
    # dont_have_account_text.place(x=200,y=580)

    dont_have_account_text1 =  tk.Label(card_frame0, text="Create one here.", font=('Rubik', 11), fg='#28adff', bg='#f2f2f2')
    dont_have_account_text1.pack()
    dont_have_account_text1.place(x=180,y=210)


    # right side
    # Create a card frame
    card_frame = tk.Frame(frame1, bg='#f8f9f9', padx=20, pady=20)
    card_frame.place(x=650, y=300)
    card_frame.pack(expand=True)

    # Heading
    heading_label = tk.Label(card_frame, text='Get Started', font=('Rubik', 18, 'bold'), fg='black', bg='#f8f9f9')
    heading_label.pack(anchor='w', pady=(0, 5))

    # Paragraph
    paragraph = tk.Label(card_frame, text='Support session', font=('Rubik', 13, 'bold'), fg='black', bg='#f8f9f9')
    paragraph.pack(anchor='w')
    paragraph1 = tk.Label(card_frame, text='''
    Enter the session code provided by your expert to grant
    them access to your device and start receiving support.
    ''', font=('Rubik', 10), fg='gray', bg='#f8f9f9', justify='left')
    paragraph1.pack(anchor='w')

    # # Create the input frame
    input_frame = tk.Frame(card_frame, padx=10, pady=10, bg='#f8f9f9')
    input_frame.pack()

    # Create the IP label and entry
    IP_label = tk.Label(input_frame, text="USERNAME     : ",  font=('Rubik', 11, 'bold'), bg='#f8f9f9')
    IP_label.grid(row=0, column=0, sticky=tk.W)

    name_entry = ttk.Entry(input_frame, font=('Rubik', 12), style='info.TEntry', width=20, foreground='gray')
    name_entry.grid(row=0, column=1, ipadx=20, ipady=5, pady=5)

    # Create the password label and entry
    password_label = tk.Label(input_frame, text="ENTRY CODE : ", font=('Rubik', 11, 'bold'), bg='#f8f9f9')
    password_label.grid(row=1, column=0, sticky=tk.W)

    password_entry = ttk.Entry(input_frame, font=('Rubik', 12), show="*", style='info.TEntry', width=20, foreground='gray')
    password_entry.grid(row=1, column=1, ipadx=20, ipady=5, pady=5)

    connect_button = tk.Button(input_frame, text="Connect", font=('Rubik', 12,'bold'), bg='#28adff', fg='white')
    connect_button.grid(row=2, column=1, padx=5, sticky=tk.N, pady=5)
    connect_button.configure(width=22, height=1)
    connect_button.config(command=login_to_connect)

    separator1 = ttk.Separator(frame1, orient='horizontal', style='info.Horizontal.TSeparator')
    separator1.pack(fill='x', pady=5,padx=20)
    
    social = tk.Frame(frame1)
    social.pack()
    
    #https://www.facebook.com/multispanindia
    facebook = tk.PhotoImage(file='assets/facebook.png')  
    fb_btn = tk.Button(social,image=facebook,relief=tk.FLAT,command=open_facebook)
    fb_btn.pack(side='left',padx=15)
    
    #https://www.instagram.com/multispanindia/
    instagram = tk.PhotoImage(file='assets/img/camera.png')   
    insta_btn = tk.Button(social,image=instagram,relief=tk.FLAT,command=open_instagram)
    insta_btn.pack(side='left',padx=15)
    
    #https://twitter.com/multispanindia
    tweeter = tk.PhotoImage(file='assets/img/twitter-logo.png')   
    tweet_btn = tk.Button(social,image=tweeter,relief=tk.FLAT,command=open_tweeter)
    tweet_btn.pack(side='left',padx=15)
    
    #https://www.linkedin.com/company/multispancontrolinstruments
    linkedin = tk.PhotoImage(file='assets/linkedin.png')   
    link_btn = tk.Button(social,image=linkedin,relief=tk.FLAT,command=open_linkedin)
    link_btn.pack(side='left',padx=15)
    
    paragraph2 = tk.Label(frame1, text='Copyright © 2023 Multispan India. All rights reserved', font=('Rubik', 10), fg='gray', bg='#f2f2f2')
    paragraph2.pack(anchor=tk.CENTER)
    
    separator2 = ttk.Separator(frame1, orient='horizontal', style='info.Horizontal.TSeparator')
    separator2.pack(fill='x', pady=5,padx=20)
        
    #==================Frame 2 code====================
    bg_img = tk.PhotoImage(file='assets/georgie-cobbs-bKjHgo_Lbpo-unsplash (1).png')
    background = tk.Label(frame2, image=bg_img)
    background.place(x=0, y=0, relwidth=1, relheight=1)

    # Create the header frame
    header_frame = tk.Frame(frame2, bg="#8A8A8A")
    header_frame.place(x=0, y=0, width=800)
    header_frame.pack(fill="x")

    logo = tk.PhotoImage(file='assets/img/logo2.png')
    logo_img = tk.Label(header_frame, image=logo, bg="#8A8A8A")
    logo_img.pack(side="left", padx=10)

    # Create a container frame for search elements
    search_container = tk.Frame(header_frame, bg="#8A8A8A")
    search_container.pack(padx=10, pady=10)

    # Create the search bar
    search_bar = tk.Entry(search_container, font=("Rubik", 14), width=50)
    search_bar.pack(side="left")

    # Create the search icon
    search_img = tk.PhotoImage(file='assets/magnifying-glass.png')
    search_icon = tk.Label(search_container, image=search_img, font=("Rubik", 14), bg="#8A8A8A")
    search_icon.pack(side="left", padx=5)

    user = tk.PhotoImage(file='assets/user.png')
    user_profile = tk.Label(search_container, image=user, bg="#8A8A8A")
    user_profile.pack()

    # Create the sidebar frame
    sidebar_frame = tk.Frame(frame2, bg="white", width=200)
    sidebar_frame.pack(fill="y", side="left")

    # Create the sidebar content
    home_img = tk.PhotoImage(file='assets/img/icons8-home-50.png')
    home_icon = tk.Button(sidebar_frame, image=home_img, font=("Rubik", 16), bg="white",fg='white',relief='flat', borderwidth=0,)
    home_icon.pack(padx=10, pady=10)

    file_img = tk.PhotoImage(file='assets/img/icons8-downlod-64.png')
    file_icon = tk.Button(sidebar_frame, image=file_img, font=("Rubik", 16), bg="white",fg='white',relief='flat', borderwidth=0)
    file_icon.pack(padx=10, pady=10)
    
    dashboard = tk.PhotoImage(file='assets/dashboard.png')
    dashboard_icon = tk.Button(sidebar_frame, image=dashboard, font=("Rubik", 16), bg="white",fg='white',relief='flat', borderwidth=0,command=lambda:show_frame(frame4))
    dashboard_icon.pack(padx=10, pady=10)

    logout = tk.Button(sidebar_frame,text="Logout", font=("Rubik", 10), bg="white",fg='black',relief='flat')
    logout.config(command=lambda:show_frame(frame1))
    logout.pack()

    # Create the content frame
    content_frame = tk.Frame(frame2, bg="white",width=600)
    content_frame.pack(expand=True)
    # content_frame.place(x=600, y=300)

    # Create the grid frames
    grid_frame = tk.Frame(content_frame, bg="white", padx=10, pady=10)
    grid_frame.pack(side="left")

    grid_frame1 = tk.Frame(content_frame,bg='#8A8A8A', padx=0, pady=10)
    grid_frame1.pack(side="left")

    label = tk.Label(grid_frame1, text='Remote Actions', font=('Rubik', 14, 'bold'), bg='#8A8A8A',fg='white')
    label.grid(row=0, column=0, columnspan=2, pady=10)

    # Create the card labels
    card1 = tk.Button(grid_frame1,bg='#8A8A8A',fg='black', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    card1.config(compound=tk.TOP, bd=0, command=remote_display)
    card2 = tk.Button(grid_frame1,bg='#8A8A8A',fg='black', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    card2.config(compound=tk.TOP, bd=0,command=remote_display_screen)
    card3 = tk.Button(grid_frame1,bg='#8A8A8A',fg='black', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    # card3.config(command=lambda:show_frame(frame5))
    card3.config(command=ui_file)
    card4 = tk.Button(grid_frame1,bg='#8A8A8A',fg='black', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    card4.config(command=lambda:show_frame(frame3))

    # Load the icon images
    icon1 = tk.PhotoImage(file="assets/img/icons8-remote-desktop-48.png")
    icon2 = tk.PhotoImage(file="assets/img/icons8-screen-share-64.png")
    icon3 = tk.PhotoImage(file="assets/img/icons8-downloads-folder-94.png")
    icon4 = tk.PhotoImage(file="assets/img/icons8-chat-94.png")

    # Set the icons for each card
    card1.config(image=icon1)
    card2.config(image=icon2)
    card3.config(image=icon3)
    card4.config(image=icon4)

    # Add text labels below the icons

    text1 = tk.Label(grid_frame1, text="Remote Access", font=('Rubik', 12, 'bold'), bg='#8A8A8A',fg='white')
    sub_text1 = tk.Label(grid_frame1, text="""Set up for Remote
    desktop control""", font=('Rubik', 10),bg='#8A8A8A',fg='#DCDEE6', pady=1,justify= tk.LEFT)

    text2 = tk.Label(grid_frame1, text="Screen Share", font=('Rubik', 12, 'bold'),bg='#8A8A8A',fg='white')
    sub_text2 = tk.Label(grid_frame1, text="""Start with sharing
    your screen""", font=('Rubik', 10),bg='#8A8A8A',fg='#DCDEE6', pady=1,justify= tk.LEFT)

    text3 = tk.Label(grid_frame1, text="File Transfer", font=('Rubik', 12, 'bold'),bg='#8A8A8A',fg='white')
    sub_text3 = tk.Label(grid_frame1, text="""Transfer files""", font=('Rubik', 10),bg='#8A8A8A',fg='#DCDEE6', pady=1,justify= tk.LEFT)

    text4 = tk.Label(grid_frame1, text="Chat", font=('Rubik', 12, 'bold'),bg='#8A8A8A',fg='white')
    sub_text4 = tk.Label(grid_frame1, text="""Start chat with your
    loved ones""", font=('Rubik', 10),bg='#8A8A8A',fg='#DCDEE6', pady=1,justify= tk.LEFT)


    # Grid layout for cards and text labels
    card1.grid(row=1, column=0, padx=10, pady=30)
    text1.grid(row=2, column=0, padx=30, pady=0)
    sub_text1.grid(row=3, column=0, padx=30)

    card2.grid(row=1, column=1, padx=10, pady=30)
    text2.grid(row=2, column=1, padx=30)
    sub_text2.grid(row=3, column=1, padx=30)

    card3.grid(row=4, column=0, padx=10, pady=30)
    text3.grid(row=5, column=0, padx=30)
    sub_text3.grid(row=6, column=0, padx=30)

    card4.grid(row=4, column=1, padx=10, pady=30)
    text4.grid(row=5, column=1, padx=30)
    sub_text4.grid(row=6, column=1, padx=30)

    heading_text = tk.Label(grid_frame, text='Start Your Journey With Us', font=('Rubik', 25,'bold'),bg='white',fg='black')
    heading_text.pack()

    pera = tk.Label(grid_frame,text="""
    Prevent malpractice and protect users from scammers by
    providing more transparency about the connection origin.
    Overall ensuring a higher level of security. Prevent 
    malpractice and protect users from scammers by providing
    more transparency about the connection origin. Overall 
    ensuring a higher level of security.\n
    TeamViewer is now easier to use and more accessible. 
    Easier to navigate, faster to train on, more intuitive to use             
    """, font=('Rubik', 11),bg='white',fg='#8A8A8A',justify= tk.LEFT).pack()
    
    paragraph3 = tk.Label(frame2, text='Copyright © 2023 Multispan India. All rights reserved', font=('Rubik', 10), fg='black', bg='#DDCEB5')
    paragraph3.pack(anchor=tk.CENTER)
    
    
    #==================Frame 3 code====================
    chat_bg = tk.PhotoImage(file='assets/chatframebg1.png')
    background = tk.Label(frame3, image=chat_bg)
    background.place(x=0, y=0, relwidth=1, relheight=1)
    
     # Heading with icon
    heading_frame = tk.Frame(frame3,bg="black")
    heading_frame.pack(fill="x", padx=450, pady=20)
    # Text
    heading_label = tk.Label(heading_frame, text="Chat Room", font=("Rubik", 14,"bold"),  bg="black", fg="white",anchor="center")
    heading_label.pack(side="left", padx=5,pady=5)
    
    chat_frame = tk.LabelFrame(frame3, padx=20, pady=20, bd=0 , width=50,height=5,background="black" ,fg='white')
    chat_frame.pack()


    text_chat_tab = scrolledtext.ScrolledText(chat_frame,bd=0, width=40, height=20,font=("Arial", 12),background="black",fg='white')
    # text_chat_tab.vbar.config(troughcolor = 'red', bg = 'blue')
    text_chat_tab.pack(padx=10,pady=10)
    text_chat_tab.configure(state="disabled")
    

    input_text_frame = tk.LabelFrame(chat_frame, pady=5, bd=0,background="black",fg='white')
    input_text_frame.pack()

    input_text_widget = tk.Entry(input_text_frame, width=40,background="black" , highlightcolor="blue",fg='white')
    input_text_widget.configure(font=("arial", 14))
    input_text_widget.bind("<Return>", send_message)
    # input_text_widget.bind("<Enter>",send_message)
    input_text_widget.pack(side="left", padx=5,pady=5)

    send_icon = tk.PhotoImage(file="assets/img/send.png")
    send_button = tk.Button(input_text_frame, image=send_icon, command=send_message,background="black",bd=0)
    send_button.pack(side="left", padx=10,pady=10)

    back_icon = tk.PhotoImage(file="assets/img/back.png")
    back_button = tk.Button(frame3,image=back_icon,command=lambda:show_frame(frame2),bd=0,background="black")
    back_button.place(x=390,y=20)
    #==================Frame 4 code====================
   
    # Create a header frame
    header_frame2 = tk.Frame(frame4, bg="#8A8A8A")
    header_frame2.place(x=0, y=0, width=800,height=20)
    header_frame2.pack(fill="x")
    
    logo2 = tk.PhotoImage(file='assets/img/logo2.png')
    logo_img2 = tk.Label(header_frame2, image=logo, bg="#8A8A8A")
    logo_img2.pack(side="left", padx=10)

    search_container2 = tk.Frame(header_frame2, bg="#8A8A8A")
    search_container2.pack(padx=10, pady=5)

    # Create a filter input Entry widget
    search_entry = tk.Entry(search_container2,font=("Rubik", 14), width=50)
    search_entry.pack(padx=10, pady=5,side="left")

    # Create the search icon
    search_icon = tk.Button(search_container2, image=search_img, bg="#8A8A8A", activebackground='#8A8A8A',relief='flat', borderwidth=0, command=apply_filter)
    search_icon.pack(side="left", padx=5)

    # Create a load button
    load_img = tk.PhotoImage(file='assets/refresh-buttons.png')
    load_button = tk.Button(search_container2,image=load_img, bg="#8A8A8A", activebackground='#8A8A8A',relief='flat', borderwidth=0,command=display_text_file )
    load_button.pack(padx=10,pady=5)
    
    
    # Create the sidebar frame
    sidebar_frame2 = tk.Frame(frame4, bg="white", width=200)
    sidebar_frame2.pack(fill="y", side="left")

    # Create the sidebar content
    home_icon2 = tk.Button(sidebar_frame2, image=home_img, font=("Rubik", 16), bg="white",fg='white',relief='flat', borderwidth=0,command=lambda:show_frame(frame2))
    home_icon2.pack(padx=10, pady=10)

    file_icon2 = tk.Button(sidebar_frame2, image=file_img, font=("Rubik", 16), bg="white",fg='white',relief='flat', borderwidth=0)
    file_icon2.pack(padx=10, pady=10)

    dashboard_icon2 = tk.Button(sidebar_frame2, image=dashboard, font=("Rubik", 16), bg="white",fg='white',relief='flat', borderwidth=0,command=lambda:show_frame(frame4))
    dashboard_icon2.pack(padx=10, pady=10)

    logout2 = tk.Button(sidebar_frame2,text="Logout", font=("Rubik", 10), bg="white",fg='black',relief='flat')
    logout2.config(command=lambda:show_frame(frame1))
    logout2.pack()

    # Create a frame Treeview widget
    tree = ttk.Treeview(frame4)
    tree['columns'] = ('Connection Data', 'Log Message')

    # Define column names and widths
    tree.column('#0', width=0, stretch=tk.NO)
    tree.column('Connection Data', width=150, anchor=tk.CENTER)
    tree.column('Log Message', width=400, anchor=tk.W)
    tree.configure(padding=5)
    # Add column headers
    tree.heading('#0', text='')
    tree.heading('Connection Data', text='Connection Data')
    tree.heading('Log Message', text='Log Message')
  
    # Pack the Treeview widget
    tree.pack(side=tk.TOP ,fill='both', expand=True)
    
   # Adjust row height
    tree.configure(height=10)  # Set the desired row height here

    # Add padding between rows
    style = ttk.Style()
    style.configure("Treeview", rowheight=30)  # Set the desired padding height here

    paragraph3 = tk.Label(frame4, text='Copyright © 2023 Multispan India. All rights reserved', font=('Rubik', 10), fg='gray', bg='#f2f2f2')
    paragraph3.pack(anchor=tk.CENTER)

    display_text_file() # Display connection log in screen
        
    show_frame(frame1)

    root.mainloop()