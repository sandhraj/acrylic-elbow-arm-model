/*
  Motorised elbow model (muscles & joints)
  Author: Sandheep Rajendran  ·  License: MIT

  Board: ESP8266 (NodeMCU / Wemos D1 mini), Arduino IDE with the ESP8266 core.
  One MG90S driven directly from a GPIO; no servo driver board needed.

  Controls
    MOVE knob  (10k pot on A0)    : arm follows the knob
    DEMO button (D6 to GND)       : slow biceps curls on/off
    Phone (optional)              : join Wi-Fi "ElbowArm" (password elbow123),
                                    open http://192.168.4.1 for a slider + demo button.
                                    Turning the knob takes control back.

  Wiring (NodeMCU labels)
    Servo orange (signal) -> D5 (GPIO14)
    Servo red (+)         -> VIN  (5 V from USB)
    Servo brown (-)       -> GND
    Pot outer legs        -> 3V3 and GND   (NOT 5 V: A0 takes 0-3.3 V on NodeMCU)
    Pot middle (wiper)    -> A0
    Button                -> D6 (GPIO12) and GND (internal pull-up)
    470 uF capacitor      -> across VIN and GND (+ leg to VIN), recommended

  Calibrate first: with the arm hanging straight, the shoulder horn must be exactly
  parallel to the elbow horn (front end pointing down-front, about 25 deg off vertical).
  Nudge REST_DEG a few degrees until it is, THEN tie the cords.
*/
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

const int SERVO_PIN  = D5;
const int POT_PIN    = A0;
const int BUTTON_PIN = D6;

const int  REST_DEG  = 25;    // servo angle with the arm straight; fine-tune so the horns are parallel
const int  RANGE_DEG = 130;   // servo travel = elbow travel (1:1). Never above 150.
const bool REVERSE   = false; // set true if the arm bends the wrong way

// MG90S pulse range. Set explicitly: the ESP8266 core's default (1000-2000 us) gives only ~90 deg.
const int PULSE_MIN_US = 500;
const int PULSE_MAX_US = 2400;

const bool  WIFI_ON   = true;           // set false to skip the phone control page
const char* AP_SSID   = "ElbowArm";
const char* AP_PASS   = "elbow123";     // at least 8 characters

Servo servo;
ESP8266WebServer web(80);

enum Mode { KNOB, DEMO, PHONE };
Mode  mode     = KNOB;
float current  = 0;      // 0 = straight, 1 = fully bent
float phoneTarget = 0;
int   lastPot  = -1;

void writeArm(float f) {
  f = constrain(f, 0.0f, 1.0f);
  int deg = REST_DEG + (int)(f * RANGE_DEG);
  if (REVERSE) deg = 180 - deg;
  servo.write(deg);
}

bool buttonPressed() {
  static bool last = HIGH;
  static unsigned long t = 0;
  bool now = digitalRead(BUTTON_PIN);
  bool pressed = (last == HIGH && now == LOW && millis() - t > 200);
  if (pressed) t = millis();
  last = now;
  return pressed;
}

void service() {                          // keep Wi-Fi and the button alive during slow moves
  if (WIFI_ON) web.handleClient();
  if (buttonPressed()) {
    mode = (mode == DEMO) ? KNOB : DEMO;
    Serial.println(mode == DEMO ? "DEMO on" : "Knob control");
  }
  yield();
}

// ease to a target so it moves like a muscle; returns false if the mode changed mid-move
bool moveSmooth(float target, int ms) {
  Mode startMode = mode;
  float start = current;
  int steps = ms / 15;
  for (int i = 1; i <= steps; i++) {
    float t = (float)i / steps;
    float e = 0.5f - 0.5f * cos(t * PI);
    current = start + (target - start) * e;
    writeArm(current);
    unsigned long until = millis() + 15;
    while (millis() < until) service();
    if (mode != startMode) return false;
  }
  return true;
}

const char PAGE[] PROGMEM = R"HTML(<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<title>Elbow arm</title><style>body{font-family:sans-serif;text-align:center;margin:2em}
input{width:90%}button{font-size:1.2em;padding:.6em 1.2em;margin:1em}</style></head><body>
<h2>Elbow arm</h2><p>Straight &larr; slider &rarr; Bent</p>
<input type=range min=0 max=100 value=0 oninput="fetch('/set?v='+this.value)">
<br><button onclick="fetch('/demo')">Demo curls on/off</button>
<p>Biceps contracts = elbow bends (flexion)<br>Triceps contracts = elbow straightens (extension)</p>
</body></html>)HTML";

void setupWeb() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  web.on("/", []() { web.send_P(200, "text/html", PAGE); });
  web.on("/set", []() {
    phoneTarget = constrain(web.arg("v").toInt(), 0, 100) / 100.0f;
    mode = PHONE;
    web.send(200, "text/plain", "ok");
  });
  web.on("/demo", []() {
    mode = (mode == DEMO) ? KNOB : DEMO;
    web.send(200, "text/plain", mode == DEMO ? "demo" : "knob");
  });
  web.begin();
  Serial.print("Wi-Fi: join "); Serial.print(AP_SSID); Serial.println(", open http://192.168.4.1");
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  servo.attach(SERVO_PIN, PULSE_MIN_US, PULSE_MAX_US);
  writeArm(0);
  if (WIFI_ON) setupWeb();
  Serial.println("Knob = move the arm. Button = demo curls on/off.");
}

void loop() {
  service();
  int pot = analogRead(POT_PIN);                  // 0..1023
  if (lastPot < 0) lastPot = pot;
  if (mode == PHONE && abs(pot - lastPot) > 40) mode = KNOB;   // knob takes control back
  lastPot = pot;

  if (mode == DEMO) {
    Serial.println("BICEPS contracts, TRICEPS relaxes -> elbow bends (flexion)");
    if (!moveSmooth(1.0f, 1400)) return;
    unsigned long until = millis() + 600; while (millis() < until) service();
    if (mode != DEMO) return;
    Serial.println("TRICEPS contracts, BICEPS relaxes -> elbow straightens (extension)");
    if (!moveSmooth(0.0f, 1400)) return;
    until = millis() + 800; while (millis() < until) service();
  } else {
    float target = (mode == PHONE) ? phoneTarget : pot / 1023.0f;
    current += (target - current) * 0.15f;        // smooth like a muscle
    writeArm(current);
    unsigned long until = millis() + 15; while (millis() < until) service();
  }
}
