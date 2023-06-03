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
import connection_common
import win32api
import datetime
import pygame
from tkinter import filedialog , StringVar
from tkinter import ttk
import os
from tkinterdnd2 import *
import time
import shutil
from tkinterdnd2 import TkinterDnD, DND_FILES
import tkinter.dnd as dnd


def show_frame(frame):
    frame.tkraise()

    
def send_event(sock,message):
    connection_common.send_data(sock, 2, message)
    
    
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
            message = connection_common.data_recive(client_socket, size_of_header, chunk_prev_message)
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
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    pygame.init()
    display_surface = pygame.display.set_mode((disp_width, disp_height))
    pygame.display.set_caption(f"Remote Desktop")
    clock = pygame.time.Clock()
    display = True
    print("inside display data function")
    while display:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                status_list.put("stop")  
                pygame.quit()
                return
        jpeg_buffer = BytesIO(jpeg_list.get())
        img = Image.open(jpeg_buffer)
        py_image = pygame.image.frombuffer(img.tobytes(), img.size, img.mode)
        if resize:
            py_image = pygame.transform.scale(py_image, (disp_width, disp_height))
        jpeg_buffer.close()
        display_surface.blit(py_image, (0, 0))
        pygame.display.flip()
        clock.tick(60)
    
        
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
        connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("stop_capture", "utf-8"))
        print("inside cleaup display process")
        cleanup_process()


def compute_resolution(cli_width, cli_height, ser_width, ser_height):
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
    connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("start_capture", "utf-8"))
    print("Start message sent")
    disable_choice = messagebox.askyesno("Remote Box", "Disable remote device wallpaper?(yes,Turn black)")

    remote_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # remote display sockets
    remote_server_socket.connect((server_ip, 1234))
    
    connection_common.send_data(remote_server_socket, HEADER_COMMAND_SIZE, bytes(str(disable_choice), "utf-8"))
    print("\n")
    print(f">>Now you can CONTROL remote desktop")
    resize_option = False
    server_width, server_height = ImageGrab.grab().size
    client_resolution = connection_common.data_recive(remote_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
    print("Received client_resolution :", client_resolution)
    client_width, client_height = client_resolution.split(",")

    display_width, display_height = compute_resolution(int(client_width), int(client_height), server_width,
                                                                   server_height)
    try:
     client_width, client_height = client_resolution.split(",")
    except ValueError:
     client_width, client_height = 1920,1020 
        
    display_width, display_height = int(client_width), int(client_height)

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
    # access_button_frame.grid_forget()

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

                connection_common.send_data(command_server_socket, 2, server_password)
                connect_response = connection_common.data_recive(command_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
                print(connect_response, "connect_response")

                if connect_response != "1":
                    print("Wrong Password Entered...!")
                else:
                    password_entered_time = time.time()
                    # label_status.grid()
                    thread1 = Thread(target=listen_for_commands, daemon=True)
                    thread1.start()

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
                    # recv_chat_msg_thread = Thread(target=receive_message, name="recv_chat_msg_thread", daemon=True)
                    # recv_chat_msg_thread.start()
                    
                    
                    show_frame(frame2)
                    expiration_thread = Thread(target=check_password_expiration, daemon=True)
                    expiration_thread.start()
                    # disconnect_button.configure(state="normal")  # Enable

            except OSError as e:
                # label_status.grid_remove()
                print(e.strerror)
        else:
            print("Password is not 6 characters")

def is_password_expired():
    global command_server_socket,remote_server_socket,thread1,server_ip,file_server_socket,f_thread,chat_server_socket,password_entered_time
    if password_entered_time is not None:
        elapsed_time = time.time() - password_entered_time
        if elapsed_time >= 30 * 60: # 30min elapsed_time >= 30 * 60: # 30min
            messagebox.showinfo("Password Expired", "Your password has expired. Please login again.")
            # reset_ui()
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
    service_socket_list = [command_server_socket, remote_server_socket,file_server_socket]
    for sock in service_socket_list:
        if sock:
            sock.close()
    print("All Sockets are closed now")


def disconnect(btn_caller):
    if btn_caller == "button":
        result = messagebox.askquestion("Disconnect", "Are you sure you want to disconnect?")
        if result == 'yes':
            connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("disconnect", "utf-8"))
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
            message = connection_common.data_recive(command_server_socket, HEADER_COMMAND_SIZE, bytes(), 1024)[0].decode("utf-8")
            if message == "disconnect":
                listen = False
               
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        # label_status.grid_remove()
        disconnect("message")
        print("Thread automatically exit")

def file_path_listbox(event):
    listbox.insert(tk.END, event.data)

def send_files():
    # global listbox
    selected_indices = listbox.curselection()
    if selected_indices:
        files = [listbox.get(index) for index in selected_indices]
        print(f"Sending files: {files}")

        for file in files:
            print(file)

            # Send file data over the socket
           
            filename = os.path.basename(file)
            file_server_socket.send(filename.encode())

                # Send the file
            with open(file, "rb") as file:
                 while True:
                    data = file.read(1024)
                    if not data:
                        break
                    file_server_socket.send(data)
            print(f"File sent: {file}")

        print("All files sent.")
    else:
        print("No files selected.")
        messagebox.showwarning("No File Selected", "Please select at least one file to send.")
        
def browse_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        listbox.insert(tk.END, file_path)
        file_server_socket.send(file_path)

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
    
    connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("start_file_explorer", "utf-8"))
    select_file_process = Process(target=browse_file,  name="select_file_process", daemon=True)
    select_file_process.start()
    
    send_file_process = Thread(target=send_files, name="send_file_process", daemon=True)
    send_file_process.start()
    
    send_button = tk.Button(button_frame, text="Send Files", command=send_files ,compound=tk.TOP, bg="#8A8A8A", activebackground='#808080',activeforeground="white")
    send_button.pack(side=tk.LEFT, padx=0)

    browse_button = tk.Button(button_frame, text="Browse File", command=browse_file,compound=tk.TOP,bg="#8A8A8A", activebackground='#808080',activeforeground="white")
    browse_button.pack(side=tk.LEFT, padx=0)

    window_file.mainloop()
    
    
