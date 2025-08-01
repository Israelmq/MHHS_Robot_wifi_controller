import network
import socket
import time
from machine import Pin, PWM

# == Wi-Fi Credentials ==
secrets = {'ssid':'Starlink_MHHS', 'password' : 'CLMLONDON2025@'}

# ==== Motor Setup ====
ENA = PWM(Pin(14))
ENB = PWM(Pin(15))
ENA.freq(1000)
ENB.freq(1000)
ENA.duty_u16(40000)  # ~60% speed

IN1 = Pin(10, Pin.OUT)
IN2 = Pin(11, Pin.OUT)
IN3 = Pin(12, Pin.OUT)
IN4 = Pin(13, Pin.OUT)

speed = 50000  # default speed
logged_in = False

def set_speed(val):
    ENA.duty_u16(val)
    ENB.duty_u16(val)

def stop(): IN1.low(); IN2.low(); IN3.low(); IN4.low(); set_speed(0)
def forward(): IN1.high(); IN2.low(); IN3.high(); IN4.low(); set_speed(speed)
def backward(): IN1.low(); IN2.high(); IN3.low(); IN4.high(); set_speed(speed)
def left(): IN1.low(); IN2.high(); IN3.high(); IN4.low(); set_speed(speed)
def right(): IN1.high(); IN2.low(); IN3.low(); IN4.high(); set_speed(speed)

# ==== Wi-Fi Setup ====
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(secrets['ssid'], secrets['password'])
        while not wlan.isconnected():
            time.sleep(1)
    print("Connected. IP:", wlan.ifconfig()[0])
    return wlan

wlan = connect_wifi()

# ==== Login Credentials ====
username = "admin"
password = "pico123"
logged_in = False

# ==== HTML Templates ====
def login_page():
    return """<!DOCTYPE html><html>
<head><title>Login</title></head>
<body style="text-align:center;font-family:sans-serif;background:#202830;color:white;">
    <h2>🔐 Enter Login to Control Robot</h2>
    <form action="/login" method="get">
        Username: <input name="user"><br><br>
        Password: <input name="pass" type="password"><br><br>
        <input type="submit" value="Login">
    </form>
</body></html>"""

def control_page():
    return f"""<!DOCTYPE html><html>
<head><title>Robot Car</title>
<style>
body {{
  background-image: url('https://i.imgur.com/trZOwBx.png');
  background-size: cover;
  text-align: center;
  font-family: sans-serif;
  color: white;
  padding-top: 50px;
}}
.btn {{
  padding: 15px 30px;
  margin: 10px;
  font-size: 18px;
  border-radius: 10px;
  background: #28a745;
  border: none;
  color: white;
  cursor: pointer;
  transition: 0.3s;
}}
.btn:hover {{
  background: #1e7e34;
  transform: scale(1.1);
}}
.voice-btn {{
  background-color: #ffc107;
  color: black;
}}
</style>
</head>
<body>
  <h1>🚗 Secure Robot Control</h1>
  <a href="/forward"><button class="btn">Forward</button></a><br>
  <a href="/left"><button class="btn">Left</button></a>
  <a href="/stop"><button class="btn">Stop</button></a>
  <a href="/right"><button class="btn">Right</button></a><br>
  <a href="/backward"><button class="btn">Backward</button></a><br>
  <a href="/faster"><button class="btn">Faster</button></a>
  <a href="/slower"><button class="btn">Slower</button></a><br><br>
  <a href="/logout"><button class="btn" style="background:#dc3545;">Logout</button></a><br><br>

  <button onclick="startVoice()" class="btn voice-btn">🎤 Voice Command</button>

  <script>
    function sendCommand(cmd) {{
        fetch('/' + cmd)
            .then(response => response.text())
            .then(data => console.log('Command sent:', cmd));
    }}

    function startVoice() {{
        if (!('webkitSpeechRecognition' in window)) {{
            alert("Voice recognition not supported.");
            return;
        }}
        const recognition = new webkitSpeechRecognition();
        recognition.lang = "en-US";
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onresult = function(event) {{
            const command = event.results[0][0].transcript.toLowerCase();
            console.log("Heard:", command);
            if (command.includes("forward")) sendCommand("forward");
            else if (command.includes("backward")) sendCommand("backward");
            else if (command.includes("left")) sendCommand("left");
            else if (command.includes("right")) sendCommand("right");
            else if (command.includes("stop")) sendCommand("stop");
            else alert("Unknown command: " + command);
        }};
        recognition.onerror = function(e) {{
            alert("Speech error: " + e.error);
        }};
        recognition.start();
    }}
  </script>
</body></html>"""

# ==== Web Server ====
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
server = socket.socket()
server.bind(addr)
server.listen(1)

print("Server running at:", wlan.ifconfig()[0])

while True:
    if not wlan.isconnected():
        print("Wi-Fi disconnected! Reconnecting...")
        wlan = connect_wifi()

    conn, addr = server.accept()
    request = conn.recv(1024).decode()
    print("Request:", request)

    if "GET /login?" in request:
        user = passwd = ""
        try:
            data = request.split("GET /login?")[1].split(" ")[0]
            params = data.split("&")
            for p in params:
                if "user=" in p: user = p.split("=")[1]
                if "pass=" in p: passwd = p.split("=")[1]
        except: pass
        if user == username and passwd == password:
            logged_in = True
            response = control_page()
        else:
            response = login_page()

    elif "/logout" in request:
        logged_in = False
        response = login_page()

    elif not logged_in:
        response = login_page()

    else:
        if "/forward" in request:
            forward()
        elif "/backward" in request:
            backward()
        elif "/left" in request:
            left()
        elif "/right" in request:
            right()
        elif "/stop" in request:
            stop()
        elif "/faster" in request:
            speed = min(65535, speed + 10000)
            set_speed(speed)
        elif "/slower" in request:
            speed = max(15000, speed - 10000)
            set_speed(speed)
        response = control_page()

    conn.send("HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n")
    conn.send(response)
    conn.close()
