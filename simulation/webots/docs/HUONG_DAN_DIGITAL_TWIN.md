# Digital Twin Webots — Hướng dẫn thao tác (không cần Blender)

## A. Tạo cánh tay / ngón tay từ khối có sẵn (15–30 phút)

### Bước 1 — Mở project
1. Webots → **File → Open World** → chọn `simulation/webots/worlds/rehab_twin.wbt`
2. Đặt **project root** = thư mục `simulation/webots` (File → Open Directory) để Webots tìm được controller.

### Bước 2 — Thêm Robot
1. Scene tree → chuột phải **WORLD** → **Add Node** → tìm **Robot** → OK  
2. Chọn Robot → trong Panel bên phải đặt **controller** = `rehab_digital_twin`

### Bước 3 — Thêm khớp gập (HingeJoint)
1. Chuột phải **Robot** → **Add Node** → **HingeJoint**
2. Mở cây **HingeJoint → jointParameters**:
   - **axis** `0 0 1` (quay quanh trục Z) hoặc `0 1 0` tùy hướng lắp
   - **anchor** = điểm bản lề (ví dụ `0 0 0.05`)
3. Trong **HingeJoint → device** (Add):
   - **RotationalMotor** → đặt **name** = `joint_motor` (trùng code)
   - **PositionSensor** → **name** = `joint_sensor`

### Bước 4 — “Xương” và ngón (Solid + hình học có sẵn)
1. Chuột phải **HingeJoint → endPoint** → **Add** → **Solid**
2. Trong Solid → **children** → **Shape** → **geometry** → chọn **Box** hoặc **Capsule**
3. Kéo **translation** để đặt cạnh vào khớp (ví dụ `0.12 0 0`)
4. **boundingObject**: copy cùng geometry (bắt buộc cho va chạm)
5. **physics**: bật **Physics** (mass ~0.05–0.1)

### Bước 5 — Cảm biến chạm (va chạm → haptic)
1. Chuột phải Solid đầu ngón → **Add** → **TouchSensor**
2. **name** = `finger_touch`, **type** = `bumper`
3. Thêm **Shape** con (Sphere nhỏ) để nhìn thấy đầu ngón

### Bước 6 — Vật thử va chạm
1. Add **Solid** + **Sphere** đỏ (đã có trong `rehab_twin.wbt`)
2. Bật **physics** + **boundingObject**

### Bước 7 — Chạy thử
1. Khởi động FastAPI + ESP32 (uplink góc)
2. Webots → **Play** (▶)
3. Console controller: `Twin WS connected`

### Mở rộng 2 khớp (ngón PIP + MCP)
- Thêm **HingeJoint** thứ hai **bên trong** endPoint khớp 1
- Motor: `joint_motor_2`
- Trong `twin_config.py` thêm tên motor (xem file cấu hình)

---

## B. Import mô hình .OBJ / .FBX từ Internet

### Chuẩn bị file
- Ưu tiên **.obj** (+ file .mtl nếu có) — Webots import ổn định nhất
- **.fbx** cần Webots bản mới; nếu lỗi → chuyển sang OBJ bằng tool online (không cần Blender cài máy)

### Bước 1 — Import vào Webots
1. **File → Import 3D Model…** (hoặc kéo thả vào Scene)
2. Chọn file `.obj` / `.fbx`
3. Webots tạo **Solid** (hoặc nhiều Solid con) — đừng gắn motor ngay

### Bước 2 — Tách thành từng đoạn xương
1. Nếu model là **một khối**: duplicate thành 2–3 **Solid** (cánh tay trên / cẳng / ngón)
2. Hoặc dùng **CadShape** trên từng Solid:
   - Field **url** trỏ tới `models/arm_upper.obj`, `models/forearm.obj`…

### Bước 3 — Gắn khớp (quan trọng)
Cấu trúc cây đúng:

```
Robot
 └── HingeJoint          ← khớp vai/khuỷu
      └── Solid (cẳng)
           └── HingeJoint ← khớp khuỷu
                └── Solid (bàn tay)
                     └── HingeJoint ← khớp ngón
                          └── Solid (ngón) + TouchSensor
```

Thao tác UI:
1. Kéo **Solid** “cẳng” vào **endPoint** của HingeJoint 1
2. Gắn HingeJoint 2 làm con của Solid cẳng (Add Node trên Solid)
3. Mỗi HingeJoint có **RotationalMotor** riêng, **name** duy nhất

### Bước 4 — Căn trục quay (axis / anchor)
1. Chọn **jointParameters** → bật hiển thị trục trong Scene
2. Xoay **axis** để trục đi qua bản lề thật của model
3. **anchor** = tọa độ bản lề trong hệ tọa độ Solid cha
4. Thử **Play** + kéo **joint** slider trong Scene (manual) để kiểm tra không xoắn mesh

### Bước 5 — Giới hạn góc motor
Trên **RotationalMotor**:
- `minPosition` / `maxPosition` (radian) — ví dụ ngón: 0 → 1.57 (90°)

### Bước 6 — Liên kết controller
1. Sửa `controllers/rehab_digital_twin/twin_config.py` — liệt kê tên motor
2. Gán **controller** = `rehab_digital_twin` trên Robot

---

## C. Chạy hệ thống đầy đủ

| Thứ tự | Thành phần | Việc cần làm |
|--------|-----------|--------------|
| 1 | FastAPI | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| 2 | ESP32 | Wi-Fi + `ws://IP:8000/ws/device?patient_id=P001` |
| 3 | Webots | Play world, controller kết nối `ws://IP:8000/ws/twin` |
| 4 | Dashboard | `http://IP:8000/dashboard/` |

Biến môi trường (tùy chọn):

```bat
set REHAB_WS_HOST=192.168.1.100
set REHAB_WS_PORT=8000
```

Cài Python cho Webots:

```bat
pip install websocket-client
```

---

## D. Xử lý lỗi thường gặp

| Triệu chứng | Cách sửa |
|-------------|----------|
| Robot đứng im | Kiểm tra tên motor = `joint_motor`; ESP32 có uplink? |
| Giật lag | Giảm `SMOOTH_TAU_SEC` trong `twin_config.py` hoặc tăng `maxVelocity` motor |
| Không va chạm | Thiếu `boundingObject` / `physics` trên Solid |
| WS lỗi | Đúng IP LAN; tắt firewall cổng 8000 |
