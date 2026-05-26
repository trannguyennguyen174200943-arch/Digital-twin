/**
 * ESP32 — IMU + Flex + WS uplink + Haptic downlink + Safety
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

#include "config.h"
#include "haptic_control.h"
#include "safety_layer.h"
#include "sensor_fusion.h"

WebSocketsClient webSocket;

unsigned long lastUplinkMs = 0;
unsigned long lastWifiRetryMs = 0;
unsigned long lastWsRetryMs = 0;
bool wsConnected = false;

void connectWiFi();
void connectWebSocket();
void sendSensorUplink();
void sendEmergencyUplink();
void handleDownlinkJson(const char* payload, size_t length);
void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length);

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println(F("\n[BOOT] Rehab ESP32 — Haptic + Safety"));

  safetyBegin();
  hapticBegin();
  sensorFusionBegin();
  connectWiFi();
  connectWebSocket();
}

void loop() {
  const unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    wsConnected = false;
    hapticEmergencyCut();
    if (now - lastWifiRetryMs >= WIFI_RECONNECT_MS) {
      lastWifiRetryMs = now;
      connectWiFi();
    }
    return;
  }

  webSocket.loop();

  const bool fused = sensorFusionStep();
  const float angle = sensorFusionAngleDeg();
  const int flex = sensorFusionRawFlex();

  if (fused) {
    const uint64_t nowUs = micros();
    static uint64_t lastPidUs = nowUs;
    const float dt = (nowUs - lastPidUs) * 1e-6f;
    lastPidUs = nowUs;
    if (dt > 0.0f && dt <= SENSOR_MAX_DT_SEC) {
      hapticControlTick(dt, angle, flex);
    }
  }

  if (safetyConsumeEmergencyNotify() && wsConnected) {
    sendEmergencyUplink();
  }

  if (!wsConnected && (now - lastWsRetryMs >= WS_RECONNECT_MS)) {
    lastWsRetryMs = now;
    connectWebSocket();
  }

  if (wsConnected && (now - lastUplinkMs >= UPLINK_INTERVAL_MS)) {
    lastUplinkMs = now;
    sendSensorUplink();
  }
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  const uint32_t timeout = millis() + 15000;
  while (WiFi.status() != WL_CONNECTED && millis() < timeout) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print(F("[WiFi] OK, IP="));
    Serial.println(WiFi.localIP());
  }
}

void connectWebSocket() {
  webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
  webSocket.onEvent(onWebSocketEvent);
  webSocket.setReconnectInterval(WS_RECONNECT_MS);
  webSocket.enableHeartbeat(15000, 3000, 2);
}

void sendSensorUplink() {
  const FusionState st = sensorFusionSnapshot();

  JsonDocument doc;
  doc["angle"] = st.angle;
  doc["raw_flex"] = st.rawFlex;
  doc["timestamp"] = millis();

  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);
}

void sendEmergencyUplink() {
  JsonDocument doc;
  doc["status"] = "EMERGENCY_STOP";
  doc["timestamp"] = millis();
  doc["angle"] = sensorFusionAngleDeg();

  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);
  Serial.println(F("[WS] EMERGENCY_STOP sent"));
}

/**
 * Downlink hot path — không Serial, không String, parse tối thiểu.
 */
void handleDownlinkJson(const char* payload, size_t length) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, length)) {
    return;
  }

  if (!doc["force_level"].is<int>()) {
    return;
  }

  const int force = doc["force_level"].as<int>();
  int direction = 1;
  if (doc["direction"].is<int>()) {
    direction = doc["direction"].as<int>();
  }

  const float angle = sensorFusionAngleDeg();
  const int flex = sensorFusionRawFlex();

  hapticOnDownlink(static_cast<uint8_t>(force), static_cast<int8_t>(direction), angle, flex);
}

void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      wsConnected = false;
      hapticEmergencyCut();
      Serial.println(F("[WS] Disconnected"));
      break;

    case WStype_CONNECTED:
      wsConnected = true;
      safetyClearLatch();
      sensorFusionReset();
      Serial.printf("[WS] Connected to %s:%d%s\n", WS_HOST, WS_PORT, WS_PATH);
      break;

    case WStype_TEXT:
      handleDownlinkJson(reinterpret_cast<const char*>(payload), length);
      break;

    case WStype_ERROR:
      hapticEmergencyCut();
      break;

    default:
      break;
  }
}