# def add_chat_display(msg, name):
#     text_chat_tab.configure(state=tk.NORMAL)
#     text_chat_tab.insert(tk.END, "\n")
#     text_chat_tab.insert(tk.END, name + ": " + msg)
#     text_chat_tab.configure(state="disabled")
       
#     if name == 'Me':
#         text_chat_tab.tag_configure("green", foreground="green")
#         text_chat_tab.insert(tk.END, "\n", "green")
#     else:
#         text_chat_tab.tag_configure("red", foreground="red")
#         text_chat_tab.insert(tk.END, "\n", "red")

# def send_message(event):
#     try:
#         msg = text_display.get()
#         if msg and msg.strip() != "":
#             text_display.delete(0, "end")
#             text_chat_tab.tag_configure("red", foreground="red")
#             connection_common.send_data(chat_server_socket, CHAT_HEADER_SIZE, bytes(msg, "utf-8"))
#             add_chat_display(msg, LOCAL_NAME)
#     except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
#         print(e.strerror)


# def receive_message():
#     try:
#         while True:
#             msg = connection_common.data_recive(chat_server_socket, CHAT_HEADER_SIZE, bytes())[0].decode("utf-8")
#             text_chat_tab.tag_configure("green", foreground="green")
#             add_chat_display(msg, REMOTE_NAME)
#     except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
#         print(e.strerror)
#     except ValueError:
#         pass



def remote_display_screen():
    global thread2, process1, process2, remote_server_socket 
    print("Send start message")
    connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("screen_sharing", "utf-8"))
    print("Start message sent")
    remote_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # remote display sockets
    remote_server_socket.connect((server_ip, 1234))
    print("\n")
    print(f">>Now you can SHARE SCREEN to remote desktop")
    resize_option = False
    server_width, server_height = ImageGrab.grab().size
    client_resolution = connection_common.data_recive(remote_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
    print("Received client_resolution :", client_resolution)
    client_width, client_height = client_resolution.split(",")

    display_width, display_height = compute_resolution(int(client_width), int(client_height), server_width,
                                                                   server_height)
    try:
     client_width, client_height = client_resolution.split(",")
    except ValueError:
     client_width, client_height = 1920,1020 

        
    display_width, display_height = int(client_width), int(client_height)

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
    # root.geometry('1900x1050')
    root.title("Remote Access Desktop Application")
    root.iconphoto(True,tk.PhotoImage(file='assets/images/img/m_logo.png'))
    # root.state('zoomed')
    root.resizable(False, False)

    # root.rowconfigure(0, weight=1)
    # root.columnconfigure(0, weight=1)

    frame1 = tk.Frame(root)
    frame2 = tk.Frame(root)
    frame3 = tk.Frame(root)
    frame4 = tk.Frame(root)
    frame5 = tk.Frame(root)


    for frame in (frame1, frame2, frame3,frame4, frame5):
        frame.grid(row=0,column=0,sticky='nsew')
        
    #==================Frame 1 code=======================
    # Set the background image
    # img = Image.open('assets/images/images/leone-venter-VieM9BdZKFo-unsplash.png')
    # resized_image = img.resize((1920, 1020), Image.LANCZOS)
    img = tk.PhotoImage(file='assets/images/images/leone-venter-VieM9BdZKFo-unsplash.png')
    # resized_image = img.resize((1920, 1020), Image.LANCZOS)

    # Convert the resized image to PhotoImage
    # new_image = ImageTk.PhotoImage(img)

    # Create a label with the new_image
    label = tk.Label(frame1, image=img, background='#f2f2f2')
    label.place(x=0, y=0, relwidth=1, relheight=1)

    logo_image = tk.PhotoImage(file='assets/images/img/multispan-logo.png')
    logo_label = tk.Label(frame1, image=logo_image, bg='#f2f2f2')
    logo_label.place(x=60, y=50)


    # left side 
    # Heading
    heading1_label = tk.Label(frame1, text='Provide help', font=('Rubik', 23, 'bold'), fg='black', bg='#f2f2f2')
    heading1_label.place(x=200,y=350)

    heading2_label = tk.Label(frame1, text='Remotely access and control.', font=('Rubik', 18, 'bold'), fg='black', bg='#f2f2f2')
    heading2_label.place(x=200,y=405)

    paragraph_label = tk.Label(frame1, text='''
    Sign in to TeamViewer Remote to view, control and
    access any device.
    ''', font=('Rubik', 13), fg='gray', bg='#f2f2f2', justify='left',padx=0,pady=0)
    paragraph_label.pack(anchor='w')
    paragraph_label.place(x=200,y=435)

    sign_in_btn = tk.Button(frame1,text='SIGN IN',width=13,height=2,bg='#28adff',fg='white', font=('Rubik', 12, 'bold'))
    sign_in_btn.pack()
    sign_in_btn.place(x=200,y=520)

    dont_have_account_text =  tk.Label(frame1, text="Don't have an account? ", font=('Rubik', 11), fg='gray', bg='#f2f2f2')
    dont_have_account_text.pack()
    dont_have_account_text.place(x=200,y=580)

    dont_have_account_text1 =  tk.Label(frame1, text="Create one here.", font=('Rubik', 11), fg='#28adff', bg='#f2f2f2')
    dont_have_account_text1.pack()
    dont_have_account_text1.place(x=357,y=580)


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

    # Create the input frame
    input_frame = tk.Frame(card_frame, padx=10, pady=10, bg='#f8f9f9')
    input_frame.pack()

    # Create the password label and entry
    IP_label = tk.Label(input_frame, text="IP:", font=('Rubik', 12), bg='#f8f9f9')
    IP_label.grid(row=0, column=0, sticky=tk.W)

    name_entry = tk.Entry(input_frame, font=('Rubik', 12))
    name_entry.grid(row=0, column=1, padx=10, pady=5)

    # Create the password label and entry
    password_label = tk.Label(input_frame, text="Password:", font=('Rubik', 12), bg='#f8f9f9')
    password_label.grid(row=1, column=0, sticky=tk.W)

    password_entry = tk.Entry(input_frame, font=('Rubik', 12), show="*")
    password_entry.grid(row=1, column=1, padx=10, pady=5)

    connect_button = tk.Button(input_frame, text="Connect", font=('Rubik', 10),bg='#28adff',fg='white')
    connect_button.grid(row=2, column=1, padx=5,sticky=tk.N)
    connect_button.configure(width=22,height=1)
    connect_button.config(command=login_to_connect)
    
    # disconnect_button = tk.Button(input_frame, text="Disconnect", font=('Rubik', 10),bg='#28adff',fg='white',command=lambda: disconnect("button"))
    # disconnect_button.grid(row=2, column=1, padx=5, sticky=tk.N)
    # disconnect_button.configure(width=22,height=1,state=tk.DISABLED)


    #==================Frame 2 code====================
    bg_img = tk.PhotoImage(file='assets/images/img/shubham-dhage-0aQ1lxP0wTs-unsplash.png')
    background = tk.Label(frame2, image=bg_img)
    background.place(x=0, y=0, relwidth=1, relheight=1)

    # Create the header frame
    header_frame = tk.Frame(frame2, bg="#2E2E2E")
    header_frame.place(x=0, y=0, width=800)
    header_frame.pack(fill="x")

    logo = tk.PhotoImage(file='assets/images/img/logo2.png')
    logo_img = tk.Label(header_frame, image=logo, bg="#2E2E2E")
    logo_img.pack(side="left", padx=10)

    # heder_text = Label(header_frame, text='Multispan', font=('Ubuntu Medium', 15, 'bold'), bg='#2E2E2E', fg='white')
    # heder_text.pack(side="left", padx=5)

    # Create a container frame for search elements
    search_container = tk.Frame(header_frame, bg="#2E2E2E")
    search_container.pack(padx=10, pady=10)

    # Create the search bar
    search_bar = tk.Entry(search_container, font=("Rubik", 14), width=50)
    search_bar.pack(side="left")

    # Create the search icon
    search_img = tk.PhotoImage(file='assets/images/img/icons8-search-48.png')
    search_icon = tk.Label(search_container, image=search_img, font=("Rubik", 14), bg="#2E2E2E")
    search_icon.pack(side="left", padx=5)

    user = tk.PhotoImage(file='assets/images/img/icons8-user-64.png')
    user_profile = tk.Label(search_container, image=user, bg="#2E2E2E")
    user_profile.pack()

    # Create the sidebar frame
    sidebar_frame = tk.Frame(frame2, bg="#8A8A8A", width=200)
    sidebar_frame.pack(fill="y", side="left")

    # Create the sidebar content
    home_img = tk.PhotoImage(file='assets/images/img/icons8-home-50.png')
    home_icon = tk.Label(sidebar_frame, image=home_img, font=("Rubik", 16), bg="#8A8A8A")
    home_icon.pack(padx=10, pady=10)

    file_img = tk.PhotoImage(file='assets/images/img/icons8-downlod-64.png')
    file_icon = tk.Label(sidebar_frame, image=file_img, font=("Rubik", 16), bg="#8A8A8A")
    file_icon.pack(padx=10, pady=10)

    logout = tk.Button(sidebar_frame,text="Logout", font=("Rubik", 10), bg="#8A8A8A",fg='black')
    logout.config(command=lambda:show_frame(frame1))
    logout.pack()

    back_btn = tk.Button(sidebar_frame,text="Back", font=("Rubik", 10), bg="#8A8A8A",fg='black')
    back_btn.config(command=lambda:show_frame(frame1))
    back_btn.pack()

    # Create the content frame
    content_frame = tk.Frame(frame2, bg="black",width=600)
    content_frame.pack(expand=True)
    # content_frame.place(x=600, y=300)

    # Create the grid frames
    grid_frame = tk.Frame(content_frame, bg="black", padx=10, pady=10)
    grid_frame.pack(side="left")

    grid_frame1 = tk.Frame(content_frame,bg='black', padx=0, pady=10)
    grid_frame1.pack(side="left")

    label = tk.Label(grid_frame1, text='Remote Actions', font=('Rubik', 14, 'bold'), bg='black',fg='white')
    label.grid(row=0, column=0, columnspan=2, pady=10)

    # Create the card labels
    card1 = tk.Button(grid_frame1,bg='black',fg='white', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    card1.config(compound=tk.TOP, bd=0, command=remote_display)
    card2 = tk.Button(grid_frame1,bg='black',fg='white', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    card2.config(compound=tk.TOP, bd=0,command=remote_display_screen)
    card3 = tk.Button(grid_frame1,bg='black',fg='white', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    # card3.config(command=lambda:show_frame(frame5))
    card3.config(command=ui_file)
    card4 = tk.Button(grid_frame1,bg='black',fg='white', width=54, height=54,relief='flat', borderwidth=0, activebackground='#171717')
    card4.config(command=lambda:show_frame(frame3))

    # Load the icon images
    icon1 = tk.PhotoImage(file="assets/images/img/icons8-remote-desktop-48.png")
    icon2 = tk.PhotoImage(file="assets/images/img/icons8-screen-share-64.png")
    icon3 = tk.PhotoImage(file="assets/images/img/icons8-downloads-folder-94.png")
    icon4 = tk.PhotoImage(file="assets/images/img/icons8-chat-94.png")

    # Set the icons for each card
    card1.config(image=icon1)
    card2.config(image=icon2)
    card3.config(image=icon3)
    card4.config(image=icon4)

    # Add text labels below the icons

    text1 = tk.Label(grid_frame1, text="Remote Access", font=('Rubik', 12, 'bold'), bg='black',fg='white')
    sub_text1 = tk.Label(grid_frame1, text="""Set up for Remote
    desktop control""", font=('Rubik', 10),bg='black',fg='#8A8A8A', pady=1,justify= tk.LEFT)

    text2 = tk.Label(grid_frame1, text="Screen Share", font=('Rubik', 12, 'bold'),bg='black',fg='white')
    sub_text2 = tk.Label(grid_frame1, text="""Start with sharing
    your screen""", font=('Rubik', 10),bg='black',fg='#8A8A8A', pady=1,justify= tk.LEFT)

    text3 = tk.Label(grid_frame1, text="File Transfer", font=('Rubik', 12, 'bold'),bg='black',fg='white')
    sub_text3 = tk.Label(grid_frame1, text="""Transfer files""", font=('Rubik', 10),bg='black',fg='#8A8A8A', pady=1,justify= tk.LEFT)

    text4 = tk.Label(grid_frame1, text="Chat", font=('Rubik', 12, 'bold'),bg='black',fg='white')
    sub_text4 = tk.Label(grid_frame1, text="""Start chat with your
    loved ones""", font=('Rubik', 10),bg='black',fg='#8A8A8A', pady=1,justify= tk.LEFT)


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

    heading_text = tk.Label(grid_frame, text='Start Your Journey With Us', font=('Rubik', 25,'bold'),bg='black',fg='white')
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
    """, font=('Rubik', 11),bg='black',fg='#8A8A8A',justify= tk.LEFT).pack()
    
    show_frame(frame1)

    root.mainloop()